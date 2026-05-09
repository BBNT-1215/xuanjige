# Hermestrix 工程产品级架构重构方案

> 综合 Skill库 × Role库 调研结论，对标 crewAI + claude-skills + GenericAgent
> 版本：v3.1 | 状态：待评审

---

## 一、现状分析

### 1.1 现有架构

```
Hermestrix/
├── agents/           # Role库（12个角色）
│   └── {role_id}/SOUL.md         # 仅prompt文本，无元数据
├── skills/          # Skill库（10个技能）
│   └── {skill_id}.json           # 纯数据，无工具，无知识库
├── three_libs/      # 三库基础设施
├── scripts/         # 核心脚本（7个）
└── dashboard/       # Web看板
```

### 1.2 核心差距

| 维度 | 现有 | 目标 | 差距 |
|------|------|------|------|
| Skill结构 | JSON纯数据 | SKILL.md + scripts/ + references/ | 无工具+无知识 |
| Role结构 | SOUL.md文本 | SOUL + METADATA双文件 | 无标准化元数据 |
| Skill×Role | 无关联 | Role声明Skill依赖，Skill被Role调用 | 未建立引用关系 |
| 进化机制 | 手动测试 | 任务完成→自动进化→库更新 | 闭环未完成 |
| Skill规模 | 10个 | 100+个 | 需批量扩展 |
| 三省六部融合 | 初步集成 | Skill/Role深度融入流程 | 需体系化融合 |

---

## 二、核心融合思路：Skill/Role × 三省六部

### 2.1 融合哲学

```
传统三省六部：人 → 职位 → 执行
Hermestrix：  旨意 → Skill → Role → 执行

Skill = 做事的方法（Know-How）
Role  = 做事的人（Know-Who）

 Skill被Role调用，Role的职责由Skill定义
 三省六部是Role的集合，Skill是执行单元的技能库
```

### 2.2 各部Role × Skill映射

| 部门 | Role | 核心Skill | 说明 |
|------|------|-----------|------|
| **太子** | chengzhi | skill_routing, skill_dispatch | 任务分拣、路由决策 |
| **中书省** | jiheng | skill_planning, skill_doc_writing | 方案起草、文档输出 |
| **门下省** | shenyi | skill_review, skill_risk_assessment | 审议、风险评估 |
| **尚书省** | jiheng | skill_skill_routing, skill_role_dispatch | Skill/Role检索、派发 |
| **吏部** | jiyan | skill_km, skill_evolution | 三库管理、进化引擎 |
| **户部** | shusuan | skill_data_analysis, skill_reporting | 数据分析、财务报表 |
| **礼部** | diancang | skill_doc_writing, skill_ui_design | 文档撰写、UI设计 |
| **兵部** | bingrong | skill_devops, skill_security, skill_monitoring | 部署运维、安全监控 |
| **工部** | jizao | skill_coding, skill_architecture, skill_testing | 开发、架构、测试 |
| **刑部** | xingce | skill_qa, skill_audit, skill_review | 质量审查、代码审计 |
| **玄档官** | morning | skill_daily_briefing | 每日晨报 |
| **钦天监** | qintian | skill_trend_analysis, skill_prediction | 趋势预测、预判 |

### 2.3 完整流程融合图

