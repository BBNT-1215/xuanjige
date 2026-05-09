#!/usr/bin/env python3
"""
Hermestrix 进化引擎

当任务完成时，自动触发进化分析：
1. 分析任务执行记录
2. 更新Skill库评分
3. 更新Role库统计
4. 生成进化报告
"""

import datetime
import json
import pathlib
import sys
import os

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
TASKS_FILE = DATA_DIR / 'tasks.json'

# 导入内部模块
sys.path.insert(0, str(_BASE / 'scripts'))
from skill_library import record_execution, add_best_practice, list_skills
from role_library import record_role_execution, scan_roles

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def _read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return None

# ── 任务分析 ─────────────────────────────────────────────

def analyze_task(task):
    """
    分析任务执行记录，提取进化所需信息
    """
    task_id = task.get('id')
    state = task.get('state')
    org = task.get('org')
    
    # 判断成功/失败
    success = state == 'Done'
    
    # 从flow_log推断参与角色
    flow_log = task.get('flow_log', [])
    participating_roles = []
    for entry in flow_log:
        agent = entry.get('agent', '')
        if agent and agent not in participating_roles:
            participating_roles.append(agent)
    
    # 从todos推断质量
    todos = task.get('todos', [])
    completed_todos = [t for t in todos if t.get('status') == 'completed']
    todo_quality = len(completed_todos) / max(len(todos), 1)
    
    # 估算时长（从createdAt到updatedAt）
    created = task.get('createdAt', now_iso())
    updated = task.get('updatedAt', now_iso())
    try:
        c = datetime.datetime.fromisoformat(created)
        u = datetime.datetime.fromisoformat(updated)
        duration_min = (u - c).total_seconds() / 60
    except:
        duration_min = 0
    
    return {
        'task_id': task_id,
        'success': success,
        'participating_roles': participating_roles,
        'todo_quality': todo_quality,
        'duration_min': duration_min,
        'state': state,
        'org': org,
        'title': task.get('title', ''),
    }

# ── 进化分析 ─────────────────────────────────────────────

def evolve_task(task_id):
    """
    对已完成任务执行进化分析
    """
    tasks = _read_json(TASKS_FILE) or []
    task = next((t for t in tasks if t.get('id') == task_id), None)
    
    if not task:
        return {'error': f'任务 {task_id} 不存在'}
    
    analysis = analyze_task(task)
    
    if not analysis['success']:
        return {
            'task_id': task_id,
            'action': 'skip',
            'reason': '任务未完成，跳过进化分析'
        }
    
    evolved = []
    
    # 1. 更新Role库统计
    for role_id in analysis['participating_roles']:
        try:
            record_role_execution(
                role_id=role_id,
                success=analysis['success'],
                duration_minutes=int(analysis['duration_min']),
                quality=analysis['todo_quality'],
                combined_roles=[r for r in analysis['participating_roles'] if r != role_id]
            )
            evolved.append(f'role:{role_id}')
        except Exception as e:
            pass  # Role可能不在agents/目录中
    
    # 2. 根据任务类型自动记录技能执行
    _auto_record_skill_execution(task, analysis)
    
    # 3. 记录吏部HR的执行
    try:
        record_role_execution(
            role_id='jiyan',
            task_type=_infer_task_type(task.get('title', '')),
            success=analysis['success'],
            duration_minutes=int(analysis['duration_min']),
            quality=analysis['todo_quality']
        )
        evolved.append('role:jiyan')
    except:
        pass
    
    # 4. 生成进化摘要
    evolution_summary = {
        'task_id': task_id,
        'evolved_items': evolved,
        'quality': analysis['todo_quality'],
        'duration_min': analysis['duration_min'],
        'roles': analysis['participating_roles'],
        'timestamp': now_iso()
    }
    
    return evolution_summary


