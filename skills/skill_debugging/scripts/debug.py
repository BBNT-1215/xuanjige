#!/usr/bin/env python3
"""
skill_debugging - 调试排错辅助脚本
系统性定位和修复软件问题
"""

import argparse
import json
import sys
import re
from typing import Dict, Any, List, Optional


# 常见错误模式与诊断规则
ERROR_PATTERNS = {
    "python": [
        {
            "pattern": r"ModuleNotFoundError|NoModuleFound",
            "root_cause": "模块未安装或路径错误",
            "fix": "pip install <module_name> 或检查 PYTHONPATH"
        },
        {
            "pattern": r"IndentationError",
            "root_cause": "缩进错误",
            "fix": "检查空格/制表符混用，使用4空格缩进"
        },
        {
            "pattern": r"SyntaxError",
            "root_cause": "语法错误",
            "fix": "检查代码语法，特别是括号、引号匹配"
        },
        {
            "pattern": r"IndexError: list index out of range",
            "root_cause": "列表索引越界",
            "fix": "访问前检查列表长度或使用 try-except 保护"
        },
        {
            "pattern": r"KeyError",
            "root_cause": "字典键不存在",
            "fix": "使用 dict.get() 或先检查键存在性"
        },
        {
            "pattern": r"TypeError.*NoneType",
            "root_cause": "对 None 值进行了不允许的操作",
            "fix": "在使用前检查是否为 None"
        },
        {
            "pattern": r"ZeroDivisionError",
            "root_cause": "除数为零",
            "fix": "在除法运算前检查除数是否为零"
        },
        {
            "pattern": r"connection refused",
            "root_cause": "网络连接被拒绝",
            "fix": "检查目标服务是否启动，端口是否正确"
        },
        {
            "pattern": r"timeout|timed out",
            "root_cause": "请求超时",
            "fix": "检查网络延迟、服务负载，或增加超时时间"
        },
        {
            "pattern": r"OutOfMemory|OOM|MemoryError",
            "root_cause": "内存耗尽",
            "fix": "检查内存泄漏、大对象、或者增加内存限制"
        },
    ],
    "javascript": [
        {
            "pattern": r"Cannot read property.*undefined",
            "root_cause": "读取了 undefined 的属性",
            "fix": "在使用前检查 undefined 或使用可选链 ?. "
        },
        {
            "pattern": r"TypeError: .* is not a function",
            "root_cause": "调用了非函数对象",
            "fix": "检查对象类型，确保方法存在"
        },
        {
            "pattern": r"ReferenceError: .* is not defined",
            "root_cause": "使用了未定义的变量",
            "fix": "检查变量名拼写，确保已声明"
        },
        {
            "pattern": r"SyntaxError: Unexpected token",
            "root_cause": "语法错误",
            "fix": "检查括号、引号、逗号是否匹配"
        },
        {
            "pattern": r"Maximum call stack size exceeded",
            "root_cause": "无限递归",
            "fix": "检查递归终止条件"
        },
    ],
    "java": [
        {
            "pattern": r"NullPointerException",
            "root_cause": "空指针异常",
            "fix": "在使用前检查是否为 null"
        },
        {
            "pattern": r"ClassNotFoundException|NoClassDefFoundError",
            "root_cause": "类未找到",
            "fix": "检查 classpath 配置，确保依赖 jar 包存在"
        },
        {
            "pattern": r"ConcurrentModificationException",
            "root_cause": "并发修改集合",
            "fix": "使用线程安全的集合或在迭代时加锁"
        },
        {
            "pattern": r"OutOfMemoryError",
            "root_cause": "内存耗尽",
            "fix": "检查内存泄漏，增加堆大小"
        },
        {
            "pattern": r"java.net.ConnectException: Connection refused",
            "root_cause": "连接被拒绝",
            "fix": "检查目标服务是否启动"
        },
    ],
    "sql": [
        {
            "pattern": r"Table.*doesn't exist",
            "root_cause": "表不存在",
            "fix": "检查表名拼写，确认数据库中有此表"
        },
        {
            "pattern": r"Column.*doesn't exist",
            "root_cause": "列不存在",
            "fix": "检查列名拼写"
        },
        {
            "pattern": r"Duplicate entry",
            "root_cause": "唯一键冲突",
            "fix": "检查插入数据是否违反唯一约束"
        },
        {
            "pattern": r"foreign key.*fails",
            "root_cause": "外键约束失败",
            "fix": "先插入/更新关联记录"
        },
    ]
}


