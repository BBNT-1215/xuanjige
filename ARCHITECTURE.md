# 玄机阁架构文档

> 三省六部 AI Agent 协作框架 — 基于 Skill 进化与 Role 组合的自我进化体系 | 适配：Hermes Agent 原生

---

## 一、核心架构

```
┌────────────────────────────────────────────────────────────────────┐
│                           用户（旨意入口）                            │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  承旨（常驻Agent）                                                  │
│  ├── 消息分拣：闲聊 → 直接回复 / 旨意 → 创建任务                     │
│  ├── 旨意整理：提取目标、要求、预期产出                              │
│  └── 用户反馈：回奏结果、阶段性进展通知                              │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  机衡（临时Subagent）                                               │
│  ├── 接收旨意                                                       │
│  ├── 调用 Skill库 检索最匹配技能                                    │
│  ├── 调用 Role库 推荐最优角色组合                                    │
│  ├── 派发六部执行                                                   │
│  └── 汇总结果，回奏承旨                                             │
└────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│  审议（临时Subagent）                                               │
│  ├── 四维审议：可行性 / 完整性 / 风险 / 代价                         │
│  ├── 准奏 → 流转回机衡执行                                         │
│  └── 封驳 → 最多3轮，第3轮强制通过                                  │
└────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        ┌───────────────────┐     ┌───────────────────┐
        │  六部（临时Subagent）│     │  机研（常驻Agent） │
        │  技造：开发         │     │  三库守护者        │
        │  刑策：质检         │     │  Skill进化执行    │
        │  文册：文档         │     │  Role进化追踪     │
        │  数算：数据分析     │     │  健康监控自愈    │
        │  兵戎：部署/安全    │     └───────────────────┘
        └───────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                       进化闭环                                       │
│                                                                     │
│   任务完成 ──▶ 机研监听 ──▶ 进化分析 ──▶ Skill库更新 ──▶ 下次优先  │
│       │                                    │                        │
│       │                                    ▼                        │
│       │                           Role库统计更新                     │
│       │                                                            │
│       └──────────────────────────────────────                      │
│                         Skill/Role库评分 ↑                          │
└────────────────────────────────────────────────────────────────────┘
```

---

## 二、Skill库

### 定位
**"用什么方法做"** 的经验沉淀，可进化、可检索、可共享。

### 数据结构
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

### 进化算法
```
有效性评分 = 成功率×0.30 + 时效性×0.15 + 历史有效度×0.40 + 复杂度×0.15

每次执行记录：
  - 成功 → success_count++
  - 失败 → failure_patterns++ 且 failure_count++

进化触发条件：
  - 有效性变化 > 0.05 → version++，evolve_count++
```

### 检索算法
```python
匹配度 = Skill.effectiveness × 0.50    # 有效度贡献
        + 适用特征命中 × 0.1             # 任务匹配
        + 标签命中 × 0.1                 # 标签匹配
        + min(成功数/100, 0.2)           # 经验加成
```

---

## 三、Role库

### 定位
**角色定义 + 执行统计 + 组合历史**，驱动角色组合的自我进化。

### 数据结构
```json
{
  "role_id": "jizao",
  "role_name": "工部",
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

### 组合推荐算法
```python
推荐分 = Role.quality_score × 0.40
       + 成功率 × 0.30
       + min(执行次数/100, 0.20)
       + 任务类型匹配 × 0.10
```

---

## 四、三库演进

### 旧三库（记忆/技能/知识）
```
记忆库：做过什么事 → 动态经验（已迁移到Skill库）
技能库：用什么方法 → 能力固化（已迁移到Skill库）
知识库：什么事是什么 → 静态事实（保留）
```

### 新体系
```
Skill库：方法经验库（进化型）
Role库：角色进化库（进化型）
Knowledge库：静态知识库（静态型）
```

---

## 五、事件驱动架构

```
任务完成事件
    │
    ▼
机研常驻进程（监听）
    │
    ├──▶ 触发进化引擎
    │         │
    │         ├──▶ 更新Skill库评分
    │         ├──▶ 更新Role库统计
    │         └──▶ 生成进化摘要
    │
    └──▶ 定期生成进化报告（每日0点）
