# 数据模型规范

**版本**: v2.0

---

## 命名规范

### 表命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 应用表 | askbi_{表名} | askbi_users |

### 字段命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 主键 | id / chat_id | id, chat_id |
| 外键 | {实体}_id | user_id, chat_id |
| 状态 | {实体}_status | - |
| 布尔 | is_{描述} | is_enabled, is_desensitized |

### 索引命名

当前项目未显式创建命名索引，依赖主键约束。

## 数据库表结构

所有表位于 `askbi_table` Schema (由 config.json 的 app_db_config.database_schema 指定)。

| 表名 | 用途 | 主键 |
|------|------|------|
| askbi_users | 用户表 | id (SERIAL) |
| askbi_chat_session | 会话表 | chat_id (TEXT) |
| askbi_messages | 消息表 | id (SERIAL) |
| askbi_request_record | 请求记录表 | record_id (SERIAL) |
| askbi_general_metadata | 通用元数据表 | metadata_id (TEXT) |
| askbi_chat_knowledge | 数据源知识表 | datasource_name (TEXT) |
| askbi_global_configs | 全局配置表 | id (SERIAL) |
| askbi_reports | 报表/大屏记录表 | id (SERIAL) |
| askbi_white_list | 用户白名单表 | id (SERIAL) |
| askbi_skills | 技能定义表 (新增) | id (SERIAL) |
| askbi_agents | 智能体配置表 (新增) | id (SERIAL) |

## 核心表定义

### askbi_users

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| username | TEXT | 否 | - | 用户名(唯一) |
| password_hash | TEXT | 否 | - | SHA-256 密码哈希 |
| role | TEXT | 否 | 'user' | 角色: admin/manager/user |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

### askbi_chat_session

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| chat_id | TEXT | 否 | - | 会话ID(主键) |
| knowledge_id | TEXT | 是 | - | 关联知识库ID |
| datasource_name | TEXT | 是 | - | 数据源名称 |
| user_id | INTEGER | 是 | - | 用户ID(FK→users) |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

### askbi_messages

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| chat_id | TEXT | 否 | - | 会话ID(FK→chat_session) |
| user_id | INTEGER | 是 | - | 用户ID(FK→users) |
| role | TEXT | 否 | - | 角色: user/assistant |
| content | TEXT | 是 | - | 消息内容 |
| structured_data | JSONB | 是 | - | 结构化数据(SQL/图表/结果) |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

### askbi_request_record

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| record_id | SERIAL | 否 | 自增 | 主键 |
| chat_id | TEXT | 否 | - | 会话ID(FK→chat_session) |
| user_id | INTEGER | 是 | - | 用户ID(FK→users) |
| knowledge_id | TEXT | 是 | - | 知识库ID |
| user_question | TEXT | 否 | - | 用户问题 |
| retrieved_knowledge | JSONB | 否 | - | 检索到的知识 |
| generated_sql | TEXT | 是 | - | 生成的SQL |
| execution_result | JSONB | 是 | - | 执行结果 |
| round_number | INTEGER | 是 | 1 | 对话轮次 |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

### askbi_chat_knowledge

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| datasource_name | TEXT | 否 | - | 数据源名称(主键) |
| content | TEXT | 是 | - | 知识内容 |
| vocabulary | JSONB | 是 | '[]' | 业务词汇表 |
| reference_sql | JSONB | 是 | '[]' | 参考SQL集 |
| schema_data | JSONB | 是 | null | 表结构元数据 |
| update_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 更新时间 |

### askbi_global_configs

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| category | TEXT | 否 | - | 配置分类(如report_rule) |
| name | TEXT | 否 | - | 配置名称 |
| content | JSONB | 否 | - | 配置内容 |
| is_enabled | BOOLEAN | 是 | TRUE | 是否启用 |
| scope_type | TEXT | 是 | 'universal' | 范围类型 |
| scope_datasources | JSONB | 是 | '[]' | 关联数据源列表 |
| user_id | INTEGER | 是 | - | 用户ID(FK→users) |
| update_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 更新时间 |

### askbi_reports

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| report_id | TEXT | 否 | - | 报表ID(唯一) |
| user_id | INTEGER | 是 | - | 用户ID(FK→users) |
| report_type | TEXT | 否 | - | 类型: 报表/大屏 |
| detail_file | TEXT | 是 | - | 明细文件名 |
| summary_file | TEXT | 是 | - | 汇总文件名 |
| original_file | TEXT | 是 | - | 输出文件名 |
| file_path | TEXT | 是 | - | 文件存储路径 |
| desensitized_file | TEXT | 是 | - | 脱敏文件名 |
| is_desensitized | BOOLEAN | 是 | FALSE | 是否已脱敏 |
| row_count | INTEGER | 是 | 0 | 行数 |
| column_count | INTEGER | 是 | 0 | 列数 |
| yellow_cells_count | INTEGER | 是 | 0 | 标黄单元格数 |
| problem_count | INTEGER | 是 | 0 | 问题数 |
| display_file_name | TEXT | 是 | - | 展示文件名 |
| status | TEXT | 是 | 'success' | 状态 |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

### askbi_skills (新增)

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| skill_name | TEXT | 否 | - | 技能名称(唯一) |
| category | TEXT | 否 | 'general' | 分类: sql/chart/report/general |
| description | TEXT | 是 | - | 技能描述 |
| instructions | TEXT | 否 | - | 技能指令(提示词文本) |
| is_enabled | BOOLEAN | 否 | TRUE | 是否启用 |
| owner_id | INTEGER | 是 | - | 创建者用户ID |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |
| update_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 更新时间 |

### askbi_agents (新增)

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| agent_name | TEXT | 否 | - | Agent名称(唯一, 如 bi_sql_agent) |
| display_name | TEXT | 否 | - | 展示名称 |
| custom_instructions | TEXT | 是 | null | 自定义指令(覆盖默认INSTRUCTIONS) |
| model_name | TEXT | 是 | null | 自定义模型名(覆盖config.json默认) |
| temperature | REAL | 是 | null | 自定义温度(覆盖默认值) |
| skill_ids | JSONB | 是 | '[]' | 绑定的技能ID列表 |
| is_enabled | BOOLEAN | 否 | TRUE | 是否启用 |
| update_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 更新时间 |

## 字段类型

| 类型 | 使用场景 |
|------|----------|
| SERIAL | 自增主键 |
| TEXT | 字符串(不限制长度) |
| INTEGER | 计数、外键、轮次 |
| REAL | 浮点数(温度等) |
| JSONB | 结构化数据(配置/结果/元数据/ID列表) |
| TIMESTAMP | 时间戳 |
| BOOLEAN | 开关状态 |

## 外部数据源元数据存储

| 存储方式 | 说明 |
|----------|------|
| DB (askbi_chat_knowledge.schema_data) | PostgreSQL/MySQL 数据源的表结构元数据 |
| 文件 (refer/{datasource_name}/*_metadata.json) | Excel 或回退模式的元数据文件 |
