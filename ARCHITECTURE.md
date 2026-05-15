# 玄机阁架构文档

> 玄机阁 AI Agent 协作框架 — 基于 Skill 进化与 Role 组合的自我进化体系 | 适配：Hermes Agent 原生

---

## 一、核心设计理念

玄机阁是一套**制度驱动的 AI Agent 协作操作系统**，以玄机阁制度为蓝本，将 Multi-Agent 协作从"自由聊天"提升为"制度化运转"：

| 现实隐喻 | 映射到玄机阁 | 职责 |
|---------|------------|------|
| 🏛️ **皇城** | 玄机阁 | 整个系统的运转中枢 |
| 📜 **圣旨** | Task | 用户提交的旨意，每条任务即一道圣旨 |
| 👤 **官员** | Agent | 11 个各司其职的 Agent，各掌一职 |
| 🗄️ **军机处** | Kanban | 任务流转的实时看板上，步步可见 |

**核心理念**：不是让 Agents 自由聊天，而是用制度化的分权、制衡、审核、进化机制，让 AI Agent 协作可量化、可审计、可进化。

---

## 二、架构分层图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              👑 用户（旨意入口）                              │
│                         飞书 · CLI · 任意消息渠道                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ 下旨
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     📋 协调层（承旨 / 机衡 / 审议）                      │   │
│  │                                                                       │   │
│  │   🤴 承旨     ── 消息分拣：闲聊 → 直接回 │ 旨意 → 创建任务                │   │
│  │   📜 机衡     ── 接旨 → Skill/Role检索 → 派发执行层                     │   │
│  │   🔍 审议     ── 四维审议（可行性/完整性/风险/代价）→ 准奏 或 封驳        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ 准奏
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     ⚙️ 执行层（技造 / 刑策 / 数算 / 文册 / 兵戎）          │   │
│  │                                                                       │   │
│  │   ⚙️ 技造  ── 开发工程 · 功能实现 · Bug修复 · 架构设计                   │   │
│  │   ⚖️ 刑策  ── 质检测试 · 安全扫描 · 合规检查                            │   │
│  │   💰 数算  ── 数据分析 · 报表生成 · 资源管理                            │   │
│  │   📝 文册  ── 文档撰写 · API文档 · 规范制定                            │   │
│  │   ⚔️ 兵戎  ── 部署运维 · Docker/K8s · 安全监控                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
┌───────────────────────────────┐     ┌───────────────────────────────────┐
│     🔬 情报层（玄档 / 枢鉴）      │     │         🔬 机研（进化守护者）          │
│                               │     │                                   │
│   📊 玄档 ── 情报汇总 · 每日简报  │     │   三库守护者                        │
│   🔭 枢鉴 ── 质量审计 · 终审把关  │     │   Skill进化执行                     │
│                               │     │   Role进化追踪                      │
└───────────────────────────────┘     │   健康监控自愈                      │
                                        └───────────────────────────────────┘
```

---

## 三、步骤链数据流

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   task创建                                                                   │
│      │                                                             ▲        │
│      ▼                                                             │        │
│   承旨分拣  ── 旨意识别 · 闲聊过滤 · 任务拆解                            │        │
│      │                                                             │        │
│      ▼                                                             │        │
│   机衡调度  ── Skill检索 · Role组合 · 任务派发                          │        │
│      │                                                             │        │
│      ▼                                                             │        │
│   执行层执行 ── ⚙️技造 ⚖️刑策 💰数算 📝文册 ⚔️兵戎 并行/串行                │        │
│      │                                                             │        │
│      ▼                                                             │        │
│   审议复核  ── 四维审议 · 准奏/封驳 · 最多3轮                           │        │
│      │                                                             │        │
│      ▼                                                             │        │
│   玄档汇总  ── 执行结果整合 · 情报汇总                                  │        │
│      │                                                             │        │
│      ▼                                                             │        │
│   枢鉴终审  ── 质量审计 · 合规检查 · 通过则完成                         │        │
│      │                                                             │        │
│      ▼                                                             │        │
│   ✅ 完成  ── 任务标记done · 触发进化引擎                              │        │
│                                                                     │        │
│   ─────────────────────────────────────────────────────────────    │        │
│                                                                     │        │
│   进化触发：任务完成 → 机研监听 → 进化分析 → Skill库更新 → Role库更新 ─┘        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 状态机

```
PENDING(待分拣) → ASSIGNED(已派发) → RUNNING(执行中)
                                          ↓
                                 REVIEW(待审核) ← 退回重做
                                          ↓
                                     DONE(已完成)
