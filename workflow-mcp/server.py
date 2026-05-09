#!/usr/bin/env python3
"""
玄机阁 MCP Server (Kanban 步骤链版)
====================================
通过MCP协议暴露工作流引擎工具给Hermes Agent使用。

暴露工具：
  workflow_submit    提交新任务（创建步骤链，Watchdog自动推进）
  workflow_chain_status   查看步骤链状态
  workflow_watchdog_info  查看Watchdog状态
  workflow_abort    中止进行中的步骤链

  [旧版兼容]
  workflow_process  执行单任务流程（手动推进，旧模式）
  workflow_status   查看引擎状态
  workflow_list     列出任务（旧队列）
  workflow_trace    查看任务流转历史（旧队列）

配置到 ~/.hermes/config.yaml:
  mcp_servers:
    xuanjige:
      command: python3
      args: [/root/hermestrix/workflow-mcp/server.py]
"""

import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'hermes-agent'))


def main():
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # Lazy import，避免启动时出错
    from workflow.kanban_step_chain import (
        create_root_task, build_step_chain, get_chain_steps,
        is_chain_complete, abort_chain,
    )
    from workflow.watchdog import tick as watchdog_tick

    # 旧引擎（兼容）
    from workflow.engine import get_engine
    from workflow.task_queue import get_queue

    engine = get_engine()
    queue = get_queue()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        ctx = {
        }
        response = handle_request(request, engine, queue,
                                 create_root_task, build_step_chain,
                                 get_chain_steps, is_chain_complete,
                                 abort_chain, watchdog_tick)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def handle_request(req, engine, queue,
                 create_root_task_fn, build_step_chain_fn,
                 get_chain_steps_fn, is_chain_complete_fn,
                 abort_chain_fn, watchdog_tick_fn):
    """Handle a single JSON-RPC request"""
    method = req.get("method", "")
    req_id = req.get("id")

    # ── MCP protocol handshake ──────────────────────

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
                "serverInfo": {
                    "name": "xuanjige-workflow",
                    "version": "3.0.0",
                },
            },
        }

    if method == "notifications/initialized":
        # Client ready signal, no response needed
        return None

    # ── Tool calls ──────────────────────────────────

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "workflow_submit",
                        "description": "提交新任务到玄机阁（Kanban步骤链版）。任务会自动走完5步：承旨→机衡→六部执行→早朝汇总→御史审核，全自动推进，无需人工干预。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "任务标题"},
                                "description": {"type": "string", "description": "任务描述"},
                                "target_agent": {"type": "string", "description": "指定执行Agent（可选，默认jizao）", "default": "jizao"},
                            },
                            "required": ["title"],
                        },
                    },
                    {
                        "name": "workflow_chain_status",
                        "description": "查看某个任务的步骤链完整状态，包含每步的名称、状态和执行结果。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string", "description": "主任务ID（workflow_submit返回的id）"},
                            },
                            "required": ["task_id"],
                        },
                    },
                    {
                        "name": "workflow_watchdog_info",
                        "description": "手动触发一次Watchdog扫描并查看进行中的任务链概览。",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "workflow_abort",
                        "description": "中止某个进行中的任务链，标记所有步骤为blocked。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string", "description": "主任务ID"},
                                "reason": {"type": "string", "description": "中止原因"},
                            },
                            "required": ["task_id"],
                        },
                    },
                    {
                        "name": "workflow_status",
                        "description": "查看玄机阁工作流引擎状态（兼容旧模式）。",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "workflow_list",
                        "description": "列出旧队列中的任务（兼容模式）。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "state": {"type": "string", "description": "按状态过滤"},
                                "limit": {"type": "integer", "description": "返回数量", "default": 20},
                            },
                        },
                    },
                ],
            },
        }

    if method == "tools/call":
        tool_name = req.get("params", {}).get("name", "")
        arguments = req.get("params", {}).get("arguments", {})

        try:
            if tool_name == "workflow_submit":
                result = _wf_submit(create_root_task_fn, build_step_chain_fn, arguments)
            elif tool_name == "workflow_chain_status":
                result = _wf_chain_status(get_chain_steps_fn, arguments)
            elif tool_name == "workflow_watchdog_info":
                result = _wf_watchdog_info(get_chain_steps_fn, watchdog_tick_fn)
            elif tool_name == "workflow_abort":
                result = _wf_abort(abort_chain_fn, arguments)
            elif tool_name == "workflow_status":
                result = _wf_status(engine)
            elif tool_name == "workflow_list":
                result = _wf_list(queue, arguments)
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            result = {"error": str(e)}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2),
                    }
                ],
                "isError": "error" in result,
            },
        }

    # Unknown method
    return None


