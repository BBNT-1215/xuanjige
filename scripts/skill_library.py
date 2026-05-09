#!/usr/bin/env python3
"""
Hermestrix Skill库核心

Skill = "用什么方法做" 的经验沉淀
支持进化：评分、适用特征、失败模式、最佳实践

数据结构：
  skills/{skill_id}.json      - 技能定义+评分
  skills/{skill_id}/history/  - 历史执行记录
  skills/skill_index.json     - 全量索引
"""

import datetime
import json
import pathlib
import sys
import os

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
SKILLS_DIR = _BASE / 'skills'
SKILLS_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_INDEX = DATA_DIR / 'skill_index.json'

# 默认评分权重（可随进化调整）
_WEIGHT_EFFECTIVENESS = 0.40
_WEIGHT_SUCCESS_RATE = 0.30
_WEIGHT_RECENCY = 0.15
_WEIGHT_COMPLEXITY = 0.15

# ── 基础读写 ──────────────────────────────────────────────

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
    if not SKILLS_INDEX.exists():
        _atomic_write(SKILLS_INDEX, {
            "skills": [],
            "domains": {},
            "last_updated": now_iso()
        })

# ── Skill CRUD ────────────────────────────────────────────

def register_skill(skill_id, name, domain, description="",
                   applicable_tasks=None, inapplicable_tasks=None,
                   best_practices=None, method="", effectiveness=None):
    """
    注册新技能
    
    Args:
        skill_id: 唯一标识，如 "code_review_python"
        name: 中文名，如 "Python代码审查"
        domain: 领域，如 "开发"
        description: 技能描述
        applicable_tasks: 适用任务特征列表
        inapplicable_tasks: 不适用任务特征列表
        best_practices: 最佳实践列表
        method: 具体方法/工具
        effectiveness: 初始有效度(0.0~1.0)
    """
    _ensure_index()
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    
    if skill_file.exists():
        print(f"[Skill库] 技能 {skill_id} 已存在，跳过注册")
        return skill_id
    
    skill = {
        "id": skill_id,
        "name": name,
        "domain": domain,
        "description": description,
        "method": method or skill_id,
        
        # 进化字段
        "effectiveness": effectiveness if effectiveness is not None else 0.50,
        "success_count": 0,
        "failure_count": 0,
        "total_duration_minutes": 0,
        "last_used": None,
        "created_at": now_iso(),
        "last_evolved": now_iso(),
        
        # 适用性
        "applicable_tasks": applicable_tasks or [],
        "inapplicable_tasks": inapplicable_tasks or [],
        
        # 经验沉淀
        "best_practices": best_practices or [],
        "failure_patterns": [],
        
        # 版本
        "version": 1,
        "evolve_count": 0,
    }
    
    _atomic_write(skill_file, skill)
    
    # 更新索引
    def modifier(idx):
        idx['skills'].append(skill_id)
        idx['domains'].setdefault(domain, []).append(skill_id)
        idx['last_updated'] = now_iso()
        return idx
    _atomic_json_update(SKILLS_INDEX, modifier)
    
    print(f"[Skill库] ✅ 注册技能: {skill_id} ({name})")
    return skill_id


def record_execution(skill_id, success, duration_minutes=0, 
                     quality_score=None, notes="", task_tags=None):
    """
    记录一次技能执行结果（触发进化分析）
    
    Args:
        success: 是否成功
        duration_minutes: 执行耗时
        quality_score: 质量评分(0.0~1.0)
        notes: 执行笔记
        task_tags: 任务标签
    """
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    if not skill_file.exists():
        print(f"[Skill库] ⚠️ 技能 {skill_id} 不存在，无法记录")
        return
    
    task_tags = task_tags or []
    
    def modifier(skill):
        if success:
            skill['success_count'] += 1
        else:
            skill['failure_count'] += 1
        
        skill['total_duration_minutes'] += duration_minutes
        skill['last_used'] = now_iso()
        
        # 更新有效性评分
        old_eff = skill['effectiveness']
        new_eff = _calculate_effectiveness(skill)
        skill['effectiveness'] = round(new_eff, 4)
        
        # 记录失败模式
        if not success and notes:
            _add_failure_pattern(skill, notes)
        
        # 进化检测：有效性变化超过阈值时触发版本更新
        if abs(new_eff - old_eff) > 0.05:
            skill['version'] += 1
            skill['evolve_count'] += 1
            skill['last_evolved'] = now_iso()
            print(f"[Skill库] 🔄 技能 {skill_id} 进化: v{skill['version']} (effectiveness {old_eff:.3f}→{new_eff:.3f})")
        
        return skill
    
    _atomic_json_update(skill_file, modifier)


def add_best_practice(skill_id, practice):
    """添加最佳实践"""
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    if not skill_file.exists():
        return
    
    def modifier(skill):
        if practice not in skill.get('best_practices', []):
            skill['best_practices'].append(practice)
            skill['last_evolved'] = now_iso()
        return skill
    
    _atomic_json_update(skill_file, modifier)


def _calculate_effectiveness(skill):
    """计算有效性评分（基于多维度）"""
    total = skill['success_count'] + skill['failure_count']
    if total == 0:
        return 0.50
    
    success_rate = skill['success_count'] / total
    
    # 基础评分
    score = (
        success_rate * _WEIGHT_SUCCESS_RATE +
        (1.0 - min(skill['total_duration_minutes'] / 1000, 1.0)) * _WEIGHT_COMPLEXITY +
        0.50 * _WEIGHT_EFFECTIVENESS  # 中立基础
    )
    
    # 近期加权
    if skill['last_used']:
        try:
            last = datetime.datetime.fromisoformat(skill['last_used'])
            days_ago = (datetime.datetime.now() - last).days
            recency = max(0, 1 - days_ago / 30)  # 30天内衰减
            score += recency * _WEIGHT_RECENCY
        except:
            pass
    
    return max(0.0, min(1.0, score))


