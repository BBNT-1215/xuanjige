# 玄机阁 · XuanJiGe

<p align="center">
  <strong>自我进化的 AI Agent 协作操作系统</strong>
</p>

<p align="center">
  基于玄机阁制度 · Skill × Role 双库进化 · 制度性审核 · 断点自愈
</p>

<p align="center">
  <a href="#-快速开始"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python"></a>
  <a href="#-快速开始"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License"></a>
  <a href="https://github.com/BBNT-1215/xuanjige/stargazers"><img src="https://img.shields.io/github/stars/BBNT-1215/xuanjige?style=flat" alt="Stars"></a>
  <a href="https://github.com/BBNT-1215/xuanjige/issues"><img src="https://img.shields.io/github/issues/BBNT-1215/xuanjige" alt="Issues"></a>
</p>

---

## 🏛️ 一句话介绍

> 玄机阁是一套**制度驱动的 AI Agent 协作操作系统**——借鉴玄机阁的制度智慧，让 AI Agent 协作从"自由聊天"进化为"制度化运转"，实现可量化、可审计、可进化的自我进化体系。

---

## ✨ 核心差异化对比

| 特性 | CrewAI | AutoGen | MetaGPT | **玄机阁** |
|:---:|:---:|:---:|:---:|:---:|
| **制度性审核** | ❌ | ⚠️ 基础 | ⚠️ 基础 | **✅ 专职审议·可封驳** |
| **真实 Skill 执行** | ⚠️ LLM调用 | ⚠️ LLM调用 | ⚠️ LLM调用 | **✅ 可进化技能卡片** |
| **Skill 进化闭环** | ❌ | ❌ | ❌ | **✅ 量化评分·自动验证** |
| **Role 进化闭环** | ❌ | ❌ | ❌ | **✅ 质量追踪·动态组合** |
| **实时看板** | ⚠️ 需集成 | ❌ | ❌ | **✅ 7列Kanban·像素风** |
| **断点自愈** | ❌ | ❌ | ❌ | **✅ 自动检测+恢复** |
| **三层记忆系统** | ❌ | ❌ | ❌ | **✅ L1任务·L2进化·L3知识** |
| **记忆衰减管理** | ❌ | ❌ | ❌ | **✅ 90天半衰·180天冷存储** |
| **零外部依赖** | 中 | 高 | 高 | **✅ 纯Python** |
| **多 Agent 协作** | ✅ | ✅ | ✅ | **✅ 11个专业Agent** |

> **一句话总结**：CrewAI/AutoGen/MetaGPT 是"让 AI 自己聊"，玄机阁是"让 AI 按制度办事"。

---

## 🚀 快速开始

### 前置条件
- Python 3.10+
- Hermes Agent（已配置）

### 安装

```bash
# 克隆项目
git clone https://github.com/BBNT-1215/xuanjige.git
cd xuanjige

# 安装（推荐：完整安装）
pip install -e ".[all]"          # 核心 + 测试 + Web看板

# 或仅核心安装
pip install -e .                  # 仅核心CLI
pip install -e ".[dev]"           # 核心 + 测试
```

### 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的模型配置
```

### 启动

```bash
# 方式1：cronjob 自动驱动（推荐）
# 玄机阁 Watchdog 每分钟自动扫描并推进所有进行中任务
hermes cron create \
  --name "玄机阁 Watchdog" \
  --every "1m" \
  --command "cd /root/hermestrix && PYTHONPATH=/root/.hermes/hermes-agent python3 workflow/watchdog.py"

# 方式2：手动持续运行（开发调试）
cd /root/hermestrix
PYTHONPATH=/root/.hermes/hermes-agent python3 workflow/watchdog.py --continuous

# 启动 Web 看板（可选，实时监控任务流转）
python dashboard/server.py

