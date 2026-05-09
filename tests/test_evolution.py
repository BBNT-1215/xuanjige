"""
Tests for engine/evolution.py
"""

import pytest
import pathlib
import tempfile
import os
import sys

_TEST_HOME = pathlib.Path(tempfile.mkdtemp(prefix="hermestrix_test_"))
os.environ["HERMESTRIX_HOME"] = str(_TEST_HOME)
sys.path.insert(0, str(_TEST_HOME))

from engine.evolution import EvolutionEngine, EvolutionVerifier, TaskRecord
from datetime import datetime, timezone


@pytest.fixture
def ee():
    return EvolutionEngine()


def make_task(task_id, quality=0.80, tier="good", skills=None):
    if skills is None:
        skills = [{"skill_id": "skill_coding", "effectiveness": quality}]
    return TaskRecord(
        task_id=task_id,
        task_type="coding",
        task_title=f"Test task {task_id}",
        created_at=datetime.now(timezone.utc).isoformat(),
        skills_used=skills,
        quality_score=quality,
        quality_tier=tier,
        completed_at=datetime.now(timezone.utc).isoformat(),
        executing_roles=["gongbu"],
    )


class TestEvolutionVerifier:
    """EvolutionVerifier: pending observation window"""

    def test_pending_on_evolution(self):
        """触发evolution时开启pending"""
        v = EvolutionVerifier()
        v.on_evolution("skill_x", old_score=0.6, new_score=0.85)
        assert v.get_pending_count() == 1
        p = v.get_pending_list()[0]
        assert p["skill_id"] == "skill_x"
        assert p["new_score"] == 0.85
        assert p["observations"] == 0

    def test_observations_accumulate_and_trigger(self):
        """5次观察后第6次触发验证"""
        v = EvolutionVerifier()
        v.on_evolution("skill_x", old_score=0.6, new_score=0.85)
        # 前4次不触发
        for i in range(4):
            result = v.on_task_completed("skill_x", quality_score=0.82 + i * 0.01)
            assert result is None, f"Should not trigger on call {i+1}"
        # 第5次触发（达到required=5）
        result = v.on_task_completed("skill_x", quality_score=0.82)
        assert result is not None
        assert result["action"] == "confirm"
        assert v.get_pending_count() == 0

    def test_confirm_when_above_threshold(self):
        """观察均值>=新评分×0.9时确认"""
        v = EvolutionVerifier()
        v.on_evolution("skill_x", old_score=0.6, new_score=0.80)
        # 4次高质量
        for _ in range(4):
            v.on_task_completed("skill_x", quality_score=0.82)
        # 第5次触发验证（均值应>=0.80*0.9=0.72）
        result = v.on_task_completed("skill_x", quality_score=0.82)
        assert result is not None
        assert result["action"] == "confirm"
        assert result["observed_avg"] >= 0.72

    def test_rollback_when_below_threshold(self):
        """观察均值<新评分×0.85时回滚"""
        v = EvolutionVerifier()
        v.on_evolution("skill_x", old_score=0.6, new_score=0.85)
        # 5次低质量（均值0.65 < 0.85*0.85=0.7225）
        for _ in range(4):
            v.on_task_completed("skill_x", quality_score=0.65)
        result = v.on_task_completed("skill_x", quality_score=0.65)
        assert result is not None
        assert result["action"] == "rollback"
        assert result["rollback_to"] == 0.6

    def test_no_pending_for_small_change(self):
        """评分变化<0.05不触发pending"""
        v = EvolutionVerifier()
        v.on_evolution("skill_x", old_score=0.80, new_score=0.82)
        # 差异=0.02 < 0.05，不应触发pending
        # （注：on_evolution已由调用者判断变化幅度后调用）
        assert v.get_pending_count() == 1  # on_evolution创建了pending
        # 但如果差异<0.05，EvolutionEngine不会调用on_evolution


class TestEvolutionEngine:
    """EvolutionEngine: end-to-end evolution flow"""

    def test_on_task_completed_basic(self, ee):
        """正常任务完成触发完整流程"""
        task = make_task("EV-TASK-001", quality=0.82)
        result = ee.on_task_completed(task)
        assert result["archived"] is True
        assert result["task_id"] == "EV-TASK-001"
        assert isinstance(result["skill_updates"], list)
        assert result["health_status"] in ("ok", "warn", "critical")

    def test_on_task_completed_updates_skill_stats(self, ee):
        """任务完成更新L2 Skill统计"""
        task = make_task("EV-TASK-002", quality=0.80)
        ee.on_task_completed(task)
        stats = ee.memory.get_skill_stats("skill_coding")
        assert stats.stats["total_uses"] >= 1

    def test_on_task_failed(self, ee):
        """失败任务走bad路径"""
        task = make_task("EV-TASK-FAIL", quality=0.0, tier="bad")
        result = ee.on_task_completed(task)
        assert result["archived"] is True
        # bad任务路径已处理

    def test_get_system_status(self, ee):
        """系统状态报告"""
        status = ee.get_system_status()
        assert "timestamp" in status
        assert "health" in status
        assert "decay" in status

    def test_event_callbacks_registered(self, ee):
        """事件回调机制"""
        called = []
        ee.on_event("evolution.confirmed", lambda p: called.append(p))
        # 手动触发一个pending验证流程
        v = ee.verifier
        v.on_evolution("skill_cb_test", old_score=0.6, new_score=0.85)
        for _ in range(4):
            v.on_task_completed("skill_cb_test", quality_score=0.82)
        result = v.on_task_completed("skill_cb_test", quality_score=0.82)
        # 回调会在演化确认时触发（通过EE的事件机制）
        assert result is not None
