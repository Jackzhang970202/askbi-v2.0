# 后端设计文档

**版本**: v1.1
**模块**: 记忆管理 (memory-management)
**关联需求**: REQ-memory-management

---

## 业务流程

### 问答前记忆注入流程
用户请求 → 解析 `user_id/chat_id/context` → 通过 mem0 查询会话记忆与用户画像记忆 → 使用 PostgreSQL 做权限过滤、映射补全与人工编辑覆盖 → 构建记忆上下文块 → 注入工作流 system prompt / messages → 执行问答

### 问答后记忆抽取流程
问答完成 → 保存 user/assistant 全量消息 → 组装本轮上下文 → 调用 MemoryExtractor → 生成候选用户画像/会话记忆 → 先写入 mem0 → mem0 以 PostgreSQL 作为持久化层保存历史/元数据 → 再写 AskBI PostgreSQL 业务映射、审计与可编辑补充字段 → 写审计事件

### 会话上下文变化流程
数据源/团队/技能/分析开关变化 → MemoryService 写入 `state` 类型会话记忆 → 后续同会话优先注入

### 记忆管理流程
前端请求 → Memory API 权限校验 → MemoryService 查询/更新/归档 → 写审计事件 → 返回结果

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | mem0 为记忆读写主链路 | 抽取、检索、更新必须实际调用 mem0 |
| R002 | PostgreSQL 仅保存映射、审计和可编辑补充字段 | PG 不得独立替代 mem0 |
| R003 | 用户画像只按 `user_id` 生效 | API 和查询条件强制过滤 user_id |
| R004 | 会话记忆只按 `chat_id` 生效 | 注入时必须匹配 chat_id |
| R005 | 去重键防重复 | `user_id/scope + memory_kind + dedupe_key` 唯一 |
| R006 | mem0 不可用时不得静默降级 | 相关记忆能力必须显式报错 |
| R006 | 删除会话同步清理会话记忆 | delete session 时调用 clear_session_memory |
| R007 | 记忆抽取异步执行 | 主问答接口先返回，记忆任务后台执行 |
| R008 | 全量消息先存库 | 记忆抽取基于已保存的 `askbi_messages` 与结构化结果 |

---

## 数据表设计

### 表名: `askbi_user_profile_memory`

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| user_id | INTEGER | 否 | - | 用户 ID |
| memory_kind | TEXT | 否 | - | preference/background/constraint/goal |
| profile_json | JSONB | 是 | NULL | 结构化画像 |
| profile_text | TEXT | 否 | - | 可注入模型的画像文本 |
| summary | TEXT | 是 | NULL | 简短摘要 |
| dedupe_key | TEXT | 否 | - | 去重键 |
| source_chat_id | TEXT | 是 | NULL | 来源会话 |
| source_message_ids | JSONB | 是 | '[]' | 来源消息 ID 列表 |
| mem0_id | TEXT | 是 | NULL | mem0 同步 ID |
| status | TEXT | 否 | 'active' | active/archived/deleted |
| created_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 更新时间 |

**约束/索引**:
- `UNIQUE(user_id, memory_kind, dedupe_key)`
- 查询索引建议：`user_id,status,memory_kind`

### 表名: `askbi_session_profile_memory`

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| chat_id | TEXT | 否 | - | 会话 ID |
| user_id | INTEGER | 是 | NULL | 用户 ID |
| memory_kind | TEXT | 否 | - | goal/subject/decision/state |
| profile_json | JSONB | 是 | NULL | 结构化会话记忆 |
| profile_text | TEXT | 否 | - | 可注入模型的会话记忆文本 |
| summary | TEXT | 是 | NULL | 简短摘要 |
| dedupe_key | TEXT | 否 | - | 去重键 |
| source_message_ids | JSONB | 是 | '[]' | 来源消息 ID 列表 |
| expires_at | TIMESTAMP | 是 | NULL | 过期时间 |
| mem0_id | TEXT | 是 | NULL | mem0 同步 ID |
| status | TEXT | 否 | 'active' | active/archived/deleted |
| created_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 更新时间 |

**约束/索引**:
- `UNIQUE(chat_id, memory_kind, dedupe_key)`
- 查询索引建议：`chat_id,status,memory_kind`

### 表名: `askbi_memory_events`

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| user_id | INTEGER | 是 | NULL | 用户 ID |
| chat_id | TEXT | 是 | NULL | 会话 ID |
| memory_scope | TEXT | 否 | - | user/session/mem0 |
| memory_id | INTEGER | 是 | NULL | 本地记忆 ID |
| event_type | TEXT | 否 | - | extract/upsert/archive/delete/sync/skip/error |
| event_payload | JSONB | 是 | '{}' | 事件详情 |
| created_at | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

