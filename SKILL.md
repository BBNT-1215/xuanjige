# 玄机阁 Skill 标准格式

> 版本：v1.0 | 状态：规范 | 适配：Hermes Agent 原生

---

## 文件结构

```
skills/
└── {skill_id}/
    ├── SKILL.md       # Skill定义（必需）
    ├── METADATA.yaml  # 元数据（必需）
    ├── scripts/       # 可执行工具（可选）
    │   ├── main.py
    │   └── utils.py
    └── references/    # 专业知识（可选）
        └── notes.md
```

---

## SKILL.md 格式

```yaml
---
name: "skill_id"
description: "一句话描述技能用途"
domain: "engineering|orchestration|analysis|documentation|operation"
version: "1.0.0"
tier: "FOUNDATIONAL|STANDARD|POWERFUL"

inputs:
  - name: "参数名"
    type: "string|number|object|array"
    required: true|false
    description: "参数说明"

outputs:
  - name: "输出名"
    type: "string|number|object|array"
    description: "输出说明"

dependencies:
  - "skill_id_1"

tools:
  - "scripts/main.py"

used_by_roles:
  - "chengzhi"
  - "jiheng"

effectiveness_score: 0.82
confidence: "high"
---

# Skill名称

## Overview
[一段话说明这个技能做什么，为什么有用]

## When to Use
- [场景1]
- [场景2]

## When NOT to Use
- [不适用场景1]
- [不适用场景2]

## Core Workflows

### Workflow 1: [名称]
**Goal:** [目标]

**Steps:**
1. [步骤1]
2. [步骤2]

**Expected Output:** [成功输出的样子]

**Time Estimate:** [预估时间]

## Script Interfaces

### scripts/main.py
```bash
python3 scripts/main.py --input <value> [--json]
```

## Best Practices
1. [最佳实践1]
2. [最佳实践2]

## Common Pitfalls
1. [错误1] → [解决方法]

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
```

---

## METADATA.yaml 格式

```yaml
---
name: "skill_id"
version: "1.0.0"
created_at: "2026-05-09T00:00:00Z"
updated_at: "2026-05-09T12:00:00Z"

effectiveness_score: 0.82
confidence: "high"

stats:
  total_uses: 47
  success_count: 41
  failure_count: 6
  avg_quality: 0.82

verification:
  status: "verified"       # pending / verifying / verified / rolled_back
  version_introduced: "1.0.0"
  observations_required: 5
  observations_collected: 5
  verification_confirmed_at: "2026-05-09T12:00:00Z"

domain: "orchestration"

tools:
  - "scripts/main.py"

used_by_roles:
  - "chengzhi"

quality_tiers:
  excellent: [0.9, 1.0]
  good: [0.8, 0.9]
  medium: [0.5, 0.8]
  bad: [0.0, 0.5]
```