```
用户旨意
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  太子 Agent（Permanent）                                     │
│  skill_routing → 判断旨意类型 → 路由到中书省 or 直接处理     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  中书省 Agent（Temporary Subagent）                          │
│  skill_planning → 起草方案                                  │
│  ├── 方案中声明需要哪些Skill → 查询Skill库                   │
│  └── 方案中声明需要哪些Role → 查询Role库                     │
│  提交门下省审议                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  门下省 Agent（Temporary Subagent）                          │
│  skill_review → 四维审议                                    │
│  ├── Skill可行性（skill库有没有？）                          │
│  ├── Role完整性（有没有能执行的人？）                        │
│  └── 风险评估（skill_risk_assessment）                       │
│  准奏 → 交尚书省                                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  尚书省 Agent（Temporary Subagent）                          │
│  skill_skill_routing → 从Skill库检索最优技能组合             │
│  skill_role_dispatch → 从Role库检索最优角色组合              │
│                                                              │
│  派发给六部：                                               │
│  ├── 派工部（携带skill_coding）                             │
│  ├── 派刑部（携带skill_qa）                                 │
│  ├── 派吏部咨询（携带skill_km）                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌──────────────────────┐   ┌──────────────────────┐
│  六部 Subagent执行    │   │  吏部 Agent（Permanent）│
│  执行Skill方法        │   │  监听任务完成事件     │
│  产出执行结果         │   │  触发进化引擎        │
└──────────┬───────────┘   │  更新Skill评分       │
           │               │  更新Role统计         │
           │               └──────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│  尚书省汇总 → 回报中书省 → 回奏太子 → 呈报用户               │
└─────────────────────────────────────────────────────────────┘
```

### 2.4 Skill进化 × 三省六部闭环

```
任务完成
    │
    ├── EventBus.emit('task.completed', task_id, quality)
    │
    ▼
吏部 Agent（Permanent，常驻进程）
    │
    ├── 读取任务执行记录
    ├── 分析使用的Skill（哪些有效？哪些失败？）
    ├── 分析执行的Role（哪些配合好？哪些有问题？）
    │
    ▼
进化引擎
    │
    ├── Skill评分更新
    │   ├── effectiveness_score ↑（成功）
    │   ├── best_practices ↑（从成功中提取）
    │   ├── failure_patterns ↑（从失败中提取）
    │   └── 新Skill自动结晶（quality≥0.9）
    │
    ├── Role统计更新
    │   ├── tasks_completed ++
    │   ├── avg_quality 更新
    │   └── combined_with 更新（协作关系）
    │
    └── 生成进化报告 → 写入 three_libs/
    │
    ▼
下次尚书省检索时：
    ├── Skill评分高的被优先推荐
    ├── Role组合更优的被使用
    └── 进化后的Skill/Role自动生效
```

### 2.5 Skill × Role 依赖声明机制

```yaml
# roles/jiheng/METADATA.yaml
skills:
  required:
    - skill_skill_routing   # 尚书省必须会用Skill检索
    - skill_role_dispatch    # 尚书省必须会用Role派发

skills:
  optional:
    - skill_data_analysis    # 可选，用于数据分析辅助

# 执行时，Router校验：
# if not all(skill in registry for skill in role.metadata.skills.required):
#     raise RuntimeError(f"Role {role_id} requires unavailable Skills")
```

---

## 三、目标架构

### 3.1 整体架构图

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           Hermestrix Framework v3                        │
│                    Skill × Role × 三省六部 深度融合                        │
│                                                                          │
│  ┌──────────────┐                                                        │
│  │   旨意入口   │                                                        │
│  └──────┬───────┘                                                        │
│         │                                                                  │
│  ┌──────▼───────┐      Skill Registry      Role Registry                  │
│  │  太子 Agent  │ ──────▶│◀────── │◀────                               │
│  │ (Permanent)  │        │ 中心索引 │ 中心索引                            │
│  └──────┬───────┘        └────┬───┘ └────┬───┘                         │
│         │                       │           │                               │
│         │              ┌────────┴───────────┴─────┐                        │
│         │              ▼                           ▼                        │
│         │     ┌─────────────────┐       ┌─────────────────┐              │
│         │     │   Skill库        │       │   Role库         │              │
│         │     │  SKILL.md        │       │  SOUL + METADATA │              │
│         │     │  scripts/        │       │                  │              │
│         │     │  references/      │       │                  │              │
│         │     └────────┬──────────┘       └────────┬─────────┘              │
│         │              │                              │                      │
│         │              │   ┌──────────────────────────┘                      │
│         │              │   │                                                 │
│         │              ▼   ▼                                                 │
│         │     ┌─────────────────────────────────────────────┐               │
│         │     │            进化引擎 (Evolution)               │               │
│         │     │  任务完成 → Skill评分 → Role统计 → 报告      │               │
│         │     └─────────────────────────────────────────────┘               │
│         │                                                            │
│  ┌──────▼──────────────────────────────────────────────────────────┐      │
│  │                    三省六部执行层                               │      │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │      │
│  │  │ 中书省  │→ │ 门下省 │→ │ 尚书省 │→ │ 六部   │            │      │
│  │  │(subagent)│ │(subagent)│ │(subagent)│ │(subagent群)│          │      │
│  │  └────────┘  └────────┘  └────┬───┘  └────────┘            │      │
│  │                                │                              │      │
│  │         Skill检索 ◀────────────┤                               │      │
│  │         Role检索 ◀────────────┤                               │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  吏部 Agent（Permanent）= 三库守护者 + 进化执行者                    │  │
│  │  基础设施：看板 │ 事件总线 │ 断点自愈 │ 三库                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构（目标状态）

