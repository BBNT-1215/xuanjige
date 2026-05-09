#!/usr/bin/env python3
"""
Hermestrix Engine - 机研常驻进程 (JiyanAgent)

职责：
  1. 监听 event_bus 事件（任务完成/流转/失败）
  2. 定时健康检查（每60秒）
  3. 定时衰减管理（每30分钟）
  4. 定时进化验证检查（每5分钟）
  5. 异常时告警（通过 event_bus emit）

用法：
  python3 engine/jiyan_agent.py [--once] [--interval <seconds>]
  --once    : 运行一次处理后退出（用于测试）
  --verbose : 输出详细日志
"""

import argparse
import os
import sys
import time
import json
import threading
import signal
import pathlib
from datetime import datetime, timezone
from typing import Optional

# HERMESTRIX_HOME setup
_FILE = pathlib.Path(__file__).resolve()
HERMESTRIX_HOME = pathlib.Path(os.environ.get("HERMESTRIX_HOME", _FILE.parent.parent))
sys.path.insert(0, str(HERMESTRIX_HOME))

from engine.evolution import EvolutionEngine
from engine.memory_manager import MemoryManager, TaskRecord
from engine.health_monitor import HealthMonitor
from engine.decay_service import DecayService

DATA_DIR = HERMESTRIX_HOME / "data"
EVENTS_FILE = DATA_DIR / "events.json"
SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
AGENT_PID_FILE = DATA_DIR / "jiyan_agent.pid"

# 事件类型常量
EVT_TASK_COMPLETED = "task.completed"
EVT_TASK_FAILED = "task.failed"
EVT_TASK_CREATED = "task.created"
EVT_TASK_FLOWED = "task.flowed"

# ============================================================
# 事件总线客户端（polling 模式）
# ============================================================

class EventBusClient:
    """事件总线轮询客户端"""

    def __init__(self):
        self.subscriptions: dict[str, dict] = {}
        self.last_event_id: str = ""
        self._load_subscriptions()

    def _load_subscriptions(self):
        data = self._read_json(SUBSCRIPTIONS_FILE)
        if data:
            self.subscriptions = data.get("subscriptions", {})

    def _read_json(self, path: pathlib.Path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def poll_new_events(self, since_id: str = "") -> list[dict]:
        """拉取自 last_event_id 后的新事件"""
        data = self._read_json(EVENTS_FILE)
        if not data or "events" not in data:
            return []

        events = data["events"]
        new_events = []
        found = since_id == ""

        for evt in reversed(events):
            if evt.get("id") == since_id:
                found = True
                break
            if found:
                new_events.append(evt)

        return list(reversed(new_events))

    def emit(self, event_type: str, payload: dict) -> bool:
        """发送事件到总线"""
        event = {
            "id": f"{int(time.time() * 1000)}",
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "jiyan_agent",
        }
        _atomic_json_update(EVENTS_FILE, lambda d: {
            "events": (d.get("events", []) if isinstance(d, dict) else []) + [event]
        }, default={"events": [event]})
        return True

    def subscribe(self, event_type: str, handler: callable):
        """注册订阅（内存中）"""
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = {"handlers": []}
        self.subscriptions[event_type]["handlers"].append(handler)


def _atomic_json_update(path: pathlib.Path, modifier, default=None):
    for attempt in range(3):
        try:
            data = None
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    data = None
            data = modifier(data) if data is not None else modifier(default)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, path)
            return
        except Exception as e:
            if attempt == 2:
                print(f"[jiyan_agent] Failed to update {path}: {e}")
            time.sleep(0.1)


# ============================================================
# 机研常驻进程主类
# ============================================================

