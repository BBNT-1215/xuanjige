"""
玄机阁 · Kanban 步骤链
========================
利用 Hermes Kanban 的 task_links 依赖机制，
实现步骤间的串行依赖：父步骤完成，子步骤自动 ready。

核心思路：
  - 每个步骤 = 一个 Kanban Task
  - 步骤间用 task_links 串成链
  - 父 done → recompute_ready() → 子自动 ready
  - Worker 被 dispatch 派发执行
"""

import sys
import pathlib
import json
import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'hermes-agent'))

from hermes_cli.kanban_db import (
    connect, create_task, get_task,
    recompute_ready, list_tasks,
)


# ── 步骤定义 ────────────────────────────────────────────────────────────────

STEPS = [
    ("chengzhi",  "承旨",  "分拣任务，判定类型和路由"),
    ("jiheng",    "机衡",  "调度派发，确定执行Agent"),
    ("execute",   "执行",  "六部执行（技造/刑策/文册/数算/兵戎/机研）"),
    ("zaohuang",  "早朝",  "情报汇总，整理执行结果"),
    ("yushi",     "御史",  "质量审计，验收或打回"),
]
STEP_BY_KEY = {s[0]: s for s in STEPS}
STEP_NAMES  = {s[0]: s[1] for s in STEPS}


# ── 主任务 ────────────────────────────────────────────────────────────────

def create_root_task(title: str, description: str = "",
                   routing: dict = None,
                   board: str = None) -> str:
    """
    创建主任务（顶级任务，步骤链的根）。
    body 是 JSON，含 root_id = 自身ID。
    """
    import uuid
    conn = connect(board=board)
    task_id = f"task_{uuid.uuid4().hex[:10]}"

    body = json.dumps({
        "root_id": task_id,
        "title": title,
        "description": description,
        "routing": routing or {},
    }, ensure_ascii=False)

    # 直接 INSERT，绕过 create_task 的 parents 依赖逻辑
    now_ts = datetime.datetime.now().timestamp()
    conn.execute("""
        INSERT INTO tasks (id, title, body, status, created_at, created_by)
        VALUES (?, ?, ?, 'ready', ?, 'user')
    """, (task_id, title, body, now_ts))
    conn.commit()
    return task_id


# ── 步骤链 ────────────────────────────────────────────────────────────────

def build_step_chain(task_id: str, title: str,
                    routing: dict = None,
                    board: str = None) -> list[str]:
    """
    在 Kanban 中创建完整的步骤链。

    Args:
        task_id:   主任务ID（用于生成子任务ID前缀）
        title:     任务标题
        routing:   承旨分拣结果 {target: "jizao", reason: "..."}
        board:     Kanban board name (默认当前board)

    Returns:
        子任务ID列表，按步骤顺序
    """
    conn = connect(board=board)
    subtask_ids = []
    prev_id = None

    for step_key, (step_id, step_name, step_desc) in enumerate(STEPS):
        body = json.dumps({
            "task_id": task_id,
            "root_id": task_id,     # 标记顶级任务ID（用于识别主任务）
            "step_key": step_key,
            "step_id": step_id,
            "step_name": step_name,
            "step_desc": step_desc,
            "title": title,
            "routing": routing or {},
        }, ensure_ascii=False)

        # 第一个步骤立即 ready；后续步骤依赖前一步
        parent_ids = (prev_id,) if prev_id else ()

        created_id = create_task(
            conn,
            title=f"「{title}」{step_name}：{step_desc}",
            body=body,
            parents=parent_ids,
        )
        subtask_ids.append(created_id)
        prev_id = created_id

    conn.commit()
    return subtask_ids


def get_step_task(subtask_id: str, board: str = None) -> dict | None:
    """获取某个步骤任务"""
    conn = connect(board=board)
    task = get_task(conn, subtask_id)
    conn.commit()
    if task is None:
        return None
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "body": task.body,
        "assignee": task.assignee,
        "updated_at": task.started_at,
    }


def get_chain_steps(root_id: str, board: str = None) -> list[dict]:
    """获取整条步骤链的状态（通过 root_id 过滤）"""
    conn = connect(board=board)
    all_tasks = list_tasks(conn, include_archived=False)

    steps = []
    for t in all_tasks:
        try:
            body = json.loads(t.body) if isinstance(t.body, str) else {}
        except Exception:
            body = {}
        # 只取属于这条链的步骤（同一 root_id）
        if body.get("root_id") == root_id:
            steps.append({
                "id": t.id,
                "step_key": body.get("step_key"),
                "step_id": body.get("step_id"),
                "step_name": body.get("step_name"),
                "title": t.title,
                "status": t.status,
                "assignee": t.assignee,
                "body": t.body,
                "updated_at": t.started_at,
            })

    steps = [s for s in steps if s.get("step_key") is not None]  # 排除主任务本身
    steps.sort(key=lambda x: x.get("step_key") if x.get("step_key") is not None else 999)
    conn.commit()
    return steps


def mark_step_done(subtask_id: str, result: str = "",
                  board: str = None) -> list[str]:
    """
    标记当前步骤完成，触发 recompute_ready，
    返回变为 ready 的下游步骤IDs。
    """
    conn = connect(board=board)
    now_ts = datetime.datetime.now().timestamp()

    # 标记 done
    conn.execute(
        "UPDATE tasks SET status = 'done', result = ?, completed_at = ? WHERE id = ?",
        (result or "", now_ts, subtask_id)
    )

    # recompute_ready：父 done → 子 todo → ready
    recompute_ready(conn)
    conn.commit()

    return []


def abort_chain(parent_id: str, reason: str = "", board: str = None):
    """中止整条链"""
    conn = connect(board=board)
    conn.execute(
        "UPDATE tasks SET status = 'blocked', result = ? WHERE id LIKE ?",
        (reason, f"{parent_id}-%")
    )
    conn.commit()


def is_chain_complete(root_id: str, board: str = None) -> bool:
    """检查整条链是否全部完成（通过 root_id 过滤所有子任务）"""
    conn = connect(board=board)
    all_tasks = list_tasks(conn, include_archived=False)

    for t in all_tasks:
        try:
            body = json.loads(t.body) if isinstance(t.body, str) else {}
        except Exception:
            continue
        # 属于这条链的步骤（同一 root_id）
        if body.get("root_id") == root_id:
            if body.get("step_key") is not None and t.status != "done":
                conn.commit()
                return False

    conn.commit()
    return True
