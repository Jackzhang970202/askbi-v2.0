# 后端设计文档

**版本**: v1.1
**模块**: Excel 问数 (excel-query)
**关联需求**: REQ-excel-query

---

## 业务流程

### 文件上传流程
接收文件 → 生成唯一文件名 → 保存到会话目录 → 创建会话 → 保存元数据 → 推送上传事件

### Excel 分析流程
获取文件列表 → 加载文件元数据（列名/sheet/样例）→ LLM 生成 pandas 代码 → 执行代码 → LLM 生成回答正文 → LLM 生成图表 → 保存记录 → 返回结果

### 从数据源初始化流程
验证数据源 → 复制文件到会话目录 → 创建会话 → 保存元数据

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 文件保存到会话目录 | `process_file` |
| R002 | Excel 会话 `chat_id` 以 `excel_` 开头 | 自动生成 chat_id |
| R003 | 文件元数据包含 sheet、列名、样例数据 | `_collect_metadata` |
| R004 | 代码执行在受限环境 | `exec` 变量白名单 |
| R005 | 代码清理去除 markdown 标记 | `_clean_code` |
| R006 | 结果序列化安全处理 | `_make_json_safe` |
| R007 | 用户只能查看自己的会话 | `session_service` 按 `user_id` 过滤 |
| R008 | 主回答统一由 `summary` 承载 | `excel_api.py` 组装结构化响应 |
| R009 | 图表字段固定为 `chart` | `chart_needed=false` 表示不出图 |
| R010 | 分析解读是否输出由提问时的开关控制 | 输出规则由 prompt 控制 |

---

## 数据表设计

复用全局数据模型中的以下表：
- `askbi_chat_session` — 会话记录（`datasource_name=__excel__`）
- `askbi_messages` — 消息记录
- `askbi_request_record` — 请求记录（`generated_sql` 存储 Python 代码）
- `askbi_general_metadata` — 文件路径元数据

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 上传文件 | POST | `/excel/upload_file` | REQ-excel-query-文件上传 |
| 提问 | POST | `/excel/ask` | REQ-excel-query-自然语言分析 |
| 获取进度 | GET | `/excel/progress?chatid=` | REQ-excel-query-进度推送 |
| 会话列表 | GET | `/excel/list_sessions` | REQ-excel-query-会话管理 |
| 会话消息 | GET | `/excel/sessions/{chat_id}/messages` | REQ-excel-query-会话管理 |
| 文件数据 | GET | `/excel/get_file_data?chatid=` | REQ-excel-query-会话管理 |
| 删除会话 | GET | `/excel/delete_chat?chatid=` | REQ-excel-query-会话管理 |
| 数据源初始化 | POST | `/excel/init_from_datasource` | REQ-excel-query-从数据源初始化 |
| 健康检查 | GET | `/excel/health` | - |
| 文件下载 | GET | `/excel/download_file?chatid=` | REQ-excel-query-文件下载与保存 |
| 保存修改文件 | POST | `/excel/save_modified_file` | REQ-excel-query-文件下载与保存 |
| 保存原始文件 | POST | `/excel/save_original_file` | REQ-excel-query-文件下载与保存 |

### POST /excel/ask

**请求体**
```json
{
  "chatid": "excel_xxx",
  "question": "哪个月份不良率最低？",
  "enable_analysis": false
}
```

**响应体**
```json
{
  "status": "success",
  "chatid": "excel_xxx",
  "summary": "按统一结构组织的回答正文",
  "code": "import pandas as pd ...",
  "result": {},
  "chart": {"series": []},
  "trace": {"metadata": [], "execution": {}, "report": "...", "chart": {}}
}
```

### structuredData 设计

历史消息与前端渲染统一使用：

```json
{
  "summary": "主回答正文",
  "code": "import pandas as pd ...",
  "result": {},
  "chart": {"series": []},
  "trace": {"metadata": [], "execution": {}, "report": "...", "chart": {}}
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

### 文件预览接口契约

`GET /excel/get_file_data` 应返回：
- `filename`
- `sheet_name`
- `columns`
- `data`
- `row_count`
- `is_original`

用于支撑“回答依据、佐证”所引用的原始明细查看。

---

## 核心类

### AskExcelWorkflow (`backend/ask/workflows/askexcel_workflow.py`)

| 方法 | 说明 |
|------|------|
| `__init__()` | 初始化模型客户端，加载配置 |
| `_emit(callback, event, payload)` | 推送进度事件 |
| `_log(callback, text)` | 推送进度文本 |
| `_preview(text, limit)` | 截断文本用于日志 |
| `_collect_metadata(paths)` | 收集 Excel 文件元数据 |
| `_llm(system, user)` | 调用 LLM |
| `_clean_code(code)` | 清理代码块标记 |
| `_make_json_safe(value)` | 安全序列化 |
| `_execute_code(code, paths, metadata)` | 执行 pandas 代码 |
| `run(payload)` | 主流程：元数据→代码→执行→回答→图表 |

### API 组装

`backend/ask/api/excel_api.py` 负责：
- 将 workflow 结果映射为接口响应
- 将 `summary/code/result/chart/trace` 写入 `structuredData`
- 暴露文件预览接口用于原始数据查看

---

## 设计约束

1. 不新增独立的“结论字段”“依据字段”“分析字段”接口键名，当前版本继续复用 `summary`
2. 前后端围绕 `structuredData.summary` 进行流式文本展示与历史回放
3. 图表展示与正文分离：正文负责说明，图表实体仅放在 `chart`
4. 可选分析解读必须可按提问参数控制，默认关闭
