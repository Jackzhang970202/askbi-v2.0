# 后端设计文档

**版本**: v1.0
**模块**: 建议问题 (suggestions)
**关联需求**: REQ-suggestions

---

## 业务流程

### 建议生成流程
接收列信息与样例数据 → 调用 SuggestionGenerator → LLM 生成问题 → 返回
如 LLM 失败 → 使用 _fallback_questions 基于列名生成 → 返回

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 优先使用 LLM 生成 | SuggestionGenerator.generate_for_excel |
| R002 | LLM 失败时使用 fallback | _fallback_questions |
| R003 | 需要 chat_id 与 columns 信息 | 参数校验 |
| R004 | 建议问题数量 4-6 条 | LLM prompt 控制 |

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 生成建议 | POST | /suggestions | REQ-suggestions-智能建议 |

### POST /suggestions

**请求体**: `{ chat_id, file_name, sheet_name, columns, sample_data (可选), qa_history (可选) }`

**响应**:
```json
{
  "success": true,
  "suggestions": ["这张表有多少行数据？", "可以先做一个数据概览吗？"],
  "fallback": false
}
```

**fallback 响应**:
```json
{
  "success": true,
  "suggestions": ["这张表有多少行数据？", "可以先做一个数据概览吗？", "哪些字段最值得关注？", "这张表有没有异常值？"],
  "fallback": true
}
```

---

## 核心类

### SuggestionGenerator (core/suggestion_generator.py)

| 方法 | 说明 |
|------|------|
| `generate_for_excel(file_name, sheet_name, columns, sample_data, qa_history)` | LLM 生成建议问题 |

### _fallback_questions (core/suggestion_generator.py)

| 函数 | 说明 |
|------|------|
| `_fallback_questions(columns)` | 基于列名生成默认建议问题 |
