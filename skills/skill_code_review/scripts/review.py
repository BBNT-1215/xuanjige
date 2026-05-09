#!/usr/bin/env python3
"""
skill_code_review - 代码审查脚本
提供系统性代码质量审查服务
"""

import argparse
import json
import sys
import re
from typing import List, Dict, Any


def analyze_security(code: str, language: str) -> List[Dict[str, Any]]:
    """安全审查：注入、认证、敏感信息"""
    issues = []
    
    # SQL注入检测
    sql_patterns = [
        (r'execute\s*\(\s*["\'].*%s', 'SQL拼接风险：使用格式化字符串拼接SQL'),
        (r'["\'].*SELECT.*{', 'SQL注入风险：字符串拼接查询'),
        (r'cursor\.execute\s*\([^,]+\+', 'SQL注入风险：使用+号拼接参数'),
    ]
    for pattern, desc in sql_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append({
                "category": "security",
                "severity": "critical",
                "title": "SQL注入风险",
                "description": desc,
                "suggestion": "使用参数化查询替代字符串拼接"
            })
    
    # 命令注入检测
    cmd_patterns = [
        (r'os\.system\s*\(', '命令注入风险：os.system执行shell命令'),
        (r'subprocess\.\w+\s*\([^)]*\+', '命令注入风险：subprocess使用+拼接命令'),
        (r'eval\s*\(', '代码注入风险：eval执行动态代码'),
        (r'exec\s*\(', '代码注入风险：exec执行动态代码'),
    ]
    for pattern, desc in cmd_patterns:
        if re.search(pattern, code):
            issues.append({
                "category": "security",
                "severity": "critical",
                "title": "命令/代码注入",
                "description": desc,
                "suggestion": "避免使用eval/exec，或使用安全的替代方案"
            })
    
    # 敏感信息检测
    secret_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', '硬编码密码：密码不应硬编码在代码中'),
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', '硬编码API Key：敏感信息应使用环境变量'),
        (r'secret\s*=\s*["\'][^"\']+["\']', '硬编码Secret：敏感信息应外部化'),
        (r'token\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', '可能的Token硬编码'),
    ]
    for pattern, desc in secret_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append({
                "category": "security",
                "severity": "major",
                "title": "敏感信息暴露",
                "description": desc,
                "suggestion": "使用环境变量或密钥管理服务存储敏感信息"
            })
    
    return issues


def analyze_logic(code: str, language: str) -> List[Dict[str, Any]]:
    """逻辑审查：控制流、数据流、边界条件"""
    issues = []
    
    lines = code.split('\n')
    
    # 检测空except块
    if re.search(r'except[^:]*:\s*(?:#.*)?\s*$', code, re.MULTILINE):
        issues.append({
            "category": "logic",
            "severity": "major",
            "title": "空except块",
            "description": "except块为空会静默吞掉异常",
            "suggestion": "至少记录日志或重新抛出异常"
        })
    
    # 检测 TODO/FIXME/HACK
    todo_matches = re.findall(r'(#\s*(TODO|FIXME|HACK|XXX):?\s*)(.*)', code, re.IGNORECASE)
    for match in todo_matches:
        issues.append({
            "category": "maintainability",
            "severity": "minor",
            "title": f"代码标记: {match[1].strip()}",
            "description": match[2].strip() if match[2].strip() else "代码中留有未完成标记",
            "suggestion": "尽快处理或创建相关issue"
        })
    
    # 检测可能的无限循环（while True without break）
    if re.search(r'while\s+True\s*:', code):
        if not re.search(r'break', code):
            issues.append({
                "category": "logic",
                "severity": "major",
                "title": "可能的无限循环",
                "description": "while True循环内没有break语句",
                "suggestion": "确认是否有退出条件"
            })
    
    return issues


