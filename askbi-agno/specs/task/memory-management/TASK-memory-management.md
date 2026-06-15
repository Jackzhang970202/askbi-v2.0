# 任务清单

**版本**: v1.1
**模块**: 记忆管理 (memory-management)
**关联需求**: REQ-memory-management

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-memory-management-数据层-001 | [后端] 新增记忆表常量、DDL 与 CRUD | REQ-memory-management-用户画像记忆 / 会话记忆 | P0 | 已完成 |
| TASK-memory-management-服务层-002 | [后端] 实现 MemoryService 与 MemoryExtractor | REQ-memory-management-用户画像记忆 / 会话记忆 | P0 | 已完成 |
| TASK-memory-management-注入-003 | [后端] 在问答前注入记忆上下文 | REQ-memory-management-用户画像记忆 / 会话记忆 | P0 | 已完成 |
| TASK-memory-management-抽取-004 | [后端] 问答完成后异步抽取记忆 | REQ-memory-management-用户画像记忆 / 会话记忆 | P0 | 已完成 |
| TASK-memory-management-mem0-005 | [后端] 保留 mem0 主链路并将其 SQLite 持久化替换为 PostgreSQL | REQ-memory-management-mem0集成 | P1 | 进行中 |
| TASK-memory-management-API-006 | [后端] 实现 Memory API 路由 | REQ-memory-management-管理与可视化 | P0 | 已完成 |
| TASK-memory-management-前端-007 | [前端] 实现记忆管理页面 | REQ-memory-management-管理与可视化 | P1 | 已完成 |
| TASK-memory-management-会话面板-008 | [前端] 实现会话记忆面板 | REQ-memory-management-会话记忆 | P1 | 已完成 |
| TASK-memory-management-删除联动-009 | [后端] 会话删除时清理会话记忆 | REQ-memory-management-会话记忆 | P0 | 已完成 |

---

## 任务详情

### TASK-memory-management-数据层-001 新增记忆表常量、DDL 与 CRUD

**关联需求**: REQ-memory-management-用户画像记忆 / REQ-memory-management-会话记忆  
**描述**: 在 `config/config_db.py` 新增记忆表常量，在 `utils/db_utils.py` 创建三张记忆表，并在 `utils/pg_db_utils.py` 或专用 repository 中实现 CRUD。  
**技术要点**: JSONB 字段、唯一约束、状态字段、事件表、幂等 DDL  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `config/config_db.py`
- `utils/db_utils.py`
- `utils/pg_db_utils.py`

**验收标准**:
- [ ] 启动后端自动创建 `askbi_user_profile_memory`
- [ ] 启动后端自动创建 `askbi_session_profile_memory`
- [ ] 启动后端自动创建 `askbi_memory_events`
- [ ] 用户画像和会话记忆 upsert 能按 dedupe_key 去重

---

### TASK-memory-management-服务层-002 实现 MemoryService 与 MemoryExtractor

**关联需求**: REQ-memory-management-用户画像记忆 / REQ-memory-management-会话记忆  
**描述**: 新增记忆服务，负责构建上下文、抽取候选记忆、去重合并、写审计事件。  
**技术要点**: LLM 抽取 JSON、失败降级、异步任务、分类映射  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/services/memory_service.py`
- `backend/ask/services/memory_extractor.py`

**验收标准**:
- [ ] 可基于一轮问答抽取用户画像候选
- [ ] 可基于一轮问答抽取会话记忆候选
- [ ] 抽取失败记录事件且不影响问答返回

---

### TASK-memory-management-注入-003 在问答前注入记忆上下文

**关联需求**: REQ-memory-management-用户画像记忆 / REQ-memory-management-会话记忆  
**描述**: 在 BI、Excel、普通对话、Team 执行前读取当前用户画像和会话记忆，并拼入模型上下文。  
**技术要点**: 先会话记忆后用户画像；控制 token 长度；权限过滤  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/api/bi_api.py`
- `backend/ask/api/excel_api.py`
- `backend/ask/api/team_api.py`
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/workflows/askexcel_workflow.py`

**验收标准**:
- [ ] 同一会话后续问题能使用会话记忆
- [ ] 同一用户新会话能使用用户画像记忆
- [ ] 其他用户无法读取该用户记忆

---

### TASK-memory-management-抽取-004 问答完成后异步抽取记忆

**关联需求**: REQ-memory-management-用户画像记忆 / REQ-memory-management-会话记忆  
**描述**: 问答完成并保存消息后，异步调度记忆抽取，将有价值的信息写入记忆表。  
**技术要点**: `asyncio.create_task` 或后台线程；读取本轮结构化结果；写 event 记录  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/api/bi_api.py`
- `backend/ask/api/excel_api.py`
- `backend/ask/api/team_api.py`
- `backend/ask/services/memory_service.py`

