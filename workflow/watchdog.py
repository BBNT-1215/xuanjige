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
from workflow.routing import read_root_routing, write_routing_to_root


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
    import sys
    print(line, file=sys.stderr)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.open("a").write(line + "\n")
    except Exception:
        pass


# ── 步骤执行器 ────────────────────────────────────────────────────────────

def execute_step(step_info: dict) -> tuple[dict, dict]:
    """
    执行单个步骤。

    步骤分工：
      chengzhi  → ChengzhiAgent（任务分拣）
      jiheng    → JihengAgent（调度写入routing）
      execute   → 从根任务读取routing → 调用对应执行Agent
      zaohuang  → ZaohuangAgent（情报汇总）
      yushi     → YushiAgent（质量终审）

    返回: (updated_ctx, result_dict)
    """
    body     = step_info.get("body", "{}")
    step_id  = step_info.get("step_id") or ""
    step_name = step_info.get("step_name", "")

    # 解析上下文
    try:
        ctx = json.loads(body) if isinstance(body, str) else (body or {})
    except Exception:
        ctx = {}

    log(f"执行步骤: {step_name}({step_id})")

    # ── 步骤路由 ────────────────────────────────
    if step_id == "chengzhi":
        agent = get_agent("chengzhi")
        result = agent.run(ctx)

    elif step_id == "jiheng":
        agent = get_agent("jiheng")
        result = agent.run(ctx)
        # 机衡执行完后：将routing写回主任务body，供execute步骤读取
        if result.get("ok"):
            write_routing_to_root(ctx, result["result"], board=BOARD_NAME)

    elif step_id == "execute":
        # 从根任务读取承旨的routing，同时读取jiheng的assignee
        root_id = ctx.get("root_id")
        target = None
        if root_id:
            root_routing = read_root_routing(root_id, board=BOARD_NAME)
            target = root_routing.get("target") or root_routing.get("assignee")

        # 如果根任务没有，从ctx的routing字段降级读取
        if not target:
            target = ctx.get("routing", {}).get("target") or ctx.get("routing", {}).get("assignee")

        if not target:
            target = "jixuan"

        agent = get_agent(target)
        if not agent:
            agent = get_agent("jixuan")

        log(f"  → 执行Agent: {agent.agent_name}({agent.agent_id})")
        result = agent.run(ctx)
        # agent.run() 可能修改了ctx（写入_generated_code等），更新本地ctx
        if isinstance(result.get("result"), dict):
            ctx.update(result["result"])

    elif step_id == "zaohuang":
        agent = get_agent("zaohuang")
        result = agent.run(ctx)

    elif step_id == "yushi":
        agent = get_agent("yushi")
        result = agent.run(ctx)

    else:
        return ctx, {"ok": False, "error": f"未知步骤: {step_id}"}

    if not agent:
        return ctx, {"ok": False, "error": f"Agent不存在: {step_id}"}

    try:
        return ctx, result
    except Exception as e:
        return ctx, {"ok": False, "error": str(e)}


# ── 核心 Watchdog ─────────────────────────────────────────────────────────

def tick():
    """单次扫描 + 推进所有进行中的步骤链。"""
    conn = connect(board=BOARD_NAME)
    now  = datetime.datetime.now()

    # 1. 找到所有进行中的主任务
    #    方式：遍历所有非 done 步骤，从 step_key==0 的步骤提取 root_id
    #    即便根任务记录不存在，也能从子步骤的 root_id 反推主任务
    all_tasks = list_tasks(conn, include_archived=False)

    # 收集所有非 done 的链（按 root_id 分组）
    # root_id -> {"id": root_id, "title": <from step 0>, "status": max_status_of_chain}
    chain_map: dict = {}
    for t in all_tasks:
        if t.status in ("done", "archived"):
            continue
        try:
            body = json.loads(t.body) if isinstance(t.body, str) else {}
        except Exception:
            continue
        root_id = body.get("root_id")
        step_key = body.get("step_key")
        if not root_id or step_key is None:
            continue
        if root_id not in chain_map:
            chain_map[root_id] = {
                "id": root_id,
                "title": body.get("title", root_id),
                "status": t.status,
            }
        else:
            # 保留已知的 status（done > running > ready > todo）
            pass

    if not chain_map:
        conn.commit()
        return

    log(f"发现 {len(chain_map)} 条进行中任务链")

    for main in chain_map.values():
        _process_chain(conn, main, now)

    conn.commit()


def _process_chain(conn, main_task: dict, now: datetime.datetime):
    """处理单条步骤链"""
    parent_id = main_task["id"]
    # 在函数开头定义 now_ts，确保 reclaim 循环可访问
    now_ts = datetime.datetime.now().timestamp()

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
        conn.execute(
            "UPDATE tasks SET status = 'running', started_at = ? WHERE id = ? AND status = 'ready'",
            (now_ts, subtask_id)
        )
        conn.commit()

        # 执行（同步）；execute_step内部会修改传入的ctx，返回(updated_ctx, result)
        step_ctx, result = execute_step(step)

        if result.get("ok"):
            # 把agent执行结果（routing/_generated_code等）合并写入body，供下游步骤读取
            mark_step_done(subtask_id,
                         result=json.dumps(result.get("result", ""), ensure_ascii=False),
                         board=BOARD_NAME,
                         ctx=step_ctx)
            log(f"  ✓ 完成: {subtask_id}，下游ready: []")
        else:
            # 失败 → 检查重试次数
            step_task = get_step_task(subtask_id, board=BOARD_NAME)
            retry_ctx = step_ctx  # 用执行后的ctx（可能有部分结果）
            if step_task:
                try:
                    retry_body = json.loads(step_task.get("body", "{}"))
                except Exception:
                    retry_body = {}
                retries = retry_body.get("retry_count", 0)
                limit   = retry_body.get("failure_limit", 3)
            else:
                retries, limit = 0, 3

            if retries >= limit:
                conn.execute(
                    "UPDATE tasks SET status = 'blocked' WHERE id = ?",
                    (subtask_id,)
                )
                log(f"  ✗ 已阻塞（重试耗尽）: {subtask_id}", "ERROR")
            else:
                # 重试时清除 started_at，使 TTL 从下次 claim 重新计算
                conn.execute(
                    "UPDATE tasks SET status = 'ready', started_at = 0 WHERE id = ?",
                    (subtask_id,)
                )
                # 写入重试次数
                retry_body["retry_count"] = retries + 1
                conn.execute(
                    "UPDATE tasks SET body = ? WHERE id = ?",
                    (json.dumps(retry_body), subtask_id)
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
