# 任务清单

**版本**: v1.0
**模块**: 数据源管理 (datasource)
**关联需求**: REQ-datasource

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-datasource-管理器-001 | [后端] 实现 DataSourceManager | REQ-datasource-数据源CRUD | P0 | 已完成 |
| TASK-datasource-PG连接器-002 | [后端] 实现 PostgreSQL 连接器 | REQ-datasource-数据源CRUD | P0 | 已完成 |
| TASK-datasource-MySQL连接器-003 | [后端] 实现 MySQL 连接器 | REQ-datasource-数据源CRUD | P0 | 已完成 |
| TASK-datasource-Excel连接器-004 | [后端] 实现 Excel 连接器 | REQ-datasource-数据源CRUD | P1 | 已完成 |
| TASK-datasource-API-005 | [后端] 实现数据源管理 API | REQ-datasource-数据源CRUD | P0 | 已完成 |
| TASK-datasource-元数据-006 | [后端] 实现元数据生成与存储 | REQ-datasource-元数据生成 | P0 | 已完成 |
| TASK-datasource-跨Schema-007 | [后端] 实现跨 Schema 支持 | REQ-datasource-跨Schema支持 | P1 | 已完成 |
| TASK-datasource-前端配置-008 | [前端] 实现数据源配置界面 | REQ-datasource-数据源CRUD | P0 | 已完成 |
| TASK-datasource-前端元数据-009 | [前端] 实现元数据查看器 | REQ-datasource-元数据生成 | P1 | 已完成 |

---

## 任务详情

### TASK-datasource-管理器-001 DataSourceManager

**关联需求**: REQ-datasource-数据源CRUD
**描述**: 实现数据源管理器，支持配置加载/保存、连接管理、CRUD 操作
**技术要点**: JSON 配置管理, 连接池缓存, 文件操作
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `datasources/datasource_manager.py`

**验收标准**:
- [ ] 配置正确加载与保存
- [ ] 连接缓存正常工作
- [ ] 用户隔离 (user_{id}:name)

---

### TASK-datasource-PG连接器-002 PostgreSQL 连接器

**关联需求**: REQ-datasource-数据源CRUD
**描述**: 实现 PostgreSQLConnector，支持连接/查询/元数据获取
**技术要点**: psycopg2, DictCursor, information_schema 查询
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `datasources/pgsql.py`

**验收标准**:
- [ ] 连接测试正常
- [ ] 表列表正确返回
- [ ] 列信息正确返回
- [ ] SQL 执行正常

---

### TASK-datasource-MySQL连接器-003 MySQL 连接器

**关联需求**: REQ-datasource-数据源CRUD
**描述**: 实现 MySQLConnector
**技术要点**: pymysql, information_schema
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `datasources/mysql.py`

**验收标准**:
- [ ] 连接测试正常
- [ ] 表列表与列信息正确

---

### TASK-datasource-Excel连接器-004 Excel 连接器

**关联需求**: REQ-datasource-数据源CRUD
**描述**: 实现 ExcelConnector
**技术要点**: pandas, Excel 元数据提取
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `datasources/excel.py`

**验收标准**:
- [ ] Excel 文件元数据正确提取
- [ ] Sheet 列表与列信息正确

---

### TASK-datasource-API-005 数据源管理 API

**关联需求**: REQ-datasource-数据源CRUD
**描述**: 实现数据源 CRUD / 测试连接 / 表信息查询路由
**技术要点**: FastAPI, 文件上传, 用户权限过滤
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 所有 CRUD 路由正常
- [ ] 连接测试返回正确结果
- [ ] 批量删除正确统计

---

### TASK-datasource-元数据-006 元数据生成与存储

**关联需求**: REQ-datasource-元数据生成
**描述**: 实现元数据生成逻辑，PG 存 DB，Excel 存文件
**技术要点**: schema_generator, db_utils.upsert_chat_knowledge
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `utils/schema_generator.py`
- `backend/legacy_routes.py`

**验收标准**:
- [ ] PG 元数据存入数据库
- [ ] Excel 元数据存入文件
- [ ] 元数据包含表/列/注释/样例

---

### TASK-datasource-跨Schema-007 跨 Schema 支持

**关联需求**: REQ-datasource-跨Schema支持
**描述**: 实现 PostgreSQL 多 Schema 元数据获取
**技术要点**: 多 Schema 遍历, 全名标识
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `datasources/pgsql.py`
- `datasources/datasource_manager.py`

**验收标准**:
- [ ] 多 Schema 配置正确
- [ ] 跨 Schema 元数据完整
- [ ] 表名使用全名格式

---

### TASK-datasource-前端配置-008 数据源配置界面

**关联需求**: REQ-datasource-数据源CRUD
**描述**: 实现数据源列表、创建表单、测试连接、删除
**技术要点**: React, 表单验证, 动态表单 (不同类型不同字段)
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/DataSourceConfig.jsx`

**验收标准**:
- [ ] 列表正确展示
- [ ] 创建表单按类型动态展示
- [ ] 测试连接反馈正常
- [ ] Excel 文件上传正常

---

### TASK-datasource-前端元数据-009 元数据查看器

**关联需求**: REQ-datasource-元数据生成
**描述**: 实现 SchemaViewer 组件，树形展示数据源元数据
**技术要点**: React 树形组件
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/SchemaViewer.jsx`

**验收标准**:
- [ ] 树形展开正常
- [ ] 列信息与样例数据正确展示
- [ ] 支持折叠/展开
