---
name: "skill_data_analysis"
description: "对结构化/非结构化数据进行统计、聚合、异常检测，输出分析结论"
domain: "data"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "data_source"
    type: "string"
    required: true
    description: "数据来源：file路径 / SQL查询 / API响应 / 内存dict"
  - name: "analysis_goal"
    type: "string"
    required: true
    description: "分析目标，如\"用户留存率\"、\"日活趋势\"、\"异常检测\""
  - name: "options"
    type: "object"
    required: false
    description: "可选参数：group_by, filters, limit, agg_func"

outputs:
  - name: "summary"
    type: "string"
    description: "分析结论摘要"
  - name: "statistics"
    type: "object"
    description: "统计指标：均值、中位数、分位数等"
  - name: "charts"
    type: "array"
    description: "生成的图表列表（base64或路径）"
  - name: "anomalies"
    type: "array"
    description: "检测到的异常点"

dependencies:
  - "pandas"
  - "numpy"

tools:
  - "scripts/analyze.py"

used_by_roles:
  - "data_analyst"
  - "chengzhi"

effectiveness_score: 0.72
confidence: "high"
---

# skill_data_analysis · 数据分析

## Overview
对结构化和非结构化数据进行统计、聚合、异常检测，输出可读的分析结论和可视化图表。是数据分析师角色的核心 Skill。

## When to Use
- 用户请求分析数据、生成报表
- 需要从原始数据提取统计结论
- 检测数据中的异常值或趋势
- 验证假设或回答数据相关问题

## When NOT to Use
- 数据尚未收集或获取（先收集再分析）
- 实时流式数据处理（应使用流式专用工具）
- 纯文本语义分析（应用 NLP 类 Skill）

## Core Workflows

### Workflow 1: 标准数据分析
**Goal:** 对给定数据源执行分析，回答业务问题

**Steps:**
1. 加载数据（CSV/JSON/SQL/API）
2. 数据清洗：缺失值、异常值、类型转换
3. 探索性分析：描述性统计、分组聚合
4. 针对性分析：按 analysis_goal 执行特定分析
5. 可视化：生成关键图表
6. 总结输出：结论 + 统计数据 + 建议

**Expected Output:**
```json
{
  "summary": "本月DAU较上月提升12%，周末为流量低谷",
  "statistics": {
    "mean": 45230,
    "median": 44100,
    "p95": 58300,
    "std": 8200
  },
  "charts": ["/tmp/chart_dau_trend.png"],
  "anomalies": [{"date": "2026-05-01", "value": 120000, "reason": "节假日峰值"}]
}
```

**Time Estimate:** 30s - 5min（视数据量而定）

## Script Interfaces

### scripts/analyze.py
```bash
# 标准分析
python3 scripts/analyze.py --goal "用户留存率" --source /data/users.json

# CSV文件分析
python3 scripts/analyze.py --goal "日活趋势" --source /data/dau.csv --format csv

# SQL数据源
python3 scripts/analyze.py --goal "收入统计" --source "SELECT date, revenue FROM orders" --format sql

# 带过滤条件
python3 scripts/analyze.py --goal "转化率分析" --source /data/funnel.json --filter '{"channel": "organic"}'
```

**Arguments:**
- `--goal`: 分析目标（必需）
- `--source`: 数据来源路径或查询（必需）
- `--format`: 数据格式：auto/csv/json/sql/api（默认auto）
- `--filter`: JSON格式过滤条件（可选）
- `--output`: 输出文件路径（默认stdout）
- `--chart`: 是否生成图表：yes/no（默认yes）

## Best Practices
1. **先理解目标再分析** — 不清楚目标时先clarify，不要盲目跑数据
2. **缺失值要显式处理** — 不能 silently drop，记录处理方式
3. **图表要带注释** — 每张图必须有标题、坐标轴标签、图例
4. **异常值要标注** — 检测到的异常必须说明原因
5. **结论要可行动** — 给出具体建议而非仅仅描述数字

## Common Pitfalls
1. **数据倾斜导致失真** — 警惕严重右偏数据，先可视化分布
2. **忽略时间维度** — 时间序列数据要检查平稳性
3. **因果混淆** — 相关性不等于因果性，谨慎下结论
4. **过度聚合** — 粒度太粗会掩盖细节，保留原始数据备份

## Failure Handling
- 数据无法加载 → 返回 error + 原因，列出支持格式
- 数据量过大 → 返回采样后的分析 + 建议全量分析参数
- 分析失败 → 返回已执行步骤 + 失败原因 + 重试建议

## Evolution History
- v1.0.0 (2026-05-09): 初始版本，基于 pandas/numpy 实现基础统计和异常检测