def _auto_record_skill_execution(task, analysis):
    """
    根据任务标题自动推断并记录技能执行
    """
    title = task.get('title', '').lower()
    
    skill_mapping = {
        '代码': 'skill_code_review',
        '审查': 'skill_code_review',
        '文档': 'skill_doc_writing',
        '测试': 'skill_qa_testing',
        '架构': 'skill_architecture_design',
        '设计': 'skill_architecture_design',
        '分析': 'skill_data_analysis',
        '数据': 'skill_data_analysis',
        '调研': 'skill_research',
        '部署': 'skill_deployment',
        '安全': 'skill_security_audit',
        '归档': 'skill_knowledge_archive',
        '看板': 'skill_kanban_crud',
    }
    
    for keyword, skill_id in skill_mapping.items():
        if keyword in title:
            try:
                record_execution(
                    skill_id=skill_id,
                    success=analysis['success'],
                    duration_minutes=int(analysis['duration_min']),
                    quality_score=analysis['todo_quality'],
                    notes=f"任务: {task.get('title', '')}"
                )
            except:
                pass
            break  # 只匹配一个最相关的


def _infer_task_type(title):
    """从任务标题推断任务类型"""
    title = title.lower()
    if any(k in title for k in ['代码', '开发', '重构']):
        return '开发'
    elif any(k in title for k in ['文档', '撰写', '写作']):
        return '文档'
    elif any(k in title for k in ['调研', '研究', '分析']):
        return '调研'
    elif any(k in title for k in ['测试', '验证']):
        return '测试'
    elif any(k in title for k in ['部署', '上线', '发布']):
        return '部署'
    elif any(k in title for k in ['架构', '设计', '方案']):
        return '架构'
    else:
        return '通用'


# ── 进化报告 ─────────────────────────────────────────────

def generate_evolution_report(days=7):
    """
    生成进化报告
    """
    tasks = _read_json(TASKS_FILE) or []
    
    # 过滤近N天完成的任务
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    recent_done = []
    
    for t in tasks:
        if t.get('state') != 'Done':
            continue
        updated = t.get('updatedAt', '')
        if updated:
            try:
                u = datetime.datetime.fromisoformat(updated)
                if u >= cutoff:
                    recent_done.append(t)
            except:
                pass
    
    if not recent_done:
        return {
            'days': days,
            'total_done': 0,
            'message': f'近{days}天无完成任务'
        }
    
    # 统计进化
    total_quality = sum(
        len([td for td in t.get('todos', []) if td.get('status') == 'completed']) /
        max(len(t.get('todos', [])), 1)
        for t in recent_done
    ) / len(recent_done)
    
    # Role统计
    role_stats = {}
    for t in recent_done:
        for entry in t.get('flow_log', []):
            agent = entry.get('agent', '')
            if agent:
                role_stats[agent] = role_stats.get(agent, 0) + 1
    
    # Skill进化
    skill_stats = []
    for s in list_skills():  # 获取所有skill
        if s:
            skill_stats.append({
                'id': s.get('id'),
                'effectiveness': s.get('effectiveness'),
                'success_count': s.get('success_count'),
                'evolve_count': s.get('evolve_count', 0)
            })
    
    return {
        'days': days,
        'total_done': len(recent_done),
        'avg_quality': round(total_quality, 3),
        'role_stats': role_stats,
        'skill_stats': sorted(skill_stats, key=lambda x: x['evolve_count'], reverse=True)[:10],
        'timestamp': now_iso()
    }


# ── CLI ──────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("用法:")
        print("  evolution_engine.py analyze <任务ID>  - 分析单个任务")
        print("  evolution_engine.py report [days]      - 生成进化报告")
        print("  evolution_engine.py scan              - 扫描并进化所有完成任务")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'analyze':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        result = evolve_task(task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif cmd == 'report':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        report = generate_evolution_report(days)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    
    elif cmd == 'scan':
        # 扫描所有Done任务并进化
        tasks = _read_json(TASKS_FILE) or []
        done_tasks = [t for t in tasks if t.get('state') == 'Done']
        
        evolved_count = 0
        for t in done_tasks:
            result = evolve_task(t.get('id'))
            if 'error' not in result:
                evolved_count += 1
        
        print(f"[进化引擎] 扫描完成，{evolved_count}/{len(done_tasks)} 个任务已进化")
    
    else:
        print(f"未知命令: {cmd}")


if __name__ == '__main__':
    main()
