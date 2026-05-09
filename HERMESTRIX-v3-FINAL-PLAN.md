# Hermestrix v3.0 最终工程方案

> Skill · Role · Memory × 三省六部 深度融合体系
> 版本：v3.0 | 状态：执行就绪 | 创建：2026-05-09

---

## 目录

1. [愿景与核心哲学](#一愿景与核心哲学)
2. [整体架构](#二整体架构)
3. [三层记忆系统](#三四层记忆系统)
4. [Skill库体系](#四skill库体系)
5. [Role库体系](#五role库体系)
6. [三省六部融合执行流程](#六三省六部融合执行流程)
7. [进化引擎](#七进化引擎)
8. [常驻Agent](#八常驻agent)
9. [基础设施](#九基础设施)
10. [分阶段执行计划](#十分阶段执行计划)
11. [技术债务与风险](#十一技术债务与风险)
12. [验收标准](#十二验收标准)

---

## 一、愿景与核心哲学

### 1.1 愿景

```
Hermestrix 是一个自我进化的 AI Agent 协作操作系统。

它以中国古代三省六部制为组织隐喻，
以 Skill 为 Know-How（做事的方法），
以 Role 为 Know-Who（做事的人），
以 Memory 为 Know-What（积累的经验），
构建一个能够：
  - 稳定执行任务（稳定层）
  - 持续自我进化（进化层）
  - 感知自身健康（监控层）

的工程产品级多Agent协作框架。
```

### 1.2 核心哲学

```
第一性原则：
  记忆不是"存储过去"，记忆是"服务于未来决策"。

三层职责：
  L0（瞬时）：当前任务的上下文，保持执行连贯性
  L1（任务）：原始经验记录，为进化提供原材料
  L2（聚合）：进化统计结果，直接服务于派发决策
  L3（知识）：客观规则与公理，是决策的约束边界

进化原则：
  所有进化必须可验证，不验证的进化等于噪音积累。

组织原则：
  三省六部不是固定流程，而是 Skill×Role 组合的动态调度场。
  流程的灵活性和组织的稳定性共存。
```

### 1.3 与现有方案的本质差异

```
v1/v2方案的问题：
  - Skill/Role/Memory 各自独立，没有形成闭环
  - 三省六部只是"角色扮演"，没有真正嵌入系统
  - 进化没有验证机制，可能"学坏"
  - 没有健康监控，问题扩散了才发现

v3.0方案的改进：
  - Skill/Role/Memory 在三省六部每一步中显式调用
  - 三省六部是调度层，Skill库和Role库是执行资源层
  - 进化有验证闭环（观察窗口+回滚机制）
  - 有系统健康监控（主动告警而非被动发现）
```

---

## 二、整体架构

### 2.1 架构总图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Hermestrix v3.0                                │
│                   Skill × Role × Memory × 三省六部 融合体系                   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        旨意入口层                                    │   │
│  │                    用户消息 / 定时任务 / 事件                         │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                     │                                          │
│                                     ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    太子 Agent（Permanent）                            │   │
│  │         职责：分拣旨意 → 判断路由 → 触发三省六部流程                  │   │
│  │         Skill：skill_routing（分拣）+ skill_dispatch（派发）         │   │
│  │         Memory：L1查询（类似旨意历史）→ L2查询（路由成功率统计）      │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                     │                                          │
│              ┌─────────────────────┴─────────────────────┐                   │
│              │                                           │                    │
│              ▼                                           ▼                    │
│  ┌─────────────────────────┐               ┌─────────────────────────┐     │
│  │      中书省 Agent       │               │      直接处理           │     │
│  │  (Temporary Subagent)   │               │  (Simple tasks)         │     │
│  │  skill_planning         │               └─────────────────────────┘     │
│  │  skill_doc_writing       │                                                │
│  └────────────┬────────────┘                                                │
│               │                                                              │
│               ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      门下省 Agent（Temporary）                          │   │
│  │              职责：四维审议 + Skill可用性预检 + 风险评估              │   │
│  │              Skill：skill_review + skill_risk_assessment               │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                     │                                          │
│                                     ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      尚书省 Agent（Temporary）                         │   │
│  │                   职责：Skill检索 + Role检索 + 派发六部                │   │
│  │              Skill：skill_skill_routing + skill_role_dispatch          │   │
│  │         Memory：L1查询（同类型任务最优方案）→ L2查询（评分/统计）       │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                     │                                          │
│              ┌─────────────────────┼─────────────────────┐                   │
│              │                     │                     │                    │
│              ▼                     ▼                     ▼                    │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐           │
│  │   工部 Subagent   │ │   刑部 Subagent  │ │   吏部咨询       │           │
│  │   skill_coding   │ │   skill_qa       │ │   skill_km       │           │
│  └────────┬─────────┘ └────────┬─────────┘ └──────────────────┘           │
│           │                    │                                          │
│           └────────────────────┼────────────────────┘                       │
│                                ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     任务完成 → EventBus                              │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                     │                                          │
│              ┌─────────────────────┴─────────────────────┐                   │
│              ▼                                           ▼                    │
│  ┌─────────────────────────┐               ┌─────────────────────────┐     │
│  │   吏部 Agent（Permanent）│               │   尚书省汇总            │     │
│  │   三库守护者 + 进化引擎  │               │   回奏中书省            │     │
│  └───────────┬─────────────┘               └─────────────────────────┘     │
│              │                                                              │
│              ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         进化引擎 v2                                   │   │
│  │  冲突解决 → 进化验证 → 健康监控 → 衰减管理 → L2更新                 │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                     │                                          │
│                                     ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         L2 进化统计层                               │   │
│  │   Skill评分（effectiveness）    Role统计（stats）                     │   │
│  │   系统健康度（health）           验证基准（verified_baseline）          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         L3 知识沉淀层                                │   │
│  │       rules/（流程规则）  axioms/（决策公理）  context/（背景知识）   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      基础设施层                                      │   │
│  │     看板 Kanban │ 事件总线 EventBus │ 断点自愈 Recovery              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流总览

```
旨意输入
    │
    ▼
太子分拣 ──L1查询──→ 类似旨意历史
    │              ──L2查询──→ 路由成功率
    ▼
中书省起草 ──L1查询──→ 类似方案
    │              ──L3查询──→ 流程规则
    ▼
门下省审议 ──Skill预检──→ required Skills是否存在
    │           ──风险评估──→ skill_risk_assessment
    ▼
尚书省派发 ──L1查询──→ 同类型任务最优方案
    │           ──L2 Skill查询──→ effectiveness 评分
    │           ──L2 Role查询──→ stats + 协作关系
    ▼
六部执行 ──使用携带Skill──→ 产出结果 + quality_score
    │
    ▼
EventBus: task.completed
    │
    ▼
吏部进化 ──写入L1──→ 原始记录
    │      ──冲突解决──→ resolved记录
    │      ──更新L2 Skill──→ effectiveness + 开启验证窗口
    │      ──更新L2 Role──→ stats + 协作关系
    │      ──健康检查──→ 异常则告警
    │      ──衰减更新──→ 旧记忆权重调整
    ▼
L2更新完成 ──下次检索时生效──→ 尚书省派发决策
```

---

## 三、四层记忆系统

### 3.1 四层职责定义

```
┌──────────┬─────────────────────┬──────────────────┬──────────────────────┐
│          │       名称          │       载体        │      生命周期         │
├──────────┼─────────────────────┼──────────────────┼──────────────────────┤
│ L0       │ 瞬时记忆            │ Agent context    │ 对话内               │
│          │ 当前任务执行上下文    │ window           │                      │
├──────────┼─────────────────────┼──────────────────┼──────────────────────┤
│ L1       │ 任务记忆            │ memory/raw/      │ 永久（但有权重衰减）  │
│          │ 原始经验记录         │ memory/resolved/ │                      │
│          │                     │ memory/cold/     │                      │
├──────────┼─────────────────────┼──────────────────┼──────────────────────┤
│ L2       │ 进化统计            │ skills/{id}/     │ 永久                 │
│          │ Skill/Role评分聚合  │ roles/{id}/      │                      │
│          │ 系统健康度           │ system_health/   │                      │
├──────────┼─────────────────────┼──────────────────┼──────────────────────┤
│ L3       │ 知识沉淀            │ knowledge/rules/ │ 永久（人工维护为主）  │
│          │ 流程规则+决策公理    │ knowledge/axioms/│                      │
│          │                     │ knowledge/context/                      │
└──────────┴─────────────────────┴──────────────────┴──────────────────────┘
```

### 3.2 L1 任务记忆结构

```
memory/
├── raw/                      # 原始记录（未处理）
│   ├── JJ-20260509-003.json
│   └── JJ-20260509-004.json
│
├── resolved/                 # 冲突解决后的记录
│   └── JJ-20260509-003.json  # resolved 字段标注了解决过程
│
├── cold/                     # 冷存储（超180天未访问）
│   └── JJ-20260101-001.json
│
└── index.json               # 全局索引
```

**L1 原始记录格式：**

```json
{
  "task_id": "JJ-20260509-003",
  "task_type": "system_setup",
  "task_title": "将Hermestrix体系投入运行",
  "created_at": "2026-05-09T11:36:00Z",
  "completed_at": "2026-05-09T11:40:00Z",
  "duration_minutes": 4,

  "executing_roles": ["jiheng", "shenyi", "jiheng"],
  "org_flow": ["chengzhi", "jiheng", "shenyi", "jiheng"],

  "skills_used": [
    {"skill_id": "skill_planning", "quality_score": 0.90},
    {"skill_id": "skill_routing", "quality_score": 0.88},
    {"skill_id": "skill_skill_routing", "quality_score": 0.85}
  ],

  "quality_score": 0.88,
  "quality_tier": "good",          // good(≥0.8) / medium(0.5-0.8) / bad(<0.5)

  "outcome": {
    "result": "体系首次完整运行成功",
    "artifacts": ["commit:7eb8520", "task:JJ-20260509-003"],
    "summary": "三省六部流程跑通，Skill/Role检索生效"
  },

  "reflection": {
    "what_worked": [
      "skill_routing检索出了正确的路由",
      "吏部常驻进程自动触发了进化"
    ],
    "what_failed": [
      "flow命令状态机有小bug，需要Review状态才能done"
    ],
    "root_cause": "状态机设计不完善，done命令校验过于严格",
    "improvement_action": "修复kanban.py的cmd_done逻辑"
  },

  "context": {
    "task_complexity": "medium",
    "task_domain": "system_operation",
    "user_id": "oc_01d61785cfc1e868a714c80d07a3ba2d"
  },

  "conflict_resolved": false,
  "decay_weight": 1.0
}
```

### 3.3 L2 进化统计结构

**Skill 进化统计：**

```json
{
  "skill_id": "skill_routing",
  "version": "3",
  "updated_at": "2026-05-09T12:00:00Z",

  "stats": {
    "total_uses": 47,
    "success_count": 41,
    "failure_count": 6,
    "avg_quality": 0.82,
    "last_used": "2026-05-09T11:40:00Z",
    "last_5_scores": [0.88, 0.85, 0.90, 0.82, 0.79]
  },

  "effectiveness_score": 0.82,
  "confidence": "high",

  "verification": {
    "status": "verified",           // pending / verifying / verified / rolled_back
    "version_introduced": "3",
    "observations_required": 5,
    "observations_collected": 5,
    "observations_avg": 0.84,
    "verification_confirmed_at": "2026-05-09T12:00:00Z"
  },

  "best_practices": [
    {
      "text": "任务分拣优先看task_type字段",
      "extracted_from": "JJ-20260509-003",
      "confidence": 0.90
    }
  ],

  "failure_patterns": [
    {
      "pattern": "模糊旨意无法分类",
      "occurrences": 3,
      "symptoms": ["type: unclear", "needs clarification"],
      "fix": "返回'type: unclear'让太子再确认",
      "last_occurred": "2026-05-09T10:00:00Z"
    }
  ],

  "decay": {
    "last_accessed": "2026-05-09T11:40:00Z",
    "decay_weight": 1.0,
    "in_cold_storage": false
  }
}
```

**Role 进化统计：**

```json
{
  "role_id": "jiheng",
  "version": "4",
  "updated_at": "2026-05-09T12:00:00Z",

  "stats": {
    "tasks_completed": 23,
    "avg_quality": 0.86,
    "avg_duration_minutes": 22,
    "last_active": "2026-05-09T11:40:00Z"
  },

  "collaborations": {
    "with_xingce": {"count": 8, "avg_quality": 0.91},
    "with_jizao": {"count": 5, "avg_quality": 0.84},
    "with_jiyan": {"count": 3, "avg_quality": 0.88}
  },

  "skill_usage": {
    "skill_skill_routing": {"uses": 23, "avg_quality": 0.85, "confidence": "high"},
    "skill_role_dispatch": {"uses": 23, "avg_quality": 0.83, "confidence": "medium"}
  },

  "health": {
    "status": "ok",
    "trend": "stable",
    "last_check": "2026-05-09T12:00:00Z"
  }
}
```

**系统健康度：**

```json
{
  "timestamp": "2026-05-09T12:00:00Z",
  "overall_status": "ok",          // ok / warn / critical

  "metrics": {
    "skill_avg_effectiveness": {
      "value": 0.78,
      "status": "ok",
      "threshold_warn": 0.6,
      "threshold_critical": 0.4
    },
    "role_avg_quality": {
      "value": 0.84,
      "status": "ok",
      "threshold_warn": 0.7,
      "threshold_critical": 0.5
    },
    "cold_storage_ratio": {
      "value": 0.08,
      "status": "ok",
      "threshold_warn": 0.7,
      "threshold_critical": 0.9
    },
    "evolution_stagnation_days": {
      "value": 2,
      "status": "ok",
      "threshold_warn": 7,
      "threshold_critical": 14
    },
    "pending_verifications": {
      "value": 2,
      "status": "ok"
    }
  },

  "alerts": []
}
```

### 3.4 L3 知识沉淀结构

```
knowledge/
├── rules/
│   ├── workflow_sanshengliubu.json    # 三省六部执行流程规则
│   ├── skill_selection.json           # Skill选择决策树
│   ├── role_assignment.json            # Role派发决策表
│   └── evolution_policy.json           # 进化策略配置
│
├── axioms/
│   ├── 001_efficiency_first.md        # 效率优先公理
│   ├── 002_simplicity_first.md        # 简单性优先公理
│   ├── 003_traceability_first.md      # 可追溯性优先公理
│   ├── 004_verification_required.md   # 验证必要性公理
│   └── 005_no_blame_culture.md        # 不归咎Role公理
│
└── context/
    ├── project_background.md           # 项目背景
    ├── glossary.md                    # 术语表
    └── users_preferences.json         # 用户偏好
```

**公理示例（001_efficiency_first.md）：**

```markdown
# 公理001：效率优先

## 陈述
当两个 Skill 或 Role 效果相当时，选择更简单的。

## 理由
复杂度是错误的来源。简单方案更容易维护和追溯。

## 应用场景
- skill_routing vs skill_routing_v2：效果相同，选简单的
- 两个 Role 组合效果相同：选组合更简单的

## 违反条件
当简单方案存在已知的扩展性瓶颈时，
宁可选择稍复杂但更具扩展性的方案。
```

### 3.5 记忆检索 API

```python
# memory_manager.py

class MemoryManager:
    """四层记忆的统一检索接口"""

    # L1 查询
    def query_similar_tasks(self, task_type, limit=5, quality_filter='good'):
        """查询同类任务的最优记忆"""

    def query_role_history(self, role_id, limit=10):
        """查询某Role的历史执行记录"""

    def query_skill_history(self, skill_id):
        """查询某Skill的历史使用记录"""

    def get_conflicts(self, skill_id, task_context):
        """检测某Skill在特定上下文下的记忆矛盾"""

    # L2 查询
    def get_skill_effectiveness(self, skill_id):
        """获取某Skill的评分（经过冲突解决）"""

    def get_role_stats(self, role_id):
        """获取某Role的统计"""

    def get_best_role_combo(self, task_type):
        """获取某任务类型的最优Role组合"""

    # L3 查询
    def get_workflow_rules(self, phase):
        """获取某流程阶段的规则"""

    def get_axiom(self, axiom_id):
        """获取某决策公理"""

    # 健康检查
    def get_system_health(self):
        """获取系统健康度"""

    # 归档
    def archive(self, task_record):
        """归档任务记录（含冲突检测和L1写入）"""
```

---

## 四、Skill库体系

### 4.1 Skill 核心结构

```
skills/
├── registry.json                    # Skill中心注册表
│
├── skill_routing/
│   ├── SKILL.md                    # Skill定义
│   ├── METADATA.yaml               # 元数据
│   ├── scripts/
│   │   └── route.py               # 路由CLI工具
│   └── references/
│       └── routing_strategies.md   # 专业知识
│
├── skill_planning/
│   ├── SKILL.md
│   ├── METADATA.yaml
│   ├── scripts/
│   │   └── plan.py
│   └── references/
│
└── ... (按需扩展)
```

### 4.2 SKILL.md 标准格式

```yaml
---
name: "skill_routing"
description: "对用户旨意进行分类，判断路由方向"
domain: "orchestration"
version: "1.0.0"
tier: "STANDARD"

inputs:
  - name: "user_message"
    type: "string"
    required: true
    description: "用户原始旨意文本"
  - name: "context"
    type: "object"
    required: false
    description: "当前上下文（用户历史、任务状态等）"

outputs:
  - name: "route"
    type: "string"
    description: "路由方向：jiheng / direct / reject / clarify"
  - name: "confidence"
    type: "float"
    description: "置信度 0.0-1.0"
  - name: "reasoning"
    type: "string"
    description: "路由理由"

dependencies: []

tools:
  - "scripts/route.py"

used_by_roles:
  - "chengzhi"

effectiveness_score: 0.82
confidence: "high"
---

# skill_routing · 旨意分拣

## Overview
对用户输入的旨意进行分类，判断应该走三省六部流程还是直接处理。
是太子 Agent 的核心 Skill。

## When to Use
- 用户发送旨意时
- 需要判断任务类型时
- 不确定如何处理用户请求时

## When NOT to Use
- 旨意已明确（不需要分拣）
- 重复确认请求

## Core Workflows

### Workflow 1: 标准分拣
**Goal:** 将旨意分类到正确处理路径

**Steps:**
1. 解析旨意文本，提取关键词
2. 查询 L1 记忆：类似旨意以前如何处理
3. 应用 L3 规则：flow规则中的分类逻辑
4. 输出路由 + 置信度

**Expected Output:**
```json
{
  "route": "jiheng",
  "confidence": 0.88,
  "reasoning": "旨意包含'构建'关键词，匹配系统建设类型"
}
```

**Time Estimate:** < 5 seconds

## Script Interfaces

### scripts/route.py
```bash
python3 scripts/route.py --message "构建一个AI漫剧工厂"
python3 scripts/route.py --message "今天的任务状态是什么" --json
```

## Best Practices
1. 置信度 < 0.6 时，返回 `clarify` 而非强行分类
2. 优先使用 task_type 字段匹配，而非全文匹配
3. 参考 L1 历史时，使用 quality=good 的记录

## Common Pitfalls
1. 过度分类 → 当置信度低时返回 clarify
2. 忽略上下文 → 相同词在不同用户下可能路由不同

## Failure Handling
当无法分类时：
→ 返回 `{"route": "clarify", "reasoning": "旨意不够清晰"}`
→ 触发太子重新询问用户

## Evolution History
- v1.0.0 (2026-05-09): 初始版本，从3次执行中提取最佳实践
```

### 4.3 Skill METADATA.yaml

```yaml
---
name: "skill_routing"
version: "1.0.0"
created_at: "2026-05-09T00:00:00Z"
updated_at: "2026-05-09T12:00:00Z"

effectiveness_score: 0.82
confidence: "high"

stats:
  total_uses: 47
  success_count: 41
  failure_count: 6
  avg_quality: 0.82

verification:
  status: "verified"
  version_introduced: "1.0.0"
  observations_required: 5
  observations_collected: 5
  verification_confirmed_at: "2026-05-09T12:00:00Z"

domain: "orchestration"

tools:
  - "scripts/route.py"

used_by_roles:
  - "chengzhi"

requires_roles: []          # 这个Skill不强制要求特定Role

quality_tiers:
  excellent: [0.9, 1.0]
  good: [0.8, 0.9]
  medium: [0.5, 0.8]
  bad: [0.0, 0.5]
```

### 4.4 Skill 注册表 (registry.json)

```json
{
  "version": "1.0",
  "updated_at": "2026-05-09T12:00:00Z",
  "total_skills": 12,

  "skills": [
    {
      "id": "skill_routing",
      "name": "旨意分拣",
      "domain": "orchestration",
      "tier": "STANDARD",
      "path": "skills/skill_routing",
      "effectiveness_score": 0.82,
      "confidence": "high",
      "status": "active",
      "used_by_roles": ["chengzhi"]
    },
    {
      "id": "skill_skill_routing",
      "name": "Skill检索派发",
      "domain": "orchestration",
      "tier": "POWERFUL",
      "path": "skills/skill_skill_routing",
      "effectiveness_score": 0.78,
      "confidence": "high",
      "status": "active",
      "used_by_roles": ["jiheng"]
    }
  ],

  "domains": {
    "orchestration": 4,
    "engineering": 3,
    "analysis": 2,
    "documentation": 2,
    "operation": 1
  }
}
```

### 4.5 Skill 评分算法

```python
def calculate_effectiveness(skill_id, records):
    """
    Skill评分 = 加权质量均值（时间衰减 + 样本量 + 方差）

    公式：
    score = Σ(record.quality * decay_weight) / Σ(decay_weight)

    其中：
    - decay_weight = 0.5 ^ (days_since / 90)  # 90天半衰期
    - 方差过大（>0.3）时，降低置信度
    """
    records = sorted(records, key=lambda r: r['completed_at'])

    weighted_sum = 0
    weight_sum = 0

    for r in records:
        days_since = (now() - r['completed_at']).days
        decay = 0.5 ** (days_since / 90)
        weight = decay * r.get('decay_weight', 1.0)

        weighted_sum += r['quality_score'] * weight
        weight_sum += weight

    if weight_sum == 0:
        return 0.5, 'low'

    raw_score = weighted_sum / weight_sum
    variance = calculate_variance([r['quality_score'] for r in records])

    # 方差校正
    if variance > 0.3:
        confidence = 'low'
        score = raw_score * 0.8  # 降低分数
    elif variance > 0.15:
        confidence = 'medium'
        score = raw_score * 0.95
    else:
        confidence = 'high'
        score = raw_score

    return round(score, 2), confidence
```

---

## 五、Role库体系

### 5.1 Role 核心结构

```
roles/
├── registry.json                    # Role中心注册表
│
├── chengzhi/
│   ├── SOUL.md                     # Role定义（prompt）
│   ├── METADATA.yaml               # 元数据
│   └── references/
│       └── routing_history.md       # 历史路由案例
│
├── jiheng/
│   ├── SOUL.md
│   ├── METADATA.yaml
│   └── references/
│
└── ... (按部门分类)
```

### 5.2 SOUL.md + METADATA.yaml 双文件

**SOUL.md** = Role的行为定义（prompt）

**METADATA.yaml** = Role的元数据（配置）

### 5.3 METADATA.yaml 标准格式

```yaml
---
name: "jiheng"
role_name: "尚书省"
department: "三省"
version: "4"
created_at: "2026-05-09T00:00:00Z"
updated_at: "2026-05-09T12:00:00Z"

description: "从Skill库和Role库检索最优组合，派发给六部执行，汇总结果"

# Skill依赖声明
skills:
  required:
    - skill_skill_routing     # 必须会从Skill库检索
    - skill_role_dispatch     # 必须会从Role库检索派发
  optional:
    - skill_data_analysis     # 可选数据分析辅助

# Role协作关系
collaborates_with:
  upstream:           # 上游（流程前置角色）
    - jiheng       # 中书省
  downstream:        # 下游（执行后汇总）
    - xingce         # 刑部（质量审查）
  consult:           # 咨询（不参与主流程）
    - jiyan        # 吏部（Skill/Role查询）
  parallel:          # 并行执行
    - bingrong         # 兵部
    - jizao         # 工部

# 执行统计
stats:
  tasks_completed: 23
  avg_quality: 0.86
  avg_duration_minutes: 22
  last_active: "2026-05-09T11:40:00Z"

health:
  status: "ok"
  trend: "stable"

# 执行约束
constraints:
  max_parallel_subtasks: 5
  requires_approval_above_quality: 0.6   # 质量低于0.6需上级确认

# 能力边界
capabilities:
  - "Skill库检索与派发"
  - "Role组合优化"
  - "六部任务协调"
  - "执行结果汇总"

limitations:
  - "不直接执行具体业务"
  - "不参与六部具体开发工作"
  - "不绕过中书省直接接旨"

# 进化历史
evolution_history:
  - version: "4"
    date: "2026-05-09"
    change: "增加Skill/Role检索能力，替代随机派发"
  - version: "3"
    date: "2026-05-08"
    change: "METADATA格式标准化"
```

### 5.4 Role 注册表 (registry.json)

```json
{
  "version": "1.0",
  "updated_at": "2026-05-09T12:00:00Z",
  "total_roles": 12,

  "departments": {
    "三省": ["chengzhi", "jiheng", "shenyi", "jiheng"],
    "六部": ["jiyan", "shusuan", "bingrong", "jizao", "xingce", "diancang"],
    "特殊": ["morning", "qintian"]
  },

  "roles": [
    {
      "id": "jiheng",
      "name": "尚书省",
      "department": "三省",
      "path": "roles/jiheng",
      "is_permanent": false,
      "version": "4",
      "stats": {"tasks_completed": 23, "avg_quality": 0.86},
      "skills_required": ["skill_skill_routing", "skill_role_dispatch"],
      "health_status": "ok"
    }
  ]
}
```

### 5.5 Role × Skill 依赖校验

```python
def validate_role_skill_dependencies(role_id):
    """
    执行前校验：Role声明的required Skills是否都在Skill库中

    在尚书省派发前调用（MENXIA审议阶段也做预检）
    """
    role_meta = load_metadata(role_id)
    registry = load_skill_registry()

    missing = []
    for skill_id in role_meta['skills']['required']:
        if skill_id not in [s['id'] for s in registry['skills']]:
            missing.append(skill_id)

    if missing:
        raise RuntimeError(
            f"Role {role_id} requires unavailable Skills: {missing}. "
            f"Install them before execution."
        )

    return True
```

---

## 六、三省六部融合执行流程

### 6.1 各部 Role × Skill 配置

| 角色 | Required Skills | Optional Skills | 核心职责 |
|------|----------------|-----------------|---------|
| **chengzhi** | skill_routing, skill_dispatch | skill_analysis | 旨意分拣与路由 |
| **jiheng** | skill_planning, skill_doc_writing | skill_analysis | 方案起草 |
| **shenyi** | skill_review, skill_risk_assessment | skill_analysis | 审议与风险 |
| **jiheng** | skill_skill_routing, skill_role_dispatch | skill_data_analysis | Skill/Role检索派发 |
| **jiyan** | skill_km, skill_evolution, skill_data_analysis | - | 三库守护+进化 |
| **shusuan** | skill_data_analysis, skill_reporting | skill_doc_writing | 数据分析 |
| **bingrong** | skill_devops, skill_security, skill_monitoring | skill_incident_response | 运维安全 |
| **jizao** | skill_coding, skill_architecture | skill_testing, skill_code_review | 开发架构 |
| **xingce** | skill_qa, skill_audit, skill_code_review | skill_testing | 质量审计 |
| **diancang** | skill_doc_writing, skill_ui_design | skill_presentation | 文档设计 |
| **morning** | skill_daily_briefing | skill_data_analysis | 每日晨报 |
| **qintian** | skill_trend_analysis, skill_prediction | skill_data_analysis | 趋势预测 |

### 6.2 各流程节点的检索操作

```
太子（分拣）
  L1: query_similar_tasks(task_type)     → 类似旨意历史
  L2: get_role_stats('chengzhi')           → chengzhi的执行质量
  L3: get_workflow_rules('routing')    → 路由规则
  → 输出：路由方向

中书省（起草）
  L1: query_similar_tasks(task_type)     → 类似方案历史
  L3: get_workflow_rules('planning')    → 起草规则
  → 查询Skill库：需要的Skill是否存在
  → 输出：方案草案

门下省（审议）
  L1: query_role_history('jiheng')     → 中书省历史表现
  Skill预检：validate_role_skill_dependencies('jiheng')
  L3: get_workflow_rules('review')      → 审议规则
  → 输出：准奏/驳回

尚书省（派发）
  L1: query_similar_tasks(task_type)     → 同类最优方案
  L2: get_all_skill_effectiveness()     → 各Skill评分
  L2: get_all_role_stats()              → 各Role统计
  L2: get_best_role_combo(task_type)    → 最优组合
  L3: get_axiom('001_efficiency_first') → 效率优先公理
  → 输出：派发决策

六部（执行）
  携带对应Skill → 执行 → 产出quality_score

吏部（进化）
  L1: archive(task_record)              → 写入原始记录
  → 冲突检测 → 解决
  → L2: update_skill_stats()
  → L2: update_role_stats()
  → L2: update_system_health()
  → L2: apply_decay_weights()
```

### 6.3 典型流程示例

```
用户旨意："将Skill库扩展到100个"

│ 时间  │ 角色      │ 操作                         │ 检索/更新
│ 11:36 │ 太子      │ 分拣旨意                     │ L1查询→同类型任务
│       │           │ → 路由到中书省               │ 置信度0.85
├───────┼───────────┼──────────────────────────────┼─────────────────
│ 11:36 │ 中书省    │ 起草扩展方案                 │ L1查询→类似方案
│       │           │ 查询Skill库：哪些Skill缺失    │ 现有12/目标100
│       │           │ 提交门下省                   │ 需新增88个
├───────┼───────────┼──────────────────────────────┼─────────────────
│ 11:37 │ 门下省    │ 四维审议                     │ Skill可用性✓
│       │           │ - 可行性：Skill标准已定义     │ 风险：中等
│       │           │ - 完整性：可分批执行         │ 资源：需人力
│       │           │ 准奏                         │
├───────┼───────────┼──────────────────────────────┼─────────────────
│ 11:37 │ 尚书省    │ 检索Skill库                  │ L2查询→评分排序
│       │           │ - skill_domain_classify×    │ 选engineering优先
│       │           │ 检索Role组合                 │ L2→jizao+shusuan协作好
│       │           │ 派发：工部(主)+户部(数据)    │ 派发成功
├───────┼───────────┼──────────────────────────────┼─────────────────
│ 11:38 │ 工部      │ 执行：批量创建Skill          │ 使用skill_domain_classify
│ 11:38 │ 户部      │ 执行：数据分析支持           │ 使用skill_data_analysis
├───────┼───────────┼──────────────────────────────┼─────────────────
│ 11:40 │ 任务完成  │ EventBus.task.completed      │ quality=0.85(good)
├───────┼───────────┼──────────────────────────────┼─────────────────
│ 11:40 │ 吏部      │ 归档L1                       │ 写入raw/good/
│       │           │ 冲突检测→无矛盾              │
│       │           │ 更新L2 Skill                 │ skill_domain_classify+1
│       │           │ 更新L2 Role                 │ jizao.stats+1
│       │           │ 健康检查→OK                  │
│       │           │ 衰减权重更新                 │ 旧记忆权重-0.1
└───────┴───────────┴──────────────────────────────┴─────────────────
```

---

## 七、进化引擎

### 7.1 进化引擎职责

```
进化引擎 = 记忆到进化的转换器

五大职责：
1. 归档：将任务记录写入L1
2. 冲突解决：检测并解决记忆矛盾
3. L2更新：更新Skill评分和Role统计
4. 验证管理：开启/确认/回滚进化
5. 健康监控：检测异常并告警
```

### 7.2 核心模块

```
engine/
├── __init__.py
├── evolution.py           # 进化引擎主类
├── memory_manager.py      # L1/L2/L3检索API
├── conflict_resolver.py   # 冲突解决
├── health_monitor.py      # 健康监控
├── decay_service.py       # 衰减管理
├── causal_tracker.py      # 因果追踪（可选）
└── registry.py           # 注册表管理
```

### 7.3 冲突解决算法

```python
class ConflictResolver:
    """
    解决L1记忆中的矛盾
    """

    def detect_conflicts(self, skill_id, task_context=None):
        """
        检测某Skill在特定上下文下是否有矛盾记忆

        矛盾定义：
        存在 ≥1 条 good 记忆 和 ≥1 条 bad 记忆
        且 数量都 >= 2（避免单次异常误判）
        """
        records = self.memory.get_records(skill_id, task_context)

        goods = [r for r in records if r['quality_tier'] == 'good']
        bads = [r for r in records if r['quality_tier'] == 'bad']

        if len(goods) >= 2 and len(bads) >= 2:
            return Conflict(
                skill_id=skill_id,
                context=task_context,
                goods=goods,
                bads=bads,
                severity='high'
            )

        return None

    def resolve(self, conflict):
        """
        解决冲突，返回推荐使用的effectiveness_score

        策略优先级：
        1. 时间加权：新记忆权重更高
        2. 样本量：样本多的更可信
        3. 方差分析：高方差时降低置信度
        4. 上下文匹配：同task_type优先
        """
        all_records = conflict.goods + conflict.bads

        # 原因分析：为什么同Skill效果不同？
        root_cause = self.analyze_root_cause(conflict)

        # 时间加权
        weighted_score = sum(
            r['quality_score'] * self.calc_decay(r['completed_at'])
            for r in all_records
        ) / len(all_records)

        # 方差检测
        variance = self.calc_variance([r['quality_score'] for r in all_records])
        if variance > 0.3:
            confidence = 'low'
            warning = f"Skill在{conflict.context}下效果不稳定(方差={variance:.2f})"
        else:
            confidence = 'medium'
            warning = None

        return ResolvedScore(
            score=round(weighted_score, 2),
            confidence=confidence,
            warning=warning,
            root_cause=root_cause,
            resolved_from={
                'good_count': len(conflict.goods),
                'bad_count': len(conflict.bads)
            }
        )

    def analyze_root_cause(self, conflict):
        """
        分析矛盾的根本原因
        """
        # 检查：是不是task_type不同导致的？
        good_types = set(r['context']['task_type'] for r in conflict.goods)
        bad_types = set(r['context']['task_type'] for r in conflict.bads)

        if good_types != bad_types:
            return RootCause(
                type='context_mismatch',
                description=f"Skill在不同task_type下效果不同",
                good_contexts=list(good_types),
                bad_contexts=list(bad_types)
            )

        # 检查：是不是执行者不同？
        good_roles = set(r['executing_roles'][0] for r in conflict.goods)
        bad_roles = set(r['executing_roles'][0] for r in conflict.bads)

        if good_roles != bad_roles:
            return RootCause(
                type='role_difference',
                description=f"不同Role执行效果不同",
                good_roles=list(good_roles),
                bad_roles=list(bad_roles)
            )

        return RootCause(
            type='unknown',
            description="无法确定原因，需人工审查"
        )
```

### 7.4 进化验证机制

```python
class EvolutionVerifier:
    """
    进化效果验证闭环

    核心思想：
    进化后的评分不是"立即生效"
    而是要经过N次观察窗口验证
    验证通过才确认为稳定进化
    """

    VERIFICATION_WINDOW = 5  # 观察5次才确认
    ROLLBACK_THRESHOLD = 0.15  # 观察均值低于预期15%则回滚

    def on_evolution(self, skill_id, old_score, new_score):
        """
        当进化引擎更新Skill评分时触发
        开启验证观察窗口
        """
        self.pending[skill_id] = {
            'old_score': old_score,
            'new_score': new_score,
            'introduced_at': now(),
            'observations': [],
            'required': self.VERIFICATION_WINDOW
        }

    def on_task_completed(self, skill_id, quality_score):
        """
        每次使用该Skill的任务完成时收集观察结果
        """
        if skill_id not in self.pending:
            return

        self.pending[skill_id]['observations'].append(quality_score)

        if len(self.pending[skill_id]['observations']) >= self.VERIFICATION_WINDOW:
            self._verify_or_rollback(skill_id)

    def _verify_or_rollback(self, skill_id):
        pending = self.pending[skill_id]
        obs_avg = mean(pending['observations'])

        if obs_avg >= pending['new_score'] * (1 - self.ROLLBACK_THRESHOLD):
            # 验证通过
            self._confirm(skill_id, obs_avg)
        else:
            # 回滚
            self._rollback(skill_id, obs_avg)

        del self.pending[skill_id]

    def _confirm(self, skill_id, observed_avg):
        """验证通过，更新确认状态"""
        skill_stats = self.load_skill_stats(skill_id)
        skill_stats['verification']['status'] = 'verified'
        skill_stats['verification']['observations_avg'] = observed_avg
        skill_stats['verification']['verification_confirmed_at'] = now()
        self.save_skill_stats(skill_id, skill_stats)

        self.event_bus.emit('evolution.confirmed', {
            'skill_id': skill_id,
            'expected': self.pending[skill_id]['new_score'],
            'observed': observed_avg
        })

    def _rollback(self, skill_id, observed_avg):
        """回滚到旧版本"""
        old = self.pending[skill_id]['old_score']
        skill_stats = self.load_skill_stats(skill_id)
        skill_stats['effectiveness_score'] = old
        skill_stats['verification']['status'] = 'rolled_back'
        self.save_skill_stats(skill_id, skill_stats)

        self.event_bus.emit('evolution.rollback', {
            'skill_id': skill_id,
            'expected': self.pending[skill_id]['new_score'],
            'observed': observed_avg,
            'rolled_back_to': old
        })
```

### 7.5 健康监控

```python
class HealthMonitor:
    """
    系统健康度监控

    主动发现而非被动等待问题扩散
    """

    THRESHOLDS = {
        'skill_avg_effectiveness': {'warn': 0.6, 'critical': 0.4},
        'role_avg_quality': {'warn': 0.7, 'critical': 0.5},
        'cold_storage_ratio': {'warn': 0.7, 'critical': 0.9},
        'evolution_stagnation_days': {'warn': 7, 'critical': 14},
        'pending_verifications': {'warn': 10, 'critical': 20},
        'skill_conflict_rate': {'warn': 0.3, 'critical': 0.5},
    }

    def check_all(self):
        """全面检查，返回健康报告"""
        report = {'timestamp': now(), 'overall': 'ok', 'alerts': [], 'checks': {}}

        for metric, thresholds in self.THRESHOLDS.items():
            value = self._get_metric(metric)
            status = self._evaluate(value, thresholds)

            report['checks'][metric] = {
                'value': value,
                'status': status,
                'thresholds': thresholds
            }

            if status == 'critical':
                report['overall'] = 'critical'
                report['alerts'].append({
                    'level': 'critical',
                    'metric': metric,
                    'message': self._format_alert(metric, value, 'critical')
                })
            elif status == 'warn':
                if report['overall'] != 'critical':
                    report['overall'] = 'warn'
                report['alerts'].append({
                    'level': 'warn',
                    'metric': metric,
                    'message': self._format_alert(metric, value, 'warn')
                })

        self._save_report(report)
        self._notify_if_needed(report)

        return report

    def _format_alert(self, metric, value, level):
        messages = {
            'skill_avg_effectiveness': f"Skill平均评分{value:.2f}过低",
            'role_avg_quality': f"Role平均质量{value:.2f}过低",
            'evolution_stagnation_days': f"进化已停滞{value}天",
        }
        return messages.get(metric, f"{metric}={value} {level}")
```

---

## 八、常驻Agent

### 8.1 常驻Agent列表

| Agent | 类型 | 职责 | 触发方式 |
|-------|------|------|---------|
| **吏部 Agent** | Permanent | 三库守护 + 进化执行 | EventBus + 定时 |
| **太子 Agent** | Permanent（可选） | 旨意分拣（替代Hermes内置分拣） | 消息入口 |

### 8.2 吏部常驻进程

```python
#!/usr/bin/env python3
"""
吏部 Agent 常驻进程

职责：
1. 监听 EventBus，响应任务完成事件
2. 触发进化引擎
3. 定期执行健康检查
4. 定期执行衰减管理

启动：
  python3 agents/permanent/diancang_agent.py [--poll-interval 5]

持久化：
  使用文件系统（JSON），无需数据库
"""

import time
import signal
import sys
from pathlib import Path

# 初始化
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.evolution import EvolutionEngine
from engine.memory_manager import MemoryManager
from engine.health_monitor import HealthMonitor
from engine.decay_service import DecayService
from engine.event_bus import EventBus

class LibuAgent:
    """
    吏部 Agent

    三库守护者，进化引擎执行者
    """

    def __init__(self, poll_interval=5, health_check_interval=3600):
        self.poll_interval = poll_interval
        self.health_check_interval = health_check_interval

        self.event_bus = EventBus()
        self.evolution = EvolutionEngine()
        self.memory = MemoryManager()
        self.health = HealthMonitor()
        self.decay = DecayService()

        self.last_health_check = 0
        self.running = False

        # 注册事件监听
        self.event_bus.subscribe('task.completed', self.on_task_completed)
        self.event_bus.subscribe('task.failed', self.on_task_failed)

    def on_task_completed(self, event):
        """任务完成时触发进化"""
        task_record = event.payload

        # 1. 归档L1
        self.memory.archive(task_record)

        # 2. 冲突检测
        conflicts = []
        for skill_used in task_record['skills_used']:
            conflict = self.evolution.detect_conflict(
                skill_used['skill_id'],
                task_record['context']
            )
            if conflict:
                conflicts.append(conflict)

        # 3. 更新L2（带冲突解决）
        for skill_used in task_record['skills_used']:
            self.evolution.update_skill(
                skill_used['skill_id'],
                skill_used['quality_score'],
                conflicts=conflicts
            )

        # 4. 更新Role统计
        for role_id in task_record['executing_roles']:
            self.evolution.update_role(
                role_id,
                task_record['quality_score']
            )

        print(f"[吏部] 任务 {task_record['task_id']} 归档完成，"
              f"质量 {task_record['quality_score']:.2f}")

    def on_task_failed(self, event):
        """任务失败时特殊处理"""
        task_record = event.payload
        task_record['quality_tier'] = 'failed'
        task_record['quality_score'] = 0.0
        self.memory.archive(task_record, force_bad=True)

        # 失败触发更严格的检查
        self.health.check_all()

    def run_health_check(self):
        """执行健康检查"""
        report = self.health.check_all()

        if report['overall'] != 'ok':
            print(f"[吏部⚠️] 系统健康度: {report['overall']}")
            for alert in report['alerts']:
                print(f"  - [{alert['level']}] {alert['message']}")

            # 通知（可扩展：飞书/邮件告警）
            self.notify_alert(report)

        return report

    def run_decay_management(self):
        """执行衰减管理"""
        self.decay.apply_decay_to_all()
        self.decay.archive_cold_memories()
        self.decay.garbage_collect()

    def run(self):
        """主循环"""
        self.running = True
        print(f"[吏部] 常驻进程启动，轮询间隔 {self.poll_interval}s")

        while self.running:
            # 1. 轮询EventBus
            self.event_bus.poll()

            # 2. 定时健康检查
            if time.time() - self.last_health_check >= self.health_check_interval:
                self.run_health_check()
                self.run_decay_management()
                self.last_health_check = time.time()

            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False
        print("[吏部] 常驻进程停止")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='吏部 Agent 常驻进程')
    parser.add_argument('--poll-interval', type=int, default=5,
                        help='EventBus轮询间隔（秒）')
    parser.add_argument('--health-interval', type=int, default=3600,
                        help='健康检查间隔（秒）')
    args = parser.parse_args()

    agent = LibuAgent(poll_interval=args.poll_interval,
                      health_check_interval=args.health_interval)

    signal.signal(signal.SIGINT, lambda s, f: agent.stop())
    signal.signal(signal.SIGTERM, lambda s, f: agent.stop())

    agent.run()
```

---

## 九、基础设施

### 9.1 看板 (Kanban)

```
职责：
- 任务创建、状态流转、进度追踪
- 与三省六部流程绑定
- 产出任务记录供L1归档

状态机：
  Pending → Zhongshu → Menxia → Shangshu → Doing → Review → Done
                              ↓
                         (Rejection → Pending重试)
```

### 9.2 事件总线 (EventBus)

```
职责：
- 解耦各模块通信
- 支持事件订阅/发布
- 支持异步处理

核心事件：
  task.created        # 任务创建
  task.assigned       # 任务派发
  task.completed      # 任务完成（触发进化）
  task.failed         # 任务失败（触发告警）
  evolution.confirmed  # 进化验证通过
  evolution.rollback   # 进化回滚
  health.critical      # 健康度告警
```

### 9.3 断点自愈 (Recovery)

```
职责：
- 检测进程异常退出
- 恢复中断任务
- 记录恢复日志
```

### 9.4 目录结构

```
hermestrix/
├── SKILL.md                    # Skill编写标准
├── ROLE.md                     # Role编写标准
│
├── roles/                      # Role库（12个）
│   ├── registry.json
│   ├── chengzhi/SOUL.md + METADATA.yaml
│   ├── jiheng/SOUL.md + METADATA.yaml
│   └── ...
│
├── skills/                     # Skill库
│   ├── registry.json
│   ├── skill_routing/SKILL.md + scripts/ + references/
│   ├── skill_planning/
│   ├── skill_skill_routing/
│   └── ...
│
├── engine/                     # 核心引擎
│   ├── __init__.py
│   ├── evolution.py            # 进化引擎
│   ├── memory_manager.py       # 记忆管理
│   ├── conflict_resolver.py    # 冲突解决
│   ├── health_monitor.py       # 健康监控
│   ├── decay_service.py        # 衰减管理
│   ├── event_bus.py            # 事件总线
│   └── registry.py             # 注册表管理
│
├── agents/                     # Agent实现
│   └── permanent/
│       └── diancang_agent.py      # 吏部常驻进程
│
├── three_libs/                 # 三库（持久化）
│   ├── memory/
│   │   ├── raw/
│   │   ├── resolved/
│   │   └── cold/
│   ├── skills/                 # L2 Skill统计
│   │   └── {skill_id}/
│   │       └── stats.json
│   ├── roles/                  # L2 Role统计
│   │   └── {role_id}/
│   │       └── stats.json
│   └── knowledge/
│       ├── rules/
│       ├── axioms/
│       └── context/
│
├── scripts/                    # CLI工具
│   ├── kanban.py
│   ├── skill_cli.py
│   └── role_cli.py
│
├── dashboard/                  # Web看板
└── tests/                      # 测试套件
```

---

## 十、分阶段执行计划

### Phase 1：核心骨架（Week 1）

**目标：三省六部 + Skill/Role/Memory 融合闭环跑通**

#### Day 1-2：记忆系统v2

```
□ 重构 memory_manager.py
  - L1 读写 + 索引
  - L2 Skill/Role 统计读写
  - L3 知识查询
  - query_similar_tasks()
  - get_skill_effectiveness()
  - get_role_stats()

□ 重构 evolution.py → EvolutionEngine
  - on_task_completed()
  - update_skill()
  - update_role()
  - detect_conflict()

□ 重构 conflict_resolver.py
  - detect_conflicts()
  - resolve()

□ 重构 health_monitor.py
  - check_all()
  - THRESHOLDS 配置

□ 重构 decay_service.py
  - calculate_decay_weight()
  - apply_decay_to_all()
  - archive_cold_memories()

□ 创建 knowledge/ 目录结构
  - rules/workflow_sanshengliubu.json
  - axioms/ 公理文件
```

#### Day 3-4：Skill库v2

```
□ 定义 SKILL.md 标准格式
□ 定义 METADATA.yaml 格式
□ 开发3个核心Skill：
  - skill_routing（太子用）
  - skill_skill_routing（尚书省用）
  - skill_role_dispatch（尚书省用）
□ 为每个Skill编写 scripts/ 工具
□ 实现 skill_cli.py
□ 创建 skills/registry.json
□ 实现 skill_manager.py（SkillManager类）
```

#### Day 5：Role库v2 + 三省六部融合

```
□ 定义 METADATA.yaml 格式
□ 为12个Role生成 METADATA.yaml
□ 实现 role_manager.py（RoleManager类）
□ 实现 role_cli.py
□ 创建 roles/registry.json
□ 验证 Role × Skill 依赖校验
□ 改造 jiheng SOUL.md：嵌入L1/L2检索调用
□ 改造 chengzhi SOUL.md：嵌入L1检索调用
```

### Phase 2：进化闭环（Week 2）

**目标：进化验证 + 健康监控 + 吏部常驻进程**

```
□ 实现 EvolutionVerifier
  - pending 观察窗口
  - _verify_or_rollback()
  - _confirm() / _rollback()

□ 实现 causal_tracker.py（可选）
  - 记录任务依赖链
  - AB测试对比

□ 实现吏部常驻进程 diancang_agent.py
  - EventBus 监听
  - 定时健康检查
  - 定时衰减管理

□ 端到端测试：
  - 完成任务 → 触发进化 → L2更新 → 检索生效
```

### Phase 3：扩展（Week 3-4）

**目标：50+ Skill，30+ Role，完整CLI**

```
□ 批量开发20+ Skill
  - engineering: skill_coding, skill_testing, skill_code_review, skill_architecture
  - analysis: skill_data_analysis, skill_reporting, skill_trend_analysis
  - documentation: skill_doc_writing, skill_ui_design, skill_presentation
  - operation: skill_devops, skill_security, skill_monitoring

□ 批量开发10+ Role
  - 补充业务Role

□ hermestrix 主CLI
  - Click框架
  - skill 子命令
  - role 子命令
  - evolution 子命令
```

### Phase 4：产品化（Week 5-6）

**目标：可发布**

```
□ pyproject.toml + pip安装
□ pytest 测试套件
□ GitHub Actions CI/CD
□ 完整文档 docs/
□ 示例项目 examples/
□ 贡献指南 CONTRIBUTING.md
□ CHANGELOG.md
```

---

## 十一、技术债务与风险

### 11.1 技术债务

| 债务项 | 影响 | 优先级 | 解决时机 |
|--------|------|--------|---------|
| kanban.py 状态机bug（done需Review） | 中 | P1 | Phase 1 |
| 三库JSON存储性能 | 低 | P2 | Phase 4 |
| 无单元测试 | 高 | P1 | Phase 4 |
| 现有SOUL.md迁移 | 低 | P2 | Phase 3 |

### 11.2 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Skill编写质量参差不齐 | 高 | 中 | SKILL.md模板+lint检查 |
| 进化产生负面反馈 | 中 | 高 | 验证闭环+回滚机制 |
| 记忆无限膨胀 | 低 | 低 | 衰减服务+冷存储 |
| Role×Skill关联维护成本 | 中 | 中 | 半自动维护 |

---

## 十二、验收标准

### Phase 1 验收

```
□ memory_manager.py 完整实现L1/L2/L3读写
□ evolution.py 完整实现进化更新
□ 3个核心Skill含完整SKILL.md + METADATA.yaml + scripts/
□ 12个Role含完整METADATA.yaml
□ jiheng/chengzhi SOUL.md 嵌入记忆检索
□ Role×Skill依赖校验正常工作
□ skill_cli.py + role_cli.py 可用
□ 端到端流程跑通
```

### Phase 2 验收

```
□ EvolutionVerifier 验证/回滚正常工作
□ 健康监控检测到异常时告警
□ 吏部常驻进程稳定运行
□ 端到端：完成任务 → 30秒内L2更新 → 下次检索生效
```

### Phase 3 验收

```
□ 50+ Skill可用
□ 30+ Role可用
□ hermestrix CLI完整可用
□ Skill×Role关联正确解析
```

### Phase 4 验收

```
□ pip install hermestrix 正常工作
□ 测试覆盖核心逻辑
□ 文档完整
□ 准备好发布PyPI
```

---

## 参考项目

| 项目 | ★ | 关键借鉴 |
|------|---|---------|
| crewAIInc/crewAI | 50,954 | Role三元素、hierarchical process |
| alirezarezvani/claude-skills | 14,175 | SKILL.md格式、scripts/工具 |
| lsdefine/GenericAgent | 9,976 | Skill自动进化结晶 |
| Donchitos/Claude-Code-Game-Studios | 17,795 | Role层级协作 |
| grapeot/context-infrastructure | 445 | 三层记忆、决策公理 |

---

*版本：v3.0 | 状态：执行就绪 | 创建：2026-05-09*
