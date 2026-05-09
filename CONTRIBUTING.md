# 贡献指南

欢迎贡献 Hermestrix！

## 项目愿景

Hermestrix 是一个自我进化的 AI Agent 协作操作系统，以中国古代三省六部制为组织隐喻，构建能够稳定执行、持续自我进化、感知自身健康的工程产品级多Agent协作框架。

## 快速开始

```bash
git clone https://github.com/BBNT-1215/hermestrix.git
cd hermestrix
pip install -e ".[dev]"    # 安装依赖（含测试套件）
pytest tests/ -v            # 运行测试
hermestrix skill --list     # 验证CLI
```

## 开发环境

- Python >= 3.10
- HERMESTRIX_HOME 环境变量指向项目根目录（默认自动检测）

```bash
export HERMESTRIX_HOME=$PWD
```

## 项目结构

```
hermestrix/
├── engine/          # 核心引擎（memory_manager, evolution, health_monitor...）
├── agents/          # Role库（SOUL.md + METADATA.yaml）
├── skills/          # Skill库（SKILL.md + METADATA.yaml + scripts/）
├── scripts/         # CLI脚本（kanban, event_bus, three_libraries...）
├── hermestrix_cli.py # 主CLI入口
└── tests/           # 测试套件
```

## 添加新 Skill

```bash
# 在 skills/ 下创建 {skill_id}/ 目录
mkdir skills/skill_my_feature/
# 添加标准文件：
# - SKILL.md       （YAML frontmatter + markdown正文）
# - METADATA.yaml  （元数据）
# - scripts/main.py （CLI工具）
```

参考 `SKILL.md` 标准格式（项目根目录）。

## 添加新 Role

```bash
mkdir agents/my_role/
# 添加：
# - SOUL.md        （Role定义）
# - METADATA.yaml  （元数据，含 skills.required 和 collaborates_with）
```

参考 `ROLE.md` 标准格式（项目根目录）。

## 测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行带覆盖率
pytest tests/ -v --cov=engine --cov-report=term-missing

# 运行特定文件
pytest tests/test_evolution.py -v
```

测试规范：
- 每个 `engine/*.py` 模块对应 `tests/test_*.py`
- 使用临时目录隔离测试数据（`tempfile.mkdtemp`）
- 设置独立的 `HERMESTRIX_HOME` 环境变量

## 提交规范（Conventional Commits）

```
feat:     新功能
fix:      修复bug
docs:     文档更新
refactor: 重构（不改变功能）
test:     测试相关
chore:    工具、构建、依赖
```

示例：
```bash
git commit -m "feat(engine): 添加进化验证闭环
git commit -m "fix(kanban): 修复flow命令状态同步
git commit -m "test(evolution): 添加验证窗口测试
```

## GitHub Actions

所有PR自动触发CI流水线（`pytest` + `ruff` + CLI smoke test）。

main分支推送自动执行完整构建检查。

## 许可证

MIT License（参见 LICENSE 文件）