def analyze_error_pattern(error_text: str, language: str = None) -> List[Dict[str, Any]]:
    """分析错误日志，匹配已知模式"""
    matches = []
    
    # 确定要检查的语言
    languages_to_check = [language] if language else list(ERROR_PATTERNS.keys())
    
    for lang in languages_to_check:
        if lang not in ERROR_PATTERNS:
            continue
        
        for rule in ERROR_PATTERNS[lang]:
            if re.search(rule["pattern"], error_text, re.IGNORECASE):
                matches.append({
                    "language": lang,
                    "pattern": rule["pattern"],
                    "root_cause": rule["root_cause"],
                    "fix": rule["fix"],
                    "confidence": 0.9
                })
    
    return matches


def analyze_symptom(symptom: str, code_context: str = None) -> Dict[str, Any]:
    """分析问题症状"""
    
    symptom_lower = symptom.lower()
    
    # 症状分类
    categories = {
        "performance": ["慢", "卡", "超时", "延迟", "响应时间", "performance", "slow", "timeout"],
        "crash": ["崩溃", "crash", "panic", "fatal"],
        "logic": ["错误", "不对", "不符", "异常", "结果不对", "bug"],
        "network": ["连接", "网络", "network", "connection", "refused"],
        "memory": ["内存", "oom", "memory", "泄漏", "leak"],
        "data": ["数据", "data", "丢失", "corrupt"],
    }
    
    detected_categories = []
    for cat, keywords in categories.items():
        if any(k in symptom_lower for k in keywords):
            detected_categories.append(cat)
    
    # 关键词分析
    keywords_found = []
    all_keywords = [
        "null", "none", "undefined", "空", "未定义",
        "timeout", "超时", "死锁", "deadlock",
        "race", "竞态", "并发", "concurrent",
        "leak", "泄漏", "内存",
        "loop", "循环", "递归", "recursive",
        "permission", "权限", "认证", "auth",
    ]
    for kw in all_keywords:
        if kw in symptom_lower:
            keywords_found.append(kw)
    
    return {
        "detected_categories": detected_categories,
        "keywords_found": keywords_found,
        "likely_types": detected_categories if detected_categories else ["unknown"]
    }


def generate_debug_questions(symptom: str, categories: List[str]) -> List[str]:
    """生成调试问题，帮助进一步诊断"""
    
    questions = []
    
    if "network" in categories:
        questions.extend([
            "目标服务是否正常运行？",
            "网络是否可达？（ping/telnet 测试）",
            "端口是否正确？防火墙是否开放？"
        ])
    
    if "performance" in categories:
        questions.extend([
            "问题发生的时间规律？（启动即发生/运行一段时间后）",
            "系统负载如何？（CPU/内存/磁盘）",
            "数据库慢查询日志是否有异常？"
        ])
    
    if "logic" in categories:
        questions.extend([
            "相同的输入是否总是产生相同的结果？",
            "问题是否在特定条件下触发？",
            "最近的代码变更是什么？"
        ])
    
    if "memory" in categories:
        questions.extend([
            "内存使用量是否持续增长？",
            "是否有大量对象被创建但未释放？",
            "缓存是否有过期或清理机制？"
        ])
    
    # 通用问题
    if not questions:
        questions.extend([
            "问题是否可以稳定复现？",
            "何时开始出现这个问题？",
            "最近有什么变更？（代码/配置/环境）"
        ])
    
    return questions