```
hermestrix/
├── SKILL.md               # Skill编写标准（参考claude-skills）
├── ROLE.md                # Role编写标准（参考crewAI三元素）
│
├── roles/                 # Role库（重命名自agents/）
│   ├── registry.json       # Role中心注册表
│   ├── chengzhi/
│   │   ├── SOUL.md        # Role定义（prompt）
│   │   └── METADATA.yaml  # 元数据（YAML frontmatter）
│   ├── jiheng/
│   ├── jiheng/
│   ├── shenyi/
│   ├── jiyan/           # 吏部（Permanent Agent）
│   ├── shusuan/
│   ├── bingrong/
│   ├── jizao/
│   ├── xingce/
│   ├── diancang/
│   ├── morning/
│   └── qintian/
│
├── skills/               # Skill库
│   ├── registry.json      # Skill中心注册表
│   ├── skill_code_review/
│   │   ├── SKILL.md       # Skill定义
│   │   ├── scripts/       # 可执行工具
│   │   │   └── review.py
│   │   └── references/    # 专业知识
│   ├── skill_skill_routing/
│   ├── skill_planning/
│   ├── skill_routing/     # 太子用：任务分拣
│   └── ... (按需扩展)
│
├── engine/               # 核心引擎
│   ├── __init__.py
│   ├── evolution.py       # 进化引擎
│   ├── router.py          # 任务路由（Skill+Role检索）
│   └── executor.py        # 执行引擎
│
├── agents/               # Agent实现
│   ├── permanent/         # 常驻Agent
│   │   ├── libu_agent.py  # 吏部常驻进程
│   │   └── chengzhi_agent.py # 太子常驻进程（可选）
│   └── templates/         # Agent模板
│
├── three_libs/           # 三库（持久化）
│   ├── memory/
│   ├── knowledge/
│   └── skills/
│
├── scripts/               # CLI工具
│   ├── skill_cli.py
│   └── role_cli.py
│
├── dashboard/
└── tests/
```

---

## 四、Skill标准（v2）

### 4.1 SKILL.md 格式

```yaml
---
name: "skill_code_review"
description: "对代码进行系统性审查，发现缺陷和优化点"
domain: "engineering"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "code_path"
    type: "string"
    required: true
    description: "代码文件或目录路径"
  - name: "language"
    type: "string"
    required: false
    description: "编程语言"

outputs:
  - name: "issues"
    type: "array"
    description: "发现的问题列表"
  - name: "quality_score"
    type: "float"

dependencies: []

tools:
  - "scripts/review.py"
  - "scripts/lint.py"
---

# 代码审查

## Overview
系统性地审查代码，发现潜在缺陷、风格问题和安全风险。

## When to Use
- 代码提交前审查
- Code Review流程中
- 发布前质量检查

## When NOT to Use
- 紧急热修复
- 原型代码

## Core Workflows

### Workflow 1: 完整代码审查
**Goal:** 对整个代码库进行全面审查

**Steps:**
1. 扫描代码结构 `scripts/review.py scan <path>`
2. 执行规则检查 `scripts/lint.py <path>`
3. 生成审查报告

**Expected Output:** JSON格式的issue列表 + quality_score

### Workflow 2: 快速检查
**Goal:** 快速发现关键问题

**Steps:**
1. `scripts/review.py quick <path>`
2. 只报告高危问题

## Script Interfaces

### scripts/review.py
```bash
python3 scripts/review.py scan <path> [--json]
python3 scripts/review.py quick <path>
```

## Best Practices
1. 先快速扫描，再完整审查
2. 优先处理高危问题

## Evolution History
- v1.0.0 (2026-05-09): 初始版本
```

