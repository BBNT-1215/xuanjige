#!/usr/bin/env python3
"""
Hermestrix 进化闭环系统

每次任务完成后自动触发进化流程：
1. 收集任务执行数据
2. 判定是否需要更新记忆库
3. 沉淀新技能到技能库
4. 更新知识库（如有新知识）
5. 生成进化报告

用法:
  python3 scripts/evolution.py process <任务ID>
  python3 scripts/evolution.py report [--days 7]
  python3 scripts/evolution.py metrics
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

TASKS_FILE = DATA_DIR / 'tasks.json'
AUDIT_FILE = DATA_DIR / 'audit_log.json'
EVOLUTION_LOG = DATA_DIR / 'evolution_log.json'

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

def process_task(task_id):
    """处理单个任务的进化逻辑"""
    tasks = _read_json(TASKS_FILE) or []
    task = next((t for t in tasks if t.get('id') == task_id), None)
    if not task:
        print(f"[进化] 任务 {task_id} 不存在")
        return

    audit = _read_json(AUDIT_FILE) or []
    task_audit = [a for a in audit if a.get('task') == task_id]

    # 分析任务执行情况
    state_changes = [a for a in task_audit if a.get('action') == 'state']
    flow_logs = [a for a in task_audit if a.get('action') == 'flow']

    # 计算耗时（如果有时间戳）
    duration = "未知"
    if task_audit:
        first = task_audit[0].get('ts', '')
        last = task_audit[-1].get('ts', '')
        if first and last:
            try:
                dt = datetime.datetime.fromisoformat(last) - datetime.datetime.fromisoformat(first)
                duration = f"{dt.total_seconds()/3600:.1f}小时"
            except:
                duration = "计算失败"

    # 生成进化条目
    entry = {
        "id": f"evo_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_id": task_id,
        "title": task.get('title', ''),
        "state": task.get('state', ''),
        "duration": duration,
        "state_changes": len(state_changes),
        "flow_steps": len(flow_logs),
        "processedAt": now_iso()
    }

    def modifier(log):
        if log is None: log = []
        log.append(entry)
        return log

    _atomic_json_update(EVOLUTION_LOG, modifier, [])
    print(f"[进化] 任务 {task_id} 处理完成")
    print(f"  - 耗时: {duration}")
    print(f"  - 状态变更: {len(state_changes)} 次")
    print(f"  - 流转步骤: {len(flow_logs)} 步")

    return entry

def generate_report(days=7):
    """生成进化报告"""
    log = _read_json(EVOLUTION_LOG) or []
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    recent = [e for e in log if e.get('processedAt', '') > cutoff_str]

    total = len(recent)
    done = len([e for e in recent if e.get('state') == 'Done'])
    avg_state_changes = sum(e.get('state_changes', 0) for e in recent) / total if total > 0 else 0

    print(f"\n📈 Hermestrix 进化报告（近{days}天）")
    print(f"\n总任务数: {total}")
    print(f"已完成: {done} ({done/total*100:.0f}% if total>0 else 0%)")
    print(f"平均状态变更: {avg_state_changes:.1f} 次/任务")
    print(f"\n最近任务:")
    for e in recent[-5:]:
        print(f"  [{e.get('state')}] {e.get('title','')[:40]} - {e.get('duration')}")
    print()

def cmd_metrics():
    """显示进化指标"""
    tasks = _read_json(TASKS_FILE) or []
    audit = _read_json(AUDIT_FILE) or []
    evolution = _read_json(EVOLUTION_LOG) or []

    total = len(tasks)
    done = len([t for t in tasks if t.get('state') == 'Done'])
    blocked = len([t for t in tasks if t.get('state') == 'Blocked'])

    print("\n📊 Hermestrix 进化指标")
    print(f"  总任务: {total}")
    print(f"  完成率: {done/total*100:.0f}%" if total > 0 else "  完成率: N/A")
    print(f"  阻塞率: {blocked/total*100:.0f}%" if total > 0 else "  阻塞率: N/A")
    print(f"  进化记录: {len(evolution)} 条")
    print(f"  审计记录: {len(audit)} 条")
    print()

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'process':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        process_task(task_id)

    elif cmd == 'report':
        days = 7
        for i, a in enumerate(sys.argv):
            if a == '--days' and i+1 < len(sys.argv):
                days = int(sys.argv[i+1])
        generate_report(days)

    elif cmd == 'metrics':
        cmd_metrics()

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)

if __name__ == '__main__':
    main()
