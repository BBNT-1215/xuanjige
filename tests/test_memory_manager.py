"""
Tests for engine/memory_manager.py
"""

import pytest
import pathlib
import tempfile
import shutil
import os
import sys

# Setup HERMESTRIX_HOME before import
_TEST_HOME = pathlib.Path(tempfile.mkdtemp(prefix="hermestrix_test_"))
os.environ["HERMESTRIX_HOME"] = str(_TEST_HOME)
sys.path.insert(0, str(_TEST_HOME))

from engine.memory_manager import (
    MemoryManager, TaskRecord, SkillStats, RoleStats
)
from datetime import datetime, timezone


@pytest.fixture
def mm():
    """Fresh MemoryManager for each test"""
    return MemoryManager()


class TestMemoryManager_L1:
    """L1: Task memory"""

    def test_archive_task_good(self, mm):
        """good tasks go to raw/"""
        record = TaskRecord(
            task_id="TEST-GOOD",
            task_type="coding",
            task_title="Good task",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_coding", "effectiveness": 0.8}],
            quality_score=0.85,
            quality_tier="good",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        path = mm.archive_task(record)
        assert pathlib.Path(path).exists()
        assert "raw" in path

    def test_archive_task_bad(self, mm):
        """bad tasks go to cold/"""
        record = TaskRecord(
            task_id="TEST-BAD",
            task_type="coding",
            task_title="Bad task",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_coding", "effectiveness": 0.2}],
            quality_score=0.1,
            quality_tier="bad",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        path = mm.archive_task(record)
        assert pathlib.Path(path).exists()
        assert "cold" in path

    def test_archive_task_medium(self, mm):
        """medium tasks go to resolved/"""
        record = TaskRecord(
            task_id="TEST-MED",
            task_type="analysis",
            task_title="Medium task",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_data_analysis", "effectiveness": 0.5}],
            quality_score=0.5,
            quality_tier="medium",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        path = mm.archive_task(record)
        assert pathlib.Path(path).exists()
        assert "resolved" in path

    def test_get_task_record(self, mm):
        """归档后可查询"""
        record = TaskRecord(
            task_id="TEST-GET",
            task_type="coding",
            task_title="Get test",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_coding", "effectiveness": 0.8}],
            quality_score=0.8,
            quality_tier="good",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        mm.archive_task(record)
        retrieved = mm.get_task_record("TEST-GET")
        assert retrieved is not None
        assert retrieved.task_id == "TEST-GET"
        assert retrieved.quality_score == 0.8

    def test_get_task_record_not_found(self, mm):
        """不存在返回None"""
        assert mm.get_task_record("NONEXISTENT") is None


class TestMemoryManager_L2_Skill:
    """L2: Skill effectiveness tracking"""

    def test_get_skill_stats_default(self, mm):
        """未知skill返回默认统计"""
        stats = mm.get_skill_stats("skill_nonexistent")
        assert stats.effectiveness_score == 0.5
        assert stats.confidence == "low"
        assert stats.stats["total_uses"] == 0

    def test_update_skill_from_record(self, mm):
        """更新Skill评分"""
        record = TaskRecord(
            task_id="TEST-SKILL-UPD",
            task_type="coding",
            task_title="Skill update test",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_coding", "effectiveness": 0.85}],
            quality_score=0.85,
            quality_tier="good",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        mm.archive_task(record)
        stats = mm.update_skill_from_record("skill_coding", 0.85)
        assert stats.effectiveness_score > 0.5

    def test_get_all_skill_effectiveness(self, mm):
        """获取所有Skill评分"""
        result = mm.get_all_skill_effectiveness()
        assert isinstance(result, dict)


class TestMemoryManager_L2_Role:
    """L2: Role statistics"""

    def test_get_role_stats_default(self, mm):
        """未知role返回默认统计"""
        stats = mm.get_role_stats("role_nonexistent")
        assert stats.stats["tasks_completed"] == 0
        assert stats.stats["avg_quality"] == 0.0

    def test_update_role_from_record(self, mm):
        """更新Role统计"""
        record = TaskRecord(
            task_id="TEST-ROLE-UPD",
            task_type="coding",
            task_title="Role update test",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_coding", "effectiveness": 0.8}],
            quality_score=0.82,
            quality_tier="good",
            completed_at=datetime.now(timezone.utc).isoformat(),
            executing_roles=["jizao"],
        )
        mm.archive_task(record)
        stats = mm.update_role_from_record("jizao", 0.82, collaborators=["bingrong"])
        assert stats.stats["tasks_completed"] >= 1
        assert "bingrong" in stats.collaborations


class TestTaskRecord:
    """TaskRecord dataclass"""

    def test_task_record_to_dict(self):
        """可序列化"""
        record = TaskRecord(
            task_id="TEST-SERIAL",
            task_type="coding",
            task_title="Serialization test",
            created_at=datetime.now(timezone.utc).isoformat(),
            skills_used=[{"skill_id": "skill_coding", "effectiveness": 0.8}],
            quality_score=0.8,
            quality_tier="good",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        d = record.to_dict()
        assert d["task_id"] == "TEST-SERIAL"
        assert d["quality_score"] == 0.8

    def test_task_record_from_dict(self):
        """可反序列化"""
        d = {
            "task_id": "TEST-DESERIAL",
            "task_type": "analysis",
            "task_title": "Deserialization test",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "skills_used": [{"skill_id": "skill_data_analysis", "effectiveness": 0.75}],
            "quality_score": 0.75,
            "quality_tier": "good",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        record = TaskRecord.from_dict(d)
        assert record.task_id == "TEST-DESERIAL"
        assert record.quality_score == 0.75