def _add_failure_pattern(skill, notes):
    """记录失败模式"""
    patterns = skill.get('failure_patterns', [])
    
    # 简单去重：如果同一条notes已存在，增加计数
    for p in patterns:
        if p.get('pattern', '') == notes[:80]:
            p['occurrences'] += 1
            return
    
    # 新增失败模式
    patterns.append({
        "pattern": notes[:80],
        "occurrences": 1,
        "detected_at": now_iso()
    })
    skill['failure_patterns'] = patterns[-10:]  # 保留最近10条


# ── Skill检索 ─────────────────────────────────────────────

def query_skills(task_description=None, domain=None, tags=None,
                  min_effectiveness=None, limit=5):
    """
    查询最匹配的技能
    
    Args:
        task_description: 任务描述（用于特征匹配）
        domain: 限定领域
        tags: 任务标签列表
        min_effectiveness: 最低有效度过滤
        limit: 返回数量
    
    Returns:
        按匹配度排序的技能列表
    """
    _ensure_index()
    idx = _read_json(SKILLS_INDEX) or {"skills": []}
    
    candidates = []
    for skill_id in idx.get('skills', []):
        skill = _read_json(SKILLS_DIR / f"{skill_id}.json")
        if not skill:
            continue
        
        # 领域过滤
        if domain and skill.get('domain') != domain:
            continue
        
        # 有效度过滤
        if min_effectiveness and skill.get('effectiveness', 0) < min_effectiveness:
            continue
        
        # 计算匹配度
        score = _compute_match_score(skill, task_description, tags)
        candidates.append((skill_id, score, skill))
    
    # 按匹配度降序
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [(sid, s) for sid, score, s in candidates[:limit]]


def _compute_match_score(skill, task_description, tags):
    """计算技能与任务的匹配度"""
    score = 0.0
    
    # 有效性贡献（最重要）
    score += skill.get('effectiveness', 0.50) * 0.50
    
    # 适用特征匹配
    applicable = skill.get('applicable_tasks', [])
    inapplicable = skill.get('inapplicable_tasks', [])
    if task_description:
        td_lower = task_description.lower()
        applicable_hits = sum(1 for a in applicable if a.lower() in td_lower)
        inapplicable_hits = sum(1 for i in inapplicable if i.lower() in td_lower)
        score += (applicable_hits * 0.1) - (inapplicable_hits * 0.2)
    
    # 标签匹配
    if tags:
        skill_tags = skill.get('applicable_tasks', [])
        tag_hits = sum(1 for t in tags if any(t.lower() in s.lower() for s in skill_tags))
        score += tag_hits * 0.1
    
    # 成功数贡献（经验加成）
    total_exec = skill.get('success_count', 0) + skill.get('failure_count', 0)
    if total_exec > 0:
        score += min(total_exec / 100, 0.2)  # 最多+0.2
    
    return max(0.0, min(1.0, score))


def get_skill(skill_id):
    """获取技能详情"""
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    return _read_json(skill_file)


def list_skills(domain=None):
    """列出技能"""
    _ensure_index()
    idx = _read_json(SKILLS_INDEX) or {"skills": [], "domains": {}}
    
    if domain:
        skill_ids = idx.get('domains', {}).get(domain, [])
    else:
        skill_ids = idx.get('skills', [])
    
    result = []
    for sid in skill_ids:
        s = _read_json(SKILLS_DIR / f"{sid}.json")
        if s:
            result.append(s)
    return result


# ── CLI ───────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == 'register':
        skill_id = sys.argv[2] if len(sys.argv) > 2 else ''
        name = sys.argv[3] if len(sys.argv) > 3 else skill_id
        domain = sys.argv[4] if len(sys.argv) > 4 else '通用'
        register_skill(skill_id, name, domain)
    
    elif cmd == 'list':
        skills = list_skills()
        print(f"\n📚 Skill库（共 {len(skills)} 项）\n")
        for s in skills:
            print(f"  [{s['domain']}] {s['id']}: {s['name']}")
            print(f"         有效度: {s['effectiveness']:.2f} | 成功: {s['success_count']} | 失败: {s['failure_count']}")
            print(f"         版本: v{s['version']} | 最佳实践: {len(s.get('best_practices',[]))}条")
            print()
    
    elif cmd == 'query':
        task_desc = sys.argv[2] if len(sys.argv) > 2 else ''
        results = query_skills(task_description=task_desc, limit=5)
        print(f"\n🔍 技能检索: {task_desc or '(无描述)'}\n")
        for sid, s in results:
            print(f"  ✅ {s['id']} ({s['name']}) [v{s['version']}]")
            print(f"     有效度: {s['effectiveness']:.3f} | 成功率: {s['success_count']}/{s['success_count']+s['failure_count']}")
            print(f"     适用: {', '.join(s.get('applicable_tasks', [])[:3])}")
            print()
    
    elif cmd == 'record':
        skill_id = sys.argv[2] if len(sys.argv) > 2 else ''
        success = '--success' in sys.argv
        record_execution(skill_id, success, notes=' '.join(sys.argv[3:]))
    
    elif cmd == 'get':
        skill_id = sys.argv[2] if len(sys.argv) > 2 else ''
        s = get_skill(skill_id)
        if s:
            print(json.dumps(s, ensure_ascii=False, indent=2))
        else:
            print(f"[Skill库] 技能 {skill_id} 不存在")
    
    else:
        print(f"未知命令: {cmd}")
        print("用法: skill_library.py [register|list|query|record|get]")


if __name__ == '__main__':
    main()
