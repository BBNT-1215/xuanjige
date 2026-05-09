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
department: "三省|六部|特殊"
version: "1"
created_at: "2026-05-09T00:00:00Z"
updated_at: "2026-05-09T12:00:00Z"

description: "角色一句话描述"

# Skill依赖声明（来自三省六部流程）
skills:
  required:
    - "skill_routing"
  optional:
    - "skill_analysis"

# Role协作关系（来自三省六部流程）
collaborates_with:
  upstream: ["zhongshu"]
  downstream: ["xingbu"]
  consult: ["libu_hr"]
  parallel: ["bingbu", "gongbu"]

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
  "version": "1.0",
  "updated_at": "2026-05-09T12:00:00Z",
  "total_roles": 12,
  "departments": {
    "三省": ["taizi", "zhongshu", "menxia", "shangshu"],
    "六部": ["libu_hr", "hubu", "bingbu", "gongbu", "xingbu", "libu"],
    "特殊": ["morning", "qintian"]
  },
  "roles": [
    {
      "id": "shangshu",
      "name": "尚书省",
      "department": "三省",
      "path": "agents/shangshu",
      "is_permanent": false,
      "version": "4",
      "stats": {"tasks_completed": 23, "avg_quality": 0.86},
      "skills_required": ["skill_skill_routing", "skill_role_dispatch"],
      "health_status": "ok"
    }
  ]
}
```