# 使用玄机阁
hermes -p xuanjige
```

---

## 🏛️ 架构概览

```
                           ┌───────────────────────────────────┐
                           │          👑 用户                   │
                           │     飞书 · CLI · 任意消息渠道     │
                           └─────────────────┬─────────────────┘
                                             │ 下旨
                           ┌─────────────────▼─────────────────┐
                           │       🤴 承旨 (chengzhi)           │
                           │    分拣：闲聊直接回 / 旨意建任务   │
                           └─────────────────┬─────────────────┘
                                             │ 传旨
                           ┌─────────────────▼─────────────────┐
                           │       📜 机衡 (jiheng)           │
                           │  接旨 → Skill/Role检索 → 派发执行层 │
                           └─────────────────┬─────────────────┘
                                             │ 提交审核
                           ┌─────────────────▼─────────────────┐
                           │       🔍 审议 (shenyi)            │
                           │    四维审议 → 准奏 ✅ / 封驳 🚫    │
                           └───┬───────────────────────────────┘
                               │ 准奏
                    ┌──────────┴──────────┐
                    ▼                     ▼
        ┌───────────────────┐ ┌───────────────────┐
        │    ⚙️ 执行层        │ │  🔬 机研（进化层）  │
        │  技造：开发        │ │  三库守护          │
        │  刑策：质检        │ │  Skill进化执行     │
        │  数算：数据分析    │ │  健康实时监控      │
        │  文册：文档        │ └───────────────────┘
        │  兵戎：部署/安全    │
        └───────────────────┘
                    │                     ▲
                    └─────── 进化闭环 ────┘
```

### 步骤链数据流

```
task创建 → 承旨分拣 → 机衡调度 → 执行层执行 → 审议复核 → 玄档汇总 → 枢鉴终审 → 完成
                                                        │
                                    进化触发 ←──────────┘
```

---

## ✨ 核心特性

### 1. 制度性审核（审议）
- 机衡起草方案后，必须经过审议审议
- 审议可「准奏」或「封驳」（最多3轮，第3轮强制通过）
- **不是可选插件，是架构强制的质量关卡**

### 2. Skill × Role 双库进化闭环
```
任务完成 → 归档L1 → 更新L2评分 → 变化>阈值?
                                        ↓
                              是 → 开启5次观察窗口
                                        ↓
                              均值≥新评分×0.9 → 确认进化
                              均值<新评分×0.85 → 回滚旧版本
```
- Skill库：16个技能卡片，每次任务后 effectiveness 动态更新
- Role库：17个角色，每次任务后 quality_score 动态更新
- EvolutionVerifier 自动验证，防止分数抖动

### 3. 三层记忆系统
```
L1 任务记忆（raw/resolved/cold）
  ↓ 每次任务归档
L2 进化层（SkillStats / RoleStats）
  ↓ 聚合统计
