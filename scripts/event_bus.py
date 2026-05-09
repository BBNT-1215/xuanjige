#!/usr/bin/env python3
"""
Hermestrix 事件总线

事件驱动通信：各Agent间通过事件总线异步通信。
支持：任务创建/状态变更/流转/进度/完成 等事件类型。

用法:
  python3 scripts/event_bus.py emit <event_type> <payload_json>
  python3 scripts/event_bus.py subscribe <event_type>
  python3 scripts/event_bus.py list [--type <type>]
  python3 scripts/event_bus.py pending
"""
import datetime
import json
import pathlib
import sys
import os
import time
import threading

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

EVENTS_FILE = DATA_DIR / 'events.json'
SUBSCRIPTIONS_FILE = DATA_DIR / 'subscriptions.json'
MAX_EVENTS = 1000

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
            time.sleep(0.1 * (attempt + 1))

# ── 事件类型定义 ─────────────────────────────────────────
EVENT_TYPES = [
    'task.created', 'task.state_changed', 'task.flow', 'task.progress',
    'task.done', 'task.blocked', 'task.cancelled',
    'agent.thought', 'agent.todo_update',
    'system.alert', 'system.recovery_triggered'
]

def emit_event(event_type, payload):
    """发布事件"""
    event = {
        "id": f"evt_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "type": event_type,
        "payload": payload,
        "timestamp": now_iso()
    }
    def modifier(events):
        if events is None: events = []
        events.append(event)
        if len(events) > MAX_EVENTS:
            events = events[-MAX_EVENTS:]
        return events
    _atomic_json_update(EVENTS_FILE, modifier, [])
    print(f"[事件总线] {event_type}: {payload.get('task_id', '')}", flush=True)

def list_events(event_type=None, limit=50):
    """列出事件"""
    events = _read_json(EVENTS_FILE) or []
    if event_type:
        events = [e for e in events if e.get('type') == event_type]
    print(f"\n📡 事件总线（共 {len(events)} 条）\n")
    for e in events[-limit:]:
        print(f"[{e.get('timestamp')[:19]}] {e.get('type')}: {str(e.get('payload',''))[:80]}")
    print()

def cmd_pending():
    """显示待处理事件"""
    events = _read_json(EVENTS_FILE) or []
    last_5 = events[-5:]
    print("\n📡 待处理事件（最近5条）")
    for e in last_5:
        print(f"[{e.get('type')}] {e.get('payload', '')}")
    print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'emit':
        event_type = sys.argv[2] if len(sys.argv) > 2 else ''
        payload_json = sys.argv[3] if len(sys.argv) > 3 else '{}'
        try:
            payload = json.loads(payload_json)
        except:
            payload = {"raw": payload_json}
        emit_event(event_type, payload)

    elif cmd == 'list':
        event_type = None
        for i, a in enumerate(sys.argv):
            if a == '--type' and i+1 < len(sys.argv):
                event_type = sys.argv[i+1]
        list_events(event_type)

    elif cmd == 'pending':
        cmd_pending()

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)

if __name__ == '__main__':
    main()
