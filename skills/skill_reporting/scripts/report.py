#!/usr/bin/env python3
"""
skill_reporting · 报表生成脚本
基于分析结果生成结构化报告，支持 Markdown/HTML/JSON 格式
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime


def format_markdown(data, goal, report_type, title):
    """生成 Markdown 格式报告"""
    lines = []
    
    # 标题
    if title:
        lines.append(f"# {title}\n")
    else:
        lines.append(f"# {goal} 分析报告\n")
    
    # 元信息
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"**生成时间**: {now}  \n")
    lines.append(f"**报告类型**: {report_type}  \n")
    lines.append(f"**数据周期**: {data.get('period', 'N/A')}  \n")
    lines.append("\n---\n")
    
    # 概述
    lines.append("## 概述\n")
    summary = data.get("summary", "无")
    lines.append(f"{summary}\n")
    
    # 关键指标
    stats = data.get("statistics", {})
    if stats:
        lines.append("\n## 关键指标\n")
        lines.append("| 指标 | 数值 |")
        lines.append("|------|------|")
        
        for col, vals in list(stats.items())[:10]:
            if isinstance(vals, dict) and "mean" in vals:
                lines.append(f"| {col}_均值 | {vals.get('mean', 'N/A')} |")
                lines.append(f"| {col}_中位数 | {vals.get('median', 'N/A')} |")
                lines.append(f"| {col}_标准差 | {vals.get('std', 'N/A')} |")
                lines.append(f"| {col}_P95 | {vals.get('p95', 'N/A')} |")
    
    # 趋势分析
    trend = data.get("trend_analysis")
    if trend:
        lines.append("\n## 趋势分析\n")
        lines.append(f"- **趋势方向**: {trend.get('trend', 'N/A')}")
        lines.append(f"- **变化幅度**: {trend.get('change_pct', 'N/A')}%")
        lines.append(f"- **起始值**: {trend.get('start_value', 'N/A')} ({trend.get('start_date', '')})")
        lines.append(f"- **结束值**: {trend.get('end_value', 'N/A')} ({trend.get('end_date', '')})")
        lines.append(f"- **斜率**: {trend.get('slope', 'N/A')}\n")
    
    # 分组分析
    group = data.get("group_analysis")
    if group:
        lines.append("\n## 分组分析\n")
        groups = group.get("groups", [])
        if groups:
            gb = group.get("group_by", "维度")
            lines.append(f"| {gb} | 平均值 | 样本数 | 汇总 |")
            lines.append(f"|------|--------|-------|------|")
            for g in groups[:10]:
                lines.append(f"| {g.get(gb, 'N/A')} | {g.get('avg', 'N/A'):.2f} | {g.get('count', 'N/A')} | {g.get('total', 'N/A'):.2f} |")
        lines.append("")
    
    # 异常分析
    anomalies = data.get("anomalies", [])
    if anomalies:
        lines.append("\n## 异常标注\n")
        for i, a in enumerate(anomalies[:10], 1):
            lines.append(f"{i}. **{a.get('column', 'N/A')}** = {a.get('value', 'N/A')}")
            lines.append(f"   - 原因: {a.get('reason', 'N/A')}")
            lines.append(f"   - Z-score: {a.get('z_score', 'N/A')}\n")
    
    # 建议
    lines.append("\n## 建议\n")
    suggestions = data.get("suggestions", [])
    if suggestions:
        for s in suggestions:
            lines.append(f"- {s}\n")
    else:
        # 自动生成建议
        if trend and trend.get("trend") == "increasing":
            lines.append("- 整体趋势向好，建议保持当前策略。\n")
        elif trend and trend.get("trend") == "decreasing":
            lines.append("- 整体趋势下降，建议排查下降原因并制定应对方案。\n")
        if anomalies:
            lines.append(f"- 检测到 {len(anomalies)} 个异常值，建议逐个分析原因。\n")
        if not suggestions:
            lines.append("- 建议持续监控关键指标，关注数据变化。\n")
    
    lines.append("\n---\n")
    lines.append(f"*报告由 skill_reporting 自动生成*")
    
    return "\n".join(lines)


def format_html(data, goal, report_type, title):
    """生成 HTML 格式报告"""
    md = format_markdown(data, goal, report_type, title)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title or goal} 分析报告</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 900px; margin: 40px auto; padding: 0 20px; 
               background: #fafafa; color: #333; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  h2 {{ color: #34495e; margin-top: 30px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
  th {{ background: #3498db; color: white; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .meta {{ color: #7f8c8d; font-size: 0.9em; }}
  .anomaly {{ background: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; margin: 10px 0; }}
  .suggestion {{ background: #d4edda; padding: 10px; border-left: 4px solid #28a745; margin: 10px 0; }}
  .trend-up {{ color: #28a745; font-weight: bold; }}
  .trend-down {{ color: #dc3545; font-weight: bold; }}
  pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
  .footer {{ color: #95a5a6; font-size: 0.8em; margin-top: 40px; text-align: center; }}
</style>
</head>
<body>
"""
    # 简单转换：Markdown 标题和列表转 HTML（简化实现）
    import re
    
    md_lines = md.split("\n")
    for line in md_lines:
        line = line.strip()
        if not line or line == "---":
            continue
        if line.startswith("# "):
            html += f"<h1>{line[2:]}</h1>\n"
        elif line.startswith("## "):
            html += f"<h2>{line[3:]}</h2>\n"
        elif line.startswith("**") and line.endswith("**"):
            html += f"<p><strong>{line[2:-2]}</strong></p>\n"
        elif line.startswith("| "):
            # 简单表格处理
            html += f"<p>{line}</p>\n"
        elif line.startswith("- "):
            html += f"<li>{line[2:]}</li>\n"
        elif line.startswith("*") and line.endswith("*"):
            html += f"<p><em>{line[1:-1]}</em></p>\n"
        elif line.startswith("!["):
            html += f"<p>{line}</p>\n"
        else:
            # 检测趋势箭头
            if "increasing" in line.lower():
                line = re.sub(r"(trend.*?)(increasing)", r'\1<span class="trend-up">↑ \2</span>', line)
            if "decreasing" in line.lower():
                line = re.sub(r"(trend.*?)(decreasing)", r'\1<span class="trend-down">↓ \2</span>', line)
            html += f"<p>{line}</p>\n"
    
    html += f"""
<div class="footer">
<hr>
<p>报告由 skill_reporting 自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
</body>
</html>"""
    
    return html


