# 后端设计文档

**版本**: v2.2
**模块**: 多智能体编排 (multi-agent-orchestration)
**关联需求**: REQ-multi-agent-orchestration

---

## 业务流程

### 普通会话创建流程
前端新建对话 → 创建统一会话记录 → 默认 `context_type=general` → 返回 chat_id

### 上下文挂载流程
前端选择数据源/团队 → 调用上下文挂载接口 → 后端校验目标存在 → 更新 chat_session 上下文字段 → 返回最新上下文

### 动态消息路由流程
前端发送消息 → 读取当前会话上下文 → 路由到 general / bi / excel / team 对应执行链路 → 写入消息与结构化结果 → 返回回复

### 历史恢复流程
前端打开 chat_id → 后端返回消息列表 + 上下文信息 → 前端恢复标签和后续路由状态

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 新建会话默认 `context_type=general` | 会话创建逻辑 |
| R002 | 同一时刻只允许一个主上下文生效 | 上下文写入逻辑 |
| R003 | 绑定 team 时必须校验 team 存在且可用 | Team API 校验 |
| R004 | 绑定 datasource 时必须校验数据源存在 | datasource 校验 |
| R005 | 清除上下文后退回 `general` | 上下文清除逻辑 |
| R006 | 普通对话不可误入 BI/Excel/Team 执行链路 | 路由分发逻辑 |
| R007 | 历史读取必须返回上下文信息 | 会话查询接口 |

---

## 数据表设计

### 表名: `askbi_chat_session`

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| chat_id | TEXT | 否 | - | 会话主键 |
| knowledge_id | TEXT | 是 | NULL | 保留现有字段 |
| datasource_name | TEXT | 是 | NULL | 保留兼容字段 |
| context_type | TEXT | 否 | 'general' | `general` / `bi` / `excel` / `team` |
| context_ref_id | TEXT | 是 | NULL | 引用对象 ID，如 team_id |
| context_ref_name | TEXT | 是 | NULL | 引用对象名称，如 datasource_name / team_name |
| user_id | INTEGER | 是 | NULL | 用户 ID |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

说明：
- 老数据迁移时，若 `datasource_name` 非空且 chat_id 前缀为 `excel_`，可回填 `context_type=excel`
- 若 `datasource_name` 非空且非 excel 前缀，可回填 `context_type=bi`
- 其他历史数据默认 `general`

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 创建统一会话 | POST | `/create_chat` 或新通用接口 | REQ-multi-agent-orchestration-统一会话模型 |
| 普通对话 | POST | `/chat/ask` 或等效接口 | REQ-multi-agent-orchestration-普通对话链路 |
| 更新会话上下文 | POST | `/chat/{chat_id}/context` | REQ-multi-agent-orchestration-会话内上下文挂载 |
| 清除会话上下文 | POST | `/chat/{chat_id}/context/clear` | REQ-multi-agent-orchestration-会话内上下文挂载 |
| 获取会话详情 | GET | `/chat/{chat_id}` 或现有 sessions 接口扩展 | REQ-multi-agent-orchestration-消息路由与历史恢复 |

### POST /chat/{chat_id}/context

**请求体**
```json
{
  "context_type": "bi",
  "context_ref_id": null,
  "context_ref_name": "sales_pg"
}
```

支持示例：
- BI: `context_type=bi`, `context_ref_name=datasource_name`
- Excel: `context_type=excel`, `context_ref_name=datasource_name`
- Team: `context_type=team`, `context_ref_id=team_id`, `context_ref_name=team_name`

**响应体**
```json
{
  "success": true,
  "chat_id": "chat_xxx",
  "context": {
    "type": "bi",
    "ref_id": null,
    "ref_name": "sales_pg"
  }
}
```

### POST /chat/ask

**请求体**
```json
{
  "chatid": "chat_xxx",
  "question": "你好，帮我总结一下今天要做什么",
  "skill_ids": [1, 2]
}
```

**响应体**
```json
{
  "status": "success",
  "chatid": "chat_xxx",
  "answer": "...",
  "summary": "..."
}
```

---

## 执行链路映射

| context_type | 执行链路 | 说明 |
|------|----------|------|
| `general` | 普通对话智能体 | 默认聊天 |
| `bi` | `bi_workflow.run()` | 数据库问数 |
| `excel` | `askexcel_workflow.run()` | Excel 分析 |
| `team` | `TeamCoordinator.run()` | 多智能体协作 |

---

## 设计约束

1. 保留现有 BI、Excel、Team 执行实现，不重写其核心工作流
2. 新增的普通对话能力应尽量复用现有模型配置与技能注入机制
3. 上下文切换是会话状态变化，不等于新建会话
4. SSE 路径选择需与 `context_type` 一致，Team 继续使用团队 stream，BI/Excel 保持原路径

---

**文档结束**