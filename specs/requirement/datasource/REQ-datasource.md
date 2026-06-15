# 数据源管理模块 - 需求文档

**版本**: v1.0
**模块**: 数据源管理 (datasource)

---

## REQ-datasource-数据源CRUD

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
支持数据源的创建、查询、详情查看、删除 (含批量删除)。

### 前置条件
- 用户已登录

### 输入
- 创建: name, type (pgsql/mysql/excel), config, knowledge_id, 文件 (Excel 类型)
- 列表: 无
- 详情: name
- 删除: name (单个/批量)
- 测试连接: name

### 输出
- 创建: {success, message, name, display_name}
- 列表: 数据源列表 (含 owner_username)
- 详情: 数据源配置
- 删除: {success, message}
- 测试: {success, message, version}

### 处理规则
1. 数据源存储键格式: user_{owner_id}:{name} (有 owner) 或 {name} (无 owner)
2. 创建时测试连接 (非 Excel 类型)
3. Excel 类型: 保存上传文件到 datasources/excel_files/user_{id}/{name}/
4. PostgreSQL 类型: 支持 schemas 字段 (跨 Schema 模式)
5. 列表时 admin/manager 可查看所有数据源，普通用户仅看自己的
6. 删除时关闭活跃连接，清理文件目录与 refer/ 元数据目录
7. 显示名称 (display_name) 去掉 user_{id}: 前缀供 UI 使用

### 验收标准
- [ ] 数据源创建成功并测试连接
- [ ] 列表正确按用户过滤
- [ ] 详情返回完整配置
- [ ] 删除后连接、文件、元数据已清理
- [ ] 批量删除正确统计成功/失败数
- [ ] Excel 文件正确保存到数据源目录

---

## REQ-datasource-元数据生成

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
为数据源生成表结构元数据，供 BI 问数使用。

### 前置条件
- 数据源已创建且连接正常

### 输入
- name (数据源名称)

### 输出
- 元数据 (表数量、存储方式、是否跨Schema)

### 处理规则
1. 判断是否为跨 Schema 模式 (is_cross_schema)
2. 跨 Schema 模式:
   - 获取所有配置的 Schema 列表
   - 获取每个 Schema 的表列表、列信息、表注释、样例数据
   - 构建完整元数据 (table_index + tables)
3. 单 Schema 模式:
   - 获取当前 Schema 的表结构与样例数据
4. PostgreSQL/MySQL 数据源: 元数据存储到 askbi_chat_knowledge.schema_data
5. Excel 数据源: 元数据存储到 refer/{name}/ 目录下的 JSON 文件

### 验收标准
- [ ] 单 Schema 模式正确生成元数据
- [ ] 跨 Schema 模式正确获取所有 Schema 的表信息
- [ ] 元数据存储到正确位置 (DB 或文件)
- [ ] 元数据包含表名、列信息、注释、样例数据
- [ ] 无表的数据源返回错误

---

## REQ-datasource-表与列信息查询

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
获取数据源的表列表与表的列信息。

### 前置条件
- 数据源已创建

### 输入
- 表列表: name
- 列信息: name, schema, table

### 输出
- 表列表: [{schema, table, full_name}]
- 列信息: [{name, type, max_length, nullable, default}]

### 处理规则
1. 通过 DataSourceManager.get_connector 获取数据源连接
2. PostgreSQL/MySQL 连接器实现 get_tables 与 get_table_columns
3. 表列表可按 schema 过滤
4. 列信息从 information_schema.columns 查询

### 验收标准
- [ ] 表列表正确返回
- [ ] 列信息正确返回
- [ ] 不存在的数据源/表返回错误

---

## REQ-datasource-连接测试

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
测试数据源连接是否正常。

### 前置条件
- 数据源已配置

### 输入
- name (数据源名称)

### 输出
- {success, message, version} (PostgreSQL)
- {success, message} (其他)

### 处理规则
1. 获取数据源连接器
2. 执行测试连接 (PostgreSQL 执行 SELECT version())
3. 返回测试结果
4. 连接池中的活跃连接会被复用

### 验收标准
- [ ] 正常连接返回 success=true
- [ ] 错误配置返回 success=false 与错误信息
- [ ] PostgreSQL 返回数据库版本信息

---

## REQ-datasource-跨Schema支持

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
PostgreSQL 数据源支持配置多个 Schema，BI 问数时可跨 Schema 查询。

### 前置条件
- PostgreSQL 数据源配置了 schemas 或 is_cross_schema=true

### 输入
- schemas 配置 (可选)
- is_cross_schema 标识

### 输出
- 跨 Schema 元数据
- 跨 Schema 表列表

### 处理规则
1. 添加数据源时检测 schemas 数量 > 1 设置 is_cross_schema
2. 如未显式指定 schemas 但 is_cross_schema=true，自动从数据库获取所有 Schema
3. get_tables_for_schemas 获取多个 Schema 的表
4. get_cross_schema_metadata 获取完整跨 Schema 元数据
5. 表名使用 schema.table 全名格式

### 验收标准
- [ ] 多 Schema 配置正确识别
- [ ] 自动获取 Schema 列表功能正常
- [ ] 跨 Schema 元数据包含所有 Schema 的表
- [ ] 表名使用全名格式 (schema.table)
