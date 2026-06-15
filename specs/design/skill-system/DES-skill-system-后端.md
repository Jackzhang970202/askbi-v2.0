# 后端设计文档

**版本**: v1.0
**模块**: 技能系统 (skill-system)
**关联需求**: REQ-skill-system

---

## 业务流程

### 技能 CRUD 流程
前端请求 → skill_api 路由 → skill_manager 业务逻辑 → db_utils CRUD → 返回结果

### 技能注入流程
工作流初始化 → skill_registry.get_active_skill_instructions(agent_name, datasource) → 查询 DB（或命中缓存）→ 拼接 skill prompt block → 注入到 system prompt → LLM 调用

### AI 辅助创建流程
前端提交描述 → skill_api 调用 LLM → 返回生成的 instructions → 前端展示供编辑

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 技能名称不可重复 | `UNIQUE` 约束 |
| R002 | 内置技能不可删除 | `is_builtin=TRUE` 时返回 403 |
| R003 | 技能注入按优先级降序 | `ORDER BY priority DESC` |
| R004 | 技能缓存 TTL 60 秒 | `skill_registry` 内存缓存 |
| R005 | 仅 admin/manager 可创建/修改 | 接口权限校验 |
| R006 | 绑定为空时匹配所有智能体 | `binding_agents = '[]'` 表示全部 |
| R007 | 作用域 specific 时仅匹配指定数据源 | JSONB contains 查询 |

---

## 数据表设计

新增表 `askbi_skills`：

| 列名 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| name | TEXT | 否 | - | 技能名称（唯一） |
| description | TEXT | 否 | '' | 简短描述 |
| instructions | TEXT | 否 | - | Markdown 提示词内容 |
| category | TEXT | 否 | 'general' | 分类 |
| is_builtin | BOOLEAN | 否 | FALSE | 是否内置 |
| is_active | BOOLEAN | 否 | TRUE | 是否启用 |
| binding_agents | JSONB | 否 | '[]' | 绑定的智能体名称列表 |
| trigger_keywords | JSONB | 否 | '[]' | 触发关键词列表 |
| priority | INTEGER | 否 | 0 | 优先级（高优先） |
| scope_type | TEXT | 否 | 'universal' | 作用域类型 |
| scope_datasources | JSONB | 否 | '[]' | 作用域数据源列表 |
| created_by | INTEGER | 是 | NULL | 创建者 user_id |
| updated_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 最后更新时间 |

内置种子数据（3 条）：
- SQL 安全规则（category: sql）
- 报告格式规范（category: report）
- 图表生成约束（category: chart）

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 技能列表 | GET | `/skills` | REQ-skill-system-技能管理 |
| 创建技能 | POST | `/skills` | REQ-skill-system-技能管理 |
| 更新技能 | PUT | `/skills/{id}` | REQ-skill-system-技能管理 |
| 删除技能 | DELETE | `/skills/{id}` | REQ-skill-system-技能管理 |
| 切换状态 | PATCH | `/skills/{id}/toggle` | REQ-skill-system-技能管理 |
| 测试技能 | POST | `/skills/{id}/test` | REQ-skill-system-技能测试 |
| AI 创建 | POST | `/skills/ai-create` | REQ-skill-system-AI辅助创建 |

### GET /skills

**查询参数**: `category`（可选）, `active_only`（可选，默认 false）

**响应体**
```json
{
  "success": true,
  "skills": [
    {
      "id": 1,
      "name": "SQL 安全规则",
      "description": "强制 SELECT-only 查询",
      "instructions": "### 规则\n1. 只允许 SELECT...",
      "category": "sql",
      "is_builtin": true,
      "is_active": true,
      "binding_agents": [],
      "trigger_keywords": [],
      "priority": 10,
      "scope_type": "universal",
      "scope_datasources": [],
      "created_by": 1,
      "updated_at": "2026-06-08T10:00:00"
    }
  ]
}
```

### POST /skills

**请求体**
```json
{
  "name": "自定义业务规则",
  "description": "某项目的特殊业务术语映射",
  "instructions": "### 业务术语\n- XX: 表示...",
  "category": "general",
  "binding_agents": ["bi_sql_agent"],
  "trigger_keywords": ["术语", "口径"],
  "priority": 5,
  "scope_type": "specific",
  "scope_datasources": ["demo_db"]
}
```

**响应体**
```json
{
  "success": true,
  "skill": { "id": 4, "name": "自定义业务规则" }
}
```

### POST /skills/{id}/test

**请求体**
```json
{
  "agent_name": "bi_sql_agent",
  "datasource_name": "demo_db",
  "question": "近三个月存款变化"
}
```

**响应体**
```json
{
  "success": true,
  "full_system_prompt": "你是 PostgreSQL BI 问数 SQL 专家...\n\n## 附加规则\n### SQL 安全规则\n...",
  "skill_instructions": "### SQL 安全规则\n..."
}
```

### POST /skills/ai-create

**请求体**
```json
{
  "description": "我需要一个技能来约束所有日期相关查询，默认使用自然年月",
  "category": "sql"
}
```

**响应体**
```json
{
  "success": true,
  "instructions": "### 日期口径规则\n1. 默认使用自然年月...\n2. ..."
}
```

---

## 核心类

### SkillManager

| 方法 | 说明 |
|------|------|
| list_skills(category, active_only) | 列出技能 |
| get_skill(skill_id) | 获取单个技能 |
| create_skill(data, user_id) | 创建技能 |
| update_skill(skill_id, data) | 更新技能 |
| delete_skill(skill_id) | 删除技能（内置不可删） |
| toggle_skill(skill_id, is_active) | 切换启用状态 |
| seed_builtin_skills() | 种子内置技能（幂等） |

### SkillRegistry

| 方法 | 说明 |
|------|------|
| get_active_skill_instructions(agent_name, datasource_name) | 获取匹配技能的拼接后 instructions |
| build_skill_prompt_block(skills) | 将技能列表拼接为 prompt 块 |

---

## 设计约束

1. 技能注入采用 Prompt 增强策略，不改变现有工作流的 Agent 调用方式
2. 技能缓存使用内存 dict + TTL，无需 Redis
3. DB 操作复用现有 `db_utils.py` 的 `DatabaseUtils` 模式
4. 内置技能种子在 `startup_init()` 中幂等执行
