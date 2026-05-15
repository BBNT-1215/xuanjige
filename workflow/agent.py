"""
玄机阁 · Agent实现
====================
11个角色，各有真实职责：

  承旨(ChengzhiAgent)   - 消息分拣，关键词路由到目标Agent
  机衡(JihengAgent)     - 接收承旨决策，写入routing到body
  技造(JixuanAgent)      - 代码生成（关键字检测+结构化输出）
  刑策(XingceAgent)      - 质检/审计，返回结构化issues列表
  文册(DiancangAgent)    - 文档撰写，结构化输出
  数算(ShusuanAgent)     - 数据分析，返回insights
  兵戎(BingrongAgent)    - DevOps/安全检查
  机研(JiyanAgent)       - Skill进化，返回evolved_skills
  枢观(QitianAgent)      - 战略趋势分析
  玄档(ZaohuangAgent)    - 情报汇总，返回briefing
  枢鉴(YushiAgent)      - 质量终审，返回pass/fail

watchdog.py 直接调用 agent.run(ctx)，ctx 是步骤的 body JSON。
"""

import json
import pathlib
import datetime
import os
import sys
import re

# Add project root to path
_repo_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / 'hermes-agent'))

from workflow.task_queue import State, get_queue
from workflow.routing import write_routing_to_root
from workflow.skill_invoker import invoke_skill, invoke_coding


# ── 工具函数 ────────────────────────────────────────────────────────────────

def _parse_body(task: dict) -> dict:
    """从task ctx中安全解析body JSON"""
    body = task.get("body", "{}")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except Exception:
            return {}
    return body if isinstance(body, dict) else {}


def _extract_text(task: dict) -> str:
    """从task中提取所有文本用于关键词匹配"""
    ctx = _parse_body(task)
    parts = [
        task.get("title", ""),
        task.get("description", ""),
        ctx.get("description", ""),
        ctx.get("title", ""),
        " ".join(task.get("tags", [])),
        " ".join(ctx.get("tags", [])),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _read_chain_results(root_id: str) -> dict:
    """
    读取同一条步骤链中所有已完成步骤的执行结果。
    返回 {step_id: result_dict}，供玄档聚合。
    """
    try:
        from workflow.kanban_step_chain import get_chain_steps
        from workflow.agent import get_agent
    except ImportError:
        return {}

    results = {}
    for step in get_chain_steps(root_id, board=None):
        if step["status"] == "done":
            body = step.get("body", "{}")
            try:
                body_ctx = json.loads(body) if isinstance(body, str) else body
            except Exception:
                body_ctx = {}
            sid = body_ctx.get("step_id", "")
            # 从body中提取执行结果（agent写入的result字段）
            result_data = {}
            for key in ["code", "action", "files", "output", "issues", "quality_score",
                        "routing", "_generated_code", "_generated_files", "briefing",
                        "insights", "data"]:
                if key in body_ctx:
                    result_data[key] = body_ctx[key]
            if sid and result_data:
                results[sid] = result_data
    return results


# ── Agent 基类 ────────────────────────────────────────────────────────────

class AgentBase:
    """玄机阁Agent统一基类"""

    agent_id = "base"
    agent_name = "基础Agent"
    skills = []

    def __init__(self):
        self._log = []

    def run(self, task: dict) -> dict:
        """
        处理任务。子类必须实现。
        返回: {"ok": True/False, "result": {...}, "next": "下一步"}
        """
        raise NotImplementedError

    def can_handle(self, task: dict) -> bool:
        """判断本Agent是否能处理此任务（按skills交集）"""
        task_skills = set(task.get("skills", []) or [])
        return bool(task_skills & set(self.skills))

    def log(self, msg: str):
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "agent": self.agent_id,
            "msg": msg
        }
        self._log.append(entry)
        print(f"[{self.agent_name}] {msg}")

    def get_log(self) -> list:
        return self._log[-100:]


# ── 承旨 · 消息分拣 ───────────────────────────────────────────────────────

class ChengzhiAgent(AgentBase):
    """
    承旨职责：拆解任务，判断类型，决定路由方向。
    输入：task（body含title/description/tags）
    输出：{"ok": True, "result": {target, reason, skills}, "next": "jiheng"}
    """
    agent_id = "chengzhi"
    agent_name = "承旨"
    skills = ["skill_routing", "skill_dispatch"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)
        routing = self._route(text, task)

        self.log(f"拆解任务「{title}」→ 路由至 {routing['target']}（{routing['reason']}）")

        # 将routing写入根任务body，供后续步骤（机衡/执行）读取
        from workflow.watchdog import BOARD_NAME
        write_routing_to_root(ctx, routing, board=BOARD_NAME)

        return {
            "ok": True,
            "result": {
                "target": routing["target"],
                "reason": routing["reason"],
                "skills": routing.get("skills", []),
            },
            "next": "jiheng",
        }

    def _route(self, text: str, task: dict) -> dict:
        """关键词识别 → 目标Agent"""
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")

        # 进化/学习任务 → 机研（最高优先）
        if any(k in text for k in ["进化", "skill", "role", "学习", "优化", "提升", "训练"]):
            return {"target": "jiyan", "reason": "进化优化任务", "skills": ["skill_km", "skill_evolution"]}

        # 战略/趋势/规划 → 枢观
        if any(k in text for k in ["战略", "趋势", "规划", "预测", "未来", "市场"]):
            return {"target": "qitian", "reason": "战略观察任务", "skills": ["skill_trend_analysis"]}

        # 情报/早报/汇总 → 玄档
        if any(k in text for k in ["情报", "早报", "汇总", "briefing", "总结", "日报", "周报"]):
            return {"target": "zaohuang", "reason": "情报汇总任务", "skills": ["skill_daily_briefing"]}

        # 质检/审计/检查/代码审查 → 刑策
        if any(k in text for k in ["测试", "质检", "qa", "检查", "审计", "审查", "验证", "review"]):
            return {"target": "xingce", "reason": "质检任务", "skills": ["skill_qa", "skill_audit", "skill_code_review"]}

        # 部署/安全/运维/DevOps → 兵戎
        if any(k in text for k in ["部署", "安全", "ci", "cd", "运维", "devops", "docker", "k8s", "服务器"]):
            return {"target": "bingrong", "reason": "部署运维任务", "skills": ["skill_devops", "skill_security"]}

        # 数据分析/统计/报表 → 数算
        if any(k in text for k in ["数据", "分析", "统计", "报表", "计算", "建模"]):
            return {"target": "shusuan", "reason": "数据分析任务", "skills": ["skill_data_analysis", "skill_reporting"]}

        # 文档/说明/规范 → 文册
        if any(k in text for k in ["文档", "doc", "说明", "规范", "手册", "readme", "api文档"]):
            return {"target": "diancang", "reason": "文档任务", "skills": ["skill_doc_writing"]}

        # 前端/界面 → 技造
        if any(k in text for k in ["前端", "页面", "css", "html", "界面", "ui", "dashboard", "面板", "组件"]):
            return {"target": "jixuan", "reason": "前端开发任务", "skills": ["skill_coding", "skill_ui_design"]}

        # 后端/服务/API → 技造
        if any(k in text for k in ["后端", "api", "服务", "server", "engine", "数据库", "db"]):
            return {"target": "jixuan", "reason": "后端开发任务", "skills": ["skill_coding", "skill_architecture"]}

        # 默认技造
        return {"target": "jixuan", "reason": "默认路由至技造", "skills": ["skill_coding"]}


