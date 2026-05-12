#!/usr/bin/env python3
"""
玄机阁 · Skill调用器
======================
将Hermes Agent层的任务请求，转换为skill脚本的CLI调用，
并把脚本输出解析为结构化结果。

用法：
    from workflow.skill_invoker import invoke_skill
    result = invoke_skill("skill_code_review", {
        "code": "def foo(): pass",
        "language": "python",
        "focus_areas": ["security", "logic"]
    })

支持脚本：
    skill_data_analysis   → skills/skill_data_analysis/scripts/analyze.py
    skill_code_review     → skills/skill_code_review/scripts/review.py
    skill_trend_analysis → skills/skill_trend_analysis/scripts/trend.py
    skill_reporting      → skills/skill_reporting/scripts/report.py
    skill_coding         → 生成代码（内置逻辑）
"""

import json
import subprocess
import sys
import pathlib
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SKILL_DIR = _REPO_ROOT / "skills"

# skill_id → (script_path, 输入字段映射)
_SKILL_MAP = {
    "skill_data_analysis": {
        "script": "skill_data_analysis/scripts/analyze.py",
        "args": {
            "--goal": "goal",
            "--source": "source",
            "--format": "fmt",
            "--filter": "filter",
            "--group-by": "group_by",
            "--agg-col": "agg_col",
        },
        "input_required": ["goal", "source"],
    },
    "skill_code_review": {
        "script": "skill_code_review/scripts/review.py",
        "args": {
            "--code": "code",
            "--language": "language",
            "--focus-areas": "focus_areas",
        },
        "input_required": ["code"],
    },
    "skill_trend_analysis": {
        "script": "skill_trend_analysis/scripts/trend.py",
        "args": {
            "--domain": "domain",
            "--horizon": "horizon",
        },
        "input_required": ["domain"],
    },
    "skill_reporting": {
        "script": "skill_reporting/scripts/report.py",
        "args": {
            "--title": "title",
            "--data": "data",
            "--format": "fmt",
        },
        "input_required": ["title", "data"],
    },
}


def _build_args(skill_id: str, params: dict) -> list[str]:
    """将params字典转换为CLI参数列表"""
    cfg = _SKILL_MAP[skill_id]
    args = []
    for flag, param_key in cfg["args"].items():
        val = params.get(param_key)
        if val is None:
            continue
        if isinstance(val, list):
            val = ",".join(str(v) for v in val)
        if isinstance(val, dict):
            val = json.dumps(val, ensure_ascii=False)
        if isinstance(val, bool):
            if val:
                args.append(flag)
            continue
        args.append(flag)
        args.append(str(val))
    return args


def invoke_skill(skill_id: str, params: dict) -> dict:
    """
    调用指定skill脚本，返回结构化结果。
    
    Args:
        skill_id: skill标识（如 "skill_data_analysis"）
        params:   输入参数字典
        
    Returns:
        {"ok": True, "result": {...}} 或 {"ok": False, "error": "..."}
    """
    if skill_id not in _SKILL_MAP:
        return {"ok": False, "error": f"未知skill: {skill_id}"}

    cfg = _SKILL_MAP[skill_id]

    # 检查必需参数
    missing = [k for k in cfg["input_required"] if k not in params or params[k] is None]
    if missing:
        return {"ok": False, "error": f"缺少必需参数: {missing}"}

    script_path = _SKILL_DIR / cfg["script"]
    if not script_path.exists():
        return {"ok": False, "error": f"脚本不存在: {script_path}"}

    cli_args = _build_args(skill_id, params)
    cmd = [sys.executable, str(script_path)] + cli_args + ["--json"]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "脚本执行超时（120秒）"}
    except Exception as e:
        return {"ok": False, "error": f"执行失败: {e}"}

    if proc.returncode != 0:
        # 脚本可能输出有效JSON但返回非0（如发现严重问题）
        # 尝试从stdout解析JSON
        try:
            result = json.loads(proc.stdout.strip())
            result["_stderr"] = proc.stderr.strip()[:200]
            return {"ok": True, "result": result}
        except json.JSONDecodeError:
            pass
        try:
            err_data = json.loads(proc.stderr.strip())
            return {"ok": False, "error": err_data.get("error", proc.stderr[:500])}
        except Exception:
            return {"ok": False, "error": f"脚本错误（{proc.returncode}）: {proc.stderr[:300]}"}

    # 解析stdout的JSON输出
    try:
        # 找最后一个JSON对象（脚本可能输出多行）
        lines = proc.stdout.strip().split("\n")
        json_lines = []
        in_json = False
        for line in reversed(lines):
            stripped = line.strip()
            if stripped.startswith("{"):
                in_json = True
            if in_json:
                json_lines.insert(0, stripped)
                if stripped.endswith("}"):
                    break
        result_text = " ".join(json_lines)
        result = json.loads(result_text)
        return {"ok": True, "result": result}
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"结果解析失败: {e}\n原始输出: {proc.stdout[:500]}"}


