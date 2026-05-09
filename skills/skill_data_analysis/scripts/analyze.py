#!/usr/bin/env python3
"""
skill_data_analysis · 数据分析脚本
支持 CSV/JSON/SQL/API 等数据源，执行统计、聚合、异常检测
"""

import argparse
import json
import sys
import os
from pathlib import Path

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print(json.dumps({"error": "pandas/numpy 未安装，请执行: pip install pandas numpy"}))
    sys.exit(1)


def load_data(source, fmt, filter_cond):
    """加载数据"""
    if fmt == "csv" or (fmt == "auto" and str(source).endswith(".csv")):
        df = pd.read_csv(source)
    elif fmt == "json" or (fmt == "auto" and str(source).endswith(".json")):
        df = pd.read_json(source)
    elif fmt == "sql":
        # 简化实现：假设 source 是 CSV 路径，实际 SQL 需要数据库连接
        df = pd.read_csv(source)
    else:
        # 尝试自动检测
        try:
            df = pd.read_csv(source)
        except Exception:
            try:
                df = pd.read_json(source)
            except Exception as e:
                raise ValueError(f"不支持的数据格式: {fmt}, 错误: {e}")
    
    # 应用过滤
    if filter_cond:
        for k, v in filter_cond.items():
            if k in df.columns:
                df = df[df[k] == v]
    
    return df


def basic_statistics(df):
    """描述性统计"""
    stats = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        stats[col] = {
            "count": int(len(s)),
            "mean": round(float(s.mean()), 4),
            "median": round(float(s.median()), 4),
            "std": round(float(s.std()), 4) if len(s) > 1 else 0.0,
            "min": round(float(s.min()), 4),
            "max": round(float(s.max()), 4),
            "p25": round(float(s.quantile(0.25)), 4),
            "p75": round(float(s.quantile(0.75)), 4),
            "p95": round(float(s.quantile(0.95)), 4),
        }
    
    # 非数值列
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in str_cols:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        stats[col] = {
            "count": int(len(s)),
            "unique": int(s.nunique()),
            "top5": s.value_counts().head(5).to_dict()
        }
    
    return stats


def detect_anomalies(df, threshold=3.0):
    """基于Z-score检测异常"""
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) <= 2:
            continue
        mean = s.mean()
        std = s.std()
        if std == 0:
            continue
        
        z_scores = np.abs((s - mean) / std)
        for idx, z in z_scores.items():
            if z > threshold:
                row = df.loc[idx]
                anomalies.append({
                    "column": col,
                    "index": int(idx),
                    "value": float(row[col]),
                    "z_score": round(float(z), 2),
                    "reason": f"Z-score={z:.2f} > {threshold}"
                })
    
    # 限制返回数量
    return anomalies[:20]


def trend_analysis(df, date_col, value_col):
    """趋势分析"""
    if date_col not in df.columns or value_col not in df.columns:
        return None
    
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col)
        
        s = df[value_col].dropna()
        if len(s) < 2:
            return None
        
        # 简单线性趋势
        x = np.arange(len(s))
        slope, intercept = np.polyfit(x, s.values, 1)
        
        # 计算趋势方向
        trend = "increasing" if slope > 0 else "decreasing"
        change_pct = round(float((s.iloc[-1] - s.iloc[0]) / s.iloc[0] * 100), 2) if s.iloc[0] != 0 else 0
        
        return {
            "trend": trend,
            "slope": round(float(slope), 4),
            "change_pct": change_pct,
            "start_value": round(float(s.iloc[0]), 4),
            "end_value": round(float(s.iloc[-1]), 4),
            "start_date": str(df[date_col].iloc[0].date()) if pd.notna(df[date_col].iloc[0]) else None,
            "end_date": str(df[date_col].iloc[-1].date()) if pd.notna(df[date_col].iloc[-1]) else None,
        }
    except Exception:
        return None


def group_analysis(df, group_by, value_col):
    """分组聚合分析"""
    if group_by not in df.columns or value_col not in df.columns:
        return None
    
    try:
        grouped = df.groupby(group_by)[value_col].agg(["mean", "count", "sum"]).reset_index()
        grouped.columns = [group_by, "avg", "count", "total"]
        grouped = grouped.sort_values("avg", ascending=False)
        return {
            "group_by": group_by,
            "value_col": value_col,
            "groups": grouped.to_dict(orient="records")
        }
    except Exception:
        return None