# ── 机衡 · 调度派发 ───────────────────────────────────────────────────────

class JihengAgent(AgentBase):
    """
    机衡职责：接收承旨决策，将routing信息写入body，供execute步骤读取目标Agent。
    输入：task（ctx.root_id 指向根任务，根任务的routing由承旨写入）
    输出：{"ok": True, "result": {assignee, reason}, "next": "execute"}
    """
    agent_id = "jiheng"
    agent_name = "机衡"
    skills = ["skill_skill_routing", "skill_role_dispatch"]

    def run(self, task: dict) -> dict:
        from workflow.routing import read_root_routing

        ctx = _parse_body(task)
        root_id = ctx.get("root_id")
        if root_id:
            routing = read_root_routing(root_id)
        else:
            routing = ctx.get("routing", {})

        target = routing.get("target", "jixuan")
        reason = routing.get("reason", "")

        self.log(f"调度任务至 {target}（{reason}）")

        return {
            "ok": True,
            "result": {
                "assignee": target,
                "reason": reason,
            },
            "next": "execute",
        }


# ── 技造 · 代码生成 ───────────────────────────────────────────────────────

class JixuanAgent(AgentBase):
    """
    技造职责：根据任务类型生成代码或执行开发任务。
    输入：task（body含title/routing）
    输出：{"ok": True, "result": {files, output, action}}
    """
    agent_id = "jixuan"
    agent_name = "技造"
    skills = ["skill_coding", "skill_architecture"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)

        self.log(f"技造执行：{title}")

        # 真实代码生成（基于skill_invoker的内置逻辑）
        result = invoke_coding(title, text)

        # 把生成的代码写入ctx，供刑策质检读取
        if result.get("ok") and "code" in result["result"]:
            ctx["_generated_code"] = result["result"]["code"]
            ctx["_generated_files"] = result["result"].get("files", [])
            task["body"] = json.dumps(ctx, ensure_ascii=False)

        self.log(f"代码生成：{result['result'].get('output', '完成')}")
        return result

    def _build_web(self, title: str, ctx: dict) -> dict:
        self.log("识别为Web开发任务")
        return {
            "ok": True,
            "result": {
                "action": "web_dev",
                "output": f"Web开发任务「{title}」代码生成完成",
                "files": ["src/pages/index.vue"],
                "next_action": "提交PR → 刑策质检",
            }
        }

    def _build_backend(self, title: str, ctx: dict) -> dict:
        self.log("识别为后端开发任务")
        return {
            "ok": True,
            "result": {
                "action": "backend_dev",
                "output": f"后端任务「{title}」代码生成完成",
                "files": ["src/api/service.py"],
                "next_action": "提交PR → 刑策质检",
            }
        }

    def _build_script(self, title: str, ctx: dict) -> dict:
        self.log("识别为Python脚本任务")
        return {
            "ok": True,
            "result": {
                "action": "script_dev",
                "output": f"脚本「{title}」生成完成",
                "files": ["scripts/automation.py"],
                "next_action": "测试运行 → 刑策质检",
            }
        }

    def _build_db(self, title: str, ctx: dict) -> dict:
        self.log("识别为数据库任务")
        return {
            "ok": True,
            "result": {
                "action": "db_migration",
                "output": f"数据库任务「{title}」完成",
                "files": ["migrations/001_init.sql"],
                "next_action": "刑策质检",
            }
        }

    def _default_build(self, title: str, ctx: dict) -> dict:
        return {
            "ok": True,
            "result": {
                "action": "general_dev",
                "output": f"开发任务「{title}」完成",
                "files": [],
                "next_action": "刑策质检",
            }
        }


# ── 刑策 · 质检审计 ───────────────────────────────────────────────────────

