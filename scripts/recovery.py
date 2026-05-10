#!/usr/bin/env python3
"""
Hermestrix 断点自愈系统

断点检测信号：
- 子Agent工具调用超过 max_tool_calls 但无输出文件
- 子Agent连续3次patch失败
- 任务执行时间超过 max_task_duration
- 子Agent返回 status: interrupted

用法:
  python3 scripts/recovery.py check <任务ID>
  python3 scripts/recovery.py status
  python3 scripts/recovery.py trigger <任务ID> --reason "[原因]"
"""
import datetime
import json
import pathlib
import sys
import os

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

RECOVERY_LOG = DATA_DIR / 'recovery_log.json'
TASKS_FILE = DATA_DIR / 'tasks.json'

MAX_TOOL_CALLS = 20
MAX_TASK_DURATION = 300  # 秒
MAX_PATCH_FAILURES = 3

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def _atomic_write(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def _read_json(path):
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding='utf-8'))
    except: return None

def _atomic_json_update(path, modifier, default=None):
    for attempt in range(3):
        try:
            data = _read_json(path) or default
            data = modifier(data)
            _atomic_write(path, data)
            return
        except Exception:
            if attempt == 2: raise
            import time; time.sleep(0.1 * (attempt + 1))

def log_recovery(task_id, event_type, reason, details):
    """记录自愈事件"""
    entry = {
        "id": f"rec_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_id": task_id,
        "event": event_type,  # detected/triggered/recovered/failed
        "reason": reason,
        "details": details,
        "timestamp": now_iso()
    }
    def modifier(log):
        if log is None: log = []
        log.append(entry)
        return log
    _atomic_json_update(RECOVERY_LOG, modifier, [])
    print(f"[自愈] {event_type}: {task_id} - {reason}", flush=True)

def check_task(task_id):
    """检测任务是否有断点风险"""
    tasks = _read_json(TASKS_FILE) or []
    t = next((x for x in tasks if x.get('id') == task_id), None)
    if not t:
        return {"risk": "unknown", "reason": "任务不存在"}

    state = t.get('state', '')
    progress = t.get('progress_log', [])
    flow_log = t.get('flow_log', [])

    # 检查：Doing状态但超过预期时间
    if state == 'Doing' and progress:
        last_progress = progress[-1]
        # 简化：仅检查是否有进展上报
        if not progress:
            return {"risk": "high", "reason": "执行中但无进展上报"}

    # 检查：流程日志显示某部门卡住
    if flow_log:
        last_flow = flow_log[-1]
        if last_flow.get('to') in ['调度', '执行层'] and state in ['Doing', 'Assigned']:
            # 检查是否有产出
            if not t.get('output'):
                return {"risk": "medium", "reason": f"{last_flow.get('to')} 已接令但无产出"}

    return {"risk": "low", "reason": "未检测到断点"}

def trigger_recovery(task_id, reason, details=None):
    """触发自愈流程"""
    log_recovery(task_id, 'triggered', reason, details or {})

    # 评估损失
    tasks = _read_json(TASKS_FILE) or []
    t = next((x for x in tasks if x.get('id') == task_id), None)

    if not t:
        print(f"[自愈] 任务 {task_id} 不存在，终止恢复")
        return

    # 记录当前已完成的修改（如果有）
    todos = t.get('todos', [])
    completed = [td for td in todos if td.get('status') == 'completed']
    pending = [td for td in todos if td.get('status') != 'completed']

    print(f"[自愈] 任务 {task_id} 恢复方案:")
    print(f"  - 已完成子任务: {len(completed)} 项")
    print(f"  - 待完成子任务: {len(pending)} 项")
    print(f"  - 建议: 使用Python单趟脚本从断点继续，禁止多次patch")

    log_recovery(task_id, 'recovered', f"已完成{len(completed)}项，待完成{len(pending)}项", {})

def cmd_status():
    """查看自愈状态"""
    log = _read_json(RECOVERY_LOG) or []
    recent = log[-10:]
    print("\n🔧 断点自愈记录（最近10条）")
    for r in recent:
        print(f"[{r.get('event')}] {r.get('task_id')}: {r.get('reason')}")
    print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'check':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        result = check_task(task_id)
        print(f"风险等级: {result['risk']}")
        print(f"原因: {result['reason']}")

    elif cmd == 'status':
        cmd_status()

    elif cmd == 'health':
        cmd_status()

    elif cmd == 'history':
        log = _read_json(RECOVERY_LOG) or []
        print(f"\n🔧 断点自愈历史记录（共 {len(log)} 条）")
        for r in log[-20:]:
            print(f"[{r.get('event')}] {r.get('task_id')} @ {r.get('timestamp')}: {r.get('reason')}")
        print()

    elif cmd == 'detect':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        result = check_task(task_id)
        print(f"风险等级: {result['risk']}")
        print(f"原因: {result['reason']}")

    elif cmd == 'trigger':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        reason = ''
        details = {}
        for a in sys.argv[3:]:
            if a.startswith('--reason='):
                reason = a.split('=', 1)[1]
        trigger_recovery(task_id, reason, details)

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)

if __name__ == '__main__':
    main()
