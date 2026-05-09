---
name: "skill_reporting"
description: "基于数据分析结果生成结构化报告，支持多格式（Markdown/HTML/JSON/PDF）"
domain: "data"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "analysis_data"
    type: "object"
    required: true
    description: "分析结果数据（来自 skill_data_analysis 的输出）"
  - name: "report_type"
    type: "string"
    required: false
    description: "报告类型：summary/detailed/comparison/audit"
  - name: "format"
    type: "string"
    required: false
    description: "输出格式：markdown/html/json/pdf"
  - name: "title"
    type: "string"
    required: false
    description: "报告标题"

outputs:
  - name: "report_content"
    type: "string"
    description: "报告内容（根据format）"
  - name: "report_path"
    type: "string"
    description: "报告文件路径（如已写入文件）"
  - name: "sections"
    type: "array"
    description: "报告章节列表"

dependencies:
  - "skill_data_analysis"

tools:
  - "scripts/report.py"

used_by_roles:
  - "data_analyst"
  - "taizi"

effectiveness_score: 0.75
confidence: "high"
---

# skill_reporting · 报表生成

## Overview
将数据分析结果转化为结构化、可读性强的报告，支持多格式输出。是数据分析流程的最后一步，负责将数字转化为决策依据。

## When to Use
- 数据分析完成后需要输出结论
- 需要生成周期性报表（日报、周报、月报）
- 需要向非技术人员展示数据结论
- 需要对比不同时间段或维度的数据

## When NOT to Use
- 数据尚未分析（先分析再报表）
- 实时数据展示（应用 Dashboard 类工具）
- 简单数据查询（不需要完整报告，直接返回数据）

## Core Workflows

### Workflow 1: 生成分析报告
**Goal:** 将分析数据转化为可读报告

**Steps:**
1. 解析 analysis_data，提取关键指标
2. 确定报告结构（summary/detailed/comparison）
3. 填充各章节内容
4. 格式化输出（Markdown/HTML/JSON）
5. 如需 PDF，触发格式转换

**Expected Output:**
```json
{
  "report_content": "# 日活分析报告\n\n## 概述\n本月DAU均值45,230，较上月提升12%...",
  "report_path": "/tmp/dau_report_20260509.md",
  "sections": ["概述", "关键指标", "趋势分析", "异常分析", "建议"]
}
```

**Time Estimate:** 10s - 2min

### Workflow 2: 对比报告
**Goal:** 对比两个时间段或维度的数据

**Steps:**
1. 收集两个数据集的分析结果
2. 计算变化率、差异值
3. 生成对比表格和结论
4. 输出对比报告

## Script Interfaces

### scripts/report.py
```bash
# 标准报告生成
python3 scripts/report.py --goal "dau" --data '{"mean":45230,"trend":"increasing"}'

# 生成详细报告
python3 scripts/report.py --goal "dau" --data_file /tmp/analysis_result.json --type detailed

# 输出HTML格式
python3 scripts/report.py --goal "dau" --data_file /tmp/analysis_result.json --format html --output /tmp/report.html

# 对比报告
python3 scripts/report.py --goal "dau_compare" --data_file /tmp/cur.json --compare_file /tmp/last.json --format markdown
```

**Arguments:**
- `--goal`: 报告主题（必需）
- `--data`: 分析数据JSON字符串（可选，与 --data_file 二选一）
- `--data_file`: 分析结果文件路径（可选）
- `--compare_file`: 对比数据文件路径（可选，用于对比报告）
- `--type`: 报告类型：summary/detailed/comparison/audit（默认summary）
- `--format`: 输出格式：markdown/html/json（默认markdown）
- `--output`: 输出文件路径（默认stdout）
- `--title`: 报告标题（可选）

## Report Templates

### Summary Report Sections
1. **概述** — 一句话总结核心发现
2. **关键指标** — 主要数字和变化率
3. **趋势分析** — 时间维度变化
4. **异常标注** — 发现的异常及原因
5. **建议** — 基于数据的行动建议

### Detailed Report Sections
在 Summary 基础上增加：
6. **统计分布** — 均值、分位数、分布图
7. **分组对比** — 各维度的细分数据
8. **方法说明** — 分析方法和参数

## Best Practices
1. **结论前置** — Executive Summary 放在报告开头
2. **数字要可视化** — 关键指标配合图表
3. **变化要有语境** — 说明环比/同比，不是孤立数字
4. **建议要可操作** — 避免"建议关注"类废话
5. **版本要记录** — 每份报告标注生成时间和数据周期

## Common Pitfalls
1. **数据堆砌** — 罗列数字没有解读，要转化为洞察
2. **格式混乱** — Markdown/HTML 混用导致可读性差
3. **过度细节** — 报告太长，要突出重点
4. **缺少建议** — 只说"下降了5%"不说"建议检查渠道X"

## Failure Handling
- 数据不完整 → 生成部分报告 + 标注缺失字段
- 格式不支持 → 降级为 JSON 输出 + 错误说明
- 写入失败 → 返回内存中的报告内容 + 错误原因

## Evolution History
- v1.0.0 (2026-05-09): 初始版本，支持 Markdown/HTML/JSON 多格式报告生成
