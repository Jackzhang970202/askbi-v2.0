# 任务清单

**版本**: v1.0
**模块**: 知识库管理 (knowledge)
**关联需求**: REQ-knowledge

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-knowledge-管理器-001 | [后端] 实现 KnowledgeManager | REQ-knowledge-知识库CRUD | P1 | 已完成 |
| TASK-knowledge-API-002 | [后端] 实现知识库 CRUD API | REQ-knowledge-知识库CRUD | P1 | 已完成 |
| TASK-knowledge-全局知识-003 | [后端] 实现全局知识读写 API | REQ-knowledge-全局知识 | P1 | 已完成 |
| TASK-knowledge-临时知识-004 | [后端] 实现临时知识读写 API | REQ-knowledge-临时知识 | P1 | 已完成 |
| TASK-knowledge-前端管理-005 | [前端] 实现知识库管理界面 | REQ-knowledge-知识库CRUD | P1 | 已完成 |
| TASK-knowledge-前端编辑-006 | [前端] 实现知识编辑器 | REQ-knowledge-全局知识 | P1 | 已完成 |

---

## 任务详情

### TASK-knowledge-管理器-001 KnowledgeManager

**关联需求**: REQ-knowledge-知识库CRUD
**描述**: 实现 KnowledgeManager 类，管理外部知识库
**技术要点**: HTTP 请求, RAG API 调用
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `datasources/knowledge_manager.py`

**验收标准**:
- [ ] 知识库添加正常
- [ ] 知识库删除正常
- [ ] 列表返回正确

---

### TASK-knowledge-API-002 知识库 CRUD API

**关联需求**: REQ-knowledge-知识库CRUD
**描述**: 实现 /knowledge_bases 路由
**技术要点**: FastAPI, knowledge_manager 调用
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] GET/POST/DELETE 路由正常
- [ ] 错误处理正确

---

### TASK-knowledge-全局知识-003 全局知识读写 API

**关联需求**: REQ-knowledge-全局知识
**描述**: 实现 /knowledge/global 路由，读写 knowledge/global_rules.txt
**技术要点**: 文件读写, 路径处理
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 文件不存在时自动创建
- [ ] 读取/写入内容正确

---

### TASK-knowledge-临时知识-004 临时知识读写 API

**关联需求**: REQ-knowledge-临时知识
**描述**: 实现 /knowledge/temp 路由，读写 askbi_chat_knowledge 表
**技术要点**: db_utils upsert, JSONB 序列化
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] vocabulary 与 reference_sql 正确序列化
- [ ] upsert 操作正确

---

### TASK-knowledge-前端管理-005 知识库管理界面

**关联需求**: REQ-knowledge-知识库CRUD
**描述**: 实现知识库列表与创建表单
**技术要点**: React, 表单组件
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/KnowledgeBaseManager.jsx`

**验收标准**:
- [ ] 列表正确加载
- [ ] 创建表单正常
- [ ] 删除确认正常

---

### TASK-knowledge-前端编辑-006 知识编辑器

**关联需求**: REQ-knowledge-全局知识
**描述**: 实现全局知识与临时知识编辑器
**技术要点**: React, 标签输入, 文本编辑
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/KnowledgeEditor.jsx`

**验收标准**:
- [ ] 全局知识文本编辑正常
- [ ] 临时知识三个标签页切换正常
- [ ] 保存成功
