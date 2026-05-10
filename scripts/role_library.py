#!/usr/bin/env python3
"""
Hermestrix Role库核心

Role = 角色定义 + 元数据 + 组合历史 + 进化记录

Role库 = agents/目录下所有角色定义文件的索引管理系统
"""

import datetime
import json
import pathlib
import sys
import os

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
AGENTS_DIR = _BASE / 'agents'
DATA_DIR = _BASE / 'data'
ROLE_INDEX = DATA_DIR / 'role_index.json'

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def _read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return None

def _atomic_json_update(path, modifier, default=None):
    for attempt in range(3):
        try:
            data = _read_json(path) or default
            data = modifier(data)
            _atomic_write(path, data)
            return
        except Exception:
            if attempt == 2:
                raise
            import time; time.sleep(0.1 * (attempt + 1))

def _ensure_index():
    if not ROLE_INDEX.exists():
        _atomic_write(ROLE_INDEX, {
            "roles": {},
            "combinations": {},
            "last_updated": now_iso()
        })

# ── Role 注册 & 扫描 ─────────────────────────────────────

def scan_roles():
    """扫描agents/目录，建立所有角色的元数据"""
    _ensure_index()
    
    roles = {}
    for role_dir in AGENTS_DIR.iterdir():
        if not role_dir.is_dir():
            continue
        role_id = role_dir.name
        soul_file = role_dir / 'SOUL.md'
        meta_file = role_dir / 'METADATA.json'
        
        # 读取SOUL
        soul_exists = soul_file.exists()
        soul_lines = 0
        if soul_exists:
            soul_lines = len(soul_file.read_text(encoding='utf-8').splitlines())
            # 提取SOUL中的职责描述
            soul_preview = soul_file.read_text(encoding='utf-8')[:200]
        else:
            soul_preview = ""
        
        # 读取或创建METADATA
        if meta_file.exists():
            meta = _read_json(meta_file)
        else:
            meta = _create_default_metadata(role_id, soul_preview)
            _atomic_write(meta_file, meta)
        
        roles[role_id] = {
            "role_id": role_id,
            "soul_exists": soul_exists,
            "soul_lines": soul_lines,
            "metadata": meta,
            "status": "active" if soul_exists else "incomplete"
        }
    
    # 更新索引
    def modifier(idx):
        idx['roles'] = roles
        idx['last_updated'] = now_iso()
        return idx
    _atomic_json_update(ROLE_INDEX, modifier)
    
    return roles


def _create_default_metadata(role_id, soul_preview=""):
    """为新角色创建默认METADATA"""
    role_names = {
        "chengzhi": "太子", "jiheng": "机衡", "shenyi": "审议",
        "jiheng": "调度", "shusuan": "数算", "diancang": "文册",
        "bingrong": "兵戎", "xingce": "刑策", "jixuan": "技造",
        "jiyan": "机研", "zaohuang": "玄档官", "qitian": "钦天监"
    }
    
    return {
        "role_id": role_id,
        "role_name": role_names.get(role_id, role_id),
        "version": 1,
        "created_at": now_iso(),
        "last_evolved": now_iso(),
        "evolve_count": 0,
        
        # 职责描述（从SOUL提取）
        "description": soul_preview.replace('\n', ' ')[:200] if soul_preview else "",
        
        # 任务统计
        "task_stats": {
            "assigned_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "avg_duration_minutes": 0,
            "last_assigned": None
        },
        
        # 技能关联（这个Role执行时需要的技能）
        "required_skills": [],
        "optional_skills": [],
        
        # 组合历史（这个Role和谁组合过）
        "combined_with": {},  # {role_id: count}
        "avoid_combination": [],
        
        # 任务类型分布
        "task_type_distribution": {},  # {task_type: count}
        
        # 质量评分
        "quality_score": 0.50,
    }


# ── Role 统计更新 ─────────────────────────────────────────

def record_role_execution(role_id, task_type=None, success=True,
                         duration_minutes=0, quality=None,
                         combined_roles=None):
    """
    记录角色执行情况（触发进化）
    """
    meta_file = AGENTS_DIR / role_id / 'METADATA.json'
    if not meta_file.exists():
        return
    
    combined_roles = combined_roles or []
    
    def modifier(meta):
        stats = meta.get('task_stats', {})
        stats['assigned_count'] = stats.get('assigned_count', 0) + 1
        
        if success:
            stats['success_count'] = stats.get('success_count', 0) + 1
        else:
            stats['failure_count'] = stats.get('failure_count', 0) + 1
        
        # 更新平均时长
        prev = stats.get('avg_duration_minutes', 0)
        n = stats['assigned_count']
        stats['avg_duration_minutes'] = round((prev * (n-1) + duration_minutes) / n, 1)
        stats['last_assigned'] = now_iso()
        
        meta['task_stats'] = stats
        
        # 更新组合历史
        for co_role in combined_roles:
            meta.setdefault('combined_with', {})[co_role] = \
                meta['combined_with'].get(co_role, 0) + 1
        
        # 更新任务类型分布
        if task_type:
            meta.setdefault('task_type_distribution', {})[task_type] = \
                meta['task_type_distribution'].get(task_type, 0) + 1
        
        # 更新质量评分
        if quality is not None:
            prev_q = meta.get('quality_score', 0.50)
            meta['quality_score'] = round((prev_q * 0.7 + quality * 0.3), 4)
        
        # 进化检测
        if stats['assigned_count'] % 10 == 0:
            meta['version'] += 1
            meta['evolve_count'] += 1
            meta['last_evolved'] = now_iso()
            print(f"[Role库] 🔄 Role {role_id} 进化: v{meta['version']} (执行{stats['assigned_count']}次)")
        
        return meta
    
    _atomic_json_update(meta_file, modifier)