# ── 新工具实现（Kanban步骤链）────────────────────────────────────

def _wf_submit(create_root_task_fn, build_step_chain_fn, args):
    title       = args["title"]
    description  = args.get("description", "")
    target      = args.get("target_agent", "jizao")

    task_id = create_root_task_fn(title, description)
    build_step_chain_fn(task_id, title, routing={"target": target})

    return {
        "ok": True,
        "task_id": task_id,
        "title": title,
        "message": f"任务已提交(ID={task_id})，5步流程自动推进中...",
    }


def _wf_chain_status(get_chain_steps_fn, args):
    task_id = args["task_id"]
    chain = get_chain_steps_fn(task_id)
    if not chain:
        return {"ok": False, "error": f"找不到任务链: {task_id}"}

    done = sum(1 for s in chain if s["status"] == "done")
    return {
        "ok": True,
        "task_id": task_id,
        "total": len(chain),
        "done": done,
        "steps": [
            {
                "name": s.get("step_name"),
                "status": s["status"],
                "title": s.get("title", "")[:50],
            }
            for s in chain
        ],
    }


def _wf_watchdog_info(get_chain_steps_fn, watchdog_tick_fn):
    # 先触发一次扫描
    watchdog_tick_fn()

    # 读取进行中的任务
    from hermes_cli.kanban_db import connect, list_tasks
    import json
    conn = connect()
    active = []
    for t in list_tasks(conn, include_archived=False):
        if t.status in ("ready", "running"):
            try:
                body = json.loads(t.body) if isinstance(t.body, str) else {}
            except Exception:
                body = {}
            root_id = body.get("root_id")
            if root_id and root_id == t.id:
                chain = get_chain_steps_fn(root_id)
                done = sum(1 for s in chain if s["status"] == "done")
                active.append({
                    "id": t.id,
                    "title": t.title[:40],
                    "done": done,
                    "total": len(chain),
                })
    conn.commit()
    return {
        "ok": True,
        "active_chains": len(active),
        "chains": active,
    }


def _wf_abort(abort_chain_fn, args):
    task_id = args["task_id"]
    reason  = args.get("reason", "用户中止")
    abort_chain_fn(task_id, reason)
    return {"ok": True, "task_id": task_id, "message": f"任务链已中止: {reason}"}


# ── 旧工具实现（兼容）────────────────────────────────────────────

def _wf_start(engine):
    if not engine.running:
        engine.start()
    return {"ok": True, "status": "engine_started", "running": engine.running}


def _wf_stop(engine):
    engine.stop()
    return {"ok": True, "status": "engine_stopped", "running": engine.running}


def _wf_process(engine, args):
    task_id = args["task_id"]
    result = engine.process_step(task_id)
    task = engine.queue.get(task_id)
    resp = {
        "ok": result.get("ok", False),
        "task_id": task_id,
        "current_state": task["state"] if task else "unknown",
        "step": result.get("step"),
        "next_agent": result.get("next_agent"),
        "message": result.get("message", ""),
    }
    if result.get("delegate"):
        resp["delegate"] = result["delegate"]
        resp["needs_execution"] = True
        resp["message"] += f"\n需要通过 delegate_task 执行"
    return resp


def _wf_trace(queue, args):
    task = queue.get(args["task_id"])
    if not task:
        return {"ok": False, "error": f"Task not found: {args['task_id']}"}
    return {
        "ok": True,
        "id": task["id"],
        "title": task["title"],
        "current_state": task["state"],
        "assignee": task.get("assignee"),
        "history": [
            {
                "time": h.get("time", "")[:19],
                "state": h.get("state"),
                "agent": h.get("agent") or "system",
                "msg": h.get("msg", ""),
            }
            for h in task.get("history", [])
        ],
    }


def _wf_status(engine):
    st = engine.status()
    logs = engine.get_log()
    recent = logs[-10:] if logs else []
    return {
        "ok": True,
        "running": st["running"],
        "total_tasks": st["stats"]["total"],
        "by_state": st["stats"]["by_state"],
        "recent_logs": [f"[{l['time'][11:19]}] {l['msg']}" for l in recent],
    }


def _wf_list(queue, args):
    state = args.get("state")
    limit = args.get("limit", 20)
    tasks = queue.filter_tasks(state=state, limit=limit)
    return {
        "ok": True,
        "count": len(tasks),
        "tasks": [
            {
                "id": t["id"],
                "title": t["title"],
                "state": t["state"],
                "assignee": t.get("assignee"),
                "created_at": t.get("created_at", "")[:19],
            }
            for t in tasks
        ],
    }


if __name__ == "__main__":
    main()

