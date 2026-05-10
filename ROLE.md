# 玄机阁 Role 标准格式

> 版本：v1.0 | 状态：规范 | 适配：Hermes Agent 原生

---

## 文件结构

```
roles/
├── registry.json           # Role中心注册表（必需）
│
└── {role_id}/
    ├── SOUL.md            # Role行为定义（必需，从agents/迁移）
    ├── METADATA.yaml      # Role元数据（必需）
    └── references/        # 专业知识（可选）
        └── notes.md
```

---

## METADATA.yaml 格式

```yaml
---
name: "role_id"
role_name: "角色名"
department: "协调层|执行层|特殊"
version: "1"
created_at: "2026-05-09T00:00:00Z"
updated_at: "2026-05-09T12:00:00Z"

description: "角色一句话描述"

# Skill依赖声明（来自玄机阁流程）
skills:
  required:
    - "skill_routing"
  optional:
    - "skill_analysis"

# Role协作关系（来自玄机阁流程）
collaborates_with:
  upstream: ["jiheng"]
  downstream: ["xingce"]
  consult: ["jiyan"]
  parallel: ["bingrong", "jizao"]

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
  requires_approval_above_quality: 0.6

# 能力边界
capabilities:
  - "能力1"
  - "能力2"

limitations:
  - "不做X"
  - "不参与Y"

evolution_history:
  - version: "2"
    date: "2026-05-09"
    change: "变更说明"
```

---

## Role注册表格式 (registry.json)

```json
{
  "version": "2.0",
  "updated_at": "2026-05-09T16:00:00Z",
  "total_roles": 11,
  "departments": {
    "入口": ["chengzhi"],
    "协调层": ["jiheng", "shenyi"],
    "执行层": ["jizao", "xingce", "diancang", "shusuan", "bingrong", "jiyan"],
    "辅助": ["qitian", "zaohuang", "yushi"]
  },
  "roles": [
    {
      "id": "chengzhi",
      "name": "承旨",
      "department": "入口",
      "path": "agents/chengzhi",
      "is_permanent": true,
      "version": "1",
      "stats": {"tasks_completed": 0, "avg_quality": 0.0},
      "skills_required": ["skill_routing", "skill_dispatch"],
      "health_status": "ok"
    },
    {
      "id": "jiheng",
      "name": "机衡",
      "department": "协调层",
      "path": "agents/jiheng",
      "is_permanent": false,
      "version": "5",
      "stats": {"tasks_completed": 0, "avg_quality": 0.0},
      "skills_required": ["skill_skill_routing", "skill_role_dispatch"],
      "health_status": "ok"
    },
    {
      "id": "shenyi",
      "name": "审议",
      "department": "协调层",
      "path": "agents/shenyi",
      "is_permanent": false,
      "version": "1",
      "stats": {"tasks_completed": 0, "avg_quality": 0.0},
      "skills_required": ["skill_review", "skill_risk_assessment"],
      "health_status": "ok"
    },
    {
      "id": "jiyan",
      "name": "机研",
      "department": "执行层",
      "path": "agents/jiyan",
      "is_permanent": true,
      "version": "1",
      "stats": {"tasks_completed": 0, "avg_quality": 0.0},
      "skills_required": ["skill_km", "skill_evolution", "skill_data_analysis"],
      "health_status": "ok"
    }
  ]
}
```