```

---

## 六、永久Agent vs 临时Subagent

| 角色 | 类型 | 理由 |
|------|------|------|
| 承旨 | 常驻 | 消息分拣、旨意入口，需要跨对话记忆 |
| 机研 | 常驻 | 三库守护者，需要持续积累进化 |
| 机衡 | 临时 | 调度型，一次任务一方案 |
| 审议 | 临时 | 审议型，规则固定 |
| 六部 | 临时 | 执行型，专业分工 |
| 枢观 | 临时 | 趋势预测，按需激活 |

---

## 七、目录结构

```
xuanjige/
├── workflow/                   # 工作流引擎（真正运转的核心）
│   ├── engine.py              # 核心调度引擎（承旨→机衡→六部→早朝→御史）
│   ├── task_queue.py          # 任务队列（状态机：待分拣→已派发→执行中→待审核→已完成）
│   └── agent.py               # Agent基类（11个Agent统一run接口）
├── agents/                    # Role库（11个角色定义）
│   ├── {role_id}/
│   │   ├── SOUL.md          # 角色定义
│   │   └── METADATA.yaml    # 角色元数据（v版本/统计/组合）
│   └── ...
├── skills/                    # Skill库（可进化技能定义）
│   └── {skill_id}/           # 每个技能的 SKILL.md + METADATA.yaml + scripts/
├── scripts/
│   ├── skill_library.py      # Skill库核心（CRUD/检索/进化）
│   ├── role_library.py       # Role库核心（扫描/统计/推荐）
│   ├── evolution_engine.py   # 进化引擎（任务→库更新）
│   ├── jiyan_agent.py        # 机研常驻进程
│   ├── kanban.py            # 看板系统
│   ├── three_libraries.py   # 三库（知识库）
│   ├── event_bus.py         # 事件总线
│   ├── recovery.py          # 断点自愈
│   └── run_loop.py          # 主循环
├── dashboard/                # Web看板
│   ├── server.py            # Web服务器（REST API + 静态文件）
│   ├── index.html           # 7列任务看板
│   └── pixel/
│       └── index.html       # 像素风众生相监控面板
├── data/                    # 运行时数据
│   ├── tasks.json           # 任务数据
│   ├── skill_index.json     # Skill索引
│   ├── role_index.json      # Role索引
│   ├── events.json          # 事件日志
│   └── ...
└── three_libs/             # 知识库（记忆/知识沉淀）
```

---

## 七+、工作流引擎详解

### 核心流程

```
用户提交任务
    ↓
承旨（消息分拣·常驻Agent）
  → 拆解任务、关键词识别、路由目标
    ↓
机衡（调度派发·临时Subagent）
  → 派发给目标执行Agent
    ↓
六部（执行层·临时Subagent）
  → 并行执行各自专业任务
    ↓
早朝（情报汇总·临时Subagent）
  → 整合执行结果
    ↓
御史（质量审计·临时Subagent）
  → 质量兜底，通过则完成，失败则退回重做
    ↓
任务完成
```

### 状态机

```
PENDING(待分拣) → ASSIGNED(已派发) → RUNNING(执行中)
                                      ↓
                               REVIEW(待审核) ← 退回重做
                                      ↓
                                  DONE(已完成)
```

### CLI命令

```bash
xuanjige workflow --start              # 启动引擎（后台线程）
xuanjige workflow --submit "任务标题"   # 提交新任务
xuanjige workflow --process <ID>       # 执行完整流程
xuanjige workflow --status              # 查看引擎状态
xuanjige workflow --watch              # 实时监控模式
xuanjige workflow --log                # 查看执行日志
```

---

## 八、进化闭环流程

```
1. 太子接收旨意，创建任务
2. 中书省起草 → 门下省审议 → 尚书省执行
3. 六部Subagent执行任务
4. 尚书省汇总，完成任务
5. 吏部常驻进程检测到 Done 状态
6. 进化引擎分析任务：
   - 分析参与角色 → 更新Role库
   - 推断任务技能 → 记录Skill执行
   - 计算质量评分 → 更新有效性
7. Skill库和Role库评分变化
8. 下次任务派发时，尚书省检索最新库
9. 高分Skill被优先推荐，高分Role被优先组合
10. 体系自我优化，越用越好
```

---

## 九、版本历史

| 版本 | 日期 | 变化 |
|------|------|------|
| v1.0 | 2026-05-09 | 初始三省六部体系 |
| v2.0 | 2026-05-09 | 玄机阁命名重构v2.0 + Skill+Role双库进化架构 |
| v3.0 | 2026-05-09 | 工作流引擎真正运转：workflow/ + CLI + 像素风面板 |
| v3.1 | 2026-05-09 | MCP融合：MCP Server + xuanji-workflow Skill + delegate_task接入Hermes原生能力 |

---

## 七++、MCP融合架构（Hermes原生接入）

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

### 关键：process_step 返回的 delegate 指令

```json
{
  "step": "jiheng",
  "next_agent": "jizao",
  "delegate": {
    "agent_id": "jizao",
    "role_name": "技造",
    "task": { ... }
  },
  "needs_execution": true
}
```

当 Hermes 收到 `needs_execution: true` 时，执行：
```
delegate_task(
  goal="作为技造Agent，完成任务...",
  context={task, agent_id, role_name},
  role="leaf"
)
```

### 触发规则

满足以下任一条件，使用玄机阁工作流：
- 任务包含"规划+执行+验证"多阶段
- 需要前端+后端+部署多技能协作
- 用户说"帮我做个xxx"
- 任务预计超过10分钟
- 用户明确说"走玄机阁"
