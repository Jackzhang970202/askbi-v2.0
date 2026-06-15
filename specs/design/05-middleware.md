# 中间件设计

**版本**: v1.0

---

## 设计原则

| 原则 | 说明 |
|------|------|
| 统一入口 | 所有中间件与工具通过 config/ 和 utils/ 统一管理 |
| 配置外置 | 数据库配置、模型配置存放在 config.json |
| 异常处理 | 各层独立异常处理，向上层传递 |
| 单一职责 | 每个工具类负责一种中间件或数据库操作 |

## 目录结构

```
config/
├── config_db.py       # 数据库配置 + 模型加载
└── config_handler.py  # 配置文件路径查找 + RAG 配置

utils/
├── db_utils.py              # 数据库工具 (继承 PgDatabaseUtils)
├── pg_db_utils.py           # PostgreSQL 基础工具
├── auth_utils.py            # 认证工具 (Token 缓存/用户获取)
├── datasource_sql_executor.py # SQL 执行器 (基于 datasource_manager)
├── schema_generator.py      # 元数据生成器
├── white_list_utils.py      # 白名单工具
├── desensitize.py           # 数据脱敏工具
└── general_utils.py         # 通用工具
```

## 数据库连接管理

### 应用数据库 (app_db)
- **Schema**: askbi_table
- **用途**: 存储用户、会话、消息、报表、配置等应用数据
- **配置**: config.json → app_db_config
- **工具类**: DatabaseUtils (utils/db_utils.py)

### 业务数据库 (db)
- **Schema**: jiceng
- **用途**: 连接用户业务数据库执行 BI 问数 SQL
- **配置**: config.json → db_config
- **工具类**: PgDatabaseUtils (utils/pg_db_utils.py)

### 数据源连接器
| 连接器 | 技术 | 用途 |
|--------|------|------|
| PostgreSQLConnector | psycopg2 | 连接用户 PG 数据库 |
| MySQLConnector | pymysql | 连接用户 MySQL 数据库 |
| ExcelConnector | pandas | 读取 Excel 文件 |
| DataSourceManager | 统一管理器 | 统一管理所有数据源 |

## 缓存机制

| 缓存类型 | 实现 | 用途 |
|----------|------|------|
| Token 缓存 | 内存字典 (TOKEN_CACHE) | 登录 Token → 用户信息映射 |
| 进度缓存 | 内存字典 (ProgressService._cache) | BI/Excel 任务进度缓存 |
| 连接缓存 | DataSourceManager.active_connections | 数据源连接复用 |

## 异常处理

| 层级 | 处理方式 |
|------|----------|
| API 层 | try/except + JSONResponse 返回错误 |
| Workflow 层 | 抛出 ValueError (如非 SELECT SQL) |
| 数据源层 | 测试连接返回 {success, message} |
| 数据库层 | execute_query 捕获异常并 rollback |

## 认证机制

| 项目 | 说明 |
|------|------|
| Token 生成 | secrets.token_hex(32) |
| Token 存储 | 内存字典 (进程重启后失效) |
| 获取方式 | Authorization: Bearer {token} 请求头 |
| 角色判断 | is_admin_or_manager() 判断 admin/manager |
| 默认用户 | 启动时自动创建 admin/admin123 |

## 文件存储

| 目录 | 用途 |
|------|------|
| runtime/excel_uploads/ | Excel 临时上传 |
| runtime/excel_chats/ | Excel 会话文件 |
| datasources/excel_files/ | 数据源 Excel 文件 |
| report_files/user_{id}/ | 用户报表文件 |
| dashboard_files/user_{id}/ | 用户大屏文件 |
| refer/{datasource_name}/ | 数据源元数据文件 |
| split_files/user_{id}/ | 报表问数文件切分 |
| knowledge/ | 全局知识文件 |