def analyze(data_source, analysis_goal, options):
    """主分析入口"""
    result = {
        "goal": analysis_goal,
        "summary": "",
        "statistics": {},
        "anomalies": [],
        "charts": [],
        "group_analysis": None,
        "trend_analysis": None
    }
    
    fmt = options.get("format", "auto")
    filter_cond = options.get("filter", {})
    
    try:
        df = load_data(data_source, fmt, filter_cond)
    except Exception as e:
        result["error"] = f"数据加载失败: {str(e)}"
        return result
    
    result["row_count"] = int(len(df))
    result["col_count"] = int(len(df.columns))
    
    # 自动检测日期列和数值列
    date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # 基础统计
    result["statistics"] = basic_statistics(df)
    
    # 异常检测
    result["anomalies"] = detect_anomalies(df)
    
    # 趋势分析（如果有日期列）
    if date_cols and numeric_cols:
        td = trend_analysis(df, date_cols[0], numeric_cols[0])
        if td:
            result["trend_analysis"] = td
    
    # 分组分析（如果有指定）
    group_by = options.get("group_by")
    agg_col = options.get("agg_col") or (numeric_cols[0] if numeric_cols else None)
    if group_by and group_by in df.columns and agg_col and agg_col in df.columns:
        result["group_analysis"] = group_analysis(df, group_by, agg_col)
    
    # 生成摘要
    summary_parts = []
    if result["row_count"] > 0:
        summary_parts.append(f"数据共{result['row_count']}行、{result['col_count']}列")
    if result["anomalies"]:
        summary_parts.append(f"检测到{len(result['anomalies'])}个异常值")
    if result.get("trend_analysis"):
        ta = result["trend_analysis"]
        summary_parts.append(f"趋势:{ta['trend']}({ta['change_pct']}%)")
    if result.get("group_analysis"):
        ga = result["group_analysis"]
        top = ga["groups"][0] if ga["groups"] else None
        if top:
            summary_parts.append(f"分组最高:{top[ga['group_by']]}={top['avg']:.2f}")
    
    result["summary"] = "；".join(summary_parts) if summary_parts else "分析完成"
    
    return result


def main():
    parser = argparse.ArgumentParser(description="数据分析脚本")
    parser.add_argument("--goal", required=True, help="分析目标")
    parser.add_argument("--source", required=True, help="数据来源路径")
    parser.add_argument("--format", default="auto", help="数据格式: auto/csv/json/sql")
    parser.add_argument("--filter", default="{}", help="过滤条件JSON")
    parser.add_argument("--group-by", dest="group_by", help="分组字段")
    parser.add_argument("--agg-col", dest="agg_col", help="聚合字段")
    parser.add_argument("--output", default="-", help="输出文件路径")
    parser.add_argument("--chart", default="no", choices=["yes", "no"], help="是否生成图表")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    args = parser.parse_args()
    
    try:
        filter_cond = json.loads(args.filter)
    except:
        filter_cond = {}
    
    options = {
        "format": args.format,
        "filter": filter_cond,
        "group_by": args.group_by,
        "agg_col": args.agg_col,
    }
    
    result = analyze(args.source, args.goal, options)
    
    if args.json:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        lines = [f"📊 分析目标: {result.get('goal', 'N/A')}",
                 f"📝 摘要: {result.get('summary', 'N/A')}",
                 f"📈 行数: {result.get('row_count', 0)} | 列数: {result.get('col_count', 0)}"]
        if result.get("trend_analysis"):
            ta = result["trend_analysis"]
            lines.append(f"📉 趋势: {ta['trend']} ({ta['change_pct']}%)")
        if result.get("anomalies"):
            lines.append(f"⚠️ 异常值: {len(result['anomalies'])}个")
        lines.append(f"\n统计数据: {json.dumps(result.get('statistics', {}), ensure_ascii=False, indent=2)}")
        output = "\n".join(lines)
    
    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"✅ 结果已保存至: {args.output}")


if __name__ == "__main__":
    main()
