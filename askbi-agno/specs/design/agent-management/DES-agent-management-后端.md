# 后端设计文档

**版本**: v1.0
**模块**: 智能体管理 (agent-management)
**关联需求**: REQ-agent-management

---

## 业务流程

### 智能体 CRUD 流程
前端请求 → agent_api 路由 → agent_manager 业务逻辑 → db_utils CRUD → 返回结果

### 工作流集成流程
工作流初始化 → agent_manager.get_agent_config(agent_name) → 查询 DB（或命中缓存）→ 加载 base_instructions + model_config → 合并 config.json 默认值 → 构建 Agent 实例 → LLM 调用

### 对话测试流程
前端提交消息 → agent_api 调用 agent_manager.test_agent() → 加载智能体完整配置 → 构建临时 Agent → 调用 LLM → 返回回复

### 技能绑定流程
前端提交技能 ID 列表 → agent_api 路由 → agent_manager.bind_skills() → 校验技能 ID 有效性 → 更新 bound_skills 字段 → 返回结果

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 智能体 name 不可重复 | `UNIQUE` 约束 |
| R002 | 内置智能体不可删除 | `is_builtin=TRUE` 时返回 403 |
| R003 | 智能体 name 创建后不可修改 | API 层拒绝 name 字段更新 |
| R004 | 仅 admin/manager 可创建/修改 | 接口权限校验 |
| R005 | model_config 字段独立覆盖 | 空值回退 config.json 默认值 |
| R006 | temperature 取值范围 0-2 | JSON 校验，超出返回 400 |
| R007 | api_key 前端脱敏展示 | API 响应中仅返回后 4 位 |
| R008 | 绑定技能 ID 必须存在 | 校验后过滤无效 ID |
| R009 | 测试对话不持久化 | 不写入 askbi_messages 表 |

---

## 数据表设计

新增表 `askbi_agents`：

| 列名 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| name | TEXT | 否 | - | 智能体标识符（唯一，创建后不可改） |
| display_name | TEXT | 否 | - | 显示名称 |
| description | TEXT | 否 | '' | 智能体描述 |
| base_instructions | TEXT | 否 | - | 系统提示词（Markdown） |
| model_config | JSONB | 否 | '{}' | 模型配置覆盖 |
| bound_skills | JSONB | 否 | '[]' | 绑定的技能 ID 列表 |
| tools | JSONB | 否 | '{}' | 工具配置 |
| is_builtin | BOOLEAN | 否 | FALSE | 是否内置 |
| is_active | BOOLEAN | 否 | TRUE | 是否启用 |
| created_by | INTEGER | 是 | NULL | 创建者 user_id |
| updated_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 最后更新时间 |

内置种子数据（6 条）：
- bi_sql_agent（BI 问数 SQL 生成专家）
- bi_report_agent（BI 问数报告生成专家）
- bi_chart_agent（BI 问数图表生成专家）
- askexcel_code_agent（Excel 分析代码生成专家）
- askexcel_report_agent（Excel 分析报告生成专家）
- askexcel_chart_agent（Excel 分析图表生成专家）

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 智能体列表 | GET | `/agents` | REQ-agent-management-智能体管理 |
| 创建智能体 | POST | `/agents` | REQ-agent-management-智能体管理 |
| 更新智能体 | PUT | `/agents/{id}` | REQ-agent-management-智能体管理 |
| 删除智能体 | DELETE | `/agents/{id}` | REQ-agent-management-智能体管理 |
| 对话测试 | POST | `/agents/{id}/test` | REQ-agent-management-对话测试 |
| 绑定技能 | POST | `/agents/{id}/bind-skills` | REQ-agent-management-技能绑定 |

### GET /agents

**查询参数**: 无