### 4.2 Skill注册表 (registry.json)

```json
{
  "version": "1.0",
  "updated_at": "2026-05-09T12:00:00Z",
  "skills": [
    {
      "id": "skill_code_review",
      "name": "代码审查",
      "domain": "engineering",
      "tier": "STANDARD",
      "path": "skills/skill_code_review",
      "effectiveness_score": 0.85,
      "success_count": 47,
      "failure_count": 8,
      "last_used": "2026-05-09T11:40:00Z",
      "version": "2",
      "tools": ["scripts/review.py", "scripts/lint.py"],
      "used_by_roles": ["xingce", "jiheng"]
    }
  ]
}
```

---

## 五、Role标准（v2）

### 5.1 SOUL.md + METADATA.yaml 双文件

**roles/jiheng/SOUL.md：**
```markdown
# 尚书省 · 执行调度

你是尚书省，以subagent方式被中书省调用...

[现有内容...]
```

**roles/jiheng/METADATA.yaml：**
```yaml
---
name: "jiheng"
role_name: "尚书省"
department: "三省"

description: "从Skill库和Role库检索最优组合，派发给六部执行，汇总结果"

skills:
  required:
    - skill_skill_routing   # 必须会从Skill库检索
    - skill_role_dispatch   # 必须会从Role库检索+派发
  optional:
    - skill_data_analysis   # 可选数据分析辅助

collaborates_with:
  - jiheng    # 上游：中书省
  - xingce      # 下游：刑部质量审查
  - jiyan     # 咨询：吏部技能查询

stats:
  tasks_completed: 12
  avg_quality: 0.88
  avg_duration_minutes: 25

evolution:
  - version: "3"
    date: "2026-05-09"
    change: "增加Skill/Role库检索能力"
```

### 5.2 Role注册表 (registry.json)

```json
{
  "version": "1.0",
  "updated_at": "2026-05-09T12:00:00Z",
  "roles": [
    {
      "id": "jiheng",
      "name": "尚书省",
      "department": "三省",
      "path": "roles/jiheng",
      "is_permanent": false,
      "version": "3",
      "stats": {
        "tasks_completed": 12,
        "avg_quality": 0.88
      },
      "skills_required": ["skill_skill_routing", "skill_role_dispatch"]
    }
  ]
}
```

---

## 六、三省六部 × Skill/Role 深度融合细则

### 6.1 各部Role的Skill配置

| 角色 | required Skills | optional Skills | 说明 |
|------|----------------|-----------------|------|
| chengzhi | skill_routing, skill_dispatch | skill_analysis | 任务分拣与路由 |
| jiheng | skill_planning, skill_doc_writing | skill_analysis | 方案起草 |
| shenyi | skill_review, skill_risk_assessment | skill_analysis | 审议与风险 |
| jiheng | skill_skill_routing, skill_role_dispatch | skill_data_analysis | Skill/Role检索 |
| jiyan | skill_km, skill_evolution, skill_data_analysis | - | 三库管理与进化 |
| shusuan | skill_data_analysis, skill_reporting | skill_doc_writing | 数据分析 |
| bingrong | skill_devops, skill_security, skill_monitoring | skill_incident_response | 运维与安全 |
| jizao | skill_coding, skill_architecture | skill_testing, skill_code_review | 开发与架构 |
| xingce | skill_qa, skill_audit, skill_code_review | skill_testing | 质量与审计 |
| diancang | skill_doc_writing, skill_ui_design | skill_presentation | 文档与设计 |
| morning | skill_daily_briefing | skill_data_analysis | 每日晨报 |
| qintian | skill_trend_analysis, skill_prediction | skill_data_analysis | 趋势预测 |