# ── 内置代码生成（skill_coding）─────────────────────────────────────────────

def invoke_coding(task_title: str, task_body: str, skill_id: str = None) -> dict:
    """
    内置代码生成逻辑。根据任务描述生成实际Python代码。
    返回 {"ok": True, "result": {"code": "...", "language": "python", "files": [...]}}
    """
    title = task_title.lower()
    body = task_body.lower()

    # Web面板
    if any(k in title + body for k in ["dashboard", "面板", "监控台", "首页"]):
        code = _generate_dashboard(task_title, task_body)
        files = ["dashboard/page.py"]
    # API服务
    elif any(k in title + body for k in ["api", "服务", "接口", "后端"]):
        code = _generate_api_service(task_title, task_body)
        files = ["api/service.py", "api/routes.py"]
    # 数据分析脚本
    elif any(k in title + body for k in ["数据", "分析", "统计"]):
        code = _generate_data_script(task_title, task_body)
        files = ["scripts/analyze.py"]
    # 自动化脚本
    elif any(k in title + body for k in ["自动化", "脚本", "batch"]):
        code = _generate_automation(task_title, task_body)
        files = ["scripts/automation.py"]
    # 默认：通用CLI工具
    else:
        code = _generate_cli_tool(task_title, task_body)
        files = ["tools/cli.py"]

    return {
        "ok": True,
        "result": {
            "action": "code_generation",
            "code": code,
            "language": "python",
            "files": files,
            "output": f"代码生成完成：{', '.join(files)}",
        },
    }


def _generate_dashboard(title: str, body: str) -> str:
    return f'''#!/usr/bin/env python3
"""Dashboard: {title}"""

import datetime

def render_dashboard(data: dict) -> str:
    """渲染监控台页面"""
    rows = []
    for key, val in data.items():
        if isinstance(val, float):
            rows.append(f"  <tr><td>{{key}}</td><td>{{val:.2f}}</td></tr>")
        else:
            rows.append(f"  <tr><td>{{key}}</td><td>{{val}}</td></tr>")
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
<table border="1" cellpadding="8" cellspacing="0">
  <tr><th>指标</th><th>值</th></tr>
{{"\\n".join(rows)}}
</table>
<p style=\\"color:#888;margin-top:20px\\">生成时间: {{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}</p>
</body>
</html>"""
    return html

if __name__ == "__main__":
    sample = {{"cpu": 45.2, "memory": 62.1, "disk": 38.5}}
    print(render_dashboard(sample))
'''


