"""
玄机阁 · 工作流引擎
====================
核心调度器：驱动承旨→机衡→六部→早朝→御史的完整流程。

流程：
  用户提交任务
      ↓
  承旨拆解分拣 → PENDING → ASSIGNED
      ↓
  机衡智能调度 → ASSIGNED → RUNNING
      ↓
  六部执行（可并行）
      ↓
  早朝汇总 → REVIEW → RUNNING（早朝）
      ↓
  御史审计 → REVIEW → DONE
      ↓
  记录归档
"""

import json
import pathlib
import datetime
import time
import threading
import sys
import os

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from workflow.task_queue import State, get_queue
from workflow.agent import get_agent, AGENT_REGISTRY


class WorkflowEngine:
    """
    玄机阁工作流引擎
    驱动整个多Agent协作体系运转
    """

    def __init__(self):
        self.queue = get_queue()
        self.running = False
        self._thread = None
        self._log = []
        self._callbacks = []  # 任务生命周期回调

        # 订阅队列变更
        self.queue.subscribe(self._on_task_state_change)

    # ── 生命周期回调 ─────────────────────────────────

    def on_task(self, callback):
        """注册任务生命周期监听器"""
        self._callbacks.append(callback)

    def _fire(self, event: str, task: dict):
        for cb in self._callbacks:
            try:
                cb(event, task)
            except Exception:
                pass

    def _on_task_state_change(self, task_id, old_state, new_state, task):
        self.log(f"状态变更: {old_state} → {new_state} | {task.get('title','')}")
        self._fire("state_change", task)

    # ── 日志 ─────────────────────────────────────

    def log(self, msg: str):
        entry = {"time": datetime.datetime.now().isoformat(), "msg": msg}
        self._log.append(entry)
        print(f"[引擎] {msg}")

    def get_log(self) -> list:
        return self._log[-100:]

    # ── 核心流程 ─────────────────────────────────

    def submit(self, title: str, description: str = "",
               skills: list = None, tags: list = None,
               priority: int = 0) -> dict:
        """
        提交新任务，触发完整工作流。
        """
        task = self.queue.create(
            title=title,
            description=description,
            skills=skills,
            tags=tags,
            priority=priority,
            created_by="user"
        )
        self.log(f"任务入队:「{title}」(id={task['id']})")
        self._fire("submitted", task)
        return task

    def process_task(self, task_id: str) -> dict:
        """
        单任务完整流程：承旨→机衡→执行→审核→完成
        """
        task = self.queue.get(task_id)
        if not task:
            return {"ok": False, "error": "任务不存在"}

        state = task['state']
        self.log(f"处理任务「{task['title']}」当前状态: {state}")

        # ── PENDING: 承旨分拣 ─────────────────────
        if state == State.PENDING:
            agent = get_agent("chengzhi")
            if not agent:
                return {"ok": False, "error": "承旨Agent不存在"}
            result = agent.run(task)
            if not result.get("ok"):
                return result

            # 承旨路由结果写入description
            routing = result.get("result", {})
            target = routing.get("target", "jizao")

            # 派发给机衡
            self.queue.transition(task_id, State.ASSIGNED,
                                 agent_id="chengzhi",
                                 msg=f"承旨分拣完成，路由至{target}")

            # 将路由信息注入任务描述（供后续使用）
            task['description'] = json.dumps(routing, ensure_ascii=False)
            self.log(f"承旨分拣 → 目标Agent: {target}")
            return {"ok": True, "step": "chengzhi", "next": target}

        # ── ASSIGNED: 机衡调度 ───────────────────
        elif state == State.ASSIGNED:
            # 从任务描述中读取承旨的路由结果
            desc = task.get('description', '{}')
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except:
                    desc = {"target": "jizao"}

            target = desc.get("target", "jizao")
            agent = get_agent(target)
            if not agent:
                self.log(f"未找到Agent: {target}，默认技造")
                agent = get_agent("jizao")

            # 机衡派发给目标Agent，开始执行
            ok = self.queue.transition(task_id, State.RUNNING,
                                       agent_id=target,
                                       msg=f"机衡调度至{agent.agent_name}")
            if not ok:
                return {"ok": False, "error": "状态转换失败"}

            self.log(f"机衡调度 → {agent.agent_name} 开始执行")
            return {"ok": True, "step": "jiheng", "next": target}

        # ── RUNNING: 执行 ────────────────────────
        elif state == State.RUNNING:
            assignee = task.get('assignee', 'jizao')
            agent = get_agent(assignee)
            if not agent:
                agent = get_agent("jizao")

            result = agent.run(task)

            if result.get("ok"):
                # 执行完成，提交给早朝汇总
                self.queue.transition(task_id, State.REVIEW,
                                     agent_id=assignee,
                                     msg=f"{agent.agent_name}完成，提交审核")
                self.log(f"{agent.agent_name}执行完成，提交早朝审核")
                return {"ok": True, "step": agent.agent_id, "next": "zaohuang"}
            else:
                self.queue.block(task_id, assignee,
                                reason=result.get("error", "执行失败"))
                return result

        # ── REVIEW: 早朝+御史审核 ────────────────
        elif state == State.REVIEW:
            # 早朝汇总
            zaohuang = get_agent("zaohuang")
            zu_result = zaohuang.run(task)
            self.log(f"早朝汇总: {zu_result.get('result')}")

            # 御史审计
            yushi = get_agent("yushi")
            yu_result = yushi.run(task)

            if yu_result.get("ok"):
                self.queue.complete(task_id, "yushi",
                                   msg="御史审计通过，任务完成")
                self.log(f"御史审计通过，任务完成")
                self._fire("completed", task)
                return {"ok": True, "step": "yushi", "next": None}
            else:
                # 审计失败，退回执行
                self.queue.transition(task_id, State.RUNNING,
                                     agent_id="yushi",
                                     msg="御史审计不通过，退回重做")
                return {"ok": True, "step": "yushi", "next": task.get("assignee", "jizao")}

        # ── BLOCKED: 解除阻塞 ────────────────────
        elif state == State.BLOCKED:
            # 自动重试一次
            assignee = task.get("assignee", "jizao")
            self.queue.transition(task_id, State.RUNNING,
                                 agent_id=assignee,
                                 msg="解除阻塞，重新执行")
            return {"ok": True, "step": "unblock", "next": assignee}

        else:
            return {"ok": False, "error": f"未知状态: {state}"}

    # ── 引擎主循环 ─────────────────────────────────

    def _loop(self):
        """后台工作线程：持续处理PENDING任务"""
        while self.running:
            try:
                pending = self.queue.pending_tasks()
                if pending:
                    for task in pending[:3]:  # 每次最多处理3个
                        if not self.running:
                            break
                        self.process_task(task['id'])
                        time.sleep(0.5)  # 防抖

                # 检查RUNNING任务是否超时（5分钟未完成则提示）
                for task in self.queue.running_tasks():
                    updated = task.get('updated_at', '')
                    if updated:
                        try:
                            dt = datetime.datetime.fromisoformat(updated)
                            age = (datetime.datetime.now() - dt).total_seconds()
                            if age > 300:
                                self.log(f"⚠️ 任务执行超时:「{task['title']}」(age={int(age)}s)")
                        except:
                            pass

                time.sleep(2)
            except Exception as e:
                self.log(f"引擎循环异常: {e}")

    def start(self):
        """启动引擎（后台线程）"""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.log("玄机阁引擎启动 ✓")

    def stop(self):
        """停止引擎"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        self.log("玄机阁引擎停止")

    def status(self) -> dict:
        """引擎状态"""
        stats = self.queue.stats()
        return {
            "running": self.running,
            "stats": stats,
            "agents": list(AGENT_REGISTRY.keys()),
        }

    # ── 任务追踪 ─────────────────────────────────

    def trace(self, task_id: str) -> dict:
        """获取任务完整流转记录"""
        task = self.queue.get(task_id)
        if not task:
            return {}
        return {
            "id": task['id'],
            "title": task['title'],
            "state": task['state'],
            "assignee": task.get('assignee'),
            "history": task.get('history', []),
            "created_at": task.get('created_at'),
            "updated_at": task.get('updated_at'),
        }


# 全局单例
_engine = None
def get_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