def analyze_performance(code: str, language: str) -> List[Dict[str, Any]]:
    """性能审查：复杂度、资源、并发"""
    issues = []
    
    # 检测循环内字符串拼接（Python）
    if 'for ' in code and '+=' in code and language == 'python':
        if re.search(r'for\s+\w+\s+in\s+.*:\s*\n\s+\w+\s*\+=', code):
            issues.append({
                "category": "performance",
                "severity": "minor",
                "title": "循环内字符串拼接",
                "description": "在循环内使用+=拼接字符串效率低下",
                "suggestion": "使用列表join或StringBuilder替代"
            })
    
    # 检测未关闭的资源
    if language == 'python':
        if 'open(' in code and 'with' not in code:
            issues.append({
                "category": "resource",
                "severity": "minor",
                "title": "文件未使用with语句",
                "description": "文件操作未使用with语句，可能导致资源泄漏",
                "suggestion": "使用with语句确保资源正确关闭"
            })
    
    return issues


def calculate_quality_score(issues: List[Dict[str, Any]]) -> float:
    """根据问题计算质量分数"""
    if not issues:
        return 1.0
    
    weights = {"critical": 0.3, "major": 0.15, "minor": 0.05, "info": 0.01}
    penalty = sum(weights.get(i["severity"], 0.1) for i in issues)
    
    return max(0.0, min(1.0, 1.0 - penalty))


def review_code(code: str, language: str = None, focus_areas: List[str] = None) -> Dict[str, Any]:
    """主审查函数"""
    
    # 自动检测语言
    if not language:
        if 'def ' in code or 'import ' in code or 'from ' in code:
            language = 'python'
        elif 'function' in code or 'const ' in code or 'let ' in code:
            language = 'javascript'
        elif 'func ' in code and 'package ' in code:
            language = 'go'
        elif 'public class' in code or 'private void' in code:
            language = 'java'
        else:
            language = 'unknown'
    
    all_issues = []
    
    areas = focus_areas or ['logic', 'security', 'performance']
    
    if 'security' in areas:
        all_issues.extend(analyze_security(code, language))
    if 'logic' in areas:
        all_issues.extend(analyze_logic(code, language))
    if 'performance' in areas:
        all_issues.extend(analyze_performance(code, language))
    
    quality_score = calculate_quality_score(all_issues)
    
    # 确定最高严重程度
    severity_order = ['critical', 'major', 'minor', 'info']
    max_severity = 'info'
    for issue in all_issues:
        if severity_order.index(issue['severity']) < severity_order.index(max_severity):
            max_severity = issue['severity']
    
    return {
        "issues": all_issues,
        "severity": max_severity if all_issues else "info",
        "quality_score": round(quality_score, 2),
        "language_detected": language,
        "summary": f"发现{len(all_issues)}个问题" if all_issues else "未发现明显问题"
    }


def main():
    parser = argparse.ArgumentParser(description='代码审查工具')
    parser.add_argument('--code', type=str, required=True, help='待审查的代码')
    parser.add_argument('--language', type=str, default=None, help='编程语言')
    parser.add_argument('--focus-areas', type=str, default='logic,security,performance', 
                        help='重点审查领域，逗号分隔')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    args = parser.parse_args()
    
    focus_areas = [x.strip() for x in args.focus_areas.split(',')]
    result = review_code(args.code, args.language, focus_areas)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("=" * 50)
        print("代码审查报告")
        print("=" * 50)
        print(f"检测语言: {result['language_detected']}")
        print(f"质量评分: {result['quality_score']} ({result['severity']})")
        print(f"发现问题: {len(result['issues'])}个")
        print("-" * 50)
        
        if result['issues']:
            for i, issue in enumerate(result['issues'], 1):
                print(f"\n[{i}] [{issue['severity'].upper()}] {issue['title']}")
                print(f"    类别: {issue['category']}")
                print(f"    描述: {issue['description']}")
                print(f"    建议: {issue['suggestion']}")
        else:
            print("\n✓ 代码未发现明显问题")
        
        print("\n" + "=" * 50)
    
    return 0 if result['quality_score'] >= 0.7 else 1


if __name__ == '__main__':
    sys.exit(main())