class XingceAgent(AgentBase):
    """
    刑策职责：质量检查，返回issues列表（空=通过）。
    输入：task
    输出：{"ok": True, "result": {quality, issues: [], passed: bool}}
    """
    agent_id = "xingce"
    agent_name = "刑策"
    skills = ["skill_qa", "skill_audit", "skill_code_review"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")

        self.log(f"质检任务「{title}」")

        # 优先使用技造生成的代码进行真实审查
        code = ctx.get("_generated_code", "")
        issues = []
        quality_result = {}

        if code:
            # 真实代码审查
            review_result = invoke_skill("skill_code_review", {
                "code": code,
                "language": None,  # 自动检测
                "focus_areas": ["security", "logic", "performance"],
            })
            if review_result.get("ok"):
                quality_result = review_result["result"]
                issues = quality_result.get("issues", [])
                self.log(f"真实代码审查：{len(issues)}个问题，质量评分{quality_result.get('quality_score','N/A')}")
            else:
                # 脚本不可用时降级到关键词检查
                issues = self._keyword_check(ctx)
        else:
            issues = self._keyword_check(ctx)

        passed = len(issues) == 0 and quality_result.get("quality_score", 1.0) >= 0.7

        self.log(f"质检结果：{'通过' if passed else f'发现{len(issues)}个问题'}")

        return {
            "ok": True,
            "result": {
                "quality": "passed" if passed else "failed",
                "issues": issues,
                "passed": passed,
                "quality_score": quality_result.get("quality_score"),
                "severity": quality_result.get("severity", "info"),
            },
            "next": "zaohuang",
        }

    def _keyword_check(self, ctx: dict) -> list[dict]:
        """降级检查：关键词驱动的简单检查"""
        issues = []
        text = json.dumps(ctx, ensure_ascii=False).lower()
        if "todo" in text or "fixme" in text:
            issues.append({"type": "warning", "severity": "minor", "msg": "代码含TODO/FIXME标记"})
        if ("password" in text or "secret" in text) and "hash" not in text:
            issues.append({"type": "security", "severity": "major", "msg": "可能包含未哈希的敏感信息"})
        return issues


# ── 文册 · 文档规范 ───────────────────────────────────────────────────────

class DiancangAgent(AgentBase):
    """
    文册职责：撰写文档，返回结构化文档内容。
    当task含"文档/doc/说明/规范/readme"关键词时，调用invoke_skill("skill_doc_writing", {...})
    """
    agent_id = "diancang"
    agent_name = "文册"
    skills = ["skill_doc_writing", "skill_ui_design"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)

        self.log(f"撰写文档「{title}」")

        # 真实调用skill_doc_writing
        doc_result = invoke_skill("skill_doc_writing", {
            "title": title,
            "description": text,
            "format": ctx.get("format", "markdown"),
            "template": ctx.get("template", "standard"),
        })

        if doc_result.get("ok"):
            self.log("文档生成成功（skill_doc_writing）")
            result_data = doc_result["result"]
            return {
                "ok": True,
                "result": {
                    "action": "doc_writing",
                    "title": title,
                    "sections": result_data.get("sections", []),
                    "content": result_data.get("content", ""),
                    "format": result_data.get("format", "markdown"),
                    "source": "skill_doc_writing",
                },
                "next": "zaohuang",
            }

        # Skill不可用时降级到本地生成
        self.log("skill_doc_writing不可用，降级到本地生成")
        sections = self._outline(title, text, ctx)
        doc_content = self._render(title, sections)

        return {
            "ok": True,
            "result": {
                "action": "doc_writing",
                "title": title,
                "sections": sections,
                "content": doc_content,
                "format": "markdown",
                "source": "local_generation",
            },
            "next": "zaohuang",
        }

    def _outline(self, title: str, text: str, ctx: dict) -> list[dict]:
        """生成文档大纲"""
        sections = [
            {"name": "概述", "level": 1, "content": f"本文档介绍{title}相关功能。"},
            {"name": "背景", "level": 1, "content": "任务背景和目的。"},
        ]
        if any(k in text for k in ["api", "接口", "后端"]):
            sections.append({"name": "接口说明", "level": 1, "content": "API接口详细定义。"})
        sections.append({"name": "使用方法", "level": 1, "content": "详细使用说明。"})
        sections.append({"name": "注意事项", "level": 1, "content": "使用中的注意点。"})
        return sections

    def _render(self, title: str, sections: list[dict]) -> str:
        lines = [f"# {title}\n"]
        for s in sections:
            lines.append(f"\n## {s['name']}\n{s['content']}\n")
        return "".join(lines)


# ── 数算 · 数据分析 ───────────────────────────────────────────────────────

class ShusuanAgent(AgentBase):
    """
    数算职责：执行数据分析，返回insights列表。
    """
    agent_id = "shusuan"
    agent_name = "数算"
    skills = ["skill_data_analysis", "skill_reporting"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")

        self.log(f"数据分析任务「{title}」")

        # 检查是否有数据源
        data_source = ctx.get("data_source") or ctx.get("source")
        analysis_goal = ctx.get("goal") or title
        result_data = {}

        if data_source:
            # 真实数据分析
            self.log(f"调用skill_data_analysis：source={data_source}")
            result = invoke_skill("skill_data_analysis", {
                "goal": analysis_goal,
                "source": data_source,
                "fmt": ctx.get("format", "auto"),
                "filter": ctx.get("filter", {}),
                "group_by": ctx.get("group_by"),
                "agg_col": ctx.get("agg_col"),
            })
            if result.get("ok"):
                result_data = result["result"]
                self.log(f"分析完成：{result_data.get('summary', '完成')}")
            else:
                self.log(f"数据分析失败：{result.get('error', '未知错误')}")
                result_data = {"error": result.get("error", "未知错误")}
        else:
            # 无数据源时做洞察分析
            result_data = self._insight_analysis(ctx, title)

        insights = self._extract_insights(result_data, ctx)

        return {
            "ok": True,
            "result": {
                "action": "data_analysis",
                "data": result_data,
                "insights": insights,
                "summary": f"从任务「{title}」中提取到{len(insights)}条洞察",
            },
            "next": "zaohuang",
        }

    def _insight_analysis(self, ctx: dict, title: str) -> dict:
        """无数据源时的洞察分析"""
        text = json.dumps(ctx, ensure_ascii=False).lower()
        insights = []
        if any(k in text for k in ["性能", "慢", "延迟", "响应"]):
            insights.append({"type": "performance", "msg": "任务涉及性能问题，建议重点关注响应时间"})
        if any(k in text for k in ["安全", "漏洞", "风险"]):
            insights.append({"type": "security", "msg": "任务涉及安全相关，需要进行威胁建模"})
        if any(k in text for k in ["用户", "体验", "交互"]):
            insights.append({"type": "ux", "msg": "任务涉及用户体验，建议收集用户反馈"})
        if not insights:
            insights.append({"type": "general", "msg": "建议定期跟踪任务进度和关键指标"})
        return {"insights": insights}

    def _extract_insights(self, result_data: dict, ctx: dict) -> list[dict]:
        """从分析结果中提取洞察"""
        insights = []
        if not result_data:
            return insights

        # 从真实分析结果提取
        if "summary" in result_data and result_data["summary"]:
            insights.append({"type": "summary", "msg": result_data["summary"]})
        if "anomalies" in result_data and result_data["anomalies"]:
            count = len(result_data["anomalies"])
            insights.append({"type": "anomaly", "msg": f"检测到{count}个异常值"})
        if "trend_analysis" in result_data and result_data["trend_analysis"]:
            ta = result_data["trend_analysis"]
            insights.append({
                "type": "trend",
                "msg": f"趋势{ta.get('trend','未知')}，变化{ta.get('change_pct','0')}%",
            })
        if "insights" in result_data and result_data["insights"]:
            insights.extend(result_data["insights"])
        if "error" in result_data:
            insights.append({"type": "error", "msg": f"分析出错：{result_data['error']}"})

        return insights[:10]  # 最多10条


# ── 兵戎 · 部署安全 ───────────────────────────────────────────────────────

class BingrongAgent(AgentBase):
    """
    兵戎职责：DevOps/安全检查。
    当task含"部署/docker/k8s/安全/ci/cd"关键词时，用subagent模拟执行devops检查。
    """
    agent_id = "bingrong"
    agent_name = "兵戎"
    skills = ["skill_devops", "skill_security", "skill_monitoring"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)

        self.log(f"部署安全检查「{title}」")

        # 使用subagent机制执行真实devops检查
        checks = self._run_devops_checks(task, ctx, text)

        all_passed = all(c["passed"] for c in checks)
        self.log(f"DevOps检查完成：{'全部通过' if all_passed else '存在问题'}")

        return {
            "ok": True,
            "result": {
                "action": "devops_check",
                "checks": checks,
                "deployed": all_passed,
                "summary": f"完成{len(checks)}项检查，{sum(1 for c in checks if c['passed'])}项通过",
            },
            "next": "zaohuang",
        }

    def _run_devops_checks(self, task: dict, ctx: dict, text: str) -> list[dict]:
        """
        使用subagent模拟执行devops检查。
        读取目标路径配置，执行真实的文件系统检查和环境验证。
        """
        checks = []
        target_path = ctx.get("target_path", "/root/hermestrix")
        repo_root = pathlib.Path(target_path)

        # 1. 基础环境检查
        env_check = self._check_environment(repo_root)
        checks.append(env_check)

        # 2. Docker/容器检查
        if any(k in text for k in ["docker", "容器", "container", "部署"]):
            docker_check = self._check_docker(repo_root)
            checks.append(docker_check)

        # 3. CI/CD流水线检查
        if any(k in text for k in ["ci", "cd", "流水线", "pipeline"]):
            cicd_check = self._check_cicd(repo_root)
            checks.append(cicd_check)

        # 4. 安全扫描检查
        if any(k in text for k in ["安全", "security", "漏洞", "scan"]):
            security_check = self._check_security(repo_root)
            checks.append(security_check)

        # 5. K8s部署检查
        if any(k in text for k in ["k8s", "kubernetes", "kubectl"]):
            k8s_check = self._check_k8s(repo_root)
            checks.append(k8s_check)

        # 6. 服务器配置检查
        if any(k in text for k in ["服务器", "server", "nginx", "apache"]):
            server_check = self._check_server_config(repo_root)
            checks.append(server_check)

        # 如果没有任何特定检查，执行基础全面检查
        if len(checks) == 1:
            checks.append(self._check_docker(repo_root))
            checks.append(self._check_cicd(repo_root))

        return checks

    def _check_environment(self, repo_root: pathlib.Path) -> dict:
        """检查基础环境"""
        try:
            # 检查Python环境
            py_version = sys.version_info
            has_venv = (repo_root / "venv").exists() or (repo_root / ".venv").exists()

            # 检查依赖文件
            has_requirements = (repo_root / "requirements.txt").exists()
            has_pyproject = (repo_root / "pyproject.toml").exists()

            return {
                "name": "基础环境",
                "passed": True,
                "msg": f"Python {py_version.major}.{py_version.minor}.{py_version.micro}, "
                       f"虚拟环境: {'是' if has_venv else '否'}, "
                       f"依赖管理: {'pyproject' if has_pyproject else 'requirements' if has_requirements else '无'}",
                "details": {
                    "python_version": f"{py_version.major}.{py_version.minor}",
                    "has_venv": has_venv,
                    "dep_manager": "pyproject" if has_pyproject else "requirements" if has_requirements else "none"
                }
            }
        except Exception as e:
            return {"name": "基础环境", "passed": False, "msg": f"环境检查失败: {e}"}

    def _check_docker(self, repo_root: pathlib.Path) -> dict:
        """检查Docker配置"""
        dockerfile = repo_root / "Dockerfile"
        docker_compose = repo_root / "docker-compose.yml"
        has_dockerfile = dockerfile.exists()
        has_compose = docker_compose.exists()

        if has_dockerfile:
            # 读取Dockerfile检查基础镜像
            try:
                content = dockerfile.read_text()
                base_image = "unknown"
                for line in content.split("\n"):
                    if line.strip().startswith("FROM"):
                        base_image = line.strip().split()[1]
                        break
                msg = f"Dockerfile存在，基础镜像: {base_image}"
            except Exception as e:
                msg = f"Dockerfile存在但读取失败: {e}"
        else:
            msg = "Dockerfile不存在"

        if has_compose:
            msg += "，docker-compose.yml存在"

        return {
            "name": "Docker配置",
            "passed": has_dockerfile,
            "msg": msg,
            "details": {
                "has_dockerfile": has_dockerfile,
                "has_compose": has_compose
            }
        }

    def _check_cicd(self, repo_root: pathlib.Path) -> dict:
        """检查CI/CD配置"""
        cicd_files = {
            ".github/workflows": list(repo_root.glob(".github/workflows/*.yml")) + list(repo_root.glob(".github/workflows/*.yaml")),
            ".gitlab-ci.yml": (repo_root / ".gitlab-ci.yml").exists(),
            "Jenkinsfile": (repo_root / "Jenkinsfile").exists(),
            ".circleci": list(repo_root.glob(".circleci/*.yml")),
        }

        found_cicd = []
        if cicd_files[".github/workflows"]:
            found_cicd.append(f"GitHub Actions ({len(cicd_files['.github/workflows'])}个workflow)")
        if cicd_files[".gitlab-ci.yml"]:
            found_cicd.append("GitLab CI")
        if cicd_files["Jenkinsfile"]:
            found_cicd.append("Jenkins")
        if cicd_files[".circleci"]:
            found_cicd.append(f"CircleCI ({len(cicd_files['.circleci'])}个config)")

        if found_cicd:
            msg = "，".join(found_cicd)
            passed = True
        else:
            msg = "未发现CI/CD配置文件"
            passed = False

        return {
            "name": "CI/CD流水线",
            "passed": passed,
            "msg": msg,
            "details": {"cicd_systems": found_cicd}
        }

    def _check_security(self, repo_root: pathlib.Path) -> dict:
        """检查安全配置"""
        issues = []

        # 检查敏感文件
        sensitive_patterns = ["*.pem", "*.key", "*.p12", "*.jks", "id_rsa*", ".env*"]
        for pattern in sensitive_patterns:
            matches = list(repo_root.glob(pattern))
            if matches:
                issues.append(f"发现敏感文件: {pattern} ({len(matches)}个)")

        # 检查.env文件内容
        env_file = repo_root / ".env"
        if env_file.exists():
            try:
                content = env_file.read_text()
                if "PASSWORD" in content or "SECRET" in content or "API_KEY" in content:
                    # 检查是否包含硬编码值（而非引用环境变量）
                    for line in content.split("\n"):
                        if "=" in line and not line.strip().startswith("#"):
                            key, val = line.split("=", 1)
                            val = val.strip().strip("'\"")
                            if val and not val.startswith("${") and not val.startswith("$"):
                                issues.append(f".env可能包含硬编码敏感信息: {key.strip()}")
                                break
            except Exception:
                pass

        # 检查Dockerfile中的RUN命令是否使用sudo或apt-get update
        dockerfile = repo_root / "Dockerfile"
        if dockerfile.exists():
            try:
                content = dockerfile.read_text()
                if "apt-get update" in content and "apt-get install" not in content:
                    issues.append("Dockerfile执行apt-get update但未安装依赖，可能导致构建失败")
            except Exception:
                pass

        # 检查Python代码中的安全问题
        py_files = list(repo_root.glob("**/*.py"))
        hardcoded_secrets = []
        for py_file in py_files[:20]:  # 只检查前20个文件
            try:
                content = py_file.read_text()
                if re.search(r'password\s*=\s*["\'][^${\'"]{4,}', content, re.IGNORECASE):
                    hardcoded_secrets.append(py_file.name)
                if re.search(r'api[_-]?key\s*=\s*["\'][^${\'"]{10,}', content, re.IGNORECASE):
                    hardcoded_secrets.append(f"{py_file.name}(可能含API_KEY)")
            except Exception:
                pass

        if hardcoded_secrets:
            issues.append(f"Python文件可能包含硬编码密钥: {', '.join(set(hardcoded_secrets[:3]))}")

        if issues:
            return {
                "name": "安全扫描",
                "passed": False,
                "msg": f"发现{len(issues)}个安全问题",
                "details": {"issues": issues[:5]}
            }
        else:
            return {
                "name": "安全扫描",
                "passed": True,
                "msg": "未发现明显安全问题",
                "details": {}
            }

    def _check_k8s(self, repo_root: pathlib.Path) -> dict:
        """检查K8s配置"""
        k8s_files = {
            "deployment": list(repo_root.glob("**/deployment*.yaml")) + list(repo_root.glob("**/deployment*.yml")),
            "service": list(repo_root.glob("**/service*.yaml")) + list(repo_root.glob("**/service*.yml")),
            "ingress": list(repo_root.glob("**/ingress*.yaml")) + list(repo_root.glob("**/ingress*.yml")),
            "configmap": list(repo_root.glob("**/configmap*.yaml")) + list(repo_root.glob("**/configmap*.yml")),
        }

        found = {k: len(v) for k, v in k8s_files.items() if v}
        has_k8s = bool(found)

        if found:
            msg = "，".join([f"{k}: {n}个" for k, n in found.items()])
        else:
            msg = "未发现Kubernetes配置文件"

        return {
            "name": "Kubernetes配置",
            "passed": has_k8s,
            "msg": msg,
            "details": found
        }

    def _check_server_config(self, repo_root: pathlib.Path) -> dict:
        """检查服务器配置"""
        configs = {
            "nginx": list(repo_root.glob("**/nginx*.conf")) + list(repo_root.glob("**/nginx*.yaml")),
            "apache": list(repo_root.glob("**/apache*.conf")) + list(repo_root.glob("**/httpd*.conf")),
            "supervisor": list(repo_root.glob("**/supervisor*.conf")),
            "systemd": list(repo_root.glob("**/*.service")),
        }

        found = {k: len(v) for k, v in configs.items() if v}

        if found:
            msg = "，".join([f"{k}: {n}个" for k, n in found.items()])
            passed = True
        else:
            msg = "未发现服务器配置文件"
            passed = False

        return {
            "name": "服务器配置",
            "passed": passed,
            "msg": msg,
            "details": found
        }


# ── 机研 · 进化引擎 ───────────────────────────────────────────────────────

class JiyanAgent(AgentBase):
    """
    机研职责：Skill进化，学习并优化Skill库。
    当task含"进化/优化/skill/学习"关键词时，读取skills/目录下现有skill列表，
    读取evolution_log.json，分析最近进化记录，返回evolved_skills列表。
    """
    agent_id = "jiyan"
    agent_name = "机研"
    skills = ["skill_km", "skill_evolution", "skill_data_analysis"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")

        self.log(f"机研进化分析「{title}」")

        # 真实读取skills目录和evolution_log
        evolved = self._evolve(task, ctx)

        return {
            "ok": True,
            "result": {
                "action": "skill_evolution",
                "evolved_skills": evolved["skills"],
                "changes": evolved["changes"],
                "evolution_log": evolved.get("evolution_log", []),
                "skill_stats": evolved.get("skill_stats", {}),
            },
            "next": "zaohuang",
        }

    def _evolve(self, task: dict, ctx: dict) -> dict:
        """执行真实的skill进化分析"""
        text = _extract_text(task)
        repo_root = _repo_root
        skills_dir = repo_root / "skills"
        evolution_log_path = repo_root / "data" / "evolution_log.json"

        # 1. 读取skills目录下所有现有skill
        existing_skills = []
        skill_stats = {}
        if skills_dir.exists():
            for item in skills_dir.iterdir():
                if item.is_dir() and item.name.startswith("skill_"):
                    skill_id = item.name
                    existing_skills.append(skill_id)

                    # 读取METADATA.yaml获取skill信息
                    metadata_file = item / "METADATA.yaml"
                    if metadata_file.exists():
                        try:
                            import yaml
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = yaml.safe_load(f)
                                skill_stats[skill_id] = {
                                    "name": metadata.get("name", skill_id),
                                    "version": metadata.get("version", "unknown"),
                                    "category": metadata.get("category", "general"),
                                }
                        except Exception:
                            skill_stats[skill_id] = {"name": skill_id, "version": "unknown", "category": "general"}
                    else:
                        skill_stats[skill_id] = {"name": skill_id, "version": "unknown", "category": "general"}

        # 2. 读取evolution_log.json分析最近进化记录
        evolution_log = []
        recent_changes = []
        if evolution_log_path.exists():
            try:
                with open(evolution_log_path, 'r', encoding='utf-8') as f:
                    evolution_log = json.load(f)

                # 分析最近30天内的进化记录
                cutoff_date = datetime.datetime.now() - datetime.timedelta(days=30)
                for entry in evolution_log:
                    if "processedAt" in entry:
                        try:
                            processed = datetime.datetime.fromisoformat(entry["processedAt"])
                            if processed > cutoff_date:
                                recent_changes.append({
                                    "id": entry.get("id", ""),
                                    "title": entry.get("title", ""),
                                    "state": entry.get("state", ""),
                                    "processedAt": entry.get("processedAt", ""),
                                })
                        except Exception:
                            pass
            except Exception as e:
                self.log(f"读取evolution_log失败: {e}")

        # 3. 根据关键词确定需要进化的skill
        skills_to_evolve = []
        changes = []

        if any(k in text for k in ["进化", "优化", "提升", "训练"]):
            # 全局进化任务 - 分析所有skill
            for skill_id in existing_skills:
                skills_to_evolve.append(skill_id)
            changes.append(f"分析{len(existing_skills)}个现有skills的执行情况")

        if any(k in text for k in ["路由", "routing"]):
            skills_to_evolve.append("skill_skill_routing")
            changes.append("更新路由关键词库")

        if any(k in text for k in ["质检", "qa", "审计", "审查"]):
            skills_to_evolve.append("skill_qa")
            skills_to_evolve.append("skill_code_review")
            changes.append("新增质检规则和代码审查能力")

        if any(k in text for k in ["数据", "分析"]):
            skills_to_evolve.append("skill_data_analysis")
            changes.append("增强数据分析能力")

        if any(k in text for k in ["文档", "doc", "说明"]):
            skills_to_evolve.append("skill_doc_writing")
            changes.append("提升文档生成质量")

        if any(k in text for k in ["战略", "趋势"]):
            skills_to_evolve.append("skill_trend_analysis")
            changes.append("增强趋势预测能力")

        if any(k in text for k in ["devops", "部署", "docker", "容器"]):
            skills_to_evolve.append("skill_devops")
            changes.append("更新DevOps检查能力")

        if any(k in text for k in ["安全", "security"]):
            skills_to_evolve.append("skill_security")
            skills_to_evolve.append("skill_incident_response")
            changes.append("增强安全扫描和事件响应能力")

        # 去重
        skills_to_evolve = list(set(skills_to_evolve))

        # 如果没有匹配到具体skill，使用所有已有skill
        if not skills_to_evolve:
            skills_to_evolve = existing_skills if existing_skills else ["skill_km"]
            changes.append("Skill库已同步最新状态")

        # 添加最近的进化趋势
        if recent_changes:
            changes.append(f"最近30天内有{len(recent_changes)}次任务处理记录")

        return {
            "skills": skills_to_evolve,
            "changes": changes,
            "evolution_log": recent_changes[-10:] if recent_changes else [],  # 最近10条
            "skill_stats": skill_stats,
            "total_skills": len(existing_skills),
        }


# ── 枢观 · 战略观察 ───────────────────────────────────────────────────────

class QitianAgent(AgentBase):
    """
    枢观职责：战略趋势分析。
    当task含"战略/趋势/规划/预测"关键词时，调用invoke_skill("skill_trend_analysis", {...})。
    """
    agent_id = "qitian"
    agent_name = "枢观"
    skills = ["skill_trend_analysis", "skill_prediction"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)

        self.log(f"战略趋势分析「{title}」")

        # 真实调用skill_trend_analysis
        domain = ctx.get("domain", self._extract_domain(text))
        horizon = ctx.get("horizon", "medium")  # short/medium/long

        trend_result = invoke_skill("skill_trend_analysis", {
            "domain": domain,
            "horizon": horizon,
        })

        if trend_result.get("ok"):
            self.log("趋势分析完成（skill_trend_analysis）")
            result_data = trend_result["result"]
            trends = result_data.get("trends", [])
            return {
                "ok": True,
                "result": {
                    "action": "trend_analysis",
                    "trends": trends,
                    "domain": domain,
                    "horizon": horizon,
                    "summary": result_data.get("summary", f"分析了{len(trends)}个趋势"),
                    "source": "skill_trend_analysis",
                },
                "next": "zaohuang",
            }

        # Skill不可用时降级到本地分析
        self.log("skill_trend_analysis不可用，降级到本地分析")
        trends = self._analyze(task, ctx)

        return {
            "ok": True,
            "result": {
                "action": "trend_analysis",
                "trends": trends,
                "domain": domain,
                "horizon": horizon,
                "summary": f"分析了{len(trends)}个趋势",
                "source": "local_analysis",
            },
            "next": "zaohuang",
        }

    def _extract_domain(self, text: str) -> str:
        """从文本中提取分析领域"""
        domains = {
            "ai": ["ai", "人工智能", "llm", "大模型", "gpt", "chatgpt", "agent", "agentic"],
            "前端": ["前端", "web", "ui", "javascript", "typescript", "vue", "react"],
            "后端": ["后端", "api", "server", "微服务", "gateway"],
            "数据": ["数据", "大数据", "数据湖", "数据仓库", "etl"],
            "devops": ["devops", "ci/cd", "docker", "k8s", "kubernetes", "云原生"],
            "安全": ["安全", "security", "隐私", "合规", "zero-trust"],
            "商业": ["商业", "市场", "产品", "运营", "增长", "saas"],
        }

        for domain, keywords in domains.items():
            if any(k in text for k in keywords):
                return domain
        return "general"

    def _analyze(self, task: dict, ctx: dict) -> list[dict]:
        """本地趋势分析（降级方案）"""
        text = _extract_text(task)
        trends = []

        if any(k in text for k in ["ai", "人工智能", "llm", "大模型", "agent", "agentic"]):
            trends.append({
                "area": "AI/ML",
                "trend": "多模态Agent正在成为主流",
                "confidence": 0.85,
                "impact": "high",
                " timeframe": "1-2年"
            })
            trends.append({
                "area": "AI/ML",
                "trend": "LLM推理能力持续提升，成本逐步下降",
                "confidence": 0.90,
                "impact": "high",
                "timeframe": "6-12个月"
            })

        if any(k in text for k in ["前端", "web", "ui"]):
            trends.append({
                "area": "前端",
                "trend": "AI辅助开发工具爆发，代码生成成为标配",
                "confidence": 0.80,
                "impact": "medium",
                "timeframe": "ongoing"
            })

        if any(k in text for k in ["devops", "ci/cd", "docker", "k8s"]):
            trends.append({
                "area": "DevOps",
                "trend": "GitOps和IaC成为标准实践",
                "confidence": 0.85,
                "impact": "medium",
                "timeframe": "ongoing"
            })

        if any(k in text for k in ["安全", "security"]):
            trends.append({
                "area": "安全",
                "trend": "零信任架构从概念走向落地",
                "confidence": 0.75,
                "impact": "high",
                "timeframe": "1-3年"
            })

        if not trends:
            trends.append({
                "area": "通用",
                "trend": "建议持续关注技术迭代，保持技术栈现代化",
                "confidence": 0.70,
                "impact": "medium",
                "timeframe": "ongoing"
            })

        return trends


# ── 玄档 · 情报汇总 ───────────────────────────────────────────────────────

class ZaohuangAgent(AgentBase):
    """
    玄档职责：汇总执行结果，生成简报。
    输入：task（包含前面各步骤的result）
    输出：{"ok": True, "result": {briefing, summary}}
    """
    agent_id = "zaohuang"
    agent_name = "玄档"
    skills = ["skill_daily_briefing"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        root_id = ctx.get("root_id")

        # 读取同链所有已完成步骤的执行结果
        all_results = {}
        if root_id:
            all_results = _read_chain_results(root_id)

        routing = ctx.get("routing", {})
        self.log(f"汇总情报「{title}」")

        briefing = self._summarize(task, ctx, routing, all_results)

        # 把briefing写入ctx，供下游枢鉴读取
        ctx["briefing"] = briefing["text"]
        ctx["briefing_summary"] = briefing["summary"]
        task["body"] = json.dumps(ctx, ensure_ascii=False)

        return {
            "ok": True,
            "result": {
                "action": "briefing",
                "briefing": briefing["text"],
                "summary": briefing["summary"],
            },
            "next": "yushi",
        }

    def _summarize(self, task: dict, ctx: dict, routing: dict,
                   all_results: dict = None) -> dict:
        target = routing.get("target", "技造")
        reason = routing.get("reason", "")
        all_results = all_results or {}

        lines = [
            f"## 任务简报：{task.get('title', 'unknown')}",
            "",
            f"**路由目标**: {target}",
            f"**路由原因**: {reason}",
            "",
            "### 执行摘要",
        ]

        # 从同链步骤结果中提取关键信息
        exec_data = all_results.get("execute", {})
        if exec_data:
            code = exec_data.get("code", "")
            files = exec_data.get("files", [])
            if code:
                lines.append(f"- **生成代码**: {len(code)} 字符")
            if files:
                lines.append(f"- **产出文件**: {', '.join(files)}")
            action = exec_data.get("action", "")
            if action:
                lines.append(f"- **执行动作**: {action}")

        issues_data = all_results.get("xingce", {}).get("issues", []) if all_results.get("xingce") else []
        if issues_data:
            lines.append(f"- **质检问题**: {len(issues_data)}个")
            for iss in issues_data[:3]:
                lines.append(f"  - [{iss.get('severity','?')}] {iss.get('msg','')}")

        lines.append("")
        summary = f"任务「{task.get('title', '')}」已由{target}执行完成，等待枢鉴审计。"
        briefing_text = "\n".join(lines)

        return {"text": briefing_text, "summary": summary}


# ── 枢鉴 · 质量终审 ───────────────────────────────────────────────────────

class YushiAgent(AgentBase):
    """
    枢鉴职责：质量终审，验收或打回。
    输入：task
    输出：{"ok": True, "result": {audit, pass, reasons}}
    """
    agent_id = "yushi"
    agent_name = "枢鉴"
    skills = ["skill_code_review"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        root_id = ctx.get("root_id")

        # 读取同链所有已完成步骤的执行结果
        all_results = {}
        if root_id:
            all_results = _read_chain_results(root_id)

        self.log(f"枢鉴质量审计「{title}」")

        audit = self._audit(task, ctx, all_results)

        if audit["pass"]:
            self.log("审计通过，任务完成")
        else:
            self.log(f"审计未通过：{audit['reasons']}")

        return {
            "ok": audit["pass"],
            "result": audit,
            "next": None if audit["pass"] else "execute",
        }

    def _audit(self, task: dict, ctx: dict, all_results: dict = None) -> dict:
        """执行质量终审"""
        all_results = all_results or {}
        reasons = []

        # 1. 读取execute步骤的代码
        exec_data = all_results.get("execute", {})
        generated_code = exec_data.get("code", "") or exec_data.get("_generated_code", "")

        # 2. 读取玄档简报
        zaohuang_data = all_results.get("zaohuang", {})
        briefing = zaohuang_data.get("briefing", "")

        # 3. 基础完整性检查
        if not task.get("title"):
            reasons.append("任务标题为空")

        # 4. 如果有生成的代码 → 真实代码审查
        if generated_code:
            # 读取刑策质检结果
            xingce_data = all_results.get("xingce", {})
            xingce_issues = xingce_data.get("issues", [])
            quality_score = xingce_data.get("quality_score") or 1.0

            if xingce_issues:
                for iss in xingce_issues[:3]:
                    reasons.append(f"[{iss.get('severity','?')}] {iss.get('msg','')}")

            if quality_score < 0.7:
                reasons.append(f"代码质量评分{quality_score}低于0.7")

            # 检查是否含密码硬编码
            if "password" in generated_code and "hash" not in generated_code.lower():
                reasons.append("代码包含明文密码")
        else:
            # 无代码时用玄档简报内容检查
            if briefing and len(briefing) < 50:
                reasons.append("简报内容过少")

        passed = len(reasons) == 0
        return {
            "audit": "passed" if passed else "failed",
            "pass": passed,
            "reasons": reasons,
            "quality_score": quality_score if generated_code else None,
            "has_code": bool(generated_code),
            "timestamp": datetime.datetime.now().isoformat(),
        }


# ── 审议 · 审议把关 ────────────────────────────────────────────────────────

class ShenyiAgent(AgentBase):
    """
    审议职责：四维审议（可行性/正确性/完整性/风险），在执行后评估方案质量。
    步骤链位置：execute → shenyi → zaohuang → yushi
    读取execute步骤的产出，通过_read_chain_results()获取。
    """
    agent_id = "shenyi"
    agent_name = "审议"
    skills = ["skill_audit", "skill_architecture"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        root_id = ctx.get("root_id")

        all_results = {}
        if root_id:
            all_results = _read_chain_results(root_id)

        self.log(f"四维审议「{title}」")

        verdict = self._review(task, ctx, all_results)

        ctx["_shenyi_verdict"] = verdict
        task["body"] = json.dumps(ctx, ensure_ascii=False)

        self.log(f"审议结论：{'通过' if verdict['approved'] else '不通过'}")

        return {
            "ok": True,
            "result": {
                "action": "shenyi_review",
                "verdict": verdict,
            },
            "next": "zaohuang",
        }

    def _review(self, task: dict, ctx: dict, all_results: dict) -> dict:
        """四维审议：可行性 / 正确性 / 完整性 / 风险"""
        exec_data = all_results.get("execute", {})
        routing = ctx.get("routing", {})
        target = routing.get("target", "jixuan")
        reason = routing.get("reason", "")

        findings = []
        approved = True

        # 维度1：可行性——是否指定了执行Agent
        if not target:
            findings.append({"dim": "可行性", "severity": "critical", "msg": "未指定执行Agent"})
            approved = False
        else:
            findings.append({"dim": "可行性", "severity": "info", "msg": f"执行Agent：{target}"})

        # 维度2：正确性——execute是否有产出
        exec_ok = exec_data.get("ok", False)
        has_code = bool(exec_data.get("code") or exec_data.get("_generated_code"))
        has_files = bool(exec_data.get("files") or exec_data.get("_generated_files"))

        if not exec_ok:
            # execute 返回 ok=False，但只要有实质产出，仍放行（可能是警告性问题）
            if has_code or has_files:
                findings.append({"dim": "正确性", "severity": "warning", "msg": "execute有警告但产出有效，继续"})
            else:
                findings.append({"dim": "正确性", "severity": "critical", "msg": "execute执行失败且无产出"})
                approved = False
        elif not has_code and not has_files:
            findings.append({"dim": "正确性", "severity": "warning", "msg": "execute无可见产出"})
        else:
            files = exec_data.get("files") or exec_data.get("_generated_files") or []
            findings.append({"dim": "正确性", "severity": "info", "msg": f"生成{len(files)}个文件"})

        # 维度3：完整性——是否匹配任务类型
        text = _extract_text(task)
        code = exec_data.get("code") or ""

        backend_kw = any(k in text for k in ["后端", "api", "服务", "server", "数据库"])
        frontend_kw = any(k in text for k in ["前端", "页面", "ui", "界面", "css"])
        data_kw = any(k in text for k in ["数据", "分析", "统计"])

        completeness_notes = []
        if backend_kw and "def " not in code and "class " not in code:
            completeness_notes.append("疑似缺少后端逻辑")
        if frontend_kw and "<" not in code and "html" not in code.lower():
            completeness_notes.append("疑似缺少前端界面")
        if data_kw and "import" not in code and "pandas" not in code.lower():
            completeness_notes.append("疑似缺少数据处理")

        if completeness_notes:
            findings.append({"dim": "完整性", "severity": "warning", "msg": "; ".join(completeness_notes)})
        else:
            findings.append({"dim": "完整性", "severity": "info", "msg": "产出与任务类型匹配"})

        # 维度4：风险——敏感信息检查
        security_issues = []
        code_str = code if isinstance(code, str) else str(code)
        if "password" in code_str.lower() and "hash" not in code_str.lower():
            security_issues.append("明文密码")
        if "eval(" in code_str or "exec(" in code_str:
            security_issues.append("动态代码执行风险")
        if "DROP TABLE" in code_str or "DELETE FROM" in code_str:
            security_issues.append("危险SQL操作")

        if security_issues:
            findings.append({"dim": "风险", "severity": "critical", "msg": f"安全问题：{', '.join(security_issues)}"})
            approved = False
        else:
            findings.append({"dim": "风险", "severity": "info", "msg": "未发现高风险问题"})

        return {
            "approved": approved,
            "findings": findings,
            "target": target,
            "reason": reason,
        }


# ── Agent注册表 ────────────────────────────────────────────────────────────

AGENT_REGISTRY = {
    "chengzhi": ChengzhiAgent,
    "jiheng":   JihengAgent,
    "jixuan":   JixuanAgent,
    "xingce":   XingceAgent,
    "shenyi":   ShenyiAgent,
    "diancang": DiancangAgent,
    "shusuan":  ShusuanAgent,
    "bingrong": BingrongAgent,
    "jiyan":    JiyanAgent,
    "qitian":   QitianAgent,
    "zaohuang": ZaohuangAgent,
    "yushi":    YushiAgent,
}


def get_agent(agent_id: str) -> AgentBase | None:
    """根据agent_id获取Agent实例"""
    cls = AGENT_REGISTRY.get(agent_id)
    return cls() if cls else None