### 6.2 流程中的Skill/Role检索时机

```
旨意入口（太子）
    ↓ [skill_routing] 判断旨意类型
    ↓
中书省起草方案
    ↓ [skill_planning] 生成方案
    ↓ [查询Skill库] 确认需要的Skill是否存在
    ↓ [查询Role库] 确认需要的Role是否可用
    ↓
门下省审议
    ↓ [skill_review] 四维审议
    ↓ [skill_risk_assessment] 评估风险
    ↓
尚书省派发
    ↓ [skill_skill_routing] 检索最优Skill组合
    ↓ [skill_role_dispatch] 检索最优Role组合
    ↓ [派发给六部] 携带对应Skill执行
    ↓
六部执行
    ↓ [使用各自Skill执行]
    ↓
任务完成 → [吏部监听] → [进化引擎] → [Skill/Role库更新]
    ↓
尚书省汇总 → 回奏
```

### 6.3 吏部常驻进程的进化职责

```
吏部 Agent（Permanent）职责：

1. 三库守护
   - 维护Skill注册表（registry.json）
   - 维护Role注册表（registry.json）
   - 维护记忆库和知识库

2. 进化监听
   - 监听 EventBus 'task.completed' 事件
   - 读取任务执行记录（使用的Skill、Role、质量评分）

3. 进化执行
   - 更新Skill effectiveness_score
   - 提取best_practices
   - 记录failure_patterns
   - 更新Role stats（tasks_completed、avg_quality）
   - 发现新协作关系（combined_with）

4. 进化报告
   - 定期生成进化报告（Markdown）
   - 写入 three_libs/evolution/

5. 异常告警
   - Skill评分下降到阈值以下 → 告警
   - Role执行质量持续下降 → 告警
```

---

## 七、分阶段实施计划

### Phase 1：骨架建立（三省六部 × Skill/Role融合核心）

**目标：** Skill+Role融入三省六部流程，核心闭环跑通

#### Week 1 Day 1-2：Skill库v2 + Skill标准建立

```
任务：
□ 定义 SKILL.md 标准格式（参考claude-skills）
□ 编写3个核心Skill：
  - skill_routing（太子用：任务分拣）
  - skill_skill_routing（尚书省用：Skill检索）
  - skill_role_dispatch（尚书省用：Role检索+派发）
□ 为每个Skill编写scripts/工具
□ 重构 skill_library.py → SkillManager类
□ 实现 SkillManager.query_best() 算法

验收：
- python3 scripts/skill_manager.py query_best "代码审查任务"
- 返回匹配的Skill + 推荐部门
```

#### Week 1 Day 3-4：Role库v2 + METADATA建立

```
任务：
□ 定义 METADATA.yaml 格式标准（role+goal+backstory + skills声明）
□ 为12个Role生成完整METADATA.yaml
□ 重构 role_library.py → RoleManager类
□ 实现 Role × Skill 依赖校验（required skills是否存在？）
□ 实现 RoleManager.recommend() 算法（根据任务推荐Role组合）

验收：
- python3 scripts/role_manager.py recommend "开发任务"
- 返回推荐Role组合 + 置信度
```

#### Week 1 Day 5：进化引擎v2 + 吏部深度集成

```
任务：
□ 重构 evolution_engine.py → EvolutionEngine类
□ 实现 EventBus 事件监听（task.completed）
□ 实现 Skill评分自动更新（基于quality_score）
□ 实现 最佳实践自动提取
□ 实现 Role统计自动更新
□ 吏部Agent读取METADATA校验Skill依赖

验收：
- 完成一个任务 → 30秒内Skill评分更新
- Skill评分变化可查询
```

### Phase 2：扩展与深化