---

## SQL 同步原则

实现时需同步更新：
- `config/config_db.py` 新增表常量
- `utils/db_utils.py#create_tables()` 新增 `CREATE TABLE IF NOT EXISTS`
- 若后续提供迁移脚本，SQL 存放于 `sql/` 并保持与代码 DDL 一致

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 查询用户画像记忆 | GET | `/memory/user` | REQ-memory-management-用户画像记忆 |
| 查询会话记忆 | GET | `/memory/session/{chat_id}` | REQ-memory-management-会话记忆 |
| 归档记忆 | PATCH | `/memory/{scope}/{id}/archive` | REQ-memory-management-管理与可视化 |
| 删除记忆 | DELETE | `/memory/{scope}/{id}` | REQ-memory-management-管理与可视化 |
| 修改记忆 | PUT | `/memory/{scope}/{id}` | REQ-memory-management-管理与可视化 |
| 手动触发会话总结 | POST | `/memory/session/{chat_id}/summarize` | REQ-memory-management-会话记忆 |
| 查询记忆事件 | GET | `/memory/events` | REQ-memory-management-管理与可视化 |

### GET `/memory/user`

**查询参数**: `memory_kind`、`status=active`、`keyword`、`user_id`（仅 admin/manager 可传）

**响应体**:
```json
{
  "success": true,
  "memories": [
    {
      "id": 1,
      "user_id": 3,
      "memory_kind": "preference",
      "summary": "偏好表格化回答",
      "profile_text": "用户偏好用 Markdown 表格展示指标对比。",
      "status": "active",
      "updated_at": "2026-06-15T10:00:00"
    }
  ]
}
```

### GET `/memory/session/{chat_id}`

**响应体**:
```json
{
  "success": true,
  "memories": [
    {
      "id": 10,
      "chat_id": "chat_xxx",
      "memory_kind": "decision",
      "summary": "已确认按自然月统计",
      "profile_text": "本会话已确认所有月份指标按自然月口径统计。"
    }
  ]
}
```

---

## 核心类

### MemoryService

| 方法 | 说明 |
|------|------|
| build_context(user_id, chat_id, mode) | 构建模型注入的记忆上下文 |
| upsert_user_memory(data) | 写入/合并用户画像记忆 |
| upsert_session_memory(data) | 写入/合并会话记忆 |
| list_user_memories(...) | 查询用户画像记忆 |
| list_session_memories(chat_id, ...) | 查询会话记忆 |
| archive_memory(scope, id, user) | 归档记忆 |
| delete_memory(scope, id, user) | 逻辑删除记忆 |
| clear_session_memory(chat_id) | 会话删除时清理会话记忆 |
| record_event(...) | 写审计事件 |

### MemoryExtractor

| 方法 | 说明 |
|------|------|
| extract_after_turn(payload) | 基于本轮问答抽取用户/会话记忆候选 |
| summarize_session(chat_id) | 手动或定时总结会话记忆 |
| build_dedupe_key(candidate) | 构造去重键 |

### Mem0SyncService

| 方法 | 说明 |
|------|------|
| write_memory(memory) | 将用户画像/会话记忆写入 mem0 |
| search(user_id, chat_id, query) | 通过 mem0 检索记忆，再结合 PG 权限过滤 |
| update_memory(mem0_id, memory) | 更新 mem0 中的记忆 |
| delete_memory(mem0_id) | 删除或失活 mem0 中的记忆 |

---

## 与现有链路集成

| 位置 | 集成方式 |
|------|----------|
| `session_service.save_message()` | 确保全量消息与结构化数据先入库 |
| `bi_api.ask_bi()` | 问答前注入记忆；问答后调度记忆抽取 |
| `excel_api.ask_api()` | Excel 问答前注入记忆；问答后调度记忆抽取 |
| `bi_api.ask_general()` | 普通对话接入用户画像和会话记忆 |
| `team_api.run_team()` | 团队问答完成后抽取会话记忆 |
| 删除会话 API | 同步清理 `askbi_session_profile_memory` |
| `backend_api_agno.py` | 挂载 `memory_router` |

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| v1.0 | 2026-06-15 | 初始版本：定义 PostgreSQL 记忆表、API、服务与 mem0 集成方式 | zhangqiyuan |

---

**文档结束**
