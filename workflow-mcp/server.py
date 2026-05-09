#!/usr/bin/env python3
"""
玄机阁 MCP Server
=================
通过MCP协议暴露工作流引擎工具给Hermes Agent使用。

暴露工具：
  workflow_submit    提交新任务
  workflow_process  执行单任务流程
  workflow_status   查看引擎状态
  workflow_list     列出任务
  workflow_trace    查看任务流转历史
  workflow_start    启动引擎
  workflow_stop     停止引擎

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

# ── Setup path so we can import the workflow engine ──
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Read request from stdin, write response to stdout ──
# MCP protocol: JSON-RPC over stdio


def main():
    """Main loop: read JSON-RPC requests from stdin, respond to stdout"""
    import signal

    # Ignore SIGPIPE
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    # Import engine components (after path setup)
    from workflow.engine import get_engine
    from workflow.task_queue import get_queue

    engine = get_engine()
    queue = get_queue()

    # Read lines from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request, engine, queue)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def handle_request(req, engine, queue):
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
                        "description": "提交新任务到玄机阁工作流引擎。任务会自动走完：承旨分拣→机衡调度→六部执行→早朝汇总→御史审核的完整流程。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "任务标题"},
                                "description": {"type": "string", "description": "任务描述"},
                                "tags": {"type": "string", "description": "标签(逗号分隔)"},
                                "priority": {"type": "integer", "description": "优先级(数字,越大越优先)", "default": 0},
                            },
                            "required": ["title"],
                        },
                    },
                    {
                        "name": "workflow_process",
                        "description": "推进任务到下一步。如果任务需要实际执行（delegate指令存在），请先用delegate_task执行对应Agent，再调用本工具推进状态。返回结果中的needs_execution=true表示需要先delegate执行。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string", "description": "任务ID"},
                            },
                            "required": ["task_id"],
                        },
                    },
                    {
                        "name": "workflow_status",
                        "description": "查看玄机阁工作流引擎的当前状态，包括各状态任务数量和最近日志。",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "workflow_list",
                        "description": "列出玄机阁中的任务列表，支持按状态过滤。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "state": {"type": "string", "description": "按状态过滤(如:待分拣/执行中/已完成)"},
                                "limit": {"type": "integer", "description": "返回数量上限", "default": 20},
                            },
                        },
                    },
                    {
                        "name": "workflow_trace",
                        "description": "查看某个任务的完整流转记录，包括每个步骤的时间和执行Agent。",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "task_id": {"type": "string", "description": "任务ID"},
                            },
                            "required": ["task_id"],
                        },
                    },
                    {
                        "name": "workflow_start",
                        "description": "启动玄机阁工作流引擎（后台自动处理待分拣任务）。",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "workflow_stop",
                        "description": "停止玄机阁工作流引擎。",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ],
            },
        }

    if method == "tools/call":
        tool_name = req.get("params", {}).get("name", "")
        arguments = req.get("params", {}).get("arguments", {})

        try:
            if tool_name == "workflow_submit":
                result = _wf_submit(engine, arguments)
            elif tool_name == "workflow_process":
                result = _wf_process(engine, arguments)
            elif tool_name == "workflow_status":
                result = _wf_status(engine)
            elif tool_name == "workflow_list":
                result = _wf_list(queue, arguments)
            elif tool_name == "workflow_trace":
                result = _wf_trace(queue, arguments)
            elif tool_name == "workflow_start":
                result = _wf_start(engine)
            elif tool_name == "workflow_stop":
                result = _wf_stop(engine)
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


# ── Tool implementations ───────────────────────────────────

def _wf_start(engine):
    if not engine.running:
        engine.start()
    return {"ok": True, "status": "engine_started", "running": engine.running}


def _wf_stop(engine):
    engine.stop()
    return {"ok": True, "status": "engine_stopped", "running": engine.running}


def _wf_submit(engine, args):
    tags = None
    if args.get("tags"):
        tags = [t.strip() for t in args["tags"].split(",")]

    task = engine.submit(
        title=args["title"],
        description=args.get("description", ""),
        tags=tags,
        priority=args.get("priority", 0),
    )
    return {
        "ok": True,
        "task_id": task["id"],
        "title": task["title"],
        "state": task["state"],
        "message": f"任务已提交(ID={task['id']})，当前状态：{task['state']}",
    }


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

    # 关键：暴露delegate指令，告诉Hermes需要实际执行
    if result.get("delegate"):
        resp["delegate"] = result["delegate"]
        resp["needs_execution"] = True
        resp["message"] += f"\n⚠️ 需要通过 delegate_task 执行：{result['delegate']['role_name']}"

    return resp


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
    tasks = queue.list(state=state, limit=limit)
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


if __name__ == "__main__":
    main()
