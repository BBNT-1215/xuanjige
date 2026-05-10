---
name: "skill_role_dispatch"
description: "从Role库检索最优角色组合并派发任务"
domain: "orchestration"
version: "1.0.0"
tier: "POWERFUL"

inputs:
  - name: "task_type"
    type: "string"
    required: true
    description: "任务类型"
  - name: "complexity"
    type: "string"
    required: false
    description: "任务复杂度：simple / medium / complex / critical"
  - name: "skills_needed"
    type: "array"
    required: true
    description: "需要的Skill ID列表"

outputs:
  - name: "dispatch_plan"
    type: "object"
    description: "派发计划"
  - name: "recommended_roles"
    type: "array"
    description: "推荐的Role ID列表"

dependencies:
  - "skill_skill_routing"

tools:
  - "scripts/role_dispatch.py"

used_by_roles:
  - "jiheng"

effectiveness_score: 0.76
confidence: "medium"
---

# skill_role_dispatch · Role检索派发

## Overview
根据任务类型和复杂度，从Role库检索最优角色组合，并制定派发计划。
是调度派发的核心能力：决定谁来执行任务。

## When to Use
- 调度接收任务，准备派发给执行层时
- 需要决定派发给哪些部门时
- 需要制定派发计划时

## When NOT to Use
- 任务已明确指定执行者
- 紧急情况（直接派发给最常用的部门）

## Core Workflows

### Workflow 1: 标准派发
**Goal:** 制定派发计划

**Steps:**
1. 根据task_type和complexity确定部门数量
2. 查询 L2：各Role的stats（tasks_completed, avg_quality）
3. 查询 L2：协作关系（with_xxx的avg_quality）
4. 查询 L1：同类任务的历史派发方案
5. 应用协作公理：选择协作效果好的组合
6. 生成派发计划

**Expected Output:**
```json
{
  "dispatch_plan": {
    "primary_role": "jizao",
    "supporting_roles": ["xingce"],
    "consult_roles": [],
    "execution_order": ["jizao", "xingce"],
    "reasoning": "..."
  }
}
```

## Complexity × 部门数量映射

| 复杂度 | 部门数量 | 说明 |
|--------|---------|------|
| simple | 1 | 1个部门独立完成 |
| medium | 2 | 1主1辅 |
| complex | 3+ | 主+辅+咨询 |
| critical | 全执行层+太子审批 | 最高级别 |

## Script Interfaces

### scripts/role_dispatch.py
```bash
python3 skills/skill_role_dispatch/scripts/role_dispatch.py --task-type "coding" --complexity "medium" --skills "skill_coding,skill_qa"
```

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
