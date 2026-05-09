---
name: "skill_database_optimization"
description: "SQL优化、索引策略、查询调优与数据库架构"
domain: "operation"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "target"
    type: "string"
    required: true
    description: "操作目标"

outputs:
  - name: "result"
    type: "object"
    description: "执行结果"

dependencies: []
tools:
  - "scripts/main.py"
used_by_roles: []
effectiveness_score: 0.70
confidence: "medium"
---

# Database Optimization

## Overview
SQL优化、索引策略、查询调优与数据库架构。这是Hermestrix系统的 operation 类Skill。

## When to Use
- 部署自动化和环境管理
- 系统监控指标配置
- 故障响应和应急处置
- 数据库性能调优
- API网关配置

## When NOT to Use
- 纯开发任务（用 skill_coding）
- 数据分析任务（用 skill_data_analysis）

## Core Workflows
### Workflow 1: 标准操作流程
1. 确认操作目标和影响范围
2. 检查当前环境状态
3. 制定操作计划（含回滚方案）
4. 执行操作
5. 验证结果
6. 记录操作日志

## Script Interfaces
```bash
python3 scripts/main.py --target <name> [--json]
```

## Best Practices
1. 操作前必读回滚方案
2. 敏感操作需二次确认
3. 保留完整操作日志

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
