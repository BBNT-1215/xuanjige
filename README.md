# 玄机阁 · XuanJiGe

<p align="center">
  <strong>自我进化的 AI Agent 协作操作系统</strong>
</p>

<p align="center">
  基于三省六部制 · Skill × Role 双库进化 · 三层记忆系统 · 健康实时自愈
</p>

<p align="center">
  <a href="#-架构">🏛️ 架构</a> ·
  <a href="#-快速开始">🚀 快速开始</a> ·
  <a href="#-核心特性">✨ 特性</a> ·
  <a href="#-项目结构">📁 结构</a> ·
  <a href="#-玄机阁与三省六部制对照">⚖️ 对照</a>
</p>

---

## 🙏 致谢

**本项目直接受 [cft0808/edict](https://github.com/cft0808/edict)（15.7k ⭐）启发**—— edict 是目前最完整的三省六部制 AI Agent 实现，奠定了"制度性审核 + 实时看板"的核心范式。本项目在 edict 基础上进行 Hermes Agent 原生适配，并新增断点自愈、三库分离、进化闭环等工程实践。

设计参考：
- [cft0808/edict](https://github.com/cft0808/edict) — 三省六部制完整实现
- [agent-governance-design skill](https://github.com/lijigang/ljg-skills) — 三省六部制方法论沉淀

---

## 🤔 为什么是玄机阁？

大多数 Multi-Agent 框架的套路是：

> *"来，你们几个 AI 自己聊，聊完把结果给我。"*

然后你拿到一坨不知道经过了什么处理的结果，无法复现，无法审计，无法干预。

**玄机阁的思路完全不同** —— 我们在存在 1400 年的三省六部制度上，为 AI Agent 加上了可量化、可进化、可自愈的记忆与调度系统：

```
用户 → 太子(分拣) → 中书省(规划) → 门下省(审核) → 尚书省(派发) → 六部(执行)
                                                          ↓
                                                    玄机阁进化引擎
                                                    Skill库 · Role库
                                                    健康监控 · 衰减管理
```

这不是花哨的 metaphor，这是**真正的分权制衡 + 系统进化**：

| | CrewAI | MetaGPT | AutoGen | **玄机阁** |
|:---:|:---:|:---:|:---:|:---:|
| **制度性审核** | ❌ | ⚠️ | ⚠️ | **✅ 门下省专职·可封驳** |
| **Skill进化闭环** | ❌ | ❌ | ❌ | **✅ 量化评分·自动验证** |
| **Role进化闭环** | ❌ | ❌ | ❌ | **✅ 质量追踪·动态更新** |
| **健康实时监控** | ❌ | ❌ | ❌ | **✅ 六维度自动告警** |
| **三层记忆系统** | ❌ | ❌ | ❌ | **✅ L1任务·L2进化·L3知识** |
| **记忆衰减管理** | ❌ | ❌ | ❌ | **✅ 90天半衰·180天冷存储** |
| **断点自愈** | ❌ | ❌ | ❌ | **✅ 自动检测+恢复** |
| **零外部依赖** | 中 | 高 | 中 | **✅ 纯Python** |

> **核心差异：制度性审核 + Skill/Role双库进化 + 健康实时自愈 + 零外部依赖**

---

## ⚖️ 玄机阁与三省六部制对照

| 维度 | 传统三省六部制 | 玄机阁 |
|---|---|---|
| **记忆载体** | 人脑（官员脑子里） | 三层可检索记忆系统（L1任务/L2进化/L3知识） |
| **经验传承** | 师徒/官员交替（人走经验失传） | Skill库量化卡片（可传承、可进化） |
| **派发依据** | 官员经验与直觉 | L1历史相似案例 + L2 Skill有效性 + L2 Role质量 + L3领域知识 |
| **质量监督** | 御史弹劾（滞后+主观） | 健康监控实时预警（六维度自动化） |
| **进化机制** | 换人（被动） | 进化引擎（主动）—— 评分变化→5次观察窗口→确认或回滚 |
| **通信机制** | 奏折同步流转（一步卡住全停） | 事件总线异步并行（高效解耦） |
| **记忆衰减** | 无 | 90天半衰期 → 180天冷存储 → 自动垃圾回收 |
| **系统自愈** | 无 | 刑部监控断点信号，自动触发恢复流程 |

**一句话**：传统三省六部是人的官僚体系，**玄机阁是能让 AI Agent 自己积累经验、自动进化、实时自愈的操作系统**。

---

## ⚖️ XuanJiGe vs Traditional Three Departments and Six Ministries

| Dimension | Traditional Three Departments and Six Ministries | XuanJiGe |
|---|---|---|
| **Memory** | Human brains (officials' minds) | Three-tier searchable memory system (L1 Task / L2 Evolution / L3 Knowledge) |
| **Experience Transfer** | Master-apprentice / official succession (knowledge lost with people) | Skill library with quantified cards (transferable, evolvable) |
| **Dispatch Basis** | Officials' experience and intuition | L1 similar cases + L2 Skill effectiveness + L2 Role quality + L3 domain knowledge |
| **Quality Oversight** | Censor impeachment (lagged + subjective) | Real-time health monitoring (6-dimension automated) |
| **Evolution Mechanism** | Personnel change (passive) | Evolution engine (proactive) — score change → 5-observation window → confirm or rollback |
| **Communication** | Synchronous memorial流转 (one bottleneck stalls all) | Event bus async parallel (efficient decoupled) |
| **Memory Decay** | None | 90-day half-life → 180-day cold storage → automatic garbage collection |
| **Self-healing** | None | Xingbu monitors breakpoints, auto-triggers recovery |

**One-liner**: Traditional Three Departments and Six Ministries is a human bureaucracy; **XuanJiGe is an operating system that lets AI Agents accumulate experience, evolve automatically, and self-heal in real time.**

---

## 🏛️ 架构 / Architecture

```
                           ┌───────────────────────────────────┐
                           │          👑 用户                  │
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
                           │  接旨 → Skill/Role检索 → 派发六部  │
                           └─────────────────┬─────────────────┘
                                             │ 提交审核
                           ┌─────────────────▼─────────────────┐
                           │       🔍 审议 (shenyi)            │
                           │    审议方案 → 准奏 / 封驳 🚫        │
                           └───┬───────────────────────────────┘
                               │ 准奏 ✅
                    ┌──────────┴──────────┐
                    ▼                     ▼
        ┌───────────────────┐ ┌───────────────────┐
        │    六部（执行层）    │ │  机研（进化层）    │
        │  技造：开发         │ │  三库守护          │
        │  刑策：质检         │ │  Skill进化执行     │
        │  文册：文档         │ │  健康实时监控      │
        │  数算：数据分析     │ └───────────────────┘
        │  兵戎：部署/安全    │
        └───────────────────┘
```

### 各省部职责 / Departments

| 部门 | Agent ID | 职责 | 擅长领域 |
|------|----------|------|---------|
| 🤴 **承旨** | `chengzhi` | 消息分拣、旨意整理 | 闲聊识别、旨意提炼、标题概括 |
| 📜 **机衡** | `jiheng` | 接旨、检索、派发 | Skill/Role检索、任务调度、结果整合 |
| 🔍 **审议** | `shenyi` | 审议、把关、封驳 | 质量评审、风险识别、标准把控 |
| ⚙️ **技造** | `jizao` | 开发、工程、架构 | 功能开发、Bug修复、架构设计 |
| ⚖️ **刑策** | `xingce` | 质检、测试、审计 | 安全扫描、合规检查、代码审计 |
| 📝 **文册** | `diancang` | 文档、规范、内容 | 技术文档、API 文档、规范制定 |
| 💰 **数算** | `shusuan` | 数据分析、资源管理 | 数据处理、报表生成、成本分析 |
| ⚔️ **兵戎** | `bingrong` | 部署、安全、监控 | Docker/K8s、安全巡检、监控配置 |
| 🔬 **机研** | `jiyan` | 三库管理、进化引擎 | Skill进化、Role追踪、健康监控 |
| 🌅 **早朝** | `zaohuang` | 每日简报、情报汇总 | 定时播报、数据汇总 |
| 🔭 **枢观** | `qitian` | 趋势分析、战略观察 | 竞品追踪、技术预测 |
| 📋 **御史** | `yushi` | 质量审计、合规检查 | 质量红线、流程监督 |

---

## 🚀 快速开始 / Quick Start

### 前置条件 / Prerequisites
- Python 3.10+
- Hermes Agent（已配置）

### 安装 / Installation

```bash
git clone https://github.com/BBNT-1215/xuanjige.git
cd xuanjige
pip install -e ".[all]"          # 完整安装（含测试+Web看板）
# 或者仅核心安装：
pip install -e .                  # 仅核心CLI
pip install -e ".[dev]"          # 核心 + 测试依赖
```

### 配置 / Configuration

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的模型配置
```

### 启动 / Launch

```bash
# 启动看板服务器
python dashboard/server.py

# 在另一个终端，启动任务刷新循环
python scripts/run_loop.py

# 使用玄机阁
hermes -p xuanjige
```

---

## ✨ 核心特性 / Core Features

### 1. 制度性审核（门下省）Institutional Review
- 中书省起草方案后，必须经过门下省审议
- 门下省可「准奏」或「封驳」（最多3轮，第3轮强制通过）
- **不是可选插件，是架构强制的质量关卡**

### 2. Skill × Role 双库进化闭环 Self-Evolving Skill & Role Libraries
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
- 进化引擎自动验证，防止分数抖动

### 3. 三层记忆系统 Three-Tier Memory System
```
L1 任务记忆（raw/resolved/cold）
  ↓ 每次任务归档
L2 进化层（SkillStats / RoleStats）
  ↓ 聚合统计
L3 知识库（workflow规则 + 决策公理 + 项目背景）
```
- 记忆不是存储过去，而是服务未来决策
- 90天半衰期 · 180天冷存储 · 自动垃圾回收

### 4. 健康实时监控 Real-Time Health Monitoring
| 指标 | 说明 | 阈值方向 |
|------|------|---------|
| skill_avg_effectiveness | Skill库平均有效性 | 越低越差 |
| role_avg_quality | Role库平均质量 | 越低越差 |
| cold_storage_ratio | 冷存储占比 | 越高越差 |
| evolution_stagnation_days | 进化停滞天数 | 越高越差 |
| pending_verifications | 待验证项数量 | 越高越差 |
| skill_conflict_rate | 记忆冲突率 | 越高越差 |

### 5. 断点自愈 Breakpoint Self-Healing
- 子Agent执行时，工具调用可能全部成功但输出文件未创建
- 刑部监控断点信号，自动触发恢复流程
- **精修类任务强制使用Python单趟脚本，禁止多次patch**

### 6. 事件驱动通信 Event-Driven Communication
- 各Agent间通过EventBus通信
- 支持异步派发、并行执行、结果汇总

---

## 📁 项目结构 / Project Structure

```
xuanjige/
├── agents/                     # Agent人格定义（SOUL.md）
│   ├── chengzhi/               # 承旨·消息分拣
│   ├── jiheng/                # 机衡·调度派发
│   ├── shenyi/                 # 审议·审核封驳
│   ├── jizao/                 # 技造·开发工程
│   ├── xingce/                 # 刑策·质检审计
│   ├── diancang/               # 文册·文档规范
│   ├── shusuan/               # 数算·数据分析
│   ├── bingrong/               # 兵戎·部署安全
│   ├── jiyan/                 # 机研·进化引擎
│   ├── zaohuang/               # 早朝·情报枢纽
│   ├── qitian/                 # 枢观·战略观察
│   └── yushi/                 # 御史·质量审计
├── skills/                     # Skill技能库
│   ├── skill_routing/         # 旨意分拣路由
│   ├── skill_skill_routing/   # Skill智能检索
│   ├── skill_role_dispatch/   # Role智能派发
│   ├── skill_architecture/    # 架构设计
│   ├── skill_code_review/     # 代码审查
│   ├── skill_debugging/       # 调试排障
│   ├── skill_data_analysis/   # 数据分析
│   ├── skill_reporting/       # 报告撰写
│   ├── skill_trend_analysis/  # 趋势分析
│   ├── skill_devops/          # 运维自动化
│   ├── skill_monitoring/      # 监控配置
│   ├── skill_incident_response/# 故障响应
│   ├── skill_database_optimization/# 数据库优化
│   ├── skill_api_gateway/     # API网关
│   ├── skill_coding/           # 代码编写
│   └── skill_qa_testing/      # 质量测试
├── engine/                     # 核心引擎
│   ├── memory_manager.py      # L0-L3记忆管理
│   ├── evolution.py           # 进化引擎+验证闭环
│   ├── health_monitor.py      # 健康监控
│   ├── conflict_resolver.py   # 记忆矛盾解决
│   ├── decay_service.py       # 衰减管理
│   └── jiyan_agent.py         # 机研常驻进程
├── three_libs/                # 三库存储
│   ├── memory/                # L1任务记忆（raw/resolved/cold）
│   ├── skills/                # L2技能进化数据
│   ├── roles/                 # L2角色进化数据
│   └── knowledge/             # L3知识库（rules/axioms/context）
├── scripts/
│   ├── kanban.py              # 看板CLI
│   ├── event_bus.py           # 事件总线
│   ├── three_libraries.py     # 三库管理CLI
│   ├── recovery.py            # 断点自愈
│   └── run_loop.py            # 主循环
├── dashboard/
│   ├── server.py              # Web看板服务器
│   └── index.html             # 看板主页
├── tests/                     # 测试套件（30/30 PASS）
├── SKILL.md                   # Skill标准格式定义
├── ROLE.md                    # Role标准格式定义
├── ARCHITECTURE.md            # 架构详细文档
├── hermestrix_cli.py          # 主CLI
├── pyproject.toml
├── CHANGELOG.md
└── README.md
```

---

## 📐 设计原则 / Design Principles

### 核心原则 / Core Principles

1. **从本质问题出发，不套模板**
   - 四个本质问题：意图传递、能力匹配、质量验证、持续进化
   - 任何架构组件必须回答：它解决哪个本质问题？

2. **每个组件必须回答三个问题**
   - 它解决哪个本质问题？
   - AI实际能力是否匹配？
   - 如果AI能力不足，如何缓解？

3. **三库必须分离**
   - 混合会导致检索质量差、更新逻辑混乱、扩展困难

4. **子Agent任务描述必须包含完整路径**
   - 工作目录 + 输入文件完整路径 + 输出文件完整路径
   - 禁止依赖搜索发现文件

5. **精修类任务用Python单趟脚本**
   - 禁止多次patch，中断=全部成果丢失

6. **进化闭环是架构的一部分，不是附加功能**

---

## 📄 License

MIT License
