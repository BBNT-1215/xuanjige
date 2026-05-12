"""
玄机阁 · 任务队列（状态机）
============================
任务生命周期管理，驱动整个工作流运转。

状态流转：
  PENDING → ASSIGNED → RUNNING → REVIEW → DONE
                        ↘ BLOCKED ↗
"""

import json
import pathlib
import uuid
import datetime
import threading
import copy

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / 'data'
TASKS_FILE = DATA_DIR / 'tasks.json'
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 任务状态枚举
class State:
    PENDING   = "待分拣"    # 承旨还未处理
    ASSIGNED  = "已派发"    # 机衡已路由
    RUNNING   = "执行中"    # 技造/刑策/文册/数算/兵戎/机研执行中
    REVIEW    = "待审核"    # 玄档/枢鉴审核
    DONE      = "已完成"    # 流程结束
    BLOCKED   = "已阻塞"    # 卡住
    CANCELLED = "已取消"

# 所有合法流转
VALID_TRANSITIONS = {
    State.PENDING:  {State.ASSIGNED, State.CANCELLED},
    State.ASSIGNED: {State.RUNNING,  State.BLOCKED, State.CANCELLED},
    State.RUNNING:  {State.REVIEW,   State.BLOCKED, State.CANCELLED},
    State.REVIEW:   {State.DONE,     State.RUNNING, State.BLOCKED, State.CANCELLED},
    State.BLOCKED:  {State.RUNNING,  State.CANCELLED},
}


class TaskQueue:
    """线程安全的任务队列"""

    def __init__(self, tasks_file: pathlib.Path = TASKS_FILE):
        self.tasks_file = tasks_file
        self._lock = threading.RLock()
        self._subscribers = []  # 状态变更回调
        self._load()

    # ── 持久化 ──────────────────────────────────────

    def _load(self):
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                    # 兼容旧格式
                    if isinstance(raw, list):
                        self.tasks = {t.get('id', str(i)): t for i, t in enumerate(raw)}
                    else:
                        self.tasks = raw
            except Exception:
                self.tasks = {}
        else:
            self.tasks = {}

    def _save(self):
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)

    # ── 订阅 ──────────────────────────────────────

    def subscribe(self, callback):
        """注册状态变更监听器"""
        self._subscribers.append(callback)

    def _notify(self, task_id: str, old_state: str, new_state: str, task: dict):
        for cb in self._subscribers:
            try:
                cb(task_id, old_state, new_state, task)
            except Exception:
                pass

    # ── 核心CRUD ──────────────────────────────────

    def create(self, title: str, description: str = "", skills: list = None,
               priority: int = 0, tags: list = None, created_by: str = "user") -> dict:
        """创建一个新任务（自动进入PENDING）"""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().isoformat()
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "skills": skills or [],
            "priority": priority,
            "tags": tags or [],
            "state": State.PENDING,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now,
            "assignee": None,
            "history": [{"state": State.PENDING, "time": now, "msg": "任务创建"}],
        }
        with self._lock:
            self.tasks[task_id] = task
            self._save()
        return task

    def get(self, task_id: str) -> dict | None:
        return self.tasks.get(task_id)

    def filter_tasks(self, state: str = None, assignee: str = None,
                    limit: int = 100) -> list[dict]:
        """查询任务列表"""
        results = list(self.tasks.values())
        if state:
            results = [t for t in results if t['state'] == state]
        if assignee:
            results = [t for t in results if t.get('assignee') == assignee]
        # ISO字符串排序改为datetime解析，确保跨年/跨月正确排序
        results.sort(
            key=lambda t: (
                t.get('priority', 0),
                datetime.datetime.fromisoformat(t['created_at']) if t.get('created_at') else datetime.datetime.min
            ),
            reverse=True
        )
        return results[:limit]

    def transition(self, task_id: str, new_state: str,
                   agent_id: str = None, msg: str = "") -> bool:
        """状态转换，带校验"""
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            old_state = task['state']
            if new_state not in VALID_TRANSITIONS.get(old_state, {}):
                return False
            now = datetime.datetime.now().isoformat()
            task['state'] = new_state
            task['updated_at'] = now
            if agent_id:
                task['assignee'] = agent_id
            task['history'].append({
                "state": new_state,
                "time": now,
                "agent": agent_id,
                "msg": msg or f"{old_state} → {new_state}"
            })
            self._save()
        self._notify(task_id, old_state, new_state, task)
        return True

    def assign(self, task_id: str, agent_id: str) -> bool:
        """派发给指定Agent"""
        return self.transition(task_id, State.ASSIGNED, agent_id=agent_id,
                               msg=f"派发给 {agent_id}")

    def start(self, task_id: str, agent_id: str) -> bool:
        """开始执行"""
        return self.transition(task_id, State.RUNNING, agent_id=agent_id,
                               msg=f"{agent_id} 开始执行")

    def block(self, task_id: str, agent_id: str, reason: str = "") -> bool:
        return self.transition(task_id, State.BLOCKED, agent_id=agent_id,
                               msg=f"阻塞: {reason}")

    def review(self, task_id: str, agent_id: str) -> bool:
        return self.transition(task_id, State.REVIEW, agent_id=agent_id,
                               msg=f"{agent_id} 提交审核")

    def complete(self, task_id: str, agent_id: str, msg: str = "") -> bool:
        return self.transition(task_id, State.DONE, agent_id=agent_id,
                               msg=msg or f"{agent_id} 完成")

    def cancel(self, task_id: str, reason: str = "") -> bool:
        return self.transition(task_id, State.CANCELLED,
                               msg=f"取消: {reason}")

    def stats(self) -> dict:
        """全局统计"""
        counts = {}
        for t in self.tasks.values():
            s = t['state']
            counts[s] = counts.get(s, 0) + 1
        return {
            "total": len(self.tasks),
            "by_state": counts,
            "updated_at": datetime.datetime.now().isoformat()
        }

    # ── 批量操作 ──────────────────────────────────

    def by_state(self, state: str) -> list[dict]:
        return [t for t in self.tasks.values() if t['state'] == state]

    def pending_tasks(self) -> list[dict]:
        return self.by_state(State.PENDING)

    def running_tasks(self) -> list[dict]:
        return self.by_state(State.RUNNING)


# 全局单例
_global_queue = None
def get_queue() -> TaskQueue:
    global _global_queue
    if _global_queue is None:
        _global_queue = TaskQueue()
    return _global_queue