**响应体**
```json
{
  "success": true,
  "agents": [
    {
      "id": 1,
      "name": "bi_sql_agent",
      "display_name": "BI SQL 专家",
      "description": "PostgreSQL BI 问数 SQL 生成智能体",
      "base_instructions": "你是一个 PostgreSQL BI 问数 SQL 专家...",
      "model_config": {
        "model": "",
        "temperature": 0.1,
        "api_key": "",
        "base_url": ""
      },
      "bound_skills": [1, 3],
      "tools": {},
      "is_builtin": true,
      "is_active": true,
      "created_by": 1,
      "updated_at": "2026-06-08T10:00:00"
    }
  ]
}
```

### POST /agents

**请求体**
```json
{
  "name": "custom_analysis_agent",
  "display_name": "自定义分析智能体",
  "description": "用于特定业务场景的分析智能体",
  "base_instructions": "你是一个业务分析专家...",
  "model_config": {
    "model": "qwen-plus",
    "temperature": 0.3,
    "api_key": "",
    "base_url": ""
  },
  "bound_skills": [2],
  "tools": {}
}
```

**响应体**
```json
{
  "success": true,
  "agent": { "id": 7, "name": "custom_analysis_agent" }
}
```

### PUT /agents/{id}

**请求体**
```json
{
  "display_name": "BI SQL 专家（已优化）",
  "description": "优化后的 SQL 生成智能体",
  "base_instructions": "你是一个高级 PostgreSQL BI 问数 SQL 专家...",
  "model_config": {
    "model": "qwen-plus",
    "temperature": 0.2,
    "api_key": "sk-****5678",
    "base_url": "https://api.example.com/v1"
  },
  "is_active": true
}
```

**响应体**
```json
{
  "success": true,
  "agent": { "id": 1, "name": "bi_sql_agent" }
}
```

### DELETE /agents/{id}

**请求体**: 无

**响应体**
```json
{
  "success": true,
  "message": "智能体已删除"
}
```

**错误响应**（内置智能体）:
```json
{
  "success": false,
  "error": "内置智能体不可删除"
}
```

### POST /agents/{id}/test

**请求体**
```json
{
  "message": "查询近三个月的存款总额变化趋势"
}
```

**响应体**
```json
{
  "success": true,
  "reply": "根据您的问题，建议执行以下 SQL 查询：\n\n```sql\nSELECT DATE_TRUNC('month', deposit_date) AS month, SUM(amount) AS total\nFROM deposits\nWHERE deposit_date >= CURRENT_DATE - INTERVAL '3 months'\nGROUP BY month\nORDER BY month;\n```"
}
```

### POST /agents/{id}/bind-skills

**请求体**
```json
{
  "skill_ids": [1, 2, 5]
}
```

**响应体**
```json
{
  "success": true,
  "agent": { "id": 1, "name": "bi_sql_agent" },
  "bound_skills": [1, 2, 5]
}
```

---

## 核心类

### AgentManager

| 方法 | 说明 |
|------|------|
| list_agents() | 列出所有智能体 |
| get_agent(agent_id) | 获取单个智能体 |
| get_agent_by_name(name) | 按名称获取智能体 |
| create_agent(data, user_id) | 创建自定义智能体 |
| update_agent(agent_id, data) | 更新智能体配置 |
| delete_agent(agent_id) | 删除智能体（内置不可删） |
| bind_skills(agent_id, skill_ids) | 绑定/解绑技能 |
| test_agent(agent_id, message) | 对话测试 |
| get_merged_model_config(agent) | 合并智能体配置与全局默认值 |
| seed_builtin_agents() | 种子内置智能体（幂等） |

---

## 设计约束

1. 智能体配置采用 DB 优先策略：DB 中有配置则使用 DB，否则回退到代码中的硬编码默认值
2. model_config 合并策略为字段级覆盖，每个字段独立判断是否为空
3. 智能体缓存使用内存 dict + TTL（60 秒），与技能系统一致
4. DB 操作复用现有 `db_utils.py` 的 `DatabaseUtils` 模式
5. 内置智能体种子在 `startup_init()` 中幂等执行，按 name 字段去重
6. 对话测试使用临时 Agent 实例，不影响正式工作流状态
