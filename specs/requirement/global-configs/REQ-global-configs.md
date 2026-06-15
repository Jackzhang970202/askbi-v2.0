# 全局配置模块 - 需求文档

**版本**: v1.0
**模块**: 全局配置 (global-configs)

---

## REQ-global-configs-配置CRUD

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
管理系统全局配置，支持分类管理、启用/禁用、作用范围控制。

### 前置条件
- 用户已登录

### 输入
- 列表: category (可选)
- 创建/更新: category, name, content (JSON), is_enabled, id (更新时), scope_type, scope_datasources
- 删除: config_id
- 切换启用: config_id, is_enabled

### 输出
- 列表: 配置列表
- 创建/更新: {success, message}
- 删除: {success, message}
- 切换: {success, message}

### 处理规则
1. 配置存储在 askbi_global_configs 表
2. 按 category 分类 (如 report_rule)
3. content 为 JSONB 格式的配置内容
4. scope_type 定义范围类型 (universal / datasource)
5. scope_datasources 为关联数据源列表 (JSONB 数组)
6. user_id 隔离配置 (同一 category+name 不同用户可不同)
7. 唯一约束: (category, name, user_id)
8. admin/manager 可查看所有配置，普通用户仅看自己的或全局的 (user_id IS NULL)

### 验收标准
- [ ] 配置正确创建与更新 (upsert)
- [ ] 按 category 过滤正常
- [ ] 按用户权限过滤正确
- [ ] 删除操作正常
- [ ] 启用/禁用切换正常

---

## REQ-global-configs-报表规则

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
全局配置中 category=report_rule 的配置项用于定义报表生成规则。

### 前置条件
- 报表规则已配置

### 输入
- 报表名称 (name)

### 输出
- 规则内容: { rule, headers }

### 处理规则
1. 报表生成时查找 category=report_rule 且 name 匹配且 is_enabled=true 的配置
2. content 包含 rule (规则字符串) 和 headers (表头列表)
3. 未找到启用规则时返回错误
4. 用户可在请求中提供 rule 覆盖配置中的规则

### 验收标准
- [ ] 报表生成正确加载匹配的规则
- [ ] 未启用规则不被使用
- [ ] 用户提供的 rule 可覆盖配置
