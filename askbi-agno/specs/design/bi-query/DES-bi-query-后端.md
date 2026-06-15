# 后端设计文档

**版本**: v1.1
**模块**: BI 问数 (bi-query)
**关联需求**: REQ-bi-query

---

## 业务流程

### 问数流程
用户提问 → 加载数据源元数据 → LLM 生成 SQL → SQL 安全校验 → 执行 SQL → LLM 生成回答正文 → LLM 生成图表 → 保存记录 → 返回结果

### 会话创建流程
接收 datasource_name + knowledge_id → 生成 chat_id → 创建会话记录 → 返回 chat_id

### 消息记录流程
用户问题保存 → 执行结果组装为 `structuredData` → AI 回复保存 → 请求记录保存

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | SQL 仅允许 SELECT/WITH 查询 | `BiWorkflow._safe_sql` |
| R002 | 用户只能查看自己的会话 | `session_service` 按 `user_id` 过滤 |
| R003 | admin/manager 可查看所有会话 | `is_admin_or_manager` 判断 |
| R004 | BI 会话列表过滤 Excel 会话 | `chat_id` 不以 `excel_` 开头 |
| R005 | 元数据加载优先 DB，回退文件 | `schema_loader.load_schema_from_refer` |
| R006 | 主回答统一由 `summary` 承载 | `bi_api.py` 组装结构化响应 |
| R007 | 图表字段固定为 `chart` | `chart_needed=false` 表示不出图 |
| R008 | 分析解读是否输出由提问时的开关控制 | 输出规则由 prompt 控制 |

---

## 数据表设计

复用全局数据模型中的以下表：
- `askbi_chat_session` — 会话记录
- `askbi_messages` — 用户消息与 AI 回复
- `askbi_request_record` — 请求记录（问题、SQL、结果）
- `askbi_chat_knowledge` — 数据源元数据

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 创建会话 | POST | `/create_chat` | REQ-bi-query-会话管理 |
| 提问 | POST | `/ask` | REQ-bi-query-自然语言问数 |
| 获取进度 | GET | `/progress?chatid=&offset=` | REQ-bi-query-进度推送 |
| 会话列表 | GET | `/bi/sessions` | REQ-bi-query-会话管理 |
| 会话消息 | GET | `/bi/sessions/{chat_id}/messages` | REQ-bi-query-会话管理 |
| 删除会话 | DELETE | `/bi/sessions/{chat_id}` | REQ-bi-query-会话管理 |

### POST /ask

**请求体**
```json
{
  "chatid": "bi_xxx",
  "question": "近三个月存款规模变化如何？",
  "knowledge_id": 1,
  "datasource_name": "demo",
  "enable_analysis": false
}
```

**响应体**
```json
{
  "status": "success",
  "chatid": "bi_xxx",
  "answer": "与 summary 一致的主回答正文",
  "summary": "按统一结构组织的回答正文",
  "sql": "SELECT ...",
  "tables": ["table_a", "table_b"],
  "chart": {"series": []},
  "thoughts": ["共执行 1 轮 SQL 生成/重试"]
}
```

### structuredData 设计

历史消息与前端渲染统一使用：

```json
{
  "summary": "主回答正文",
  "sql": "SELECT ...",
  "tables": ["table_a", "table_b"],
  "chart": {"series": []},
  "thoughts": ["..."]
}
```

### summary 内容契约

`summary` 为 Markdown 文本，逻辑顺序固定为：
1. 问题结果、结论
2. 回答依据、佐证
3. 数据图表说明（图表实体仍由 `chart` 承载）
4. 分析解读（仅开关开启时输出）

### chart 内容契约

- 成功出图：返回合法 ECharts option，至少可被前端识别为含 `series`
- 不出图：返回
```json
{"chart_needed": false, "reason": "数据不适合生成图表"}
```

---

## 核心类

### BiWorkflow (`backend/ask/workflows/bi_workflow.py`)

| 方法 | 说明 |
|------|------|
| `__init__()` | 初始化模型客户端，加载配置 |
| `_llm(system, user)` | 调用 LLM，返回响应文本 |
| `_schema_context(datasource_name)` | 加载元数据并构建 schema 上下文 |
| `_safe_sql(sql)` | 校验 SQL 仅包含 SELECT/WITH 查询 |
| `run(question, datasource_name, progress_callback)` | 主流程：SQL 生成→执行→回答→图表 |

### API 组装

`backend/ask/api/bi_api.py` 负责：
- 将 workflow 结果映射为接口响应
- 将 `summary/sql/tables/chart/thoughts` 写入 `structuredData`
- 将 `summary` 同时映射到 `answer`

---

## 设计约束

1. 不新增独立的“结论字段”“依据字段”“分析字段”接口键名，当前版本继续复用 `summary`
2. 前后端围绕 `structuredData.summary` 进行流式文本展示与历史回放
3. 图表展示与正文分离：正文负责说明，图表实体仅放在 `chart`
4. 可选分析解读必须可按提问参数控制，默认关闭
