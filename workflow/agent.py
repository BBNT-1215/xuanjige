"""
玄机阁 · Agent基类
====================
所有Agent的抽象基类，定义统一接口。
每个Agent需要实现 run(task) 方法。
"""

import json
import pathlib
import datetime
import os
import sys

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from workflow.task_queue import State, get_queue


class AgentBase:
    """玄机阁Agent统一基类"""

    # 子类覆盖
    agent_id = "base"
    agent_name = "基础Agent"
    skills = []

    def __init__(self):
        self.queue = get_queue()
        self._log = []

    # ── 核心接口 ──────────────────────────────────

    def run(self, task: dict) -> dict:
        """
        处理任务。子类必须实现。
        返回: {"ok": True/False, "result": ..., "next": "下一步"}
        """
        raise NotImplementedError

    def can_handle(self, task: dict) -> bool:
        """
        判断本Agent是否能处理此任务。
        默认按skills匹配，子类可重写。
        """
        task_skills = set(task.get('skills', []) or [])
        return bool(task_skills & set(self.skills))

    # ── 生命周期 ──────────────────────────────────

    def execute(self, task_id: str) -> dict:
        """
        从队列取出任务，执行，然后流转状态。
        """
        task = self.queue.get(task_id)
        if not task:
            return {"ok": False, "error": "任务不存在"}

        # 标记开始执行
        self.queue.start(task_id, self.agent_id)
        self.log(f"开始执行: {task['title']}")

        try:
            result = self.run(task)
            if result.get("ok", False):
                self.queue.review(task_id, self.agent_id)
                self.log(f"完成执行，等待审核: {task['title']}")
            else:
                self.queue.block(task_id, self.agent_id,
                                 reason=result.get("error", "未知错误"))
                self.log(f"执行失败: {result.get('error')}")
            return result
        except Exception as e:
            self.queue.block(task_id, self.agent_id, reason=str(e))
            self.log(f"异常: {e}")
            return {"ok": False, "error": str(e)}

    # ── 日志 ──────────────────────────────────

    def log(self, msg: str):
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "agent": self.agent_id,
            "msg": msg
        }
        self._log.append(entry)
        print(f"[{self.agent_name}] {msg}")

    def get_log(self) -> list:
        return self._log


class ChengzhiAgent(AgentBase):
    """承旨·消息分拣"""
    agent_id = "chengzhi"
    agent_name = "承旨"
    skills = ["skill_routing", "skill_dispatch"]

    def can_handle(self, task: dict) -> bool:
        # 承旨处理所有PENDING任务
        return task.get('state') == State.PENDING

    def run(self, task: dict) -> dict:
        """
        承旨职责：拆解任务，判断类型，决定路由方向。
        返回目标Agent。
        """
        title = task.get('title', '')
        desc = task.get('description', '')
        tags = task.get('tags', [])

        # 关键词识别 → 目标Agent
        routing = self._route(title, desc, tags)

        self.log(f"拆解任务「{title}」→ 路由至 {routing['target']}（{routing['reason']}）")

        return {
            "ok": True,
            "result": {
                "target": routing['target'],
                "reason": routing['reason'],
                "skills_matched": routing.get('skills', []),
            },
            "next": "jiheng"  # 交给机衡
        }

    def _route(self, title: str, desc: str, tags: list) -> dict:
        text = (title + " " + desc + " " + " ".join(tags)).lower()

        if any(k in text for k in ['前端', '页面', 'css', 'html', '界面', 'ui', 'dashboard', '面板']):
            return {"target": "jizao", "reason": "前端开发任务", "skills": ["skill_coding", "skill_ui_design"]}
        if any(k in text for k in ['后端', 'api', '服务', 'server', 'engine']):
            return {"target": "jizao", "reason": "后端开发任务", "skills": ["skill_coding", "skill_architecture"]}
        if any(k in text for k in ['测试', '质检', 'qa', '检查', '审计']):
            return {"target": "xingce", "reason": "质检任务", "skills": ["skill_qa", "skill_audit"]}
        if any(k in text for k in ['文档', 'doc', '说明', '规范']):
            return {"target": "diancang", "reason": "文档任务", "skills": ["skill_doc_writing"]}
        if any(k in text for k in ['数据', '分析', '统计', '报表']):
            return {"target": "shusuan", "reason": "数据分析任务", "skills": ["skill_data_analysis"]}
        if any(k in text for k in ['部署', '安全', 'ci', 'cd', '运维', 'devops']):
            return {"target": "bingrong", "reason": "部署运维任务", "skills": ["skill_devops"]}
        if any(k in text for k in ['进化', 'skill', 'role', '学习', '优化']):
            return {"target": "jiyan", "reason": "进化优化任务", "skills": ["skill_km", "skill_evolution"]}
        if any(k in text for k in ['战略', '趋势', '规划', '预测']):
            return {"target": "qitian", "reason": "战略观察任务", "skills": ["skill_trend_analysis"]}
        if any(k in text for k in ['情报', '早报', '汇总', 'briefing']):
            return {"target": "zaohuang", "reason": "情报汇总任务", "skills": ["skill_daily_briefing"]}

        # 默认技造
        return {"target": "jizao", "reason": "默认路由至技造", "skills": ["skill_coding"]}