def format_json(data, goal, report_type, title):
    """生成 JSON 格式报告"""
    output = {
        "goal": goal,
        "title": title or f"{goal} 分析报告",
        "report_type": report_type,
        "generated_at": datetime.now().isoformat(),
        "summary": data.get("summary", ""),
        "statistics": data.get("statistics", {}),
        "trend_analysis": data.get("trend_analysis"),
        "group_analysis": data.get("group_analysis"),
        "anomalies": data.get("anomalies", []),
        "suggestions": data.get("suggestions", []),
    }
    return json.dumps(output, ensure_ascii=False, indent=2)


def generate_report(goal, data, report_type, output_format, title, compare_data=None):
    """生成报告"""
    report_type = report_type or "summary"
    output_format = output_format or "markdown"
    
    # 处理对比数据
    if compare_data:
        data["compare"] = compare_data
        # 计算变化
        if "statistics" in data and "statistics" in compare_data:
            changes = {}
            for k in data["statistics"]:
                if k in compare_data["statistics"]:
                    cur = data["statistics"][k].get("mean", 0)
                    prev = compare_data["statistics"][k].get("mean", 0)
                    if prev != 0:
                        change = round((cur - prev) / prev * 100, 2)
                        changes[k] = {"current": cur, "previous": prev, "change_pct": change}
            data["changes"] = changes
    
    if output_format == "markdown":
        return format_markdown(data, goal, report_type, title)
    elif output_format == "html":
        return format_html(data, goal, report_type, title)
    elif output_format == "json":
        return format_json(data, goal, report_type, title)
    else:
        raise ValueError(f"不支持的格式: {output_format}")


def main():
    parser = argparse.ArgumentParser(description="报表生成脚本")
    parser.add_argument("--goal", required=True, help="报告主题")
    parser.add_argument("--data", help="分析数据JSON字符串")
    parser.add_argument("--data_file", dest="data_file", help="分析结果文件路径")
    parser.add_argument("--compare_file", dest="compare_file", help="对比数据文件路径")
    parser.add_argument("--type", default="summary", choices=["summary", "detailed", "comparison", "audit"],
                        help="报告类型")
    parser.add_argument("--format", default="markdown", choices=["markdown", "html", "json"],
                        help="输出格式")
    parser.add_argument("--output", default="-", help="输出文件路径")
    parser.add_argument("--title", help="报告标题")
    parser.add_argument("--json", action="store_true", help="JSON格式输出")
    
    args = parser.parse_args()
    
    # 加载数据
    if args.data_file and Path(args.data_file).exists():
        data = json.loads(Path(args.data_file).read_text(encoding="utf-8"))
    elif args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"JSON解析失败: {e}"}))
            sys.exit(1)
    else:
        data = {}
    
    # 加载对比数据
    compare_data = None
    if args.compare_file and Path(args.compare_file).exists():
        compare_data = json.loads(Path(args.compare_file).read_text(encoding="utf-8"))
    
    try:
        output_format = "json" if args.json else args.format
        report = generate_report(args.goal, data, args.type, output_format, args.title, compare_data)
    except Exception as e:
        print(json.dumps({"error": f"报告生成失败: {str(e)}"}))
        sys.exit(1)
    
    if args.output == "-":
        print(report)
    else:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"✅ 报告已保存至: {args.output}")


if __name__ == "__main__":
    main()