**目标：** 100+ Skill、50+ Role，完整CLI

#### Week 2：Skill库扩展

```
任务：
□ 批量开发20+ Skill（engineering/marketing/product/operation）
□ 为每个Skill编写scripts/工具
□ 建立Skill知识库 references/
□ 实现 Skill依赖解析
□ 实现 Skill版本管理

目标：50+ Skill可用
```

#### Week 3：Role库深化 + CLI

```
任务：
□ 增加业务Role（参考crewAI examples）
□ Role × Role 协作关系建模
□ hermestrix主CLI（Python Click框架）
□ skill子命令 + role子命令
□ 自动补全脚本

目标：30+ Role可用
```

### Phase 3：产品化

**目标：** 可发布到PyPI

#### Week 4-5：产品化

```
任务：
□ pip安装包（pyproject.toml）
□ Docker支持
□ 完整测试套件（pytest）
□ CI/CD（GitHub Actions）
□ 完整文档（docs/）
□ 示例项目（examples/）
□ 贡献指南 + 变更日志

目标：准备好发布
```

---

## 八、关键设计决策

### 8.1 Skill × Role 依赖校验

```
执行前校验：
  Role.METADATA.skills.required ⊆ SkillRegistry.ids

  如果缺少required Skill：
  → 拒绝执行，报错"缺少必要Skill: xxx"
  → 提示用户先安装或创建该Skill

这个校验在尚书省派发前执行（MENXIA审议阶段也做预检）
```

### 8.2 进化触发时机

```
自动触发（推荐）：
  task.done → EventBus → 吏部监听 → 进化引擎 → 库更新

手动触发（调试用）：
  $ hermestrix evolution run --task-id JJ-xxx

定期扫描（兜底）：
  吏部常驻进程每小时扫描未归档任务
```

### 8.3 Skill自动结晶

```
触发条件：
  - 任务执行质量 >= 0.9
  - 执行路径可复用（有明确的输入/输出）
  - 相同类型任务出现 >= 3次

执行流程：
  1. 提取执行步骤为workflow
  2. 生成 skill_id
  3. 创建 SKILL.md 骨架
  4. 生成 scripts/ 工具（如有）
  5. 写入 skills/
  6. 更新 registry.json
  7. 通知尚书省"Skill xxx已加入Skill库"
  8. 下次任务可直接检索使用

注意：自动结晶的Skill初始 effectiveness_score = 0.5（需通过使用逐步提升）
```

---

## 九、验收标准

### Phase 1 验收

```
□ Skill库可按标准创建/检索/执行
□ Role库含完整METADATA + Skill依赖声明
□ 尚书省执行时校验Skill依赖（缺失则报错）
□ 进化引擎自动触发，Skill评分更新
□ 吏部常驻进程稳定运行
□ 完整流程跑通：旨意 → 太子 → 中书省 → 门下省 → 尚书省 → 六部 → 吏部进化
□ GitHub提交
```

### Phase 2 验收

```
□ 50+ Skill可用
□ 30+ Role可用
□ hermestrix CLI完整可用
□ Skill × Role关联正确解析
```

### Phase 3 验收

```
□ pip install hermestrix 正常工作
□ 完整测试套件
□ 文档完整
□ 准备好发布PyPI
```

---

## 十、参考项目索引

| 项目 | ★ | 关键借鉴 |
|------|---|---------|
| crewAIInc/crewAI | 50,954 | Role三元素、hierarchical process |
| alirezarezvani/claude-skills | 14,175 | SKILL.md格式、scripts/工具 |
| lsdefine/GenericAgent | 9,976 | Skill自动进化结晶 |
| Donchitos/Claude-Code-Game-Studios | 17,795 | 工作室层级Role协作 |
| grapeot/context-infrastructure | 445 | 三层记忆、决策公理 |

---

*Plan版本：v3.1 | 更新：2026-05-09 | 状态：待评审*
*核心变化：Skill/Role与三省六部深度融合，各部Role声明Skill依赖，流程中嵌入检索节点*