class JihengAgent(AgentBase):
    """机衡·调度派发"""
    agent_id = "jiheng"
    agent_name = "机衡"
    skills = ["skill_skill_routing", "skill_role_dispatch"]

    def run(self, task: dict) -> dict:
        """
        机衡职责：接收承旨决策，分配给具体执行Agent。
        """
        routing = task.get('description', {})

        # routing info is embedded by chengzhi
        target = routing.get('target', 'jizao') if isinstance(routing, dict) else 'jizao'

        self.log(f"调度任务至 {target}")

        return {
            "ok": True,
            "result": {"assignee": target},
            "next": target  # 直接派发给目标Agent
        }


class JizaoAgent(AgentBase):
    """技造·开发工程"""
    agent_id = "jizao"
    agent_name = "技造"
    skills = ["skill_coding", "skill_architecture"]

    def run(self, task: dict) -> dict:
        title = task.get('title', '')

        # 模拟开发过程
        if 'html' in title.lower() or 'css' in title.lower() or '页面' in title or '面板' in title:
            return self._build_web(task)
        return self._default_build(task)

    def _build_web(self, task: dict) -> dict:
        self.log("识别为Web开发任务")
        # 实际生产中这里会调用真正的代码生成
        return {
            "ok": True,
            "result": {
                "output": "已生成Web页面",
                "files": ["dashboard/pixel/index.html"],
            }
        }

    def _default_build(self, task: dict) -> dict:
        return {
            "ok": True,
            "result": {"output": "代码生成完成"}
        }


class XingceAgent(AgentBase):
    """刑策·质检审计"""
    agent_id = "xingce"
    agent_name = "刑策"
    skills = ["skill_qa", "skill_audit", "skill_code_review"]

    def run(self, task: dict) -> dict:
        self.log("执行质量检查...")
        return {
            "ok": True,
            "result": {"quality": "passed", "issues": []}
        }


class DiancangAgent(AgentBase):
    """文册·文档规范"""
    agent_id = "diancang"
    agent_name = "文册"
    skills = ["skill_doc_writing", "skill_ui_design"]

    def run(self, task: dict) -> dict:
        self.log("撰写文档...")
        return {"ok": True, "result": {"docs": "文档已生成"}}


class ShusuanAgent(AgentBase):
    """数算·数据分析"""
    agent_id = "shusuan"
    agent_name = "数算"
    skills = ["skill_data_analysis", "skill_reporting"]

    def run(self, task: dict) -> dict:
        self.log("执行数据分析...")
        return {"ok": True, "result": {"insights": []}}


class BingrongAgent(AgentBase):
    """兵戎·部署安全"""
    agent_id = "bingrong"
    agent_name = "兵戎"
    skills = ["skill_devops", "skill_security", "skill_monitoring"]

    def run(self, task: dict) -> dict:
        self.log("执行部署和安全检查...")
        return {"ok": True, "result": {"deployed": True}}


class JiyanAgent(AgentBase):
    """机研·进化引擎"""
    agent_id = "jiyan"
    agent_name = "机研"
    skills = ["skill_km", "skill_evolution", "skill_data_analysis"]

    def run(self, task: dict) -> dict:
        self.log("执行进化分析...")
        return {"ok": True, "result": {"evolved": True}}


class QitianAgent(AgentBase):
    """枢观·战略观察"""
    agent_id = "qitian"
    agent_name = "枢观"
    skills = ["skill_trend_analysis", "skill_prediction"]

    def run(self, task: dict) -> dict:
        self.log("执行战略趋势分析...")
        return {"ok": True, "result": {"trends": []}}


class ZaohuangAgent(AgentBase):
    """早朝·情报枢纽"""
    agent_id = "zaohuang"
    agent_name = "早朝"
    skills = ["skill_daily_briefing"]

    def run(self, task: dict) -> dict:
        self.log("汇总情报...")
        return {"ok": True, "result": {"briefing": "早报已生成"}}


class YushiAgent(AgentBase):
    """御史·质量审计"""
    agent_id = "yushi"
    agent_name = "御史"
    skills = ["skill_code_review"]

    def run(self, task: dict) -> dict:
        self.log("执行最终质量审计...")
        return {"ok": True, "result": {"audit": "通过"}}


# ── Agent注册表 ──────────────────────────────────────────

AGENT_REGISTRY = {
    "chengzhi": ChengzhiAgent,
    "jiheng":   JihengAgent,
    "jizao":    JizaoAgent,
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
    cls = AGENT_REGISTRY.get(agent_id)
    return cls() if cls else None
