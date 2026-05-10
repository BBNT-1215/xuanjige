# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-09

### Added

#### Core Engine (`engine/`)
- `memory_manager.py` — 四层记忆系统（L0瞬时/L1任务/L2进化/L3知识）
- `conflict_resolver.py` — L1记忆矛盾检测与解决（时间加权+方差检测+根因分析）
- `health_monitor.py` — 6维度系统健康监控（自动阈值推断）
- `decay_service.py` — 记忆衰减管理（90天半衰期+180天冷存储+垃圾回收）
- `evolution.py` — EvolutionEngine进化引擎 + EvolutionVerifier验证闭环
- `libu_agent.py` — 机研常驻进程（EventBus监听+定时健康检查+衰减管理）

#### Skill库（14个）
- orchestration: `skill_routing`, `skill_skill_routing`, `skill_role_dispatch`
- engineering: `skill_architecture`, `skill_code_review`, `skill_debugging`
- analysis: `skill_data_analysis`, `skill_reporting`, `skill_trend_analysis`
- operation: `skill_devops`, `skill_monitoring`, `skill_incident_response`, `skill_database_optimization`, `skill_api_gateway`

#### Role库（17个）
- 协调层: `chengzhi`, `jiheng`, `shenyi`, `jiheng`
- 执行层: `shusuan`, `jizao`, `bingrong`, `xingce`, `diancang`, `jiyan`
- 扩展: `bishou` (笔受), `yushi` (枢鉴), `jiedushi` (节度使), `silium` (司礼监), `xingke` (刑科)
- 扩展: `bishou` (笔受), `yushi` (枢鉴), `jiedushi` (节度使), `silium` (司礼监), `xingke` (刑科)

#### CLI工具链 (`hermestrix_cli.py`)
- `hermestrix skill` — --list / --inspect / --search
- `hermestrix role` — --list / --inspect / --search
- `hermestrix evolution` — --status / --rollback
- `hermestrix task` — --create / --list / --state / --flow / --show
- `hermestrix health` — --check / --monitor
- `hermestrix diancang` — --start / --stop / --status / --once

#### 测试套件 (`tests/`)
- `test_memory_manager.py` — 17 tests (L1/L2 CRUD)
- `test_evolution.py` — 11 tests (验证闭环+端到端)
- `test_health_monitor.py` — 9 tests (健康检查+阈值)

#### CI/CD
- `.github/workflows/ci.yml` — pytest + ruff + CLI smoke test + build check
- Issue templates (bug report / feature request)

### Fixed
- `memory_manager.archive_task`: 路径分配bug（bad→COLD_DIR, medium→RESOLVED_DIR）
- `memory_manager._update_memory_index`: skills_used 存储完整dict（含quality_score）
- `memory_manager._get_records_for_skill`: 兼容新旧skills_used格式
- `evolution.py`: verification_triggered字段访问路径bug
- `evolution.py`: rollback事件未emit
- `libu_agent.emit`: _atomic_json_update对None值处理

### Changed
- 进化验证阈值: confirm≥新评分×0.9, rollback<新评分×0.85
- 健康监控阈值方向自动推断（higher_is_worse）

### Documentation
- `CONTRIBUTING.md` — 完整开发指南
- `HERMESTRIX-v3-FINAL-PLAN.md` — 1823行完整工程方案
- `SKILL.md` / `ROLE.md` — 标准编撰格式
- `ARCHITECTURE.md` — 系统架构文档
