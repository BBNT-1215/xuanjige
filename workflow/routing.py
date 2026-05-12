"""
玄机阁 · 共享工具
==================
routing 读写工具：供 agent.py 和 watchdog.py 共用。
"""

import json
import sys
import pathlib

_repo_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / 'hermes-agent'))

from hermes_cli.kanban_db import connect, get_task


def read_root_routing(root_id: str, board: str = None) -> dict:
    """从根任务读取routing信息（承旨分拣结果）"""
    try:
        conn = connect(board=board)
        task = get_task(conn, root_id)
        if task:
            body = task.body
            if isinstance(body, str):
                body = json.loads(body)
            return body.get("routing", {}) if isinstance(body, dict) else {}
    except Exception:
        pass
    return {}


def write_routing_to_root(ctx: dict, routing: dict, board: str = None):
    """
    将routing信息写入根任务body。

    Args:
        ctx:     当前步骤的body dict（含root_id）
        routing: 要写入的routing dict {target, reason, ...}
        board:   Kanban board名
    """
    try:
        root_id = ctx.get("root_id")
        if not root_id:
            return
        conn = connect(board=board)
        task = get_task(conn, root_id)
        if not task:
            return
        body = task.body
        if isinstance(body, str):
            body = json.loads(body)
        if not isinstance(body, dict):
            return

        # 合并routing（保留已有字段）
        existing = body.get("routing", {})
        existing.update(routing)
        body["routing"] = existing

        conn.execute(
            "UPDATE tasks SET body = ? WHERE id = ?",
            (json.dumps(body, ensure_ascii=False), root_id)
        )
        conn.commit()
    except Exception:
        pass
