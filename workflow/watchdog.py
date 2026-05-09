"""
玄机阁 · Watchdog（自动运转主循环）
======================================
作为 cronjob 每30秒运行，自动推进所有进行中的步骤链。

运转逻辑：
  1. 扫描所有进行中的步骤链
  2. 对每个 READY 步骤 → 执行（调用内置Agent）→ 标记 done → recompute_ready
  3. 对超时 RUNNING 步骤 → reclaim 回 ready
  4. 整条链完成 → 标记主任务 done

启动方式：
  # 开发调试（持续模式）
  cd /root/hermestrix && python3 workflow/watchdog.py --continuous

  # 生产（cronjob，每分钟触发）
  */1 * * * * cd /root/hermestrix && PYTHONPATH=/root/.hermes/hermes-agent python3 workflow/watchdog.py
"""

import sys
import pathlib
import datetime
import time
import json
import os

# 设置 PYTHONPATH 以便直接运行
_repo_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / 'hermes-agent'))

from hermes_cli.kanban_db import connect, list_tasks, get_task

from workflow.kanban_step_chain import (
    STEP_BY_KEY, STEP_NAMES,
    get_chain_steps, get_step_task,
    mark_step_done, is_chain_complete,
    abort_chain,
)
from workflow.agent import get_agent


# ── 配置 ──────────────────────────────────────────────────────────────────

CHECK_INTERVAL  = 30
RUNNING_TTL    = 15 * 60   # 15分钟无心跳 = 超时
BOARD_NAME     = os.environ.get("HERMES_KANBAN_BOARD", None)
LOG_FILE       = _repo_root / 'data' / 'watchdog.log'
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── 日志 ──────────────────────────────────────────────────────────────────