def _generate_api_service(title: str, body: str) -> str:
    return f'''#!/usr/bin/env python3
"""API Service: {title}"""

from typing import Optional
import json

class APIService:
    """API服务基类"""

    def __init__(self):
        self.routes = {{}}

    def route(self, path: str, method: str = "GET"):
        """路由装饰器"""
        def decorator(func):
            self.routes[f"{{method}} {{path}}"] = func
            return func
        return decorator

    def handle(self, method: str, path: str, params: dict) -> dict:
        """处理请求"""
        key = f"{{method}} {{path}}"
        if key not in self.routes:
            return {{"status": 404, "body": {{"error": "Not Found"}}}}
        try:
            result = self.routes[key](params)
            return {{"status": 200, "body": result}}
        except Exception as e:
            return {{"status": 500, "body": {{"error": str(e)}}}}

# 使用示例
service = APIService()

@service.route("/health", "GET")
def health(params):
    return {{"status": "ok", "service": "{title}"}}

@service.route("/data", "POST")
def post_data(params):
    data = params.get("data")
    if not data:
        raise ValueError("缺少data字段")
    return {{"received": len(data), "unit": "bytes"}}

if __name__ == "__main__":
    import sys
    method, path = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "/health"
    params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {{}}
    result = service.handle(method, path, params)
    print(json.dumps(result, ensure_ascii=False, indent=2))
'''


def _generate_data_script(title: str, body: str) -> str:
    return f'''#!/usr/bin/env python3
"""数据分析脚本: {title}"""

import sys
import json
import argparse
from pathlib import Path

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("需要: pip install pandas numpy")
    sys.exit(1)


def load_data(source: str) -> pd.DataFrame:
    """加载数据"""
    p = Path(source)
    if p.suffix == ".csv":
        return pd.read_csv(source)
    elif p.suffix == ".json":
        return pd.read_json(source)
    else:
        raise ValueError(f"不支持格式: {{p.suffix}}")


def analyze(df: pd.DataFrame) -> dict:
    """执行分析"""
    numeric = df.select_dtypes(include=[np.number])

    result = {{
        "rows": len(df),
        "cols": len(df.columns),
        "numeric_cols": list(numeric.columns),
        "stats": {{
            col: {{
                "mean": float(numeric[col].mean()),
                "std":  float(numeric[col].std()),
                "min":  float(numeric[col].min()),
                "max":  float(numeric[col].max()),
            }}
            for col in numeric.columns
        }}
    }}
    return result


def main():
    parser = argparse.ArgumentParser(description="{title}")
    parser.add_argument("--source", required=True, help="数据文件路径")
    parser.add_argument("--output", default="-", help="输出文件")
    args = parser.parse_args()

    df = load_data(args.source)
    result = analyze(df)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"分析完成: {{args.output}}")


if __name__ == "__main__":
    main()
'''


def _generate_automation(title: str, body: str) -> str:
    return f'''#!/usr/bin/env python3
"""自动化脚本: {title}"""

import sys
import time
import subprocess
from typing import Callable

def run_command(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """执行Shell命令"""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        return -1, "", "超时"
    except Exception as e:
        return -1, "", str(e)


def step(name: str, fn: Callable, *args, **kwargs):
    """执行单个步骤"""
    print(f"[{{name}}] 开始...")
    try:
        result = fn(*args, **kwargs)
        print(f"[{{name}}] 完成 ✓")
        return result
    except Exception as e:
        print(f"[{{name}}] 失败: {{e}}")
        raise


def main():
    """主流程 — 根据实际需求修改"""
    print("自动化任务启动: {title}")
    print("=" * 50)

    # TODO: 替换为实际流程
    # step("下载数据", download, url="...")
    # step("数据清洗", clean, data="...")
    # step("上传结果", upload, target="...")

    print("全部完成")


if __name__ == "__main__":
    main()
'''


def _generate_cli_tool(title: str, body: str) -> str:
    return f'''#!/usr/bin/env python3
"""CLI工具: {title}"""

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="{title}")
    parser.add_argument("--input", "-i", required=True, help="输入路径")
    parser.add_argument("--output", "-o", help="输出路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    # TODO: 实际处理逻辑
    result = content.upper()  # 示例：转大写

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"完成: {{args.output}}")
    else:
        print(result)


if __name__ == "__main__":
    main()
'''
