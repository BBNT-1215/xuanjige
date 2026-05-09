---
name: "skill_debugging"
description: "调试排错技能，系统性定位和修复软件问题"
domain: "engineering"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "symptom"
    type: "string"
    required: true
    description: "问题现象描述"
  - name: "error_logs"
    type: "string"
    required: false
    description: "错误日志内容"
  - name: "code_context"
    type: "string"
    required: false
    description: "相关代码片段"
  - name: "environment"
    type: "object"
    required: false
    description: "环境信息（语言、框架、版本等）"

outputs:
  - name: "root_cause"
    type: "string"
    description: "推断的根因"
  - name: "confidence"
    type: "float"
    description: "诊断置信度 0.0-1.0"
  - name: "root_causes"
    type: "array"
    description: "可能的根因列表"
  - name: "error_pattern_matches"
    type: "array"
    description: "匹配的错误模式"
  - name: "debug_questions"
    type: "array"
    description: "进一步诊断的问题"
  - name: "fix_steps"
    type: "array"
    description: "建议的修复步骤"

dependencies: []

tools:
  - "scripts/debug.py"

used_by_roles:
  - "jiheng"
  - "jizao"
  - "zaohuang"

effectiveness_score: 0.82
confidence: "high"
---

# skill_debugging · 调试排错

## Overview
系统性定位和修复软件问题。通过分析错误日志、代码上下文和问题症状，快速推断根因并给出修复建议。

## When to Use
- 软件出现 bug 需要定位
- 错误日志无法直接看出问题
- 不确定问题根因时
- 疑难杂症反复出现

## When NOT to Use
- 硬件故障（需物理检查）
- 需求/业务逻辑不清（先澄清需求）
- 简单配置错误（可直接检查配置）

## Core Workflows

### Workflow 1: 问题诊断
**Goal:** 根据症状和错误日志定位根因

**Steps:**
1. 分析问题现象，识别症状类型
2. 匹配已知错误模式库
3. 基于症状推断可能根因
4. 生成调试问题进一步确认
5. 给出修复建议

**Expected Output:**
```json
{
  "symptom": "服务响应超时",
  "confidence": 0.75,
  "root_cause": "数据库连接池耗尽",
  "root_causes": [
    {
      "cause": "数据库查询慢导致连接占用",
      "fix": "优化SQL查询或增加连接池大小",
      "confidence": 0.75
    }
  ],
  "debug_questions": [
    "数据库慢查询日志是否有异常？",
    "连接池配置大小是多少？"
  ],
  "fix_steps": [
    {"step": 1, "action": "检查数据库连接池配置", "priority": "high"},
    {"step": 2, "action": "查看慢查询日志", "priority": "high"}
  ]
}
```

**Time Estimate:** 5-15分钟

### Workflow 2: 错误日志分析
**Goal:** 从错误日志提取关键信息

**Steps:**
1. 提取错误类型和错误信息
2. 定位异常发生的文件和行号
3. 追溯调用栈，理解执行流程
4. 匹配已知错误模式

## Script Interfaces

### scripts/debug.py
```bash
# 基本诊断
python3 skills/skill_debugging/scripts/debug.py --symptom "服务崩溃"

# 带错误日志
python3 skills/skill_debugging/scripts/debug.py --symptom "接口超时" \
  --error-logs "Connection timeout after 30000ms"

# 带代码上下文
python3 skills/skill_debugging/scripts/debug.py --symptom "数据不一致" \
  --code-context "def process(): return db.query()"

# 指定环境
python3 skills/skill_debugging/scripts/debug.py --symptom "启动失败" \
  --environment '{"language": "python", "framework": "django"}'

# JSON输出
python3 skills/skill_debugging/scripts/debug.py --symptom "内存泄漏" --json
```

**Arguments:**
- `--symptom`: 问题现象描述（必需）
- `--error-logs`: 错误日志内容（可选）
- `--code-context`: 相关代码片段（可选）
- `--environment`: JSON格式环境信息（可选）
- `--json`: 输出JSON格式

## Error Pattern Database

内置支持以下语言的常见错误模式：

| 语言 | 错误类型 | 根因 |
|------|---------|------|
| Python | ModuleNotFoundError | 模块未安装 |
| Python | IndexError | 列表索引越界 |
| Python | KeyError | 字典键不存在 |
| JavaScript | Cannot read property | 读取undefined属性 |
| JavaScript | Maximum call stack | 无限递归 |
| Java | NullPointerException | 空指针 |
| SQL | Table doesn't exist | 表不存在 |

## Best Practices
1. **收集完整信息**：症状 + 错误日志 + 代码上下文缺一不可
2. **追问验证**：不确定时生成调试问题让用户确认
3. **考虑多种可能**：给出多个根因假设，按置信度排序
4. **给出具体步骤**：每条修复建议都应可操作

## Common Pitfalls
1. **过早下结论** → 多匹配几个错误模式验证
2. **忽略上下文** → 相同错误在不同场景根因不同
3. **只给建议不追踪** → 建议记录到issue跟踪

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
