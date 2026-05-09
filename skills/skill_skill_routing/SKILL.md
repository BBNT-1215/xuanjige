---
name: "skill_skill_routing"
description: "从Skill库检索最优技能组合"
domain: "orchestration"
version: "1.0.0"
tier: "POWERFUL"

inputs:
  - name: "task_type"
    type: "string"
    required: true
    description: "任务类型"
  - name: "task_context"
    type: "object"
    required: false
    description: "任务上下文（复杂度、领域等）"

outputs:
  - name: "recommended_skills"
    type: "array"
    description: "推荐的Skill ID列表，按优先级排序"
  - name: "reasoning"
    type: "string"
    description: "推荐理由"

dependencies:
  - "skill_data_analysis"

tools:
  - "scripts/skill_routing.py"

used_by_roles:
  - "shangshu"

effectiveness_score: 0.78
confidence: "high"
---

# skill_skill_routing · Skill检索派发

## Overview
从Skill库中检索最适合当前任务的技能组合。
是尚书省派发的核心能力：拿到任务后，决定用哪些Skill来完成。

## When to Use
- 尚书省接收到任务派发指令时
- 需要确定任务执行方案时
- 需要决定派发给哪个部门时

## When NOT to Use
- 任务类型已明确（直接按预设映射派发）
- 紧急情况（直接用最常用的Skill组合）

## Core Workflows

### Workflow 1: 标准Skill检索
**Goal:** 根据任务类型检索最优Skill组合

**Steps:**
1. 解析任务类型和上下文
2. 查询 L1 记忆：同类型任务以前用什么Skill
3. 查询 L2：各Skill的effectiveness评分
4. 排序：effectiveness高的优先
5. 应用效率公理：效果相同时选更简单的
6. 输出推荐组合

**Expected Output:**
```json
{
  "recommended_skills": [
    {"skill_id": "skill_coding", "score": 0.85, "reasoning": "代码开发首选"},
    {"skill_id": "skill_code_review", "score": 0.82, "reasoning": "配合代码开发使用"}
  ],
  "recommended_department": "gongbu",
  "reasoning": "任务类型为代码开发，工部执行，skill_coding为主，skill_code_review辅助"
}
```

## Skill × 部门映射（来自 L3 knowledge/rules/workflow_sanshengliubu.json）

| Skill领域 | 派发部门 |
|-----------|---------|
| skill_coding / skill_architecture | 工部 |
| skill_testing / skill_qa / skill_code_review | 刑部 |
| skill_doc_writing / skill_ui_design | 礼部 |
| skill_data_analysis / skill_reporting | 户部 |
| skill_devops / skill_security / skill_monitoring | 兵部 |
| skill_km / skill_evolution | 吏部 |
| skill_routing / skill_planning | 太子/中书省 |

## Script Interfaces

### scripts/skill_routing.py
```bash
python3 skills/skill_skill_routing/scripts/skill_routing.py --task-type "代码开发"
python3 skills/skill_skill_routing/scripts/skill_routing.py --task-type "系统扩展" --json
```

## Best Practices
1. 优先查询L1历史：有同类任务时参考历史方案
2. 评分相近时应用效率公理：选更简单的
3. 返回的结果要包含 reasoning，供尚书省决策

## Common Pitfalls
1. 只看评分不看上下文：task_type不同，评分高的Skill可能不适用
2. 返回太多Skill：一般不超过3个，否则派发太复杂

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
