#!/usr/bin/env python3
"""
skill_skill_routing/scripts/skill_routing.py

Skill检索派发CLI工具

用法：
  python3 skill_routing.py --task-type "代码开发"
  python3 skill_routing.py --task-type "系统扩展" --json
  python3 skill_routing.py --task-type "数据分析" --context '{"complexity":"high"}'
"""

import json
import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent  # /skills/skill_skill_routing/ → /skills/ → /hermestrix/
PROJECT_ROOT_STR = str(PROJECT_ROOT)

# Add project root to path
if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

os.environ.setdefault("HERMESTRIX_HOME", PROJECT_ROOT_STR)


# Skill × 部门 映射（与 L3 knowledge/rules/workflow_sanshengliubu.json 保持一致）
SKILL_DEPARTMENT_MAP = {
    "coding": "gongbu",
    "architecture": "gongbu",
    "testing": "xingbu",
    "qa": "xingbu",
    "code_review": "xingbu",
    "audit": "xingbu",
    "doc_writing": "libu",
    "ui_design": "libu",
    "documentation": "libu",
    "data_analysis": "hubu",
    "reporting": "hubu",
    "trend_analysis": "hubu",
    "devops": "bingbu",
    "security": "bingbu",
    "monitoring": "bingbu",
    "incident_response": "bingbu",
    "km": "libu_hr",
    "evolution": "libu_hr",
    "routing": "taizi",
    "planning": "zhongshu",
    "review": "menxia",
    "risk_assessment": "menxia",
}

# Task type → Skill映射
TASK_TYPE_SKILL_MAP = {
    "system_setup": ["skill_coding", "skill_architecture"],
    "system_expansion": ["skill_coding", "skill_planning"],
    "coding": ["skill_coding"],
    "analysis": ["skill_data_analysis", "skill_trend_analysis"],
    "documentation": ["skill_doc_writing"],
    "qa": ["skill_qa", "skill_testing"],
    "devops": ["skill_devops", "skill_security"],
    "research": ["skill_data_analysis", "skill_planning"],
    "bug_fix": ["skill_coding", "skill_code_review"],
    "code_review": ["skill_code_review"],
    "report": ["skill_data_analysis", "skill_reporting"],
    "routing": ["skill_routing"],
    "planning": ["skill_planning"],
}


def get_all_skill_effectiveness():
    """从L2获取所有Skill的effectiveness评分"""
    from engine.memory_manager import MemoryManager
    mm = MemoryManager()
    return mm.get_all_skill_effectiveness()


def query_l1_history(task_type: str, limit: int = 3):
    """查询L1同类任务历史"""
    from engine.memory_manager import MemoryManager
    mm = MemoryManager()
    records = mm.query_similar_tasks(task_type=task_type, quality_filter="good", limit=limit)
    return [
        {
            "task_id": r.task_id,
            "skills_used": r.skills_used,
            "quality": r.quality_score
        }
        for r in records
    ]


def skill_routing(task_type: str, task_context: dict = None) -> dict:
    """
    根据任务类型检索最优Skill组合

    Returns:
        {
            "recommended_skills": [...],
            "recommended_department": "...",
            "reasoning": "...",
            "l1_history": [...]
        }
    """
    # 1. 从L1查询历史
    l1_history = query_l1_history(task_type)

    # 2. 从L2获取所有Skill评分
    all_effectiveness = get_all_skill_effectiveness()

    # 3. 基础映射：task_type → skills
    base_skills = TASK_TYPE_SKILL_MAP.get(task_type, [])

    # 4. 如果L1有历史，用历史的Skill
    if l1_history:
        # 取历史中效果最好的记录
        best_history = max(l1_history, key=lambda h: h["quality"])
        recommended = []
        for entry in best_history.get("skills_used", []):
            skill_id = entry["skill_id"]
            score = all_effectiveness.get(skill_id, entry.get("quality_score", 0.5))
            recommended.append({
                "skill_id": skill_id,
                "score": score,
                "from": "l1_history",
                "historical_quality": entry.get("quality_score")
            })
    else:
        # 无历史，用基础映射
        recommended = []
        for skill_id in base_skills:
            score = all_effectiveness.get(skill_id, 0.5)
            recommended.append({
                "skill_id": skill_id,
                "score": score,
                "from": "task_type_mapping",
                "historical_quality": None
            })

    # 5. 填充缺失Skill（从effectiveness排序补足）
    if len(recommended) < 2 and all_effectiveness:
        for sid in sorted(all_effectiveness, key=all_effectiveness.get, reverse=True):
            if sid not in [r["skill_id"] for r in recommended]:
                recommended.append({
                    "skill_id": sid,
                    "score": all_effectiveness[sid],
                    "from": "effectiveness_fallback",
                    "historical_quality": None
                })
            if len(recommended) >= 3:
                break

    # 6. 按评分排序
    recommended.sort(key=lambda x: x["score"], reverse=True)

    # 7. 推荐部门（根据最高评分Skill推断）
    top_skill_id = recommended[0]["skill_id"] if recommended else None
    dept = None
    for key, val in SKILL_DEPARTMENT_MAP.items():
        if key in (top_skill_id or ""):
            dept = val
            break

    # 8. 生成reasoning
    reasoning = f"任务类型={task_type}"
    if l1_history:
        reasoning += f"，参考L1历史最佳方案（质量{best_history['quality']:.0%}）"
    reasoning += f"，推荐{len(recommended)}个Skill"
    if dept:
        reasoning += f"，建议派发到{dept}"

    return {
        "task_type": task_type,
        "recommended_skills": recommended[:3],
        "recommended_department": dept,
        "reasoning": reasoning,
        "l1_history": l1_history
    }


def main():
    parser = argparse.ArgumentParser(description="Skill检索派发工具")
    parser.add_argument("--task-type", "-t", required=True, help="任务类型")
    parser.add_argument("--context", "-c", help="JSON格式上下文")
    parser.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    context = None
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError:
            print("Error: --context 必须是有效JSON", file=sys.stderr)
            sys.exit(1)

    result = skill_routing(args.task_type, context)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"任务类型: {result['task_type']}")
        print(f"推荐部门: {result['recommended_department']}")
        print(f"推荐Skills:")
        for s in result["recommended_skills"]:
            print(f"  - {s['skill_id']}: {s['score']:.2f} ({s['from']})")
        print(f"理由: {result['reasoning']}")


if __name__ == "__main__":
    main()
