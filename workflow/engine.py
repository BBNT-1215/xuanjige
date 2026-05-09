"""
玄机阁 · 工作流引擎（执行层）
===============================
状态机核心：只管状态流转，不做实际执行。
实际执行由 Hermes 的 delegate_task 在 Skill 层完成。

流程：
  Skill层：submit() → process()循环
    ↓
  引擎层：管理状态（待分拣→已派发→执行中→待审核→已完成）
    ↓
  Hermes层：delegate_task 实际执行（技造/刑策/文册...）
"""

import json
import pathlib
import datetime
import time
import threading
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from workflow.task_queue import State, get_queue
from workflow.agent import get_agent, AGENT_REGISTRY


# Agent ID → 角色名（用于delegate_task的goal模板）
AGENT_ROLE_NAMES = {
    "jixuan":    "技造",
    "xingce":   "刑策",
    "diancang": "文册",
    "shusuan":  "数算",
    "bingrong": "兵戎",
    "jiyan":    "机研",
    "qitian":   "枢观",
    "zaohuang": "玄档",
    "yushi":    "枢鉴",
    "chengzhi": "承旨",
    "jiheng":   "机衡",
}


class WorkflowEngine:
    """
    玄机阁工作流引擎（状态管理层）
    实际执行由 Hermes Skill 层通过 delegate_task 完成
    """

    def __init__(self):
        self.queue = get_queue()
        self.running = False
        self._thread = None
        self._log = []
        self._callbacks = []
        self.queue.subscribe(self._on_task_state_change)

    # ── 日志 ─────────────────────────────────────

    def log(self, msg: str):
        entry = {"time": datetime.datetime.now().isoformat(), "msg": msg}
        self._log.append(entry)
        print(f"[引擎] {msg}")

    def get_log(self) -> list:
        return self._log[-100:]

    def _fire(self, event: str, task: dict):
        for cb in self._callbacks:
            try:
                cb(event, task)
            except Exception:
                pass

    def _on_task_state_change(self, task_id, old_state, new_state, task):
        self.log(f"状态变更: {old_state} → {new_state} | {task.get('title','')}")
        self._fire("state_change", task)

    # ── 核心API ─────────────────────────────────

    def submit(self, title: str, description: str = "",
               skills: list = None, tags: list = None,
               priority: int = 0) -> dict:
        """提交新任务（状态=PENDING）"""
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

    def process_step(self, task_id: str) -> dict:
        """
        执行单个任务的当前状态→下一步状态。
        状态转换规则：
          PENDING  → ASSIGNED  （承旨分拣）
          ASSIGNED → RUNNING    （机衡调度）
          RUNNING  → REVIEW     （执行完成，提交审核）
          REVIEW   → DONE       （枢鉴通过）
          REVIEW   → RUNNING     （枢鉴退回重做）
          BLOCKED  → RUNNING     （解除阻塞）
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

            routing = result.get("result", {})
            target = routing.get("target", "jixuan")
            reason = routing.get("reason", "")

            # 派发给机衡，状态变为ASSIGNED
            self.queue.transition(task_id, State.ASSIGNED,
                                 agent_id="chengzhi",
                                 msg=f"承旨分拣完成，路由至{target}（{reason}）")

            # 将路由信息注入任务，供后续使用
            task['description'] = json.dumps(routing, ensure_ascii=False)

            self.log(f"承旨分拣 → 目标Agent: {target}")
            return {
                "ok": True,
                "step": "chengzhi",
                "next_agent": target,
                "state": State.ASSIGNED,
                "routing": routing,
                "message": f"承旨分拣完成，路由至{target}"
            }

        # ── ASSIGNED: 机衡调度 ───────────────────
        elif state == State.ASSIGNED:
            desc = task.get('description', '{}')
            if isinstance(desc, str):
                try:
                    desc = json.loads(desc)
                except Exception:
                    desc = {"target": "jixuan"}

            target = desc.get("target", "jixuan")
            role_name = AGENT_ROLE_NAMES.get(target, target)

            # 机衡派发给目标Agent，状态变为RUNNING
            ok = self.queue.transition(task_id, State.RUNNING,
                                       agent_id=target,
                                       msg=f"机衡调度至{role_name}")
            if not ok:
                return {"ok": False, "error": "状态转换失败"}

            self.log(f"机衡调度 → {role_name} 开始执行")
            return {
                "ok": True,
                "step": "jiheng",
                "next_agent": target,
                "state": State.RUNNING,
                "delegate": {
                    "agent_id": target,
                    "role_name": role_name,
                    "task": task,
                },
                "message": f"请通过 delegate_task 指派{role_name}执行任务"
            }

        # ── RUNNING: 执行 ────────────────────────
        elif state == State.RUNNING:
            assignee = task.get('assignee', 'jixuan')
            role_name = AGENT_ROLE_NAMES.get(assignee, assignee)

            # 执行完成，提交审核
            self.queue.transition(task_id, State.REVIEW,
                                 agent_id=assignee,
                                 msg=f"{role_name}执行完成，提交审核")

            self.log(f"{role_name}执行完成，提交玄档审核")
            return {
                "ok": True,
                "step": assignee,
                "next_agent": "zaohuang",
                "state": State.REVIEW,
                "message": f"{role_name}执行完成，等待玄档汇总"
            }

        # ── REVIEW: 玄档+枢鉴审核 ────────────────
        elif state == State.REVIEW:
            assignee = task.get('assignee', 'jixuan')
            role_name = AGENT_ROLE_NAMES.get(assignee, assignee)

            # 玄档汇总（内嵌）
            zaohuang = get_agent("zaohuang")
            zu_result = zaohuang.run(task)
            self.log(f"玄档汇总: {zu_result.get('result')}")

            # 枢鉴审计（内嵌）
            yushi = get_agent("yushi")
            yu_result = yushi.run(task)

            if yu_result.get("ok"):
                self.queue.complete(task_id, "yushi",
                                   msg="枢鉴审计通过，任务完成")
                self.log(f"枢鉴审计通过，任务完成")
                self._fire("completed", task)
                return {
                    "ok": True,
                    "step": "yushi",
                    "next_agent": None,
                    "state": State.DONE,
                    "message": "枢鉴审计通过，任务完成"
                }
            else:
                # 审计失败，退回执行
                self.queue.transition(task_id, State.RUNNING,
                                     agent_id="yushi",
                                     msg="枢鉴审计不通过，退回重做")
                return {
                    "ok": True,
                    "step": "yushi",
                    "next_agent": assignee,
                    "state": State.RUNNING,
                    "delegate": {
                        "agent_id": assignee,
                        "role_name": role_name,
                        "task": task,
                        "retry": True,
                    },
                    "message": "枢鉴审计不通过，退回重做"
                }

        # ── BLOCKED: 解除阻塞 ────────────────────
        elif state == State.BLOCKED:
            assignee = task.get("assignee", "jixuan")
            role_name = AGENT_ROLE_NAMES.get(assignee, assignee)
            self.queue.transition(task_id, State.RUNNING,
                                 agent_id=assignee,
                                 msg="解除阻塞，重新执行")
            return {
                "ok": True,
                "step": "unblock",
                "next_agent": assignee,
                "state": State.RUNNING,
                "delegate": {
                    "agent_id": assignee,
                    "role_name": role_name,
                    "task": task,
                    "retry": True,
                },
                "message": f"解除阻塞，{role_name}重新执行"
            }

        else:
            return {"ok": False, "error": f"未知状态: {state}"}

    # ── 引擎主循环（后台自动处理PENDING） ─────────

    def _loop(self):
        while self.running:
            try:
                pending = self.queue.pending_tasks()
                if pending:
                    for task in pending[:3]:
                        if not self.running:
                            break
                        self.process_step(task['id'])
                        time.sleep(0.5)

                for task in self.queue.running_tasks():
                    updated = task.get('updated_at', '')
                    if updated:
                        try:
                            dt = datetime.datetime.fromisoformat(updated)
                            age = (datetime.datetime.now() - dt).total_seconds()
                            if age > 300:
                                self.log(f"⚠️ 任务执行超时:「{task['title']}」(age={int(age)}s)")
                        except Exception:
                            pass

                time.sleep(2)
            except Exception as e:
                self.log(f"引擎循环异常: {e}")

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.log("玄机阁引擎启动 ✓")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=3)
        self.log("玄机阁引擎停止")

    def status(self) -> dict:
        stats = self.queue.stats()
        return {
            "running": self.running,
            "stats": stats,
            "agents": list(AGENT_REGISTRY.keys()),
        }

    def trace(self, task_id: str) -> dict:
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


_engine = None
def get_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