def debug(symptom: str, error_logs: str = None, 
          code_context: str = None, 
          environment: Dict[str, Any] = None) -> Dict[str, Any]:
    """主调试函数"""
    
    language = environment.get("language") if environment else None
    
    # 1. 分析症状
    symptom_analysis = analyze_symptom(symptom, code_context)
    
    # 2. 分析错误日志
    error_matches = []
    if error_logs:
        error_matches = analyze_error_pattern(error_logs, language)
    
    # 3. 如果有代码上下文，尝试分析
    code_issues = []
    if code_context:
        # 检测常见代码问题
        if "print(" in code_context and "debug" not in symptom_lower:
            code_issues.append("代码中可能残留调试用的 print 语句")
        
        if re.search(r'\.get\s*\(\s*["\']', code_context):
            code_issues.append("使用 dict.get() 是好习惯，但需注意默认值处理")
    
    # 4. 生成根因假设
    root_causes = []
    confidence = 0.5
    
    if error_matches:
        for match in error_matches:
            root_causes.append({
                "cause": match["root_cause"],
                "fix": match["fix"],
                "source": f"从错误日志匹配: {match['pattern']}",
                "confidence": match["confidence"]
            })
        confidence = max(m["confidence"] for m in error_matches)
    else:
        # 基于症状的推断
        if "timeout" in symptom.lower() or "超时" in symptom:
            root_causes.append({
                "cause": "可能是网络延迟、服务负载过高或死循环",
                "fix": "1. 检查网络连通性 2. 查看服务资源使用 3. 添加超时控制",
                "source": "基于症状推断",
                "confidence": 0.6
            })
        if "null" in symptom.lower() or "空指针" in symptom:
            root_causes.append({
                "cause": "变量未初始化或返回 None 后未做检查",
                "fix": "在使用变量前添加 None 检查",
                "source": "基于症状推断",
                "confidence": 0.7
            })
    
    # 5. 生成调试问题
    debug_questions = generate_debug_questions(
        symptom, 
        symptom_analysis["detected_categories"]
    )
    
    # 6. 生成修复建议
    fix_steps = []
    if error_matches:
        for i, match in enumerate(error_matches, 1):
            fix_steps.append({
                "step": i,
                "action": match["fix"],
                "priority": "high"
            })
    
    return {
        "symptom": symptom,
        "symptom_analysis": symptom_analysis,
        "root_cause": root_causes[0]["cause"] if root_causes else "需要更多信息定位",
        "confidence": confidence,
        "root_causes": root_causes,
        "error_pattern_matches": error_matches,
        "code_issues": code_issues,
        "debug_questions": debug_questions,
        "fix_steps": fix_steps if fix_steps else [{"step": 1, "action": "请回答上述问题以进一步定位", "priority": "medium"}],
        "prevention": "完善单元测试、集成测试，增加日志输出，使用不可变数据结构"
    }


def main():
    parser = argparse.ArgumentParser(description='调试排错辅助工具')
    parser.add_argument('--symptom', type=str, required=True, help='问题现象描述')
    parser.add_argument('--error-logs', type=str, default='', help='错误日志')
    parser.add_argument('--code-context', type=str, default='', help='相关代码片段')
    parser.add_argument('--environment', type=str, default='{}', help='环境信息JSON')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    args = parser.parse_args()
    
    try:
        env = json.loads(args.environment)
    except json.JSONDecodeError:
        env = {}
    
    result = debug(
        args.symptom,
        args.error_logs or None,
        args.code_context or None,
        env
    )
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print("调试诊断报告")
        print("=" * 60)
        
        print(f"\n问题现象: {result['symptom']}")
        print(f"诊断置信度: {result['confidence']:.0%}")
        
        if result['symptom_analysis']['detected_categories']:
            print(f"问题类型: {', '.join(result['symptom_analysis']['detected_categories'])}")
        
        if result['root_causes']:
            print("\n" + "-" * 40)
            print("根因分析:")
            for rc in result['root_causes']:
                print(f"  可能原因: {rc['cause']}")
                print(f"  建议修复: {rc['fix']}")
                print(f"  (置信度: {rc['confidence']:.0%})")
        
        if result['error_pattern_matches']:
            print("\n" + "-" * 40)
            print("错误模式匹配:")
            for match in result['error_pattern_matches']:
                print(f"  [{match['language']}] {match['root_cause']}")
                print(f"    → {match['fix']}")
        
        if result['debug_questions']:
            print("\n" + "-" * 40)
            print("请确认以下信息以进一步定位:")
            for q in result['debug_questions']:
                print(f"  ? {q}")
        
        if result['fix_steps']:
            print("\n" + "-" * 40)
            print("建议修复步骤:")
            for step in result['fix_steps']:
                print(f"  {step['step']}. [{step['priority']}] {step['action']}")
        
        print("\n" + "-" * 40)
        print(f"预防建议: {result['prevention']}")
        print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
