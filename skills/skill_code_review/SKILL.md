---
name: "skill_code_review"
description: "代码审查技能，系统性地审查代码质量、发现潜在问题和安全漏洞"
domain: "engineering"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "code"
    type: "string"
    required: true
    description: "待审查的代码文本"
  - name: "language"
    type: "string"
    required: false
    description: "编程语言（python/js/ts/go/java等）"
  - name: "context"
    type: "object"
    required: false
    description: "代码上下文（文件路径、功能描述等）"
  - name: "focus_areas"
    type: "array"
    required: false
    description: "重点审查领域：logic/security/performance/readability/security"

outputs:
  - name: "issues"
    type: "array"
    description: "发现的问题列表"
  - name: "severity"
    type: "string"
    description: "严重程度：critical/major/minor/info"
  - name: "suggestions"
    type: "array"
    description: "改进建议"
  - name: "quality_score"
    type: "float"
    description: "代码质量评分 0.0-1.0"

dependencies: []

tools:
  - "scripts/review.py"

used_by_roles:
  - "shangshu"
  - "gongbu"

effectiveness_score: 0.78
confidence: "high"
---

# skill_code_review · 代码审查

## Overview
系统性地审查代码质量、发现潜在问题和安全漏洞。涵盖逻辑错误、性能瓶颈、安全风险、可读性维护等多个维度。

## When to Use
- PR/MR 合并前进行代码审查
- 发现 bug 后定位问题根源
- 重构前评估代码质量
- 代码评审 checkpoint

## When NOT to Use
- 简单配置或数据文件（非代码）
- 原型/POC 代码（可跳过审查）
- 紧急 hotfix（事后补审）

## Core Workflows

### Workflow 1: 全面代码审查
**Goal:** 对代码进行全面系统性审查

**Steps:**
1. 解析代码结构和语言
2. 静态分析：语法、类型、风格
3. 逻辑审查：控制流、数据流、边界条件
4. 安全审查：注入、认证、加密敏感信息
5. 性能审查：复杂度、资源泄漏、并发问题
6. 输出结构化审查报告

**Expected Output:**
```json
{
  "issues": [
    {
      "line": 42,
      "severity": "major",
      "category": "security",
      "title": "SQL注入风险",
      "description": "用户输入直接拼接到SQL查询中",
      "suggestion": "使用参数化查询"
    }
  ],
  "quality_score": 0.72,
  "summary": "发现3个问题，建议修复后合并"
}
```

**Time Estimate:** 代码量 < 500行：5-10分钟；500-2000行：15-30分钟

### Workflow 2: 快速安全扫描
**Goal:** 快速发现常见安全漏洞

**Steps:**
1. 扫描注入类风险（SQL/命令/代码注入）
2. 检查认证和授权问题
3. 检查敏感信息暴露（密码/密钥/Token）
4. 检查加密和哈希使用

**Time Estimate:** < 5分钟

## Script Interfaces

### scripts/review.py
```bash
# 标准审查
python3 skills/skill_code_review/scripts/review.py --code "def foo(): pass"

# 指定语言
python3 skills/skill_code_review/scripts/review.py --code "$CODE" --language python

# 重点领域
python3 skills/skill_code_review/scripts/review.py --code "$CODE" --focus-areas security performance

# JSON输出
python3 skills/skill_code_review/scripts/review.py --code "$CODE" --json
```

**Arguments:**
- `--code`: 待审查代码（必需）
- `--language`: 编程语言（默认：自动推断）
- `--focus-areas`: 重点审查领域，用逗号分隔
- `--json`: 输出JSON格式

## Best Practices
1. **先逻辑后语法**：优先审查业务逻辑，再看代码风格
2. **关注边界条件**：null/空/极值情况容易出bug
3. **安全第一**：涉及用户数据/认证/授权必须严格审查
4. **给出具体建议**：每个问题都应附带修复方案
5. **区分严重程度**：critical必须修复，minor可选择性处理

## Common Pitfalls
1. **只关注语法** → 忽略业务逻辑错误
2. **忽略上下文** → 同一代码在不同场景下风险不同
3. **过度审查** → POC代码不应按生产标准要求

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
