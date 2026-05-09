#!/usr/bin/env python3
"""
skill_role_dispatch/scripts/role_dispatch.py

Role检索派发CLI工具

用法：
  python3 role_dispatch.py --task-type "coding" --complexity "medium" --skills "skill_coding,skill_qa"
  python3 role_dispatch.py --task-type "system_setup" --json
"""

import json
import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent  # /skills/skill_role_dispatch/ → /skills/ → /hermestrix/
PROJECT_ROOT_STR = str(PROJECT_ROOT)

if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

os.environ.setdefault("HERMESTRIX_HOME", PROJECT_ROOT_STR)


# 复杂度 × 部门数量
COMPLEXITY_DEPT_MAP = {
    "simple": {"primary": 1, "support": 0, "consult": 0},
    "medium": {"primary": 1, "support": 1, "consult": 0},
    "complex": {"primary": 1, "support": 1, "consult": 1},
    "critical": {"primary": 2, "support": 2, "consult": 1},
}

# Skill领域 → Role映射
SKILL_ROLE_MAP = {
    "skill_coding": "gongbu",
    "skill_architecture": "gongbu",
    "skill_testing": "xingbu",
    "skill_qa": "xingbu",
    "skill_code_review": "xingbu",
    "skill_audit": "xingbu",
    "skill_doc_writing": "libu",
    "skill_ui_design": "libu",
    "skill_data_analysis": "hubu",
    "skill_reporting": "hubu",
    "skill_trend_analysis": "hubu",
    "skill_devops": "bingbu",
    "skill_security": "bingbu",
    "skill_monitoring": "bingbu",
    "skill_km": "libu_hr",
    "skill_evolution": "libu_hr",
}


def get_all_role_stats():
    """从L2获取所有Role的stats"""
    from engine.memory_manager import MemoryManager
    mm = MemoryManager()
    from pathlib import Path
    import json

    stats = {}
    role_dir = PROJECT_ROOT / "three_libs" / "roles"
    if not role_dir.exists():
        return stats

    for role_path in role_dir.iterdir():
        if role_path.is_dir():
            stats_file = role_path / "stats.json"
            if stats_file.exists():
                with open(stats_file, encoding="utf-8") as f:
                    data = json.load(f)
                    stats[role_path.name] = data.get("stats", {})
    return stats


def get_role_collaborations(role_id: str) -> dict:
    """获取某Role的协作关系"""
    from engine.memory_manager import MemoryManager
    mm = MemoryManager()
    stats = mm.get_role_stats(role_id)
    return stats.collaborations


def role_dispatch(task_type: str, complexity: str, skills_needed: list) -> dict:
    """
    根据任务类型和复杂度制定派发计划

    Returns:
        dispatch_plan
    """
    # 1. 确定部门数量
    dept_config = COMPLEXITY_DEPT_MAP.get(complexity, COMPLEXITY_DEPT_MAP["medium"])

    # 2. 从skills推断主责部门
    dept_scores = {}
    for skill in skills_needed:
        role = SKILL_ROLE_MAP.get(skill, "gongbu")
        if role not in dept_scores:
            dept_scores[role] = 0
        dept_scores[role] += 1

    # 3. 从L2获取各Role历史表现
    role_stats = get_all_role_stats()

    # 4. 排序部门（历史质量 × skill匹配度）
    ranked_depts = sorted(
        dept_scores.items(),
        key=lambda x: role_stats.get(x[0], {}).get("avg_quality", 0.5) * x[1],
        reverse=True
    )

    # 5. 构建派发计划
    primary = ranked_depts[0][0] if ranked_depts else "gongbu"
    support = [d for d, _ in ranked_depts[1:1+dept_config["support"]]]
    consult = [d for d, _ in ranked_depts[1+dept_config["support"]:]]
    if dept_config["consult"] > 0 and "libu_hr" not in support and "libu_hr" not in consult:
        consult.append("libu_hr")
    consult = consult[:dept_config["consult"]]

    # 6. 检查协作关系
    for sup in support:
        collabs = get_role_collaborations(primary)
        if sup in collabs:
            collab_quality = collabs[sup].get("avg_quality", 0.5)
            if collab_quality >= 0.85:
                # 协作效果好，优先使用
                pass

    reasoning = f"复杂度{complexity}，需要{dept_config['primary']}主+{dept_config['support']}辅+{dept_config['consult']}咨询"
    if support:
        reasoning += f"，主{primary}配合{support}"
    else:
        reasoning += f"，{primary}独立执行"

    return {
        "task_type": task_type,
        "complexity": complexity,
        "dispatch_plan": {
            "primary_role": primary,
            "supporting_roles": support,
            "consult_roles": consult,
            "execution_order": [primary] + support,
            "reasoning": reasoning
        },
        "role_stats": {
            role: role_stats.get(role, {}) for role in [primary] + support + consult
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Role检索派发工具")
    parser.add_argument("--task-type", "-t", required=True, help="任务类型")
    parser.add_argument("--complexity", "-c", default="medium",
                       choices=["simple", "medium", "complex", "critical"],
                       help="任务复杂度")
    parser.add_argument("--skills", "-s", default="",
                       help="逗号分隔的Skill ID列表")
    parser.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    skills = [s.strip() for s in args.skills.split(",") if s.strip()] if args.skills else ["skill_coding"]

    result = role_dispatch(args.task_type, args.complexity, skills)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        plan = result["dispatch_plan"]
        print(f"派发计划: {plan['primary_role']}", end="")
        if plan["supporting_roles"]:
            print(f" + {', '.join(plan['supporting_roles'])}", end="")
        if plan["consult_roles"]:
            print(f" (咨询: {', '.join(plan['consult_roles'])})", end="")
        print()
        print(f"执行顺序: {' → '.join(plan['execution_order'])}")
        print(f"理由: {plan['reasoning']}")


if __name__ == "__main__":
    main()
