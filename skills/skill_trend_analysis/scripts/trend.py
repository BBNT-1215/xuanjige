#!/usr/bin/env python3
"""
skill_trend_analysis · 趋势分析脚本
时间序列趋势检测、季节性分析、变点检测和预测
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print(json.dumps({"error": "pandas/numpy 未安装，请执行: pip install pandas numpy"}))
    sys.exit(1)


def detect_trend(series):
    """基于线性回归检测趋势"""
    x = np.arange(len(series))
    y = series.values
    
    # 去除NaN
    mask = ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]
    
    if len(x_clean) < 2:
        return None, None, None
    
    # 线性回归
    slope, intercept = np.polyfit(x_clean, y_clean, 1)
    
    # 计算趋势强度（R²）
    if len(x_clean) > 2:
        y_pred = slope * x_clean + intercept
        ss_res = np.sum((y_clean - y_pred) ** 2)
        ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    else:
        r_squared = 0
    
    # 判断趋势方向
    slope_per_unit = slope
    total_change = slope * (len(series) - 1)
    change_pct = (total_change / np.mean(y_clean) * 100) if np.mean(y_clean) != 0 else 0
    
    if abs(slope_per_unit) < 0.01:
        trend = "stable"
    elif slope_per_unit > 0:
        trend = "increasing"
    else:
        trend = "decreasing"
    
    return trend, slope_per_unit, r_squared, change_pct


def detect_seasonality(series, period_hint=None):
    """基于自相关检测季节性"""
    s = series.dropna()
    if len(s) < period_hint * 2 if period_hint else 10:
        return {"detected": False, "reason": "数据不足"}
    
    # 尝试不同周期
    best_period = 0
    best_corr = 0
    
    max_period = min(365, len(s) // 2)
    min_period = 2
    
    for period in range(min_period, max_period + 1):
        if len(s) < period * 2:
            continue
        # 计算滞后period的自相关
        corr = s.autocorr(lag=period)
        if corr > best_corr:
            best_corr = corr
            best_period = period
    
    if best_corr > 0.5 and best_period > 0:
        return {
            "detected": True,
            "period": int(best_period),
            "correlation": round(float(best_corr), 3),
            "pattern": f"周期={best_period}"
        }
    
    return {"detected": False, "reason": "未检测到显著季节性"}


def moving_average_trend(series, window=7):
    """移动平均趋势"""
    ma = series.rolling(window=window, min_periods=1).mean()
    
    # 计算移动平均的斜率
    if len(ma) < 2:
        return 0
    
    x = np.arange(len(ma))
    slope, _ = np.polyfit(x, ma.dropna().values, 1)
    return slope


def detect_changepoints(series, threshold=2.0):
    """基于滚动统计检测变点"""
    changepoints = []
    
    if len(series) < 10:
        return changepoints
    
    window = max(3, len(series) // 10)
    rolling_mean = series.rolling(window=window, min_periods=window).mean()
    rolling_std = series.rolling(window=window, min_periods=window).std()
    
    for i in range(window, len(series)):
        if pd.isna(rolling_std.iloc[i]) or rolling_std.iloc[i] == 0:
            continue
        
        z_score = abs((series.iloc[i] - rolling_mean.iloc[i]) / rolling_std.iloc[i])
        
        if z_score > threshold:
            changepoints.append({
                "index": int(i),
                "position": i / len(series),  # 相对位置
                "value": float(series.iloc[i]),
                "z_score": round(float(z_score), 2),
                "type": "spike" if series.iloc[i] > rolling_mean.iloc[i] else "drop"
            })
    
    # 合并相邻的变点
    merged = []
    for cp in changepoints:
        if not merged or cp["index"] - merged[-1]["index"] > window:
            merged.append(cp)
    
    return merged[:10]  # 最多返回10个


def simple_forecast(series, periods=5, method="linear"):
    """简单预测"""
    x = np.arange(len(series))
    y = series.values
    
    mask = ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]
    
    if len(x_clean) < 3:
        return []
    
    slope, intercept = np.polyfit(x_clean, y_clean, 1)
    
    # 生成预测
    forecasts = []
    last_date = None
    freq = infer_frequency(series)
    
    for i in range(1, periods + 1):
        pred_value = slope * (len(x_clean) - 1 + i) + intercept
        
        # 计算预测区间（简化版：基于残差标准差）
        residuals = y_clean - (slope * x_clean + intercept)
        std_res = np.std(residuals)
        conf_interval = 1.96 * std_res * np.sqrt(1 + i / len(x_clean))
        
        forecasts.append({
            "period": i,
            "value": round(float(max(0, pred_value)), 2),
            "lower": round(float(max(0, pred_value - conf_interval)), 2),
            "upper": round(float(pred_value + conf_interval), 2)
        })
    
    return forecasts


def infer_frequency(series):
    """推断时间频率"""
    if len(series) < 2:
        return timedelta(days=1)
    
    try:
        dates = pd.to_datetime(series.index if hasattr(series, 'index') else series)
        if hasattr(dates, 'diff'):
            diffs = dates.diff().dropna()
            if len(diffs) > 0:
                median_diff = diffs.median()
                return median_diff
    except:
        pass
    
    return timedelta(days=1)


def trend_analysis(source, date_col, value_col, forecast_periods, seasonality, detect_changepoint):
    """主分析入口"""
    result = {
        "date_column": date_col,
        "value_column": value_col,
        "trend": None,
        "slope": None,
        "trend_strength": None,
        "change_pct": None,
        "seasonality": {},
        "changepoints": [],
        "forecast": [],
        "summary": ""
    }
    
    try:
        # 加载数据
        if str(source).endswith(".csv"):
            df = pd.read_csv(source)
        elif str(source).endswith(".json"):
            df = pd.read_json(source)
        else:
            df = pd.read_csv(source)
        
        # 解析日期列
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col, value_col])
        df = df.sort_values(date_col)
        
        if len(df) < 3:
            result["error"] = "数据不足，至少需要3个数据点"
            return result
        
        # 设置日期为索引
        series = df.set_index(date_col)[value_col]
        
        # 1. 趋势检测
        trend, slope, r_squared, change_pct = detect_trend(series)
        result["trend"] = trend
        result["slope"] = round(float(slope), 4) if slope is not None else None
        result["trend_strength"] = round(float(r_squared), 3) if r_squared is not None else None
        result["change_pct"] = round(float(change_pct), 2) if change_pct is not None else None
        
        # 2. 季节性检测
        period_hint = int(seasonality) if seasonality else None
        result["seasonality"] = detect_seasonality(series, period_hint)
        
        # 3. 变点检测
        if detect_changepoint:
            result["changepoints"] = detect_changepoints(series)
        
        # 4. 预测
        if forecast_periods > 0:
            result["forecast"] = simple_forecast(series, forecast_periods)
        
        # 5. 生成摘要
        summary_parts = []
        if trend:
            summary_parts.append(f"趋势{trend}（斜率{result['slope']:.2f}，变化{result['change_pct']}%）")
        if result["seasonality"].get("detected"):
            summary_parts.append(f"存在{result['seasonality']['period']}周期季节性")
        if result["changepoints"]:
            summary_parts.append(f"检测到{len(result['changepoints'])}个变点")
        if result["forecast"]:
            f = result["forecast"][-1]
            summary_parts.append(f"预测{forecast_periods}期后约{f['value']}")
        
        result["summary"] = "，".join(summary_parts) if summary_parts else "分析完成"
        
    except Exception as e:
        result["error"] = f"分析失败: {str(e)}"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="趋势分析脚本")
    parser.add_argument("--source", required=True, help="数据来源路径")
    parser.add_argument("--date_col", dest="date_col", required=True, help="日期列名")
    parser.add_argument("--value_col", dest="value_col", required=True, help="值列名")
    parser.add_argument("--forecast", type=int, default=5, help="预测周期数")
    parser.add_argument("--seasonality", help="季节性周期（数字或auto）")
    parser.add_argument("--changepoint", choices=["yes", "no"], default="yes", help="是否检测变点")
    parser.add_argument("--output", default="-", help="输出文件路径")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    args = parser.parse_args()
    
    result = trend_analysis(
        args.source,
        args.date_col,
        args.value_col,
        args.forecast,
        args.seasonality,
        args.changepoint == "yes"
    )
    
    if args.json:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        lines = [f"📈 趋势分析: {args.value_col}",
                 f"趋势方向: {result.get('trend', 'N/A')}",
                 f"斜率: {result.get('slope', 'N/A')}",
                 f"变化幅度: {result.get('change_pct', 'N/A')}%"]
        if result.get("seasonality"):
            sea = result["seasonality"]
            if sea.get("detected"):
                lines.append(f"季节性: 检测到周期={sea['period']}（相关性={sea['correlation']}）")
            else:
                lines.append(f"季节性: 未检测到")
        if result.get("changepoints"):
            lines.append(f"变点: 检测到{len(result['changepoints'])}个")
        if result.get("forecast"):
            lines.append(f"预测: {result['forecast'][-1]}")
        lines.append(f"\n摘要: {result.get('summary', 'N/A')}")
        if result.get("error"):
            lines.append(f"错误: {result['error']}")
        output = "\n".join(lines)
    
    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"✅ 趋势分析结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
