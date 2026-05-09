---
name: "skill_routing"
description: "对用户旨意进行分类，判断路由方向"
domain: "orchestration"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "user_message"
    type: "string"
    required: true
    description: "用户原始旨意文本"
  - name: "context"
    type: "object"
    required: false
    description: "当前上下文（用户历史、任务状态等）"

outputs:
  - name: "route"
    type: "string"
    description: "路由方向：zhongshu / direct / reject / clarify"
  - name: "confidence"
    type: "float"
    description: "置信度 0.0-1.0"
  - name: "reasoning"
    type: "string"
    description: "路由理由"

dependencies: []

tools:
  - "scripts/route.py"

used_by_roles:
  - "taizi"

effectiveness_score: 0.82
confidence: "high"
---

# skill_routing · 旨意分拣

## Overview
对用户输入的旨意进行分类，判断应该走三省六部流程还是直接处理。
是太子 Agent 的核心 Skill，决定每个旨意的命运起点。

## When to Use
- 用户发送旨意时
- 需要判断任务类型时
- 不确定如何处理用户请求时

## When NOT to Use
- 旨意已明确（不需要分拣，直接派发）
- 重复确认请求（已经是处理中任务）

## Core Workflows

### Workflow 1: 标准分拣
**Goal:** 将旨意分类到正确处理路径

**Steps:**
1. 解析旨意文本，提取关键词
2. 查询 L1 记忆：类似旨意以前如何处理
3. 应用 L3 规则：workflow_sanshengliubu/routing
4. 输出路由 + 置信度

**Expected Output:**
```json
{
  "route": "zhongshu",
  "confidence": 0.88,
  "reasoning": "旨意包含'构建'关键词，匹配系统建设类型，应走中书省起草"
}
```

**Time Estimate:** < 5 seconds

## Routing Rules（来自 L3 knowledge/rules/workflow_sanshengliubu.json）

| 关键词 | 路由方向 |
|--------|---------|
| 构建 / 开发 / 创建 / 设计 | zhongshu |
| 查询 / 状态 / 情况 | direct |
| 模糊 / 不确定 | clarify |
| 违规 / 不当 | reject |

## Script Interfaces

### scripts/route.py
```bash
# 标准分拣
python3 skills/skill_routing/scripts/route.py --message "构建一个AI漫剧工厂"

# JSON格式输出
python3 skills/skill_routing/scripts/route.py --message "今天的任务状态是什么" --json

# 带上下文
python3 skills/skill_routing/scripts/route.py --message "扩展Skill库" --context '{"user_id": "xxx"}'
```

**Arguments:**
- `--message`: 用户旨意文本（必需）
- `--context`: JSON格式上下文对象（可选）
- `--json`: 输出JSON格式

## Best Practices
1. 置信度 < 0.6 时，返回 `clarify` 而非强行分类
2. 优先使用 task_type 字段匹配，而非全文匹配
3. 参考 L1 历史时，使用 quality=good 的记录
4. 路由决策必须记录 reasoning，供后续审计

## Common Pitfalls
1. **过度分类** → 当置信度低时返回 clarify
2. **忽略上下文** → 相同词在不同用户下可能路由不同（如"构建"在公司vs个人语境）
3. **硬编码关键词** → 应使用 L3 规则而非代码中的 if-else

## Failure Handling
当无法分类时：
→ 返回 `{"route": "clarify", "reasoning": "旨意不够清晰，需要用户提供更多信息"}`
→ 不应返回 reject（只有明确违规才reject）

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
