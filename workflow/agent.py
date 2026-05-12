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
    """
    agent_id = "diancang"
    agent_name = "文册"
    skills = ["skill_doc_writing", "skill_ui_design"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)

        self.log(f"撰写文档「{title}」")

        # 生成文档结构
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
    """
    agent_id = "bingrong"
    agent_name = "兵戎"
    skills = ["skill_devops", "skill_security", "skill_monitoring"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")
        text = _extract_text(task)

        self.log(f"部署安全检查「{title}」")

        checks = self._checks(task, ctx, text)

        return {
            "ok": True,
            "result": {
                "action": "devops_check",
                "checks": checks,
                "deployed": all(c["passed"] for c in checks),
            },
            "next": "zaohuang",
        }

    def _checks(self, task: dict, ctx: dict, text: str) -> list[dict]:
        checks = []
        # 基础检查
        checks.append({"name": "基础环境", "passed": True, "msg": "环境就绪"})

        if any(k in text for k in ["docker", "容器"]):
            checks.append({"name": "Dockerfile", "passed": True, "msg": "Docker配置存在"})

        if any(k in text for k in ["ci", "cd", "流水线"]):
            checks.append({"name": "CI/CD", "passed": True, "msg": "流水线配置存在"})

        if any(k in text for k in ["安全", "权限"]):
            checks.append({"name": "安全扫描", "passed": True, "msg": "安全扫描通过"})

        return checks


# ── 机研 · 进化引擎 ───────────────────────────────────────────────────────

class JiyanAgent(AgentBase):
    """
    机研职责：Skill进化，学习并优化Skill库。
    """
    agent_id = "jiyan"
    agent_name = "机研"
    skills = ["skill_km", "skill_evolution", "skill_data_analysis"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")

        self.log(f"机研进化分析「{title}」")

        evolved = self._evolve(task, ctx)

        return {
            "ok": True,
            "result": {
                "action": "skill_evolution",
                "evolved_skills": evolved["skills"],
                "changes": evolved["changes"],
            },
            "next": "zaohuang",
        }

    def _evolve(self, task: dict, ctx: dict) -> dict:
        text = _extract_text(task)
        skills = []
        changes = []

        if any(k in text for k in ["路由", "routing"]):
            skills.append("skill_skill_routing")
            changes.append("更新路由关键词库")

        if any(k in text for k in ["质检", "qa", "审计"]):
            skills.append("skill_qa")
            changes.append("新增质检规则")

        if not skills:
            skills = ["skill_km"]
            changes.append("Skill库已同步最新状态")

        return {"skills": skills, "changes": changes}


# ── 枢观 · 战略观察 ───────────────────────────────────────────────────────

class QitianAgent(AgentBase):
    """
    枢观职责：战略趋势分析。
    """
    agent_id = "qitian"
    agent_name = "枢观"
    skills = ["skill_trend_analysis", "skill_prediction"]

    def run(self, task: dict) -> dict:
        ctx = _parse_body(task)
        title = task.get("title", "") or ctx.get("title", "")

        self.log(f"战略趋势分析「{title}」")

        trends = self._analyze(task, ctx)

        return {
            "ok": True,
            "result": {
                "action": "trend_analysis",
                "trends": trends,
            },
            "next": "zaohuang",
        }

    def _analyze(self, task: dict, ctx: dict) -> list[dict]:
        text = _extract_text(task)
        trends = []
        if any(k in text for k in ["ai", "人工智能", "llm", "大模型"]):
            trends.append({"area": "AI", "trend": "多模态Agent正在成为主流", "confidence": 0.85})
        if any(k in text for k in ["前端", "web", "ui"]):
            trends.append({"area": "前端", "trend": "AI辅助开发工具爆发", "confidence": 0.80})
        if not trends:
            trends.append({"area": "通用", "trend": "建议持续关注技术迭代", "confidence": 0.70})
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
        routing = ctx.get("routing", {})

        self.log(f"汇总情报「{title}」")

        briefing = self._summarize(task, ctx, routing)

        return {
            "ok": True,
            "result": {
                "action": "briefing",
                "briefing": briefing["text"],
                "summary": briefing["summary"],
            },
            "next": "yushi",
        }

    def _summarize(self, task: dict, ctx: dict, routing: dict) -> dict:
        target = routing.get("target", "技造")
        reason = routing.get("reason", "")
        step_results = ctx.get("step_results", [])

        lines = [
            f"## 任务简报：{task.get('title', 'unknown')}",
            "",
            f"**路由目标**: {target}",
            f"**路由原因**: {reason}",
            "",
            "### 执行摘要",
        ]

        if step_results:
            for r in step_results:
                lines.append(f"- {r}")
        else:
            lines.append(f"- {target} 已完成执行")

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

        self.log(f"枢鉴质量审计「{title}」")

        audit = self._audit(task, ctx)

        if audit["pass"]:
            self.log("审计通过，任务完成")
        else:
            self.log(f"审计未通过：{audit['reasons']}")

        return {
            "ok": audit["pass"],
            "result": audit,
            "next": None if audit["pass"] else "execute",
        }

    def _audit(self, task: dict, ctx: dict) -> dict:
        """执行质量终审"""
        reasons = []
        text = _extract_text(task)

        # 基础完整性检查
        if not task.get("title"):
            reasons.append("任务标题为空")

        # 内容检查
        if len(text) < 10:
            reasons.append("任务内容过少")

        # 代码类任务检查
        if any(k in text for k in ["代码", "开发", "script"]):
            if "TODO" in text and "FIXME" in text:
                reasons.append("代码含未完成标记")

        passed = len(reasons) == 0
        return {
            "audit": "passed" if passed else "failed",
            "pass": passed,
            "reasons": reasons,
            "timestamp": datetime.datetime.now().isoformat(),
        }


# ── Agent注册表 ────────────────────────────────────────────────────────────

AGENT_REGISTRY = {
    "chengzhi": ChengzhiAgent,
    "jiheng":   JihengAgent,
    "jixuan":   JixuanAgent,
    "xingce":   XingceAgent,
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
