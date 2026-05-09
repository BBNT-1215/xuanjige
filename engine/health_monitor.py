"""
Hermestrix Engine - Health Monitor

系统健康度监控，主动发现异常而非被动响应
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.memory_manager import MemoryManager

# ============================================================
# 配置
# ============================================================

HERMESTRIX_HOME = Path(__file__).parent.parent

HEALTH_REPORT_PATH = HERMESTRIX_HOME / "three_libs" / "system_health.json"


# ============================================================
# 数据结构
# ============================================================

@dataclass
class Alert:
    level: str  # warn / critical
    metric: str
    message: str
    value: Any = None
    threshold: Any = None


@dataclass
class HealthReport:
    timestamp: str
    overall: str  # ok / warn / critical
    checks: Dict[str, Dict[str, Any]]
    alerts: List[Alert]
    recommendations: List[str] = field(default_factory=list)


# ============================================================
# HealthMonitor
# ============================================================

class HealthMonitor:
    """
    系统健康度监控

    主动检测而非被动响应
    定期检查并在异常时告警
    """

    THRESHOLDS = {
        "skill_avg_effectiveness": {
            "warn": 0.6,
            "critical": 0.4,
            "description": "Skill平均评分"
        },
        "role_avg_quality": {
            "warn": 0.7,
            "critical": 0.5,
            "description": "Role平均质量"
        },
        "cold_storage_ratio": {
            "warn": 0.7,
            "critical": 0.9,
            "description": "冷存储占比"
        },
        "evolution_stagnation_days": {
            "warn": 7,
            "critical": 14,
            "description": "进化停滞天数"
        },
        "pending_verifications": {
            "warn": 10,
            "critical": 20,
            "description": "待验证进化数量"
        },
        "skill_conflict_rate": {
            "warn": 0.3,
            "critical": 0.5,
            "description": "Skill冲突率"
        }
    }

    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()

    def check_all(self) -> HealthReport:
        """
        全面检查，返回健康报告
        """
        report = HealthReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall="ok",
            checks={},
            alerts=[]
        )

        for metric, config in self.THRESHOLDS.items():
            value = self._get_metric(metric)
            status = self._evaluate(value, config)

            report.checks[metric] = {
                "value": value,
                "status": status,
                "threshold_warn": config["warn"],
                "threshold_critical": config["critical"],
                "description": config["description"]
            }

            if status == "critical":
                report.overall = "critical"
                report.alerts.append(Alert(
                    level="critical",
                    metric=metric,
                    message=self._format_alert(metric, value, "critical", config),
                    value=value,
                    threshold=config
                ))
            elif status == "warn":
                if report.overall != "critical":
                    report.overall = "warn"
                report.alerts.append(Alert(
                    level="warn",
                    metric=metric,
                    message=self._format_alert(metric, value, "warn", config),
                    value=value,
                    threshold=config
                ))

        # 生成建议
        report.recommendations = self._generate_recommendations(report)

        # 保存报告
        self._save_report(report)

        return report

    def _get_metric(self, metric: str) -> float:
        """获取指定指标的值"""
        if metric == "skill_avg_effectiveness":
            summary = self.memory.get_system_health_summary()
            return summary.get("skill_avg_effectiveness", 0.5)

        elif metric == "role_avg_quality":
            summary = self.memory.get_system_health_summary()
            return summary.get("role_avg_quality", 0.5)

        elif metric == "cold_storage_ratio":
            summary = self.memory.get_system_health_summary()
            total = summary.get("total_memory_records", 0)
            if total == 0:
                return 0.0
            cold = len(list((self.memory.home / "three_libs" / "memory" / "cold").glob("*.json")))
            return round(cold / total, 3)

        elif metric == "evolution_stagnation_days":
            # 检查最近一次进化距今多少天
            return self._get_evolution_stagnation_days()

        elif metric == "pending_verifications":
            return self._get_pending_verification_count()

        elif metric == "skill_conflict_rate":
            return self._get_skill_conflict_rate()

        return 0.0

    def _get_evolution_stagnation_days(self) -> float:
        """获取进化停滞天数"""
        from engine.memory_manager import SKILL_STATS_DIR
        if not SKILL_STATS_DIR.exists():
            return 0.0

        latest_update = None
        for stats_path in SKILL_STATS_DIR.glob("*/stats.json"):
            try:
                import json
                with open(stats_path, encoding="utf-8") as f:
                    data = json.load(f)
                    updated = data.get("updated_at", "")
                    if updated:
                        dt = datetime.fromisoformat(updated)
                        if latest_update is None or dt > latest_update:
                            latest_update = dt
            except:
                continue

        if latest_update is None:
            return 0.0

        return (datetime.now(timezone.utc) - latest_update).days

    def _get_pending_verification_count(self) -> int:
        """获取待验证进化数量"""
        from engine.memory_manager import SKILL_STATS_DIR
        if not SKILL_STATS_DIR.exists():
            return 0

        count = 0
        for stats_path in SKILL_STATS_DIR.glob("*/stats.json"):
            try:
                import json
                with open(stats_path, encoding="utf-8") as f:
                    data = json.load(f)
                    v = data.get("verification", {})
                    if v.get("status") == "verifying":
                        count += 1
            except:
                continue
        return count

    def _get_skill_conflict_rate(self) -> float:
        """获取Skill冲突率"""
        from engine.memory_manager import SKILL_STATS_DIR
        if not SKILL_STATS_DIR.exists():
            return 0.0

        conflict_resolver = __import__(
            "engine.conflict_resolver",
            fromlist=["ConflictResolver"]
        ).ConflictResolver(self.memory)

        total_skills = 0
        conflicted_skills = 0

        for stats_path in SKILL_STATS_DIR.glob("*/stats.json"):
            try:
                skill_id = stats_path.parent.name
                total_skills += 1

                conflict = conflict_resolver.detect_conflicts(skill_id)
                if conflict:
                    conflicted_skills += 1
            except:
                continue

        if total_skills == 0:
            return 0.0
        return round(conflicted_skills / total_skills, 3)

    @staticmethod
    def _evaluate(value: float, config: Dict[str, Any]) -> str:
        """评估指标状态"""
        warn = config["warn"]
        critical = config["critical"]

        # 判断方向：有些指标是越高越差（cold_storage_ratio等）
        # 有些是越低越差（skill_avg_effectiveness等）
        # 通过比较warn和critical的大小判断方向
        # 方向推断：critical > warn → 越高越差；critical < warn → 越低越差
        if critical > warn:
            # 越高越差
            if value >= critical:
                return "critical"
            elif value >= warn:
                return "warn"
        else:
            # 越低越差（默认）
            if value <= critical:
                return "critical"
            elif value <= warn:
                return "warn"
        return "ok"

    @staticmethod
    def _format_alert(metric: str, value: float, level: str, config: Dict[str, Any]) -> str:
        """格式化告警消息"""
        messages = {
            "skill_avg_effectiveness": f"Skill平均评分 {value:.2f} {'过低' if level == 'critical' else '偏低'}（warn<={config['warn']}）",
            "role_avg_quality": f"Role平均质量 {value:.2f} {'过低' if level == 'critical' else '偏低'}（warn<={config['warn']}）",
            "cold_storage_ratio": f"冷存储占比 {value:.2%} {'过高' if level == 'critical' else '偏高'}，考虑清理",
            "evolution_stagnation_days": f"进化已停滞 {value:.0f} 天，{'严重' if level == 'critical' else '建议'}检查",
            "pending_verifications": f"待验证进化 {value:.0f} 个，{'积压严重' if level == 'critical' else '建议处理'}",
            "skill_conflict_rate": f"Skill冲突率 {value:.2%} {'过高' if level == 'critical' else '偏高'}，需解决矛盾"
        }
        return messages.get(metric, f"{metric}={value:.2f} {level}")

    def _generate_recommendations(self, report: HealthReport) -> List[str]:
        """生成健康建议"""
        recs = []

        if report.overall == "critical":
            recs.append("系统处于CRITICAL状态，建议立即处理")

        for alert in report.alerts:
            if alert.metric == "skill_avg_effectiveness":
                recs.append("建议检查最近失败的Task，优化相关Skill的使用场景")
            elif alert.metric == "role_avg_quality":
                recs.append("建议Review最近质量低的Role执行记录，分析原因")
            elif alert.metric == "evolution_stagnation_days":
                recs.append("尝试运行测试任务触发进化，或检查Skill库是否饱和")
            elif alert.metric == "pending_verifications":
                recs.append("运行更多任务以完成验证窗口，或手动确认进化结果")
            elif alert.metric == "skill_conflict_rate":
                recs.append("使用conflict_resolver分析矛盾，解决后重新验证")

        return recs

    def _save_report(self, report: HealthReport):
        """保存报告"""
        HEALTH_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        import json
        with open(HEALTH_REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": report.timestamp,
                "overall": report.overall,
                "checks": report.checks,
                "alerts": [
                    {"level": a.level, "metric": a.metric, "message": a.message}
                    for a in report.alerts
                ],
                "recommendations": report.recommendations
            }, f, ensure_ascii=False, indent=2)

    def get_latest_report(self) -> Optional[HealthReport]:
        """获取最新健康报告"""
        if not HEALTH_REPORT_PATH.exists():
            return None

        import json
        with open(HEALTH_REPORT_PATH, encoding="utf-8") as f:
            data = json.load(f)

        alerts = [
            Alert(level=a["level"], metric=a["metric"], message=a["message"])
            for a in data.get("alerts", [])
        ]

        return HealthReport(
            timestamp=data["timestamp"],
            overall=data["overall"],
            checks=data["checks"],
            alerts=alerts,
            recommendations=data.get("recommendations", [])
        )

    def is_healthy(self) -> bool:
        """快速检查是否健康"""
        report = self.check_all()
        return report.overall == "ok"