```

---

## 四、Skill 进化机制

### 4.1 EvolutionVerifier 核心算法

```python
# 有效性评分公式
effectiveness = (
    success_rate × 0.30 +      # 成功率贡献
    recency × 0.15 +            # 时效性
    historical_effectiveness × 0.40 +  # 历史有效度
    complexity × 0.15           # 复杂度适配
)

# 进化触发条件
if abs(effectiveness_change) > 0.05:
    version += 1
    evolve_count += 1
```

### 4.2 进化闭环流程

```
任务完成
    │
    ├──▶ 记录执行结果
    │         │
    │         ├──▶ 成功 → success_count++
    │         └──▶ 失败 → failure_patterns++ 且 failure_count++
    │
    ├──▶ 更新 Skill 评分
    │         │
    │         └──▶ 变化 > 0.05 → 开启5次观察窗口
    │                            │
    │                            ├──▶ 均值 ≥ 新评分 × 0.9 → 确认进化
    │                            └──▶ 均值 < 新评分 × 0.85 → 回滚旧版本
    │
    └──▶ 更新 Role 统计
              │
              └──▶ quality_score 动态调整
```

### 4.3 Skill 检索算法

```python
match_score = (
    Skill.effectiveness × 0.50    # 有效度贡献（主导）
  + task_feature_hit × 0.1        # 任务特征命中
  + tag_hit × 0.1                  # 标签匹配
  + min(success_count / 100, 0.2)  # 经验加成（上限0.2）
)
```

### 4.4 Skill 数据结构

```json
{
  "id": "skill_code_review",
  "name": "Python代码审查",
  "domain": "开发",
  "effectiveness": 0.85,
  "success_count": 47,
  "failure_count": 8,
  "version": 3,
  "last_evolved": "2026-05-09T11:40:00",
  "best_practices": [
    "检查空指针引用",
    "检查异常捕获完整性",
    "检查类型提示覆盖率"
  ],
  "failure_patterns": [
    {"pattern": "异步代码遗漏await", "occurrences": 3}
  ],
  "applicable_tasks": ["Python项目", "多人协作"],
  "inapplicable_tasks": ["简单脚本(<100行)"]
}
```

---

## 五、Role 库与组合推荐

### 5.1 Role 数据结构

```json
{
  "role_id": "jizao",
  "role_name": "技造",
  "version": 2,
  "task_stats": {
    "assigned_count": 38,
    "success_count": 34,
    "failure_count": 4,
    "avg_duration_minutes": 45
  },
  "required_skills": ["skill_code_review"],
  "optional_skills": ["skill_architecture_design"],
  "combined_with": {"xingce": 15, "jiyan": 8},
  "avoid_combination": ["bingrong"],
  "task_type_distribution": {
    "开发": 28, "重构": 7, "架构": 3
  },
  "quality_score": 0.82
}
```

### 5.2 组合推荐算法

```python
recommendation_score = (
    Role.quality_score × 0.40    # 质量分数
  + success_rate × 0.30          # 成功率
  + min(execution_count / 100, 0.20)  # 经验加成
  + task_type_match × 0.10       # 任务类型匹配
)
```

---

## 六、目录结构

```
xuanjige/                              # 玄机阁根目录
│
├── workflow/                          # 工作流引擎（核心运转）
│   ├── engine.py                      # 核心调度引擎
│   ├── task_queue.py                  # 任务队列（状态机）
│   ├── agent.py                       # Agent基类（11个Agent统一run接口）
│   ├── routing.py                     # 路由分发
│   ├── skill_invoker.py               # Skill调用器
│   ├── kanban_step_chain.py           # 看板步骤链
│   └── watchdog.py                    # 看门狗（自动推进任务）
│
├── engine/                            # 核心引擎模块
│   ├── memory_manager.py              # L0-L3记忆管理
│   ├── evolution.py                   # 进化引擎（EvolutionVerifier）
│   ├── health_monitor.py              # 健康监控
│   ├── conflict_resolver.py           # 记忆矛盾解决
│   ├── decay_service.py               # 衰减管理（90天半衰）
│   └── jiyan_agent.py                 # 机研常驻进程
│
├── agents/                            # Agent人格定义（11个角色）
│   ├── chengzhi/                      # 承旨·消息分拣
│   │   ├── SOUL.md                    # 角色定义
│   │   └── METADATA.yaml              # 角色元数据
│   ├── jiheng/                        # 机衡·调度派发
│   ├── shenyi/                        # 审议·审核封驳
│   ├── jizao/                         # 技造·开发工程
│   ├── xingce/                        # 刑策·质检审计
│   ├── diancang/                      # 文册·文档规范
│   ├── shusuan/                       # 数算·数据分析
│   ├── bingrong/                      # 兵戎·部署安全
│   ├── jiyan/                         # 机研·进化守护
│   ├── zaohuang/                      # 玄档·情报枢纽
│   ├── qitian/                        # 枢观·战略观察
│   └── yushi/                         # 枢鉴·质量审计
│
├── skills/                            # Skill技能库（可进化）
│   ├── skill_routing/                 # 旨意分拣路由
│   ├── skill_code_review/             # 代码审查
│   ├── skill_debugging/               # 调试排障
│   ├── skill_architecture/            # 架构设计
│   ├── skill_data_analysis/           # 数据分析
│   └── ...（16个技能卡片）
│
├── scripts/                            # 工具脚本
│   ├── kanban.py                      # 看板CLI
│   ├── event_bus.py                   # 事件总线
│   ├── three_libraries.py             # 三库管理
│   ├── recovery.py                     # 断点自愈
│   └── run_loop.py                    # 主循环
│
├── dashboard/                          # Web看板
│   ├── server.py                       # Web服务器（REST API）
│   └── index.html                      # 7列任务看板
│
├── three_libs/                         # 三库存储
│   ├── memory/                         # L1任务记忆（raw/resolved/cold）
│   ├── skills/                         # L2技能进化数据
│   ├── roles/                          # L2角色进化数据
│   └── knowledge/                      # L3知识库（rules/axioms/context）
│
├── data/                               # 运行时数据
│   ├── tasks.json                      # 任务数据
│   ├── skill_index.json                # Skill索引
│   ├── role_index.json                 # Role索引
│   └── events.json                     # 事件日志
│
├── hermestrix_cli.py                   # 主CLI入口
├── pyproject.toml                      # 项目配置
├── SKILL.md                            # Skill标准格式定义
├── ROLE.md                             # Role标准格式定义
├── ARCHITECTURE.md                      # 本文档
├── README.md                           # 项目概览
└── CHANGELOG.md                        # 变更日志
```

---

## 七、永久 Agent vs 临时 Subagent

| 角色 | Agent ID | 类型 | 理由 |
|------|----------|------|------|
| 🤴 承旨 | `chengzhi` | 常驻 | 消息分拣、旨意入口，需要跨对话记忆 |
| 🔬 机研 | `jiyan` | 常驻 | 三库守护者，需要持续积累进化 |
| 📜 机衡 | `jiheng` | 临时 | 调度型，一次任务一方案 |
| 🔍 审议 | `shenyi` | 临时 | 审议型，规则固定 |
| ⚙️ 技造 | `jizao` | 临时 | 执行型，专业分工 |
| ⚖️ 刑策 | `xingce` | 临时 | 质检型，任务触发 |
| 📝 文册 | `diancang` | 临时 | 文档型，按需激活 |
| 💰 数算 | `shusuan` | 临时 | 数据型，按需激活 |
| ⚔️ 兵戎 | `bingrong` | 临时 | 运维型，按需激活 |
| 📊 玄档 | `zaohuang` | 临时 | 情报汇总，定时触发 |
| 🔭 枢观 | `qitian` | 临时 | 趋势预测，按需激活 |
| 🔭 枢鉴 | `yushi` | 临时 | 质量审计，终审关卡 |

---

## 八、MCP 融合架构（Hermes 原生接入）

### 三层架构

```
Hermes Agent（用户交互层）
    ↓ 调用