**验收标准**:
- [ ] 主问答返回不等待记忆抽取完成
- [ ] 抽取成功后记忆表出现新记录或更新记录
- [ ] 重复事实不会写出多条活跃记录

---

### TASK-memory-management-mem0-005 实现 mem0 可选同步与降级

**关联需求**: REQ-memory-management-mem0集成  
**描述**: 复用上层 `components/memory.py` 的 mem0 接入思路，使 mem0 成为记忆读写主链路；保留现有向量存储，只将 mem0 当前 SQLite 持久化改为 PostgreSQL；AskBI PostgreSQL 继续保存映射、审计和可编辑补充字段。  
**技术要点**: mem0 add/search/update/delete 必须实际调用；替换 mem0 SQLite 持久化为 PostgreSQL；记录 `mem0_id`；mem0 不可用时显式报错  
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/ask/services/mem0_sync_service.py`
- `config.json`
- `backend/ask/services/memory_service.py`

**验收标准**:
- [ ] 用户画像和会话记忆写入实际调用 mem0
- [ ] 记忆检索实际调用 mem0
- [ ] mem0 不可用时记忆相关能力显式报错，不发生 PostgreSQL-only 降级

---

### TASK-memory-management-API-006 实现 Memory API 路由

**关联需求**: REQ-memory-management-管理与可视化  
**描述**: 新增 `memory_api.py`，提供用户画像、会话记忆、事件审计查询和归档/删除接口，并挂载到 `backend_api_agno.py`。  
**技术要点**: Bearer token 权限；普通用户只看自己；admin/manager 可筛选用户  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/api/memory_api.py`
- `backend_api_agno.py`

**验收标准**:
- [ ] `GET /memory/user` 返回当前用户画像
- [ ] `GET /memory/session/{chat_id}` 返回当前会话记忆
- [ ] `PUT /memory/{scope}/{id}` 可手动修改记忆内容
- [ ] 归档/删除操作写入事件表
- [ ] 越权访问返回 403

---

### TASK-memory-management-前端-007 实现记忆管理页面

**关联需求**: REQ-memory-management-管理与可视化  
**描述**: 新增记忆管理页面，支持用户画像、会话记忆、事件审计查询和归档/删除。  
**技术要点**: 复用现有管理页风格；详情抽屉；API 封装  
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/MemoryManager.jsx`
- `frontend/src/components/MemoryDetailDrawer.jsx`
- `frontend/src/services/api.js`
- `frontend/src/App.jsx`
- `frontend/src/components/Sidebar.jsx`

**验收标准**:
- [ ] 侧边栏可进入记忆管理页
- [ ] 可查询用户画像和会话记忆
- [ ] 可查看完整记忆详情
- [ ] 可手动修改用户画像记忆
- [ ] 可归档/删除记忆

---

### TASK-memory-management-会话面板-008 实现会话记忆面板

**关联需求**: REQ-memory-management-会话记忆  
**描述**: 在聊天页提供当前会话记忆查看入口，支持手动总结当前会话。  
**技术要点**: 按 chat_id 加载；面板不影响主消息流  
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/SessionMemoryPanel.jsx`
- `frontend/src/App.jsx`
- `frontend/src/services/api.js`

**验收标准**:
- [ ] 当前会话可打开会话记忆面板
- [ ] 可手动触发会话总结
- [ ] 可手动修改当前会话摘要记忆
- [ ] 错误会话记忆可归档

---

### TASK-memory-management-删除联动-009 会话删除时清理会话记忆

**关联需求**: REQ-memory-management-会话记忆  
**描述**: 会话删除时同步清理或归档 `askbi_session_profile_memory`，并写审计事件。  
**技术要点**: BI/Excel/general/team 删除链路统一调用 MemoryService  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/api/bi_api.py`
- `backend/ask/api/excel_api.py`
- `backend/ask/services/memory_service.py`

**验收标准**:
- [ ] 删除会话后查询不到活跃会话记忆
- [ ] 删除事件写入 `askbi_memory_events`

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| v1.0 | 2026-06-15 | 初始版本：拆分数据层、服务层、注入、抽取、mem0、API、前端任务 | zhangqiyuan |

---

**文档结束**
