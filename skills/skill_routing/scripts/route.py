#!/usr/bin/env python3
"""
skill_routing/scripts/route.py

旨意分拣路由CLI工具

用法：
  python3 route.py --message "构建一个AI漫剧工厂"
  python3 route.py --message "今天的任务状态" --json
  python3 route.py --message "扩展Skill库" --context '{"user_id":"xxx"}'
"""

import json
import argparse
import os
import sys
from pathlib import Path

# 路径设置：支持直接从skills/目录运行，也支持从项目根目录运行
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent  # /skills/skill_routing/ → /skills/ → /hermestrix/
PROJECT_ROOT_STR = str(PROJECT_ROOT)

if PROJECT_ROOT_STR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_STR)

os.environ.setdefault("HERMESTRIX_HOME", PROJECT_ROOT_STR)


def route_message(message: str, context: dict = None) -> dict:
    """
    对旨意进行分拣路由

    Returns:
        {
            "route": "jiheng|direct|reject|clarify",
            "confidence": 0.0-1.0,
            "reasoning": "...",
            "task_type": "...",
            "keywords": [...]
        }
    """
    message_lower = message.lower()

    # 关键词提取
    keywords = []
    if any(k in message_lower for k in ["构建", "开发", "创建", "设计", "build", "create", "develop"]):
        keywords.append("构建/开发")
    if any(k in message_lower for k in ["查询", "状态", "情况", "query", "status", "list"]):
        keywords.append("查询/状态")
    if any(k in message_lower for k in ["扩展", "增加", "添加", "expand", "add"]):
        keywords.append("扩展")
    if any(k in message_lower for k in ["修复", "bug", "错误", "fix", "error"]):
        keywords.append("修复")
    if any(k in message_lower for k in ["分析", "调研", "研究", "analyze", "research"]):
        keywords.append("分析/调研")
    if any(k in message_lower for k in ["文档", "说明", "写", "文档化", "doc", "write"]):
        keywords.append("文档")

    # 路由决策
    routing_rules = [
        (["构建", "开发", "创建", "设计", "扩展", "增加", "添加",
          "build", "create", "develop", "expand", "add", "设计"],
         "jiheng", 0.85, "旨意包含建设性关键词，应由机衡规划方案"),

        (["查询", "状态", "情况", "list", "status", "query", "有什么", "多少"],
         "direct", 0.80, "旨意是简单查询，可直接处理"),

        (["修复", "bug", "错误", "fix", "error", "问题"],
         "direct", 0.75, "旨意是修复类任务，可直接执行"),

        (["分析", "调研", "研究", "analyze", "research", "调查"],
         "jiheng", 0.80, "旨意是分析调研类，应由机衡规划"),

        (["文档", "说明", "写", "doc", "write", "撰写"],
         "jiheng", 0.75, "旨意是文档类，可由机衡规划或直接处理"),
    ]

    best_match = None
    best_confidence = 0.0

    for keywords_list, route, confidence, reasoning in routing_rules:
        if any(k in message_lower for k in keywords_list):
            if confidence > best_confidence:
                best_match = {"route": route, "confidence": confidence,
                              "reasoning": reasoning}
                best_confidence = confidence

    # 默认决策：置信度低时要求澄清
    if best_match is None:
        return {
            "route": "clarify",
            "confidence": 0.5,
            "reasoning": "旨意不明确，无法自动分类，需要用户澄清",
            "task_type": None,
            "keywords": []
        }

    # 判断task_type
    task_type = None
    if best_match["route"] == "jiheng":
        if any(k in message_lower for k in ["构建", "开发", "创建", "设计", "build", "create", "develop"]):
            task_type = "system_setup"
        elif any(k in message_lower for k in ["扩展", "增加", "添加", "expand", "add"]):
            task_type = "expansion"
        elif any(k in message_lower for k in ["分析", "调研", "研究", "analyze", "research"]):
            task_type = "analysis"
        elif any(k in message_lower for k in ["文档", "说明", "写", "doc", "write"]):
            task_type = "documentation"

    return {
        "route": best_match["route"],
        "confidence": best_match["confidence"],
        "reasoning": best_match["reasoning"],
        "task_type": task_type,
        "keywords": keywords
    }


def main():
    parser = argparse.ArgumentParser(description="旨意分拣路由工具")
    parser.add_argument("--message", "-m", required=True, help="用户旨意文本")
    parser.add_argument("--context", "-c", help="JSON格式上下文")
    parser.add_argument("--json", "-j", action="store_true", help="JSON格式输出")

    args = parser.parse_args()

    context = None
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError:
            print("Error: --context 必须是有效JSON", file=sys.stderr)
            sys.exit(1)

    result = route_message(args.message, context)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"路由: {result['route']}")
        print(f"置信度: {result['confidence']:.0%}")
        print(f"理由: {result['reasoning']}")
        if result.get("task_type"):
            print(f"任务类型: {result['task_type']}")
        if result.get("keywords"):
            print(f"关键词: {', '.join(result['keywords'])}")


if __name__ == "__main__":
    main()