Skill层：xuanji-workflow（工作流编排）
    ↓ workflow_submit/process/list/trace
MCP Server（workflow-mcp/server.py - JSON-RPC over stdio）
    ↓ 状态读写
引擎层：workflow/engine.py（状态机）
    ↓ 状态持久化
TaskQueue（workflow/task_queue.py - tasks.json）
    ↓ delegate指令
Hermes层：delegate_task（实际执行）
    ↓ 继承
Hermes工具 + 技能库 + 角色库 + 记忆
```

### 触发规则

满足以下任一条件，使用玄机阁工作流：
- 任务包含"规划+执行+验证"多阶段
- 需要前端+后端+部署多技能协作
- 用户说"帮我做个xxx"
- 任务预计超过10分钟
- 用户明确说"走玄机阁"

---

## 九、版本历史

| 版本 | 日期 | 变化 |
|------|------|------|
| v1.0 | 2026-05-09 | 初始玄机阁体系 |
| v2.0 | 2026-05-09 | 玄机阁命名重构v2.0 + Skill+Role双库进化架构 |
| v3.0 | 2026-05-09 | 工作流引擎真正运转：workflow/ + CLI + 像素风面板 |
| v3.1 | 2026-05-09 | MCP融合：MCP Server + xuanji-workflow Skill + delegate_task接入Hermes原生能力 |
