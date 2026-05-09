"""
Hermestrix Engine - Memory Manager v2

四层记忆的统一读写接口：
- L1: 任务原始记录（memory/raw/）
- L2: Skill/Role进化统计（three_libs/skills/、three_libs/roles/）
- L3: 知识沉淀（knowledge/rules/、knowledge/axioms/、knowledge/context/）
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
import math

# ============================================================
# 配置
# ============================================================

HERMESTRIX_HOME = Path(os.environ.get("HERMESTRIX_HOME", "/root/hermestrix"))

MEMORY_DIR = HERMESTRIX_HOME / "three_libs" / "memory"
SKILL_STATS_DIR = HERMESTRIX_HOME / "three_libs" / "skills"
ROLE_STATS_DIR = HERMESTRIX_HOME / "three_libs" / "roles"
KNOWLEDGE_DIR = HERMESTRIX_HOME / "three_libs" / "knowledge"

RAW_DIR = MEMORY_DIR / "raw"
RESOLVED_DIR = MEMORY_DIR / "resolved"
COLD_DIR = MEMORY_DIR / "cold"

DECAY_HALF_LIFE_DAYS = 90
COLD_STORAGE_THRESHOLD_DAYS = 180

# ============================================================
# 数据结构
# ============================================================

@dataclass
class TaskRecord:
    """L1: 任务记忆记录"""
    task_id: str
    task_type: str
    task_title: str
    created_at: str
    completed_at: Optional[str] = None
    duration_minutes: int = 0
    executing_roles: List[str] = field(default_factory=list)
    org_flow: List[str] = field(default_factory=list)
    skills_used: List[Dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0
    quality_tier: str = "medium"  # good / medium / bad
    outcome: Dict[str, Any] = field(default_factory=dict)
    reflection: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    conflict_resolved: bool = False
    decay_weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'TaskRecord':
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})


@dataclass
class SkillStats:
    """L2: Skill进化统计"""
    skill_id: str
    version: str = "1"
    updated_at: str = ""
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "total_uses": 0,
        "success_count": 0,
        "failure_count": 0,
        "avg_quality": 0.0,
        "last_used": "",
        "last_5_scores": []
    })
    effectiveness_score: float = 0.5
    confidence: str = "low"
    best_practices: List[Dict[str, Any]] = field(default_factory=list)
    failure_patterns: List[Dict[str, Any]] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=lambda: {
        "status": "pending",
        "version_introduced": "1",
        "observations_required": 5,
        "observations_collected": 0,
        "observations_avg": 0.0,
        "verification_confirmed_at": ""
    })
    decay: Dict[str, Any] = field(default_factory=lambda: {
        "last_accessed": "",
        "decay_weight": 1.0,
        "in_cold_storage": False
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'SkillStats':
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})


@dataclass
class RoleStats:
    """L2: Role进化统计"""
    role_id: str
    version: str = "1"
    updated_at: str = ""
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "tasks_completed": 0,
        "avg_quality": 0.0,
        "avg_duration_minutes": 0,
        "last_active": ""
    })
    collaborations: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    skill_usage: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=lambda: {
        "status": "ok",
        "trend": "stable",
        "last_check": ""
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'RoleStats':
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})


# ============================================================
# MemoryManager 主类
# ============================================================

class MemoryManager:
    """
    四层记忆的统一读写接口
    """

    def __init__(self, home: Optional[Path] = None):
        self.home = home or HERMESTRIX_HOME
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保所有目录存在"""
        for d in [RAW_DIR, RESOLVED_DIR, COLD_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ============================================================
    # L1: 任务记忆读写
    # ============================================================

    def archive_task(self, record: TaskRecord) -> str:
        """
        归档任务记录到L1
        根据quality_tier决定存储位置
        """
        if record.quality_tier == "good":
            path = RAW_DIR / f"{record.task_id}.json"
        elif record.quality_tier == "bad":
            path = RAW_DIR / f"{record.task_id}.json"
        else:
            path = RAW_DIR / f"{record.task_id}.json"

        # 计算衰减权重
        record.decay_weight = self.calculate_decay_weight(
            datetime.fromisoformat(record.completed_at or record.created_at)
        )

        with open(path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)

        # 更新索引
        self._update_memory_index(record)

        return str(path)

    def get_task_record(self, task_id: str) -> Optional[TaskRecord]:
        """读取指定任务记录"""
        for d in [RAW_DIR, RESOLVED_DIR, COLD_DIR]:
            path = d / f"{task_id}.json"
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return TaskRecord.from_dict(json.load(f))
        return None

    def query_similar_tasks(
        self,
        task_type: Optional[str] = None,
        quality_filter: str = "good",
        limit: int = 5
    ) -> List[TaskRecord]:
        """
        查询同类任务的最优记忆记录
        quality_filter: 'good' / 'bad' / 'all'
        """
        index = self._load_memory_index()
        records = []

        for task_id in index.get("tasks", {}).keys():
            record = self.get_task_record(task_id)
            if not record:
                continue

            # 质量过滤
            if quality_filter == "good" and record.quality_tier != "good":
                continue
            elif quality_filter == "bad" and record.quality_tier != "bad":
                continue

            # 类型过滤
            if task_type and record.task_type != task_type:
                continue

            records.append(record)

        # 按衰减权重排序（权重高的在前）
        records.sort(key=lambda r: r.decay_weight, reverse=True)
        return records[:limit]

    def _load_memory_index(self) -> Dict[str, Any]:
        """加载记忆索引"""
        index_path = MEMORY_DIR / "index.json"
        if index_path.exists():
            with open(index_path, encoding="utf-8") as f:
                return json.load(f)
        return {"version": "1.0", "tasks": {}, "updated_at": ""}

    def _update_memory_index(self, record: TaskRecord):
        """更新记忆索引"""
        index = self._load_memory_index()
        index["tasks"][record.task_id] = {
            "task_type": record.task_type,
            "quality_tier": record.quality_tier,
            "completed_at": record.completed_at,
            "skills_used": [s["skill_id"] for s in record.skills_used],
            "executing_roles": record.executing_roles
        }
        index["updated_at"] = self._now()

        index_path = MEMORY_DIR / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    # ============================================================
    # L2: Skill进化统计
    # ============================================================

    def get_skill_stats(self, skill_id: str) -> SkillStats:
        """读取Skill进化统计，不存在则创建默认"""
        path = SKILL_STATS_DIR / skill_id / "stats.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return SkillStats.from_dict(json.load(f))

        # 返回默认统计
        stats = SkillStats(skill_id=skill_id, updated_at=self._now())
        return stats

    def save_skill_stats(self, stats: SkillStats):
        """保存Skill进化统计"""
        path = SKILL_STATS_DIR / stats.skill_id / "stats.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)

    def get_all_skill_effectiveness(self) -> Dict[str, float]:
        """获取所有Skill的effectiveness评分"""
        result = {}
        if not SKILL_STATS_DIR.exists():
            return result

        for skill_dir in SKILL_STATS_DIR.iterdir():
            if skill_dir.is_dir():
                stats_path = skill_dir / "stats.json"
                if stats_path.exists():
                    with open(stats_path, encoding="utf-8") as f:
                        data = json.load(f)
                        result[skill_dir.name] = data.get("effectiveness_score", 0.5)
        return result

    def update_skill_from_record(self, skill_id: str, quality_score: float):
        """
        根据任务记录更新Skill统计
        """
        stats = self.get_skill_stats(skill_id)
        now = self._now()

        # 更新统计
        stats.stats["total_uses"] += 1
        stats.stats["last_used"] = now

        # 维护最近5次评分
        last_5 = stats.stats.get("last_5_scores", [])
        last_5.append(quality_score)
        if len(last_5) > 5:
            last_5 = last_5[-5:]
        stats.stats["last_5_scores"] = last_5

        if quality_score >= 0.8:
            stats.stats["success_count"] += 1
        elif quality_score < 0.5:
            stats.stats["failure_count"] += 1

        # 重新计算平均
        all_records = self._get_records_for_skill(skill_id)
        if all_records:
            stats.stats["avg_quality"] = sum(r["quality_score"] for r in all_records) / len(all_records)

        # 重新计算effectiveness（加权）
        new_score, confidence = self._calculate_effectiveness(all_records)
        stats.effectiveness_score = new_score
        stats.confidence = confidence
        stats.updated_at = now
        stats.decay["last_accessed"] = now
        stats.decay["decay_weight"] = 1.0

        self.save_skill_stats(stats)
        return stats

    def _get_records_for_skill(self, skill_id: str) -> List[Dict[str, Any]]:
        """获取某Skill的所有L1记录"""
        records = []
        index = self._load_memory_index()

        for task_id, info in index.get("tasks", {}).items():
            if skill_id in info.get("skills_used", []):
                record = self.get_task_record(task_id)
                if record:
                    records.append({
                        "task_id": task_id,
                        "quality_score": next(
                            (s["quality_score"] for s in record.skills_used if s["skill_id"] == skill_id),
                            0.5
                        ),
                        "completed_at": record.completed_at or record.created_at,
                        "decay_weight": record.decay_weight
                    })
        return records

    def _calculate_effectiveness(self, records: List[Dict[str, Any]]) -> tuple[float, str]:
        """
        计算加权effectiveness评分

        公式：
        score = Σ(quality * decay_weight) / Σ(decay_weight)
        decay_weight = 0.5 ^ (days_since / 90)
        """
        if not records:
            return 0.5, "low"

        weighted_sum = 0.0
        weight_sum = 0.0

        for r in records:
            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(r["completed_at"])).days
            decay = 0.5 ** (days_since / DECAY_HALF_LIFE_DAYS)
            weight = decay * r.get("decay_weight", 1.0)

            weighted_sum += r["quality_score"] * weight
            weight_sum += weight

        if weight_sum == 0:
            return 0.5, "low"

        raw_score = weighted_sum / weight_sum

        # 方差检测
        scores = [r["quality_score"] for r in records]
        variance = self._variance(scores)

        if variance > 0.3:
            confidence = "low"
            raw_score *= 0.8
        elif variance > 0.15:
            confidence = "medium"
            raw_score *= 0.95
        else:
            confidence = "high"

        return round(min(max(raw_score, 0.0), 1.0), 2), confidence

    @staticmethod
    def _variance(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)

    # ============================================================
    # L2: Role进化统计
    # ============================================================

    def get_role_stats(self, role_id: str) -> RoleStats:
        """读取Role进化统计，不存在则创建默认"""
        path = ROLE_STATS_DIR / role_id / "stats.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return RoleStats.from_dict(json.load(f))

        stats = RoleStats(role_id=role_id, updated_at=self._now())
        return stats

    def save_role_stats(self, stats: RoleStats):
        """保存Role进化统计"""
        path = ROLE_STATS_DIR / stats.role_id / "stats.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats.to_dict(), f, ensure_ascii=False, indent=2)

    def update_role_from_record(self, role_id: str, quality_score: float, collaborators: List[str] = None):
        """
        根据任务记录更新Role统计
        """
        stats = self.get_role_stats(role_id)
        now = self._now()

        # 更新统计
        stats.stats["tasks_completed"] += 1
        stats.stats["last_active"] = now

        # 滚动平均
        n = stats.stats["tasks_completed"]
        old_avg = stats.stats.get("avg_quality", 0.0)
        new_avg = (old_avg * (n - 1) + quality_score) / n
        stats.stats["avg_quality"] = round(new_avg, 3)

        # 更新协作关系
        if collaborators:
            for collab_id in collaborators:
                if collab_id == role_id:
                    continue
                if collab_id not in stats.collaborations:
                    stats.collaborations[collab_id] = {"count": 0, "total_quality": 0.0, "avg_quality": 0.0}

                c = stats.collaborations[collab_id]
                c["count"] += 1
                c["total_quality"] += quality_score
                c["avg_quality"] = round(c["total_quality"] / c["count"], 3)

        stats.updated_at = now
        self.save_role_stats(stats)
        return stats

    def get_best_role_combo(self, task_type: str) -> List[str]:
        """
        获取某任务类型的最优Role组合
        基于历史协作质量排序
        """
        index = self._load_memory_index()
        role_scores: Dict[str, List[float]] = {}

        for task_id, info in index.get("tasks", {}).items():
            if info.get("task_type") == task_type:
                record = self.get_task_record(task_id)
                if not record:
                    continue

                for role_id in record.executing_roles:
                    if role_id not in role_scores:
                        role_scores[role_id] = []
                    role_scores[role_id].append(record.quality_score)

        # 计算各Role的平均质量
        role_avg = {
            rid: sum(scores) / len(scores)
            for rid, scores in role_scores.items()
            if scores
        }

        # 排序返回
        sorted_roles = sorted(role_avg.items(), key=lambda x: x[1], reverse=True)
        return [rid for rid, _ in sorted_roles]

    # ============================================================
    # L3: 知识查询
    # ============================================================

    def get_workflow_rules(self, phase: str) -> Dict[str, Any]:
        """获取某流程阶段的规则"""
        rules_path = KNOWLEDGE_DIR / "rules" / "workflow_sanshengliubu.json"
        if rules_path.exists():
            with open(rules_path, encoding="utf-8") as f:
                data = json.load(f)
                return data.get(phase, {})
        return {}

    def get_axiom(self, axiom_id: str) -> Optional[Dict[str, Any]]:
        """获取决策公理"""
        axiom_path = KNOWLEDGE_DIR / "axioms" / f"{axiom_id}.json"
        if axiom_path.exists():
            with open(axiom_path, encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_axioms(self) -> List[str]:
        """列出所有公理ID"""
        axioms_dir = KNOWLEDGE_DIR / "axioms"
        if not axioms_dir.exists():
            return []
        return [p.stem for p in axioms_dir.glob("*.json")]

    def get_context(self, key: str) -> Optional[Any]:
        """获取上下文知识"""
        ctx_path = KNOWLEDGE_DIR / "context" / f"{key}.json"
        if ctx_path.exists():
            with open(ctx_path, encoding="utf-8") as f:
                return json.load(f)
        return None

    # ============================================================
    # 衰减
    # ============================================================

    def calculate_decay_weight(self, record_time: datetime) -> float:
        """计算时间衰减权重"""
        days_since = (datetime.now(timezone.utc) - record_time).days
        return round(0.5 ** (days_since / DECAY_HALF_LIFE_DAYS), 4)

    def apply_decay_to_all(self):
        """对所有L1记录应用衰减"""
        index = self._load_memory_index()

        for task_id in index.get("tasks", {}).keys():
            record = self.get_task_record(task_id)
            if not record:
                continue

            new_weight = self.calculate_decay_weight(
                datetime.fromisoformat(record.completed_at or record.created_at)
            )

            if abs(new_weight - record.decay_weight) > 0.01:
                record.decay_weight = new_weight
                path = RAW_DIR / f"{task_id}.json"
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)

    def archive_cold_memories(self):
        """将长期未访问的记忆移到cold storage"""
        threshold_days = COLD_STORAGE_THRESHOLD_DAYS
        index = self._load_memory_index()

        for task_id, info in index.get("tasks", {}).items():
            if info.get("in_cold_storage"):
                continue

            record = self.get_task_record(task_id)
            if not record:
                continue

            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(
                record.completed_at or record.created_at
            )).days

            if days_since >= threshold_days:
                # 移到cold storage
                raw_path = RAW_DIR / f"{task_id}.json"
                cold_path = COLD_DIR / f"{task_id}.json"

                if raw_path.exists():
                    with open(raw_path, encoding="utf-8") as f:
                        data = json.load(f)
                    data["decay"]["in_cold_storage"] = True

                    with open(cold_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    raw_path.unlink()

                    info["in_cold_storage"] = True
                    self._update_memory_index(record)

    # ============================================================
    # 工具
    # ============================================================

    def get_system_health_summary(self) -> Dict[str, Any]:
        """获取系统健康摘要"""
        skill_stats = list(SKILL_STATS_DIR.glob("*/stats.json"))
        role_stats = list(ROLE_STATS_DIR.glob("*/stats.json"))

        skill_avg = 0.0
        if skill_stats:
            total = 0.0
            for p in skill_stats:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
                    total += d.get("effectiveness_score", 0.5)
            skill_avg = total / len(skill_stats)

        role_avg = 0.0
        if role_stats:
            total = 0.0
            for p in role_stats:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
                    total += d.get("stats", {}).get("avg_quality", 0.0)
            role_avg = total / len(role_stats)

        return {
            "skill_avg_effectiveness": round(skill_avg, 3),
            "role_avg_quality": round(role_avg, 3),
            "total_skills": len(skill_stats),
            "total_roles": len(role_stats),
            "total_memory_records": len(self._load_memory_index().get("tasks", {}))
        }
