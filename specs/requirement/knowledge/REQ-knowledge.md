# 知识库管理模块 - 需求文档

**版本**: v1.0
**模块**: 知识库管理 (knowledge)

---

## REQ-knowledge-知识库CRUD

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
支持外部知识库的创建、列表查看与删除，用于扩展数据源知识。

### 前置条件
- 用户已登录

### 输入
- 创建: id, name, type (默认 rag), description, api_url, headers
- 列表: 无
- 删除: kb_id

### 输出
- 创建: {success, ...}
- 列表: 知识库列表
- 删除: {success, ...}

### 处理规则
1. 知识库通过 knowledge_manager (datasources/knowledge_manager.py) 管理
2. 支持 rag 类型的外部知识库
3. api_url 为外部 RAG 服务地址
4. headers 包含认证信息 (如 Authorization: Bearer ragflow-xxx)
5. 删除时同步清理关联数据

### 验收标准
- [ ] 知识库创建成功
- [ ] 列表返回所有已创建知识库
- [ ] 删除后知识库不再出现

---

## REQ-knowledge-全局知识

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
维护全局业务规则与知识，适用于所有数据源。

### 前置条件
- 用户已登录

### 输入
- 获取: 无
- 保存: content (文本内容)

### 输出
- 获取: {success, content, path}
- 保存: {success, message}

### 处理规则
1. 全局知识存储在 knowledge/global_rules.txt 文件
2. 文件不存在时自动创建空文件
3. 保存时覆盖写入
4. 返回文件路径供调试

### 验收标准
- [ ] 空知识库返回空字符串
- [ ] 保存后内容正确写入文件
- [ ] 文件路径正确返回

---

## REQ-knowledge-临时知识

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
为特定数据源维护临时知识 (业务词汇、参考 SQL、自由文本)，辅助 BI 问数。

### 前置条件
- 数据源已存在

### 输入
- 获取: datasource_name
- 保存: datasource_name, content, vocabulary, reference_sql

### 输出
- 获取: {success, content, vocabulary, reference_sql}
- 保存: {success, message}

### 处理规则
1. 临时知识存储在 askbi_chat_knowledge 表
2. vocabulary 为业务词汇数组 (JSONB)
3. reference_sql 为参考 SQL 数组 (JSONB)
4. 保存时使用 upsert (ON CONFLICT DO UPDATE)
5. BI 问数时优先加载临时知识作为 prompt 补充

### 验收标准
- [ ] 数据源知识正确保存与获取
- [ ] vocabulary 与 reference_sql 正确序列化
- [ ] 重复保存时更新而非新增