# ── Role 检索 ────────────────────────────────────────────

def query_roles(task_type=None, required_skill=None, 
                min_quality=None, limit=10):
    """
    根据任务特征查找最合适的Role
    
    Args:
        task_type: 任务类型
        required_skill: 需要的技能
        min_quality: 最低质量评分
        limit: 返回数量
    """
    _ensure_index()
    roles = scan_roles()
    
    candidates = []
    for role_id, role_info in roles.items():
        if role_info['status'] != 'active':
            continue
        
        meta = role_info.get('metadata', {})
        
        # 质量过滤
        quality = meta.get('quality_score', 0.50)
        if min_quality and quality < min_quality:
            continue
        
        # 技能匹配
        if required_skill:
            req_skills = meta.get('required_skills', [])
            opt_skills = meta.get('optional_skills', [])
            if required_skill not in req_skills and required_skill not in opt_skills:
                continue
        
        # 计算综合分
        score = _compute_role_score(meta, task_type)
        candidates.append((role_id, score, meta))
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [(rid, meta) for rid, score, meta in candidates[:limit]]


def _compute_role_score(meta, task_type):
    """计算Role的综合匹配分"""
    score = 0.0
    
    # 质量评分贡献
    score += meta.get('quality_score', 0.50) * 0.40
    
    # 任务成功率贡献
    stats = meta.get('task_stats', {})
    total = stats.get('success_count', 0) + stats.get('failure_count', 0)
    if total > 0:
        rate = stats.get('success_count', 0) / total
        score += rate * 0.30
    
    # 经验加成（执行次数）
    count = stats.get('assigned_count', 0)
    score += min(count / 100, 0.20)
    
    # 任务类型匹配
    if task_type:
        dist = meta.get('task_type_distribution', {})
        type_count = dist.get(task_type, 0)
        score += min(type_count / 20, 0.10)
    
    return max(0.0, min(1.0, score))


# ── 组合推荐 ─────────────────────────────────────────────

def recommend_combination(task_type=None, complexity="medium"):
    """
    根据任务类型推荐Role组合
    
    Returns:
        (primary_roles, supporting_roles)
    """
    # 复杂度决定参与角色数量
    complexity_map = {
        "simple": 1,
        "medium": 2,
        "complex": 3,
        "critical": 4
    }
    
    n = complexity_map.get(complexity, 2)
    
    # 查询各维度最合适的角色
    if task_type:
        roles = query_roles(task_type=task_type, limit=n*2)
    else:
        roles = query_roles(limit=n*2)
    
    if not roles:
        # 默认组合
        return ["jiheng"], ["shusuan"]
    
    role_ids = [r[0] for r in roles]
    
    # 分离主角色和辅助角色
    # 主角色：调度必须，核心执行部门
    primary = ["jiheng"] if "jiheng" in role_ids else [role_ids[0]]
    supporting = [r for r in role_ids[1:n] if r != "jiheng"]
    
    return primary, supporting


# ── CLI ──────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("用法: role_library.py [scan|list|stats|recommend|get]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'scan':
        roles = scan_roles()
        print(f"\n🔍 扫描完成（共 {len(roles)} 个角色）\n")
        for rid, info in roles.items():
            status = "✅" if info['status'] == 'active' else "⚠️"
            meta = info.get('metadata', {})
            stats = meta.get('task_stats', {})
            print(f"  {status} {rid}: {meta.get('role_name','')}")
            print(f"       SOUL: {info['soul_lines']}行 | v{meta.get('version',1)}")
            print(f"       执行: {stats.get('assigned_count',0)}次 | 质量: {meta.get('quality_score',0):.2f}")
            print()
    
    elif cmd == 'list':
        roles = scan_roles()
        print(f"\n📋 Role库（共 {len(roles)} 项）\n")
        for rid, info in roles.items():
            meta = info.get('metadata', {})
            print(f"  [{meta.get('role_name', rid)}] {rid}")
    
    elif cmd == 'stats':
        role_id = sys.argv[2] if len(sys.argv) > 2 else 'jiheng'
        meta_file = AGENTS_DIR / role_id / 'METADATA.json'
        if meta_file.exists():
            meta = _read_json(meta_file)
            print(json.dumps(meta, ensure_ascii=False, indent=2))
        else:
            print(f"[Role库] Role {role_id} 不存在")
    
    elif cmd == 'recommend':
        task_type = sys.argv[2] if len(sys.argv) > 2 else None
        complexity = sys.argv[3] if len(sys.argv) > 3 else 'medium'
        primary, supporting = recommend_combination(task_type, complexity)
        print(f"\n🎯 推荐组合（复杂度: {complexity}）")
        print(f"  主角色: {', '.join(primary)}")
        print(f"  辅助角色: {', '.join(supporting)}")
    
    elif cmd == 'get':
        role_id = sys.argv[2] if len(sys.argv) > 2 else ''
        if not role_id:
            print("用法: role_library.py get <role_id>")
            return
        meta_file = AGENTS_DIR / role_id / 'METADATA.json'
        if meta_file.exists():
            print(json.dumps(_read_json(meta_file), ensure_ascii=False, indent=2))
        else:
            print(f"[Role库] Role {role_id} 不存在")
    
    else:
        print(f"未知命令: {cmd}")


if __name__ == '__main__':
    main()