L3 知识库（workflow规则 + 决策公理 + 项目背景）
```
- 记忆不是存储过去，而是服务未来决策
- 90天半衰期 · 180天冷存储 · 自动垃圾回收

### 4. 健康实时监控
| 指标 | 说明 | 阈值方向 |
|------|------|---------|
| skill_avg_effectiveness | Skill库平均有效性 | 越低越差 |
| role_avg_quality | Role库平均质量 | 越低越差 |
| cold_storage_ratio | 冷存储占比 | 越高越差 |
| evolution_stagnation_days | 进化停滞天数 | 越高越差 |
| pending_verifications | 待验证项数量 | 越高越差 |
| skill_conflict_rate | 记忆冲突率 | 越高越差 |

### 5. 断点自愈
- 子Agent执行时，工具调用可能全部成功但输出文件未创建
- 刑策监控断点信号，自动触发恢复流程
- **精修类任务强制使用Python单趟脚本，禁止多次patch**

### 6. 实时看板
- 7列 Kanban：待分拣 → 已派发 → 执行中 → 待审核 → 已完成 → 已归档 → 阻塞
- 像素风众生相监控面板
- 事件驱动实时更新

---

## 👥 Agent 角色说明

玄机阁共有 **11 个专业 Agent**，各司其职：

| 部门 | Agent ID | 职责 | 擅长领域 |
|------|----------|------|---------|
| 🤴 **承旨** | `chengzhi` | 消息分拣、旨意整理 | 闲聊识别、旨意提炼、标题概括 |
| 📜 **机衡** | `jiheng` | 接旨、检索、派发 | Skill/Role检索、任务调度、结果整合 |
| 🔍 **审议** | `shenyi` | 审议、把关、封驳 | 质量评审、风险识别、标准把控 |
| ⚙️ **技造** | `jizao` | 开发、工程、架构 | 功能开发、Bug修复、架构设计 |
| ⚖️ **刑策** | `xingce` | 质检、测试、审计 | 安全扫描、合规检查、代码审计 |
| 📝 **文册** | `diancang` | 文档、规范、内容 | 技术文档、API文档、规范制定 |
| 💰 **数算** | `shusuan` | 数据分析、资源管理 | 数据处理、报表生成、成本分析 |
| ⚔️ **兵戎** | `bingrong` | 部署、安全、监控 | Docker/K8s、安全巡检、监控配置 |
| 🔬 **机研** | `jiyan` | 三库管理、进化引擎 | Skill进化、Role追踪、健康监控 |
| 📊 **玄档** | `zaohuang` | 每日简报、情报汇总 | 定时播报、数据汇总 |
| 🔭 **枢鉴** | `yushi` | 质量审计、合规检查 | 质量红线、流程监督 |

---

## 📁 项目结构

```
xuanjige/
├── workflow/                     # 工作流引擎（核心运转）
│   ├── engine.py                 # 核心调度引擎
│   ├── task_queue.py             # 任务队列（状态机）
│   ├── agent.py                  # Agent基类
│   ├── routing.py                # 路由分发
│   ├── skill_invoker.py          # Skill调用器
│   ├── kanban_step_chain.py      # 看板步骤链
│   └── watchdog.py               # 看门狗（自动推进任务）
│
├── engine/                       # 核心引擎模块
│   ├── memory_manager.py         # L0-L3记忆管理
│   ├── evolution.py              # 进化引擎（EvolutionVerifier）
│   ├── health_monitor.py         # 健康监控
│   ├── conflict_resolver.py      # 记忆矛盾解决
│   ├── decay_service.py          # 衰减管理
│   └── jiyan_agent.py            # 机研常驻进程
│
├── agents/                       # Agent人格定义（11个角色）
│   ├── chengzhi/                 # 承旨·消息分拣
│   ├── jiheng/                   # 机衡·调度派发
│   ├── shenyi/                   # 审议·审核封驳
│   ├── jizao/                    # 技造·开发工程
│   ├── xingce/                   # 刑策·质检审计
│   ├── diancang/                 # 文册·文档规范
│   ├── shusuan/                  # 数算·数据分析
│   ├── bingrong/                 # 兵戎·部署安全
│   ├── jiyan/                    # 机研·进化守护
│   ├── zaohuang/                 # 玄档·情报枢纽
│   ├── qitian/                   # 枢观·战略观察
│   └── yushi/                    # 枢鉴·质量审计
│
├── skills/                       # Skill技能库（16个可进化技能）
│   ├── skill_routing/            # 旨意分拣路由
│   ├── skill_code_review/        # 代码审查
│   ├── skill_debugging/          # 调试排障
│   ├── skill_architecture/       # 架构设计
│   └── ...（更多技能卡片）
│
├── scripts/                      # 工具脚本
│   ├── kanban.py                 # 看板CLI
│   ├── event_bus.py              # 事件总线
│   ├── three_libraries.py        # 三库管理
│   ├── recovery.py               # 断点自愈
│   └── run_loop.py               # 主循环
│
├── dashboard/                    # Web看板
│   ├── server.py                 # Web服务器（REST API）
│   └── index.html                # 看板主页
│
├── three_libs/                   # 三库存储
│   ├── memory/                   # L1任务记忆
│   ├── skills/                   # L2技能进化数据
│   ├── roles/                    # L2角色进化数据
│   └── knowledge/                # L3知识库
│
├── data/                         # 运行时数据
│   ├── tasks.json                # 任务数据
│   ├── skill_index.json          # Skill索引
│   └── events.json               # 事件日志
│
├── hermestrix_cli.py             # 主CLI入口
├── pyproject.toml                # 项目配置
├── SKILL.md                      # Skill标准格式
├── ROLE.md                       # Role标准格式
├── ARCHITECTURE.md               # 架构详细文档
└── README.md                    # 本文档
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/BBNT-1215/xuanjige.git
cd xuanjige

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[all]"

# 运行测试
pytest

# 代码格式化
ruff check --fix .
```

### 贡献方式

1. **Fork** 本仓库
2. **创建特性分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **创建 Pull Request**

### 贡献范围

- 🐛 Bug 修复
- ✨ 新功能开发
- 📚 文档改进
- 🧪 测试覆盖
- 🎨 代码格式化
- 🌍 国际化

---

## 🙏 致谢

**本项目直接受 [cft0808/edict](https://github.com/cft0808/edict)（15.7k ⭐）启发**—— edict 是目前最完整的玄机阁框架 AI Agent 实现，奠定了"制度性审核 + 实时看板"的核心范式。本项目在 edict 基础上进行 Hermes Agent 原生适配，并新增断点自愈、三库分离、进化闭环等工程实践。

设计参考：
- [cft0808/edict](https://github.com/cft0808/edict) — 玄机阁框架完整实现
- [agent-governance-design skill](https://github.com/lijigang/ljg-skills) — 玄机阁框架方法论沉淀

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件
