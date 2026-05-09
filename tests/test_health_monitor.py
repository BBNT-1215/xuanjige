"""
Tests for engine/health_monitor.py
"""

import pytest
import pathlib
import tempfile
import os
import sys

_TEST_HOME = pathlib.Path(tempfile.mkdtemp(prefix="hermestrix_test_"))
os.environ["HERMESTRIX_HOME"] = str(_TEST_HOME)
sys.path.insert(0, str(_TEST_HOME))

from engine.health_monitor import HealthMonitor, HealthReport, Alert
from engine.memory_manager import MemoryManager


@pytest.fixture
def hm():
    return HealthMonitor()


class TestHealthMonitor:
    """HealthMonitor: system health checking"""

    def test_check_all_returns_health_report(self, hm):
        """返回HealthReport对象"""
        report = hm.check_all()
        assert isinstance(report, HealthReport)
        # overall: ok/warn/critical
        assert report.overall in ("ok", "warn", "critical")
        assert isinstance(report.alerts, list)

    def test_report_has_checks(self, hm):
        """报告包含checks字典"""
        report = hm.check_all()
        assert isinstance(report.checks, dict)
        # 6个指标
        assert len(report.checks) == 6

    def test_no_critical_alerts_when_healthy(self, hm):
        """新系统健康时无critical告警"""
        report = hm.check_all()
        critical = [a for a in report.alerts if a.level == "critical"]
        assert len(critical) == 0

    def test_checks_has_expected_metrics(self, hm):
        """6个健康指标都存在"""
        report = hm.check_all()
        expected_metrics = {
            "skill_avg_effectiveness",
            "role_avg_quality",
            "cold_storage_ratio",
            "evolution_stagnation_days",
            "pending_verifications",
            "skill_conflict_rate",
        }
        assert expected_metrics == set(report.checks.keys())

    def test_each_check_has_value_and_status(self, hm):
        """每个check包含value和status"""
        report = hm.check_all()
        for metric, check in report.checks.items():
            assert "value" in check, f"{metric} missing value"
            assert "status" in check, f"{metric} missing status"


class TestAlert:
    """Alert dataclass-like class"""

    def test_alert_fields(self):
        """Alert有所有必要字段"""
        alert = Alert(
            level="warn",
            metric="role_avg_quality",
            message="Role平均质量偏低",
            value=0.62,
            threshold={"warn": 0.7},
        )
        assert alert.level == "warn"
        assert alert.metric == "role_avg_quality"
        assert alert.value == 0.62


class TestHealthReport:
    """HealthReport dataclass"""

    def test_report_requires_checks(self):
        """HealthReport需要checks参数"""
        report = HealthReport(
            timestamp="2026-05-09T00:00:00Z",
            overall="ok",
            checks={},
            alerts=[],
        )
        assert report.overall == "ok"
        assert report.checks == {}
        assert len(report.alerts) == 0

    def test_recommendations_optional(self):
        """recommendations有默认值"""
        report = HealthReport(
            timestamp="2026-05-09T00:00:00Z",
            overall="ok",
            checks={},
            alerts=[],
        )
        assert isinstance(report.recommendations, list)
