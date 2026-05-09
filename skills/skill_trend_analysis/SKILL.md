---
name: "skill_trend_analysis"
description: "时间序列趋势分析、季节性检测、预测和周期性模式识别"
domain: "data"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "data_source"
    type: "string"
    required: true
    description: "数据来源：CSV/JSON 文件路径或 DataFrame"
  - name: "date_column"
    type: "string"
    required: true
    description: "日期/时间列名"
  - name: "value_column"
    type: "string"
    required: true
    description: "要分析的值列名"
  - name: "forecast_periods"
    type: "integer"
    required: false
    description: "预测周期数（默认5）"
  - name: "options"
    type: "object"
    required: false
    description: "可选参数：seasonality, detection_method, confidence_level"

outputs:
  - name: "trend"
    type: "string"
    description: "趋势方向：increasing/decreasing/stable"
  - name: "slope"
    type: "float"
    description: "趋势斜率"
  - name: "seasonality"
    type: "object"
    description: "季节性分析结果"
  - name: "forecast"
    type: "array"
    description: "预测值列表"
  - name: "changepoints"
    type: "array"
    description: "检测到的变点"
  - name: "summary"
    type: "string"
    description: "趋势分析总结"

dependencies:
  - "pandas"
  - "numpy"

tools:
  - "scripts/trend.py"

used_by_roles:
  - "data_analyst"
  - "taizi"

effectiveness_score: 0.70
confidence: "medium"
---

# skill_trend_analysis · 趋势分析

## Overview
对时间序列数据进行深度趋势分析，包括趋势方向检测、季节性模式识别、变点检测和未来预测。是数据分析中理解数据演变规律的核心 Skill。

## When to Use
- 分析指标随时间的变化趋势
- 检测数据中的周期性模式（周/月/季/年）
- 发现数据中的突变点（拐点）
- 需要预测未来走势
- 比较多段时间的变化

## When NOT to Use
- 非时间序列数据的静态分析（用 skill_data_analysis）
- 实时流式数据（应用专用流处理工具）
- 数据量太少（少于10个时间点难以做趋势分析）

## Core Workflows

### Workflow 1: 标准趋势分析
**Goal:** 分析时间序列数据的趋势和模式

**Steps:**
1. 加载数据，按时间排序
2. 趋势检测：线性回归/移动平均
3. 季节性分析：周期检测、分解
4. 变点检测：识别趋势突变
5. 预测：如需要，输出未来N期预测
6. 总结输出

**Expected Output:**
```json
{
  "trend": "increasing",
  "slope": 125.5,
  "trend_strength": 0.85,
  "seasonality": {
    "detected": true,
    "period": 7,
    "pattern": "周周期性"
  },
  "changepoints": [{"date": "2026-04-01", "type": "increase", "reason": "活动促销"}],
  "forecast": [{"date": "2026-05-10", "value": 48200}, {"date": "2026-05-11", "value": 47500}],
  "summary": "DAU呈上升趋势（斜率125.5），存在明显周周期性，周末为低谷"
}
```

**Time Estimate:** 30s - 3min（视数据量和预测周期而定）

### Workflow 2: 变点检测
**Goal:** 发现数据中的结构性突变

**Steps:**
1. 计算滚动统计量（均值/方差）
2. 应用变点检测算法
3. 标注每个变点的位置和类型
4. 分析变点原因（需结合上下文）

## Script Interfaces

### scripts/trend.py
```bash
# 标准趋势分析
python3 scripts/trend.py --date_col date --value_col dau --source /data/dau.csv

# 指定日期列和值列
python3 scripts/trend.py --source /data/sales.json --date_col order_date --value_col revenue

# 预测未来10期
python3 scripts/trend.py --source /data/metrics.csv --date_col timestamp --value_col value --forecast 10

# 检测季节性（周期=7表示周）
python3 scripts/trend.py --source /data/ traffic.csv --date_col day --value_col views --seasonality 7

# 输出JSON格式
python3 scripts/trend.py --source /data/dau.csv --date_col date --value_col dau --json
```

**Arguments:**
- `--source`: 数据来源（必需）
- `--date_col`: 日期列名（必需）
- `--value_col`: 值列名（必需）
- `--forecast`: 预测周期数（默认5）
- `--seasonality`: 季节性周期（默认自动检测）
- `--changepoint`: 是否检测变点：yes/no（默认yes）
- `--output`: 输出文件路径（默认stdout）
- `--json`: JSON格式输出

## Trend Detection Methods

| 方法 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| 线性回归 | 稳定趋势 | 简单、可解释 | 不能捕捉非线性 |
| 移动平均 | 去除噪声 | 平滑直观 | 有滞后效应 |
| 多项式拟合 | 非线性趋势 | 灵活 | 容易过拟合 |
| 指数平滑 | 短期预测 | 重视近期 | 需要足够历史 |

## Seasonality Detection

1. **自相关分析 (ACF)** — 检测周期性相关性
2. **傅里叶变换** — 提取周期频率
3. **STL分解** — 分离趋势/季节/残差

## Best Practices
1. **数据要先排序** — 确保时间顺序正确
2. **处理缺失日期** — 用前向填充或插值
3. **异常值会影响趋势** — 先用 skill_data_analysis 检测异常
4. **预测要有置信区间** — 给出不确定性范围
5. **变点要结合业务** — 算法检测到变点，还需业务解释

## Common Pitfalls
1. **忽略季节性** — 不检测季节性会导致错误趋势判断
2. **趋势外推过远** — 预测周期越长，误差越大
3. **忽视变点** — 突变会被平滑算法掩盖
4. **数据太少** — 少于20个点难以做可靠分析

## Failure Handling
- 数据不足 → 返回 error + 最小数据量要求
- 日期格式无法解析 → 尝试多种格式，标注解析方式
- 季节性检测失败 → 返回无季节性 + 原因
- 预测失败 → 返回趋势分析结果，跳过预测部分

## Evolution History
- v1.0.0 (2026-05-09): 初始版本，基于线性回归和移动平均实现趋势检测，支持简单预测
