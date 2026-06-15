# 后端设计文档

**版本**: v1.0
**模块**: 数据源管理 (datasource)
**关联需求**: REQ-datasource

---

## 业务流程

### 创建数据源流程
接收参数 → 验证类型 → 测试连接 → 生成存储键 (user_{id}:name) → 保存配置 → Excel 类型保存文件 → 返回结果

### 元数据生成流程
判断跨Schema模式 → 获取表列表 → 获取列信息/注释/样例 → 存储到 DB 或文件 → 返回结果

### 删除数据源流程
关闭活跃连接 → 删除配置 → 清理文件目录 (Excel) → 清理 refer/ 元数据目录 → 返回结果

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 数据源存储键包含 owner 隔离 | user_{owner_id}:{name} |
| R002 | 创建时测试连接 (非 Excel) | connector.test_connection() |
| R003 | Excel 文件保存到数据源目录 | datasources/excel_files/user_{id}/{name}/ |
| R004 | PostgreSQL 支持 schemas 配置 | 多 Schema 支持 |
| R005 | 元数据 PG/MySQL 存 DB，Excel 存文件 | db_utils.upsert_chat_knowledge / save_schema_to_refer |
| R006 | 列表按用户权限过滤 | is_admin_or_manager 判断 |
| R007 | 删除时清理所有关联数据 | 连接、文件、元数据目录 |
| R008 | 连接复用通过 active_connections 缓存 | DataSourceManager.active_connections |

---

## 数据表设计

配置存储:
- datasources_config.json — 数据源配置 (JSON 文件)
- askbi_chat_knowledge — PG/MySQL 数据源的元数据 (schema_data 字段)
- refer/{name}/*.json — Excel 数据源的元数据文件

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 列表 | GET | /datasources | REQ-datasource-数据源CRUD |
| 创建 | POST | /datasources | REQ-datasource-数据源CRUD |
| 详情 | GET | /datasources/{name} | REQ-datasource-数据源CRUD |
| 删除 | DELETE | /datasources/{name} | REQ-datasource-数据源CRUD |
| 批量删除 | POST | /datasources/batch_delete | REQ-datasource-数据源CRUD |
| 测试连接 | POST | /datasources/{name}/test | REQ-datasource-连接测试 |
| 元数据生成 | POST | /datasources/{name}/generate_metadata | REQ-datasource-元数据生成 |
| 表列表 | GET | /datasources/{name}/tables | REQ-datasource-表与列信息查询 |
| 列信息 | GET | /datasources/{name}/tables/{schema}/{table}/columns | REQ-datasource-表与列信息查询 |
| 元数据查看 | GET | /refer/schema?datasource_name= | REQ-datasource-元数据生成 |

### POST /datasources

**请求类型**: application/json 或 multipart/form-data

**JSON 请求体**: `{ name, type, config, knowledge_id }`

**Form 请求体 (Excel)**: name, type=excel, knowledge_id, file (多个), table_header_rows, sub_name_rows

**响应**: `{ success, message, name, display_name }`

### POST /datasources/{name}/generate_metadata

**响应**:
```json
{
  "success": true,
  "message": "元数据生成并已存入数据库",
  "tables_count": 10,
  "storage": "database",
  "is_cross_schema": false
}
```

---

## 核心类

### DataSourceManager (datasources/datasource_manager.py)

| 方法 | 说明 |
|------|------|
| `__init__(config_file)` | 加载 datasources_config.json |
| `_load_config()` | 读取配置文件 |
| `_save_config()` | 保存配置文件 |
| `add_datasource(name, type, config, knowledge_id, owner_id)` | 添加数据源 |
| `remove_datasource(name)` | 删除数据源 |
| `get_datasource(name)` | 获取配置 |
| `list_datasources()` | 列出所有数据源 |
| `get_connector(name)` | 获取连接器 (带连接缓存) |
| `test_datasource(name)` | 测试连接 |
| `get_tables(name, schema)` | 获取表列表 |
| `get_table_columns(name, schema, table)` | 获取列信息 |
| `is_cross_schema(name)` | 检查是否跨 Schema |
| `get_datasource_schemas(name)` | 获取 Schema 列表 |
| `get_cross_schema_metadata(name)` | 获取跨 Schema 元数据 |

### PostgreSQLConnector (datasources/pgsql.py)
- connect / test_connection / get_tables / get_table_columns / execute_query
- get_tables_for_schemas / get_schemas_list / get_cross_schema_metadata

### MySQLConnector (datasources/mysql.py)
- connect / test_connection / get_tables / get_table_columns / execute_query

### ExcelConnector (datasources/excel.py)
- connect / test_connection / get_tables / get_table_columns

### KnowledgeManager (datasources/knowledge_manager.py)
- add_kb / remove_kb / list_kbs