class JiyanAgent:
    """
    机研常驻进程

    三大循环：
    - 事件循环：监听任务事件，触发进化
    - 健康循环：定时系统健康检查
    - 衰减循环：定时记忆衰减管理
    """

    DEFAULT_HEALTH_INTERVAL = 60     # 健康检查间隔（秒）
    DEFAULT_DECAY_INTERVAL = 1800    # 衰减管理间隔（30分钟）
    DEFAULT_EVOLUTION_INTERVAL = 300  # 进化验证检查间隔（5分钟）
    DEFAULT_POLL_INTERVAL = 5        # 事件轮询间隔（秒）

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.running = False
        self._shutdown = threading.Event()

        # 核心引擎
        self.evolution = EvolutionEngine()
        self.memory = self.evolution.memory
        self.health = self.evolution.health
        self.decay = self.evolution.decay

        # 事件客户端
        self.eb = EventBusClient()

        # 定时器状态
        self._last_health_check = 0
        self._last_decay_run = 0
        self._last_evolution_check = 0
        self._last_event_id = ""

        # 统计
        self._stats = {
            "events_processed": 0,
            "tasks_evolved": 0,
            "health_alerts": 0,
            "decay_runs": 0,
            "evolution_verifications": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        self._register_handlers()

    def _register_handlers(self):
        """注册事件处理器"""
        self.eb.subscribe(EVT_TASK_COMPLETED, self._on_task_completed)
        self.eb.subscribe(EVT_TASK_FAILED, self._on_task_failed)

    def _on_task_completed(self, event: dict):
        """处理任务完成事件"""
        payload = event.get("payload", {})
        task_id = payload.get("task_id", "unknown")
        self._log(f"任务完成事件: {task_id}")

        # 如果事件携带了完整任务记录，直接处理
        if "task_record" in payload:
            try:
                record = TaskRecord.from_dict(payload["task_record"])
                result = self.evolution.on_task_completed(record)
                self._stats["tasks_evolved"] += 1
                self._log(f"  进化完成: {task_id}, new_score={result['skill_updates']}")
                return
            except Exception as e:
                self._log(f"  进化处理失败: {e}")

        # 否则仅记录已完成
        self._stats["events_processed"] += 1

    def _on_task_failed(self, event: dict):
        """处理任务失败事件"""
        payload = event.get("payload", {})
        task_id = payload.get("task_id", "unknown")
        self._log(f"任务失败事件: {task_id}")

        if "task_record" in payload:
            try:
                record = TaskRecord.from_dict(payload["task_record"])
                self.evolution.on_task_failed(record)
                self._stats["tasks_evolved"] += 1
            except Exception as e:
                self._log(f"  失败处理失败: {e}")

        self._stats["events_processed"] += 1

    def _log(self, msg: str):
        if self.verbose:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] [jiyan_agent] {msg}")

    # ============================================================
    # 事件循环
    # ============================================================

    def _event_loop(self):
        """事件轮询循环"""
        while self.running and not self._shutdown.is_set():
            try:
                new_events = self.eb.poll_new_events(self._last_event_id)
                if new_events:
                    self._last_event_id = new_events[-1].get("id", self._last_event_id)
                    for evt in new_events:
                        evt_type = evt.get("type", "")
                        handlers = self.eb.subscriptions.get(evt_type, {}).get("handlers", [])
                        for h in handlers:
                            try:
                                h(evt)
                            except Exception as e:
                                print(f"[jiyan_agent] Handler error for {evt_type}: {e}")
                        self._stats["events_processed"] += 1
            except Exception as e:
                print(f"[jiyan_agent] Event loop error: {e}")

            self._shutdown.wait(timeout=self.DEFAULT_POLL_INTERVAL)

    # ============================================================
    # 健康检查循环
    # ============================================================

    def _health_loop(self):
        """定时健康检查"""
        while self.running and not self._shutdown.is_set():
            self._shutdown.wait(timeout=self.DEFAULT_HEALTH_INTERVAL)
            if not self.running:
                break

            try:
                report = self.health.check_all()
                if report.alerts:
                    self._stats["health_alerts"] += len(report.alerts)
                    for alert in report.alerts:
                        self._log(f"[HEALTH ALERT] {alert['level']}: {alert['message']}")
                        # 发出告警事件
                        self.eb.emit("health.alert", {
                            "alert": alert,
                            "report": report.to_dict() if hasattr(report, "to_dict") else str(report),
                        })
                elif self.verbose:
                    self._log(f"[HEALTH OK] overall={report.overall}")
            except Exception as e:
                print(f"[jiyan_agent] Health check error: {e}")

    # ============================================================
    # 衰减管理循环
    # ============================================================

    def _decay_loop(self):
        """定时衰减管理"""
        while self.running and not self._shutdown.is_set():
            self._shutdown.wait(timeout=self.DEFAULT_DECAY_INTERVAL)
            if not self.running:
                break

            try:
                result = self.decay.run_decay_cycle()
                self._stats["decay_runs"] += 1
                archived = result.get("archived_to_cold", 0)
                if archived > 0 or self.verbose:
                    self._log(f"[DECAY] cold_archive={archived}, deleted={result.get('deleted', 0)}")
            except Exception as e:
                print(f"[jiyan_agent] Decay error: {e}")

    # ============================================================
    # 进化验证循环
    # ============================================================

    def _evolution_loop(self):
        """定时进化验证检查"""
        pending = self.evolution.verifier.get_pending_list()
        if pending:
            self._log(f"[EVOLUTION] {len(pending)} pending verifications: {pending}")

        # 检查 pending 验证超期（超过1小时未确认，强制回滚）
        for p in pending:
            skill_id = p["skill_id"]
            # pending 结构：skill_id, new_score, observations, required
            pending_info = self.evolution.verifier.pending.get(skill_id)
            if pending_info:
                introduced_at = datetime.fromisoformat(pending_info["introduced_at"])
                age_minutes = (datetime.now(timezone.utc) - introduced_at).total_seconds() / 60
                if age_minutes > 60:
                    self._log(f"[EVOLUTION] Force rollback {skill_id} (age={age_minutes:.0f}min > 60min)")
                    # 强制回滚
                    old_score = pending_info["old_score"]
                    self.evolution.verifier.pending.pop(skill_id, None)
                    stats = self.memory.get_skill_stats(skill_id)
                    stats.effectiveness_score = old_score
                    stats.verification["status"] = "forced_rollback"
                    self.memory.save_skill_stats(stats)
                    self.eb.emit("evolution.forced_rollback", {
                        "skill_id": skill_id,
                        "old_score": old_score,
                        "age_minutes": age_minutes,
                    })

        self._stats["evolution_verifications"] = len(pending)

    # ============================================================
    # 主循环
    # ============================================================

    def run(self, once: bool = False):
        """启动机研常驻进程"""
        self.running = True
        self._save_pid()

        # 注册信号处理器
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

        print(f"[jiyan_agent] 机研常驻进程启动 (PID={os.getpid()})")
        print(f"[jiyan_agent] 健康检查: {self.DEFAULT_HEALTH_INTERVAL}s")
        print(f"[jiyan_agent] 衰减管理: {self.DEFAULT_DECAY_INTERVAL}s")
        print(f"[jiyan_agent] 事件轮询: {self.DEFAULT_POLL_INTERVAL}s")

        if once:
            self._log("运行一次模式（--once）")
            self._run_once()
            return

        # 启动子线程
        threads = [
            threading.Thread(target=self._event_loop, daemon=True, name="event_loop"),
            threading.Thread(target=self._health_loop, daemon=True, name="health_loop"),
            threading.Thread(target=self._decay_loop, daemon=True, name="decay_loop"),
        ]

        for t in threads:
            t.start()

        # 主线程定期打印状态
        try:
            while self.running and not self._shutdown.is_set():
                self._shutdown.wait(timeout=30)
                if self.running:
                    self._log(f"[STATS] {self._stats}")
                    # 顺便检查进化
                    self._evolution_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _run_once(self):
        """执行一次所有维护任务后退出"""
        self._log("执行一次性维护检查...")

        # 健康检查
        report = self.health.check_all()
        print(f"  健康状态: {report.overall}")
        if report.alerts:
            print(f"  告警: {len(report.alerts)}")
            for a in report.alerts:
                print(f"    - [{a['level']}] {a['message']}")

        # 衰减管理
        archived = self.decay.archive_cold_memories()
        deleted = self.decay.garbage_collect().get("deleted", 0)
        print(f"  衰减: archived={archived}, deleted={deleted}")

        # 进化验证
        pending = self.evolution.verifier.get_pending_list()
        print(f"  待验证: {len(pending)}")
        for p in pending:
            print(f"    - {p}")

        # 事件处理（拉取并处理所有待处理事件）
        new_events = self.eb.poll_new_events()
        print(f"  待处理事件: {len(new_events)}")
        for evt in new_events:
            self._log(f"  处理事件: {evt.get('type')} / {evt.get('id')}")

        print(f"  统计: {self._stats}")
        self._cleanup_pid()

    def stop(self):
        """停止进程"""
        print("[jiyan_agent] 停止中...")
        self.running = False
        self._shutdown.set()
        self._cleanup_pid()

    def _on_signal(self, signum, frame):
        print(f"[jiyan_agent] 收到信号 {signum}")
        self.stop()

    def _save_pid(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        AGENT_PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    def _cleanup_pid(self):
        if AGENT_PID_FILE.exists():
            AGENT_PID_FILE.unlink()


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hermestrix 机研常驻进程")
    parser.add_argument("--once", action="store_true", help="运行一次后退出")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--interval", type=int, default=None, help="健康检查间隔（秒）")
    args = parser.parse_args()

    if args.interval:
        JiyanAgent.DEFAULT_HEALTH_INTERVAL = args.interval

    agent = JiyanAgent(verbose=args.verbose)
    agent.run(once=args.once)
