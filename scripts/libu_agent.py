#!/usr/bin/env python3
"""
Hermestrix 吏部常驻进程

职责：
1. 三库守护者——监听任务完成事件，自动触发进化分析
2. 定期生成进化报告
3. 响应三库检索请求

启动：
  python3 scripts/libu_agent.py [--poll-interval 5]

常驻模式：
  - 监听事件总线（通过文件轮询）
  - 或定时扫描tasks.json的Done任务
"""

import datetime
import json
import pathlib
import sys
import os
import time

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
TASKS_FILE = DATA_DIR / 'tasks.json'
EVENTS_FILE = DATA_DIR / 'events.json'
SKILLS_DIR = _BASE / 'skills'
AGENTS_DIR = _BASE / 'agents'

# 进化引擎
sys.path.insert(0, str(_BASE / 'scripts'))

import importlib.util

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

try:
    evolution_engine = _load_module('evolution', _BASE / 'scripts' / 'evolution_engine.py')
    skill_lib = _load_module('skill_lib', _BASE / 'scripts' / 'skill_library.py')
    role_lib = _load_module('role_lib', _BASE / 'scripts' / 'role_library.py')
except Exception as e:
    print(f"[吏部] 警告：无法加载进化引擎模块: {e}")
    evolution_engine = None
    skill_lib = None
    role_lib = None

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def _read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return None

def _write_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

# ── 事件总线 ─────────────────────────────────────────────

def emit_event(event_type, payload):
    """向事件总线发送事件"""
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    events = _read_json(EVENTS_FILE) or []
    entry = {
        "id": f"evt_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "type": event_type,
        "payload": payload,
        "timestamp": now_iso()
    }
    events.append(entry)
    
    # 保留最近1000条
    if len(events) > 1000:
        events = events[-1000:]
    
    _write_json(EVENTS_FILE, events)
    print(f"[吏部] 📡 事件已记录: {event_type}", flush=True)


# ── 吏部核心逻辑 ───────────────────────────────────────

def on_task_done(task_id):
    """任务完成时触发进化分析"""
    if not evolution_engine:
        print(f"[吏部] ⚠️ 进化引擎未加载，跳过任务 {task_id}")
        return
    
    try:
        print(f"[吏部] 🔄 触发进化分析: {task_id}", flush=True)
        result = evolution_engine.evolve_task(task_id)
        
        if 'error' in result:
            print(f"[吏部] ⚠️ {result['error']}")
        else:
            print(f"[吏部] ✅ 进化完成: {result.get('task_id')} - 进化项: {result.get('evolved_items', [])}")
    except Exception as e:
        print(f"[吏部] ❌ 进化分析失败: {e}", flush=True)


def on_task_created(task_id, task_title, official):
    """新任务创建时记录"""
    print(f"[吏部] 📝 新任务: [{task_id}] {task_title} (旨意: {official})", flush=True)
    emit_event('libu.task.created', {'task_id': task_id, 'title': task_title})


def daily_report():
    """每日进化报告"""
    if not evolution_engine:
        return
    
    try:
        report = evolution_engine.generate_evolution_report(days=1)
        print(f"\n{'='*50}")
        print(f"[吏部] 📊 每日进化报告 ({report.get('timestamp', '')})")
        print(f"{'='*50}")
        print(f"  今日完成: {report.get('total_done', 0)} 项任务")
        print(f"  平均质量: {report.get('avg_quality', 0):.2%}")
        
        role_stats = report.get('role_stats', {})
        if role_stats:
            print(f"  角色活跃度:")
            for role, count in sorted(role_stats.items(), key=lambda x: -x[1])[:5]:
                print(f"    - {role}: {count}次")
        
        skill_stats = report.get('skill_stats', [])
        if skill_stats:
            evolved = [s for s in skill_stats if s.get('evolve_count', 0) > 0]
            if evolved:
                print(f"  技能进化:")
                for s in evolved[:3]:
                    print(f"    - {s['id']}: 进化{s['evolve_count']}次, 有效度{s['effectiveness']:.3f}")
        print()
    except Exception as e:
        print(f"[吏部] ⚠️ 报告生成失败: {e}", flush=True)


# ── 主循环 ─────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Hermestrix 吏部常驻进程')
    parser.add_argument('--poll-interval', type=int, default=10,
                        help='轮询间隔(秒)，默认10秒')
    parser.add_argument('--once', action='store_true',
                        help='单次运行后退出（用于测试）')
    args = parser.parse_args()
    
    print(f"""
╔═══════════════════════════════════════════╗
║   Hermestrix 吏部常驻进程                 ║
║   三库守护者 · 进化引擎                   ║
╚═══════════════════════════════════════════╝
""", flush=True)
    
    # 初始化Role库
    if role_lib:
        try:
            role_lib.scan_roles()
            print(f"[吏部] ✅ Role库扫描完成", flush=True)
        except Exception as e:
            print(f"[吏部] ⚠️ Role库扫描失败: {e}", flush=True)
    
    # 扫描已完成任务并进化（启动时一次性执行）
    print(f"[吏部] 🔍 启动时扫描已完成任务...", flush=True)
    tasks = _read_json(TASKS_FILE) or []
    done_tasks = [t for t in tasks if t.get('state') == 'Done']
    print(f"[吏部] 发现 {len(done_tasks)} 个已完成任务", flush=True)
    
    last_daily_report = datetime.datetime.now().date()
    last_evolution_check = {}  # task_id -> last_checked_time
    
    if args.once:
        # 单次运行模式
        for t in done_tasks:
            on_task_done(t.get('id'))
        daily_report()
        return
    
    print(f"[吏部] ▶ 常驻监听中（轮询间隔 {args.poll_interval}秒）...", flush=True)
    
    while True:
        try:
            tasks = _read_json(TASKS_FILE) or []
            
            # 检查新完成的任务
            for t in tasks:
                if t.get('state') == 'Done':
                    tid = t.get('id')
                    # 检查是否已处理过
                    last_check = last_evolution_check.get(tid)
                    updated = t.get('updatedAt', '')
                    
                    if last_check != updated:
                        on_task_done(tid)
                        last_evolution_check[tid] = updated
            
            # 每日报告（每天0点执行）
            today = datetime.datetime.now().date()
            if today > last_daily_report:
                daily_report()
                last_daily_report = today
            
            time.sleep(args.poll_interval)
            
        except KeyboardInterrupt:
            print(f"\n[吏部] 🛑 收到中断信号，正在停止...", flush=True)
            break
        except Exception as e:
            print(f"[吏部] ⚠️ 异常: {e}", flush=True)
            time.sleep(args.poll_interval)


if __name__ == '__main__':
    main()
