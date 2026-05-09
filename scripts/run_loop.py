#!/usr/bin/env python3
"""
Hermestrix 主循环

定期刷新看板数据、事件总线、自愈检测。

用法:
  python3 scripts/run_loop.py [--interval 15]
"""
import json
import pathlib
import sys
import os
import time
import datetime

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

TASKS_FILE = DATA_DIR / 'tasks.json'

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def load_tasks():
    if not TASKS_FILE.exists():
        return []
    try:
        return json.loads(TASKS_FILE.read_text(encoding='utf-8'))
    except:
        return []

def save_tasks(tasks):
    tmp = TASKS_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, TASKS_FILE)

def refresh_live_data():
    """刷新实时数据：补充 outputMeta、计算统计"""
    tasks = load_tasks()
    changed = False
    for t in tasks:
        # 补充 outputMeta
        if t.get('state') == 'Done' and t.get('output'):
            if 'outputMeta' not in t:
                p = pathlib.Path(t['output'])
                t['outputMeta'] = {
                    "exists": p.exists(),
                    "lastModified": datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S') if p.exists() else None
                }
                changed = True
        # 补充 updatedAt 缺失
        if 'updatedAt' not in t:
            t['updatedAt'] = t.get('createdAt', now_iso())
            changed = True
    if changed:
        save_tasks(tasks)
    return len(tasks)

def main():
    interval = 15
    for i, a in enumerate(sys.argv):
        if a == '--interval' and i+1 < len(sys.argv):
            interval = int(sys.argv[i+1])

    print(f"[Hermestrix] 主循环启动，刷新间隔 {interval} 秒")
    while True:
        try:
            count = refresh_live_data()
            print(f"[{now_iso()[:19]}] 刷新完成，当前 {count} 个任务", flush=True)
        except Exception as e:
            print(f"[Hermestrix] 刷新异常: {e}", flush=True)
        time.sleep(interval)

if __name__ == '__main__':
    main()
