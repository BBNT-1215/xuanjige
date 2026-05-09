"""
Hermestrix Engine

核心引擎模块：
- memory_manager: 四层记忆读写
- conflict_resolver: 记忆矛盾解决
- health_monitor: 系统健康监控
- decay_service: 记忆衰减管理
- evolution: 进化引擎主类
"""

from engine.memory_manager import MemoryManager, TaskRecord, SkillStats, RoleStats
from engine.conflict_resolver import ConflictResolver, Conflict, ResolvedScore, RootCause
from engine.health_monitor import HealthMonitor, HealthReport, Alert
from engine.decay_service import DecayService
from engine.evolution import EvolutionEngine, EvolutionVerifier

__all__ = [
    "MemoryManager",
    "TaskRecord",
    "SkillStats",
    "RoleStats",
    "ConflictResolver",
    "Conflict",
    "ResolvedScore",
    "RootCause",
    "HealthMonitor",
    "HealthReport",
    "Alert",
    "DecayService",
    "EvolutionEngine",
    "EvolutionVerifier",
]