def log(msg: str, level: str = "INFO"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][{level}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.open("a").write(line + "\n")
    except Exception:
        pass


# ── 步骤执行器 ────────────────────────────────────────────────────────────

def execute_step(step_info: dict) -> dict:
    """
    执行单个步骤。
    当前实现：调用玄机阁内置 Agent（同步，主进程内）。
    未来可替换为 subprocess worker 或 Hermes profile。
    """
    body   = step_info.get("body", "{}")
    step_id = step_info.get("step_id") or ""
    step_name = step_info.get("step_name", "")

    # 解析上下文
    try:
        ctx = json.loads(body) if isinstance(body, str) else (body or {})
    except Exception:
        ctx = {}

    log(f"执行步骤: {step_name}({step_id})")

    # 根据 step_id 选择 Agent
    if step_id == "chengzhi":
        agent = get_agent("chengzhi")
    elif step_id == "jiheng":
        agent = get_agent("jiheng")
    elif step_id == "execute":
        routing = ctx.get("routing", {})
        target  = routing.get("target", "jizao")
        agent   = get_agent(target)
        if not agent:
            agent = get_agent("jizao")
    elif step_id == "zaohuang":
        agent = get_agent("zaohuang")
    elif step_id == "yushi":
        agent = get_agent("yushi")
    else:
        return {"ok": False, "error": f"未知步骤: {step_id}"}

    if not agent:
        return {"ok": False, "error": f"Agent不存在: {step_id}"}

    try:
        result = agent.run(ctx)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── 核心 Watchdog ─────────────────────────────────────────────────────────

def tick():
    """单次扫描 + 推进所有进行中的步骤链。"""
    conn = connect(board=BOARD_NAME)
    now  = datetime.datetime.now()
    # 1. 找到所有进行中的主任务
    #    主任务：有 body.root_id 指向自己的顶级任务（步骤链的根）
    #    识别方式：遍历所有非 done 任务，body JSON 的 root_id == task_id 自身
    all_tasks = list_tasks(conn, include_archived=False)

    main_tasks = {}
    for t in all_tasks:
        if t.status in ("done", "archived"):
            continue
        # 解析 body JSON
        try:
            body = json.loads(t.body) if isinstance(t.body, str) else {}
        except Exception:
            continue
        # root_id 指向自己 = 主任务
        if body.get("root_id") == t.id:
            main_tasks[t.id] = {
                "id": t.id,
                "title": t.title,
                "status": t.status,
            }

    if not main_tasks:
        conn.commit()
        return

    log(f"发现 {len(main_tasks)} 条进行中任务链")

    for main in main_tasks.values():
        _process_chain(conn, main, now)

    conn.commit()


def _process_chain(conn, main_task: dict, now: datetime.datetime):
    """处理单条步骤链"""
    parent_id = main_task["id"]

    steps = get_chain_steps(parent_id, board=BOARD_NAME)
    if not steps:
        return

    log(f"  链 {parent_id}：{len(steps)} 个步骤")

    # 2. 处理每个 READY 步骤
    for step in steps:
        if step["status"] != "ready":
            continue

        subtask_id = step["id"]
        step_id    = step.get("step_id") or ""

        log(f"  → 派发: {step.get('title', subtask_id)}")

        # 原子 claim（防止并发抢占）
        now_ts = datetime.datetime.now().timestamp()
        conn.execute(
            "UPDATE tasks SET status = 'running', started_at = ? WHERE id = ? AND status = 'ready'",
            (now_ts, subtask_id)
        )
        conn.commit()

        # 执行（同步）
        result = execute_step(step)

        if result.get("ok"):
            next_ids = mark_step_done(subtask_id,
                                     result=str(result.get("result", "")),
                                     board=BOARD_NAME)
            log(f"  ✓ 完成: {subtask_id}，下游ready: {next_ids}")
        else:
            # 失败 → 检查重试次数
            step_task = get_step_task(subtask_id, board=BOARD_NAME)
            if step_task:
                try:
                    ctx = json.loads(step_task.get("body", "{}"))
                except Exception:
                    ctx = {}
                retries = ctx.get("retry_count", 0)
                limit   = ctx.get("failure_limit", 3)
            else:
                retries, limit = 0, 3

            if retries >= limit:
                conn.execute(
                    "UPDATE tasks SET status = 'blocked' WHERE id = ?",
                    (subtask_id,)
                )
                log(f"  ✗ 已阻塞（重试耗尽）: {subtask_id}", "ERROR")
            else:
                conn.execute(
                    "UPDATE tasks SET status = 'ready', started_at = ? WHERE id = ?",
                    (now_ts, subtask_id)
                )
                log(f"  ↺ 重试: {subtask_id} ({retries+1}/{limit})")

            conn.commit()

    # 3. 检查超时 RUNNING 步骤 → reclaim 回 ready
    running = [s for s in steps if s["status"] == "running"]
    for step in running:
        started_at = step.get("started_at")
        if not started_at:
            continue
        try:
            age = now_ts - started_at
            if age > RUNNING_TTL:
                log(f"  ⏱ 超时回收: {step['id']} (age={int(age)}s)", "WARN")
                conn.execute(
                    "UPDATE tasks SET status = 'ready', started_at = ? WHERE id = ?",
                    (now_ts, step["id"])
                )
                conn.commit()
        except Exception:
            pass

    # 4. 整条链完成
    if is_chain_complete(parent_id, board=BOARD_NAME):
        conn.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?",
            (now_ts, parent_id)
        )
        conn.commit()
        log(f"  ✓✓ 任务链完成: {parent_id}")


# ── CLI 入口 ──────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="玄机阁 Watchdog")
    parser.add_argument("--continuous", action="store_true",
                        help="持续运行（替代 cronjob）")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL,
                        help=f"轮询间隔秒数（默认{CHECK_INTERVAL}）")
    args = parser.parse_args()

    if args.continuous:
        log("Watchdog 持续模式启动")
        while True:
            tick()
            time.sleep(args.interval)
    else:
        log("Watchdog 单次运行")
        tick()


if __name__ == "__main__":
    main()
