"""
Hermestrix Engine - Evolution Engine v2

进化引擎主类：记忆→进化的转换器

职责：
1. 归档任务记录到L1
2. 检测并解决记忆矛盾
3. 更新L2：Skill评分 + Role统计
4. 进化验证闭环（观察窗口 + 回滚）
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timezone
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.memory_manager import MemoryManager, TaskRecord, SkillStats, RoleStats
from engine.conflict_resolver import ConflictResolver, Conflict, ResolvedScore
from engine.health_monitor import HealthMonitor, HealthReport
from engine.decay_service import DecayService

# ============================================================
# 进化验证状态
# ============================================================

class EvolutionVerifier:
    """
    进化效果验证闭环

    核心思想：
    进化后的评分不是"立即确认"
    而是要经过N次观察窗口验证
    验证通过才确认为稳定进化
    """

    VERIFICATION_WINDOW = 5  # 观察5次才确认
    ROLLBACK_THRESHOLD = 0.15  # 观察均值低于预期15%则回滚

    def __init__(self):
        # skill_id -> {old_score, new_score, observations[], required}
        self.pending: Dict[str, Dict[str, Any]] = {}

    def on_evolution(self, skill_id: str, old_score: float, new_score: float):
        """当进化引擎更新Skill评分时触发，开启验证观察窗口"""
        self.pending[skill_id] = {
            "old_score": old_score,
            "new_score": new_score,
            "introduced_at": datetime.now(timezone.utc).isoformat(),
            "observations": [],
            "required": self.VERIFICATION_WINDOW
        }

    def on_task_completed(self, skill_id: str, quality_score: float) -> Optional[Dict[str, Any]]:
        """
        每次使用该Skill的任务完成时收集观察结果

        Returns:
            如果触发验证完成，返回 {action: 'confirm'/'rollback', details}
        """
        if skill_id not in self.pending:
            return None

        pending = self.pending[skill_id]
        pending["observations"].append(quality_score)

        if len(pending["observations"]) >= pending["required"]:
            return self._verify_or_rollback(skill_id)

        return None

    def _verify_or_rollback(self, skill_id: str) -> Dict[str, Any]:
        pending = self.pending[skill_id]
        obs_avg = sum(pending["observations"]) / len(pending["observations"])

        expected = pending["new_score"]
        threshold = expected * (1 - self.ROLLBACK_THRESHOLD)

        if obs_avg >= threshold:
            result = {
                "action": "confirm",
                "skill_id": skill_id,
                "expected": expected,
                "observed_avg": round(obs_avg, 3),
                "observations_count": len(pending["observations"])
            }
        else:
            result = {
                "action": "rollback",
                "skill_id": skill_id,
                "expected": expected,
                "observed_avg": round(obs_avg, 3),
                "rollback_to": pending["old_score"],
                "observations_count": len(pending["observations"]),
            }

        del self.pending[skill_id]
        return result

    def get_pending_count(self) -> int:
        return len(self.pending)

    def get_pending_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "skill_id": k,
                "new_score": v["new_score"],
                "observations": len(v["observations"]),
                "required": v["required"]
            }
            for k, v in self.pending.items()
        ]


# ============================================================
# EvolutionEngine 主类
# ============================================================

class EvolutionEngine:
    """
    进化引擎主类

    使用方式：
    engine = EvolutionEngine()
    engine.on_task_completed(task_record)
    """

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        conflict_resolver: Optional[ConflictResolver] = None,
        health_monitor: Optional[HealthMonitor] = None,
        decay_service: Optional[DecayService] = None
    ):
        self.memory = memory or MemoryManager()
        self.conflict = conflict_resolver or ConflictResolver(self.memory)
        self.health = health_monitor or HealthMonitor(self.memory)
        self.decay = decay_service or DecayService(self.memory)
        self.verifier = EvolutionVerifier()

        # 事件回调
        self._callbacks: Dict[str, List[Callable]] = {
            "evolution.confirmed": [],
            "evolution.rollback": [],
            "conflict.detected": [],
            "health.alert": []
        }

    # ============================================================
    # 事件机制
    # ============================================================

    def on_event(self, event: str, callback: Callable):
        """注册事件回调"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def _emit(self, event: str, payload: Any):
        """触发事件"""
        for cb in self._callbacks.get(event, []):
            try:
                cb(payload)
            except Exception as e:
                print(f"[EvolutionEngine] Callback error for {event}: {e}")

    # ============================================================
    # 核心流程
    # ============================================================

    def on_task_completed(self, task_record: TaskRecord) -> Dict[str, Any]:
        """
        任务完成时调用，执行完整进化流程

        Returns:
            进化结果摘要
        """
        result = {
            "task_id": task_record.task_id,
            "archived": False,
            "conflicts": [],
            "skill_updates": [],
            "role_updates": [],
            "verification_triggered": [],
            "health_status": "ok"
        }

        # 1. 归档L1
        path = self.memory.archive_task(task_record)
        result["archived"] = True

        # 2. 冲突检测与解决
        for skill_entry in task_record.skills_used:
            skill_id = skill_entry["skill_id"]
            quality = skill_entry.get("quality_score", task_record.quality_score)

            conflict = self.conflict.detect_conflicts(skill_id, task_record.context.get("task_type"))
            if conflict:
                self._emit("conflict.detected", conflict)
                result["conflicts"].append({
                    "skill_id": skill_id,
                    "severity": conflict.severity
                })

        # 3. 更新L2 Skill
        for skill_entry in task_record.skills_used:
            skill_id = skill_entry["skill_id"]
            quality = skill_entry.get("quality_score", task_record.quality_score)

            # 检测是否有冲突需要解决
            conflict = self.conflict.detect_conflicts(skill_id, task_record.context.get("task_type"))
            resolved_score = None

            if conflict:
                resolved = self.conflict.resolve(conflict)
                resolved_score = resolved.score

            # 更新Skill统计
            old_stats = self.memory.get_skill_stats(skill_id)
            old_score = old_stats.effectiveness_score

            new_stats = self.memory.update_skill_from_record(skill_id, quality)

            # 如果评分变化了，开启验证
            if abs(new_stats.effectiveness_score - old_score) > 0.05:
                self.verifier.on_evolution(skill_id, old_score, new_stats.effectiveness_score)

            result["skill_updates"].append({
                "skill_id": skill_id,
                "old_score": old_score,
                "new_score": new_stats.effectiveness_score,
                "confidence": new_stats.confidence
            })

        # 4. 更新L2 Role
        for role_id in task_record.executing_roles:
            old_stats = self.memory.get_role_stats(role_id)
            new_stats = self.memory.update_role_from_record(
                role_id,
                task_record.quality_score,
                collaborators=task_record.executing_roles
            )
            result["role_updates"].append({
                "role_id": role_id,
                "tasks_completed": new_stats.stats["tasks_completed"],
                "avg_quality": new_stats.stats["avg_quality"]
            })

        # 5. 检查验证触发（从pending中）
        for skill_entry in task_record.skills_used:
            skill_id = skill_entry["skill_id"]
            quality = skill_entry.get("quality_score", task_record.quality_score)

            verification_result = self.verifier.on_task_completed(skill_id, quality)
            if verification_result:
                result["verification_triggered"].append(verification_result)

                if verification_result["action"] == "confirm":
                    self._emit("evolution.confirmed", verification_result)
                    # 更新确认状态
                    stats = self.memory.get_skill_stats(verification_result["skill_id"])
                    stats.verification["status"] = "verified"
                    stats.verification["observations_avg"] = verification_result["observed_avg"]
                    stats.verification["verification_confirmed_at"] = datetime.now(timezone.utc).isoformat()
                    self.memory.save_skill_stats(stats)
                elif verification_result["action"] == "rollback":
                    self._emit("evolution.rollback", verification_result)
                    # 回滚评分
                    stats = self.memory.get_skill_stats(verification_result["skill_id"])
                    stats.effectiveness_score = verification_result["rollback_to"]
                    stats.verification["status"] = "rolled_back"
                    self.memory.save_skill_stats(stats)

        # 6. 健康检查
        health_report = self.health.check_all()
        result["health_status"] = health_report.overall
        if health_report.alerts:
            for alert in health_report.alerts:
                self._emit("health.alert", alert)

        return result

    def on_task_failed(self, task_record: TaskRecord):
        """任务失败时特殊处理"""
        task_record.quality_tier = "bad"
        task_record.quality_score = 0.0
        self.memory.archive_task(task_record)

        # 失败触发更严格的健康检查
        health_report = self.health.check_all()
        if health_report.overall != "ok":
            for alert in health_report.alerts:
                self._emit("health.alert", alert)

    # ============================================================
    # 便捷方法
    # ============================================================

    def update_skill(self, skill_id: str, quality_score: float, task_context: str = None):
        """手动更新单个Skill评分"""
        conflict = self.conflict.detect_conflicts(skill_id, task_context)

        old_stats = self.memory.get_skill_stats(skill_id)
        old_score = old_stats.effectiveness_score

        new_stats = self.memory.update_skill_from_record(skill_id, quality_score)

        if abs(new_stats.effectiveness_score - old_score) > 0.05:
            self.verifier.on_evolution(skill_id, old_score, new_stats.effectiveness_score)

        return new_stats

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        health = self.health.check_all()
        decay_stats = self.decay.get_decay_stats()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": {
                "overall": health.overall,
                "alerts_count": len(health.alerts)
            },
            "decay": decay_stats,
            "pending_verifications": self.verifier.get_pending_count(),
            "memory_summary": self.memory.get_system_health_summary()
        }

    # ============================================================
    # CLI支持
    # ============================================================

    @staticmethod
    def cmd_status():
        """CLI: 显示状态"""
        engine = EvolutionEngine()
        status = engine.get_system_status()

        print("=== Hermestrix System Status ===")
        print(f"Timestamp: {status['timestamp']}")
        print(f"Health: {status['health']['overall']}")
        print(f"Pending Verifications: {status['pending_verifications']}")
        print(f"Decay Stats: {status['decay']}")
        print(f"Memory: {status['memory_summary']}")

        return status
