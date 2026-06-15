# 后端设计文档

**版本**: v1.0
**模块**: 知识库管理 (knowledge)
**关联需求**: REQ-knowledge

---

## 业务流程

### 知识库 CRUD 流程
接收参数 → 调用 knowledge_manager 操作 → 返回结果

### 全局知识读写流程
读取: 检查 knowledge/global_rules.txt 存在性 → 读取内容 → 返回
保存: 写入 content 到文件 → 返回成功

### 临时知识读写流程
读取: 查询 askbi_chat_knowledge 表 → 返回 content/vocabulary/reference_sql
保存: upsert 到 askbi_chat_knowledge 表

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 全局知识存储为文本文件 | knowledge/global_rules.txt |
| R002 | 临时知识存储在数据库 | askbi_chat_knowledge 表 |
| R003 | 临时知识支持 upsert | ON CONFLICT DO UPDATE |
| R004 | vocabulary 与 reference_sql 为 JSONB | db_utils 序列化 |

---

## 数据表设计

复用 askbi_chat_knowledge 表 (临时知识):
- datasource_name: 主键
- content: 知识文本
- vocabulary: JSONB 词汇数组
- reference_sql: JSONB 参考 SQL 数组

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 知识库列表 | GET | /knowledge_bases | REQ-knowledge-知识库CRUD |
| 创建知识库 | POST | /knowledge_bases | REQ-knowledge-知识库CRUD |
| 删除知识库 | DELETE | /knowledge_bases/{kb_id} | REQ-knowledge-知识库CRUD |
| 获取全局知识 | GET | /knowledge/global | REQ-knowledge-全局知识 |
| 保存全局知识 | POST | /knowledge/global | REQ-knowledge-全局知识 |
| 获取临时知识 | GET | /knowledge/temp/{datasource_name} | REQ-knowledge-临时知识 |
| 保存临时知识 | POST | /knowledge/temp | REQ-knowledge-临时知识 |

### POST /knowledge/temp

**请求体**: `{ datasource_name, content, vocabulary, reference_sql }`

**响应**: `{ success, message }`

### GET /knowledge/global

**响应**: `{ success, content, path }`

---

## 核心类

### KnowledgeManager (datasources/knowledge_manager.py)

| 方法 | 说明 |
|------|------|
| `add_kb(kb_id, name, type, description, api_url, headers)` | 添加知识库 |
| `remove_kb(kb_id)` | 删除知识库 |
| `list_kbs()` | 列出知识库 |
