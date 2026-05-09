"""
Hermestrix Engine - Conflict Resolver

解决L1记忆中的Skill效果矛盾
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.memory_manager import MemoryManager, TaskRecord

# ============================================================
# 数据结构
# ============================================================

@dataclass
class RootCause:
    """矛盾根本原因分析"""
    type: str  # context_mismatch / role_difference / unknown
    description: str
    good_contexts: List[str] = field(default_factory=list)
    bad_contexts: List[str] = field(default_factory=list)
    good_roles: List[str] = field(default_factory=list)
    bad_roles: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """检测到的矛盾"""
    skill_id: str
    context: str
    goods: List[Dict[str, Any]]
    bads: List[Dict[str, Any]]
    severity: str = "high"  # high / medium / low


@dataclass
class ResolvedScore:
    """解决后的评分"""
    score: float
    confidence: str  # high / medium / low
    warning: Optional[str]
    root_cause: Optional[RootCause]
    resolved_from: Dict[str, int] = field(default_factory=dict)  # good_count, bad_count


# ============================================================
# ConflictResolver
# ============================================================

class ConflictResolver:
    """
    解决L1记忆中的矛盾

    矛盾定义：
    存在 ≥2 条 good 记忆 且 ≥2 条 bad 记忆
    对同一Skill在同一context下效果截然相反
    """

    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()

    def detect_conflicts(self, skill_id: str, task_context: Optional[str] = None) -> Optional[Conflict]:
        """
        检测某Skill在特定上下文下是否有矛盾

        Args:
            skill_id: Skill ID
            task_context: 可选的上下文（如 task_type）

        Returns:
            Conflict对象，如果存在矛盾；否则None
        """
        index = self.memory._load_memory_index()
        goods = []
        bads = []

        for task_id, info in index.get("tasks", {}).items():
            if skill_id not in info.get("skills_used", []):
                continue

            # 上下文过滤
            if task_context:
                rec_context = info.get("task_type", "")
                if rec_context != task_context:
                    continue

            record = self.memory.get_task_record(task_id)
            if not record:
                continue

            # 找到该Skill在记录中的评分
            skill_entry = next(
                (s for s in record.skills_used if s.get("skill_id") == skill_id),
                None
            )
            if not skill_entry:
                continue

            quality = skill_entry.get("quality_score", 0.5)
            entry = {
                "task_id": task_id,
                "quality_score": quality,
                "task_type": info.get("task_type", ""),
                "executing_roles": info.get("executing_roles", []),
                "completed_at": info.get("completed_at", "")
            }

            if record.quality_tier == "good":
                goods.append(entry)
            elif record.quality_tier == "bad":
                bads.append(entry)

        # 需要两边都有足够样本才算矛盾
        if len(goods) >= 2 and len(bads) >= 2:
            return Conflict(
                skill_id=skill_id,
                context=task_context or "all",
                goods=goods,
                bads=bads,
                severity="high"
            )
        elif len(goods) >= 1 and len(bads) >= 2:
            return Conflict(skill_id=skill_id, context=task_context or "all",
                          goods=goods, bads=bads, severity="medium")
        elif len(goods) >= 2 and len(bads) >= 1:
            return Conflict(skill_id=skill_id, context=task_context or "all",
                          goods=goods, bads=bads, severity="low")

        return None

    def resolve(self, conflict: Conflict) -> ResolvedScore:
        """
        解决冲突，返回推荐使用的effectiveness_score

        策略：
        1. 时间加权：新记忆权重更高
        2. 样本量：样本多的更可信
        3. 方差分析：高方差时降低置信度
        4. 上下文匹配：同task_type优先
        """
        all_records = conflict.goods + conflict.bads

        # 原因分析
        root_cause = self._analyze_root_cause(conflict)

        # 时间加权计算
        weighted_sum = 0.0
        weight_sum = 0.0

        for r in all_records:
            from datetime import datetime, timezone
            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(r["completed_at"])).days
            decay = 0.5 ** (days_since / 90)
            weight = decay

            weighted_sum += r["quality_score"] * weight
            weight_sum += weight

        if weight_sum == 0:
            return ResolvedScore(
                score=0.5,
                confidence="low",
                warning="无法计算评分",
                root_cause=root_cause,
                resolved_from={"good_count": len(conflict.goods), "bad_count": len(conflict.bads)}
            )

        raw_score = weighted_sum / weight_sum

        # 方差检测
        scores = [r["quality_score"] for r in all_records]
        variance = self._variance(scores)

        warning = None
        if variance > 0.3:
            confidence = "low"
            raw_score *= 0.8
            warning = f"Skill在{conflict.context}下效果不稳定(方差={variance:.2f})，建议检查root cause"
        elif variance > 0.15:
            confidence = "medium"
            raw_score *= 0.95
        else:
            confidence = "high"

        return ResolvedScore(
            score=round(min(max(raw_score, 0.0), 1.0), 2),
            confidence=confidence,
            warning=warning,
            root_cause=root_cause,
            resolved_from={"good_count": len(conflict.goods), "bad_count": len(conflict.bads)}
        )

    def _analyze_root_cause(self, conflict: Conflict) -> RootCause:
        """
        分析矛盾的根本原因
        """
        good_types = set(r.get("task_type", "") for r in conflict.goods)
        bad_types = set(r.get("task_type", "") for r in conflict.bads)

        if good_types != bad_types and good_types and bad_types:
            return RootCause(
                type="context_mismatch",
                description=f"Skill在不同task_type下效果不同",
                good_contexts=list(good_types),
                bad_contexts=list(bad_types)
            )

        good_roles = set()
        bad_roles = set()
        for r in conflict.goods:
            good_roles.update(r.get("executing_roles", []))
        for r in conflict.bads:
            bad_roles.update(r.get("executing_roles", []))

        if good_roles != bad_roles and good_roles and bad_roles:
            return RootCause(
                type="role_difference",
                description=f"不同Role执行时效果不同",
                good_roles=list(good_roles),
                bad_roles=list(bad_roles)
            )

        return RootCause(
            type="unknown",
            description="无法确定原因，需人工审查"
        )

    @staticmethod
    def _variance(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    def get_conflict_report(self, skill_id: str) -> Dict[str, Any]:
        """
        获取某Skill的冲突报告（供调试/审查用）
        """
        conflict = self.detect_conflicts(skill_id)
        if not conflict:
            return {"has_conflict": False, "skill_id": skill_id}

        resolved = self.resolve(conflict)
        return {
            "has_conflict": True,
            "skill_id": skill_id,
            "severity": conflict.severity,
            "good_count": len(conflict.goods),
            "bad_count": len(conflict.bads),
            "resolved_score": resolved.score,
            "confidence": resolved.confidence,
            "warning": resolved.warning,
            "root_cause": {
                "type": resolved.root_cause.type if resolved.root_cause else "unknown",
                "description": resolved.root_cause.description if resolved.root_cause else ""
            }
        }
