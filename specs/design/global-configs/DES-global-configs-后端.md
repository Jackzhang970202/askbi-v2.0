# 后端设计文档

**版本**: v1.0
**模块**: 全局配置 (global-configs)
**关联需求**: REQ-global-configs

---

## 业务流程

### 配置列表流程
接收 category (可选) → 判断用户角色 → 按权限过滤 → 返回列表

### 配置创建/更新流程
接收参数 → upsert 到数据库 → 返回结果

### 配置删除流程
接收 config_id → 删除记录 → 返回结果

### 启用切换流程
接收 config_id + is_enabled → 更新 is_enabled 字段 → 返回结果

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 配置按 category 分类 | category 字段 |
| R002 | 配置按用户隔离 | user_id 字段 |
| R003 | 唯一约束: (category, name, user_id) | 数据库约束 |
| R004 | content 为 JSONB 格式 | JSONB 存储 |
| R005 | admin/manager 可查看所有配置 | is_admin_or_manager 判断 |
| R006 | 普通用户仅看自己的或全局配置 | WHERE user_id = ? OR user_id IS NULL |
| R007 | scope_type/scope_datasources 控制作用范围 | JSONB 数组存储 |

---

## 数据表设计

复用 askbi_global_configs 表:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | 主键 |
| category | TEXT | 配置分类 |
| name | TEXT | 配置名称 |
| content | JSONB | 配置内容 |
| is_enabled | BOOLEAN | 是否启用 |
| scope_type | TEXT | 范围类型 |
| scope_datasources | JSONB | 关联数据源列表 |
| user_id | INTEGER | 用户 ID |
| update_time | TIMESTAMP | 更新时间 |

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 配置列表 | GET | /global_configs?category= | REQ-global-configs-配置CRUD |
| 创建/更新 | POST | /global_configs | REQ-global-configs-配置CRUD |
| 删除 | DELETE | /global_configs/{config_id} | REQ-global-configs-配置CRUD |
| 切换启用 | PATCH | /global_configs/{config_id}/toggle | REQ-global-configs-配置CRUD |

### POST /global_configs

**请求体**: `{ category, name, content, is_enabled, id (更新时), scope_type, scope_datasources }`

**响应**: `{ success, message }`

### GET /global_configs

**参数**: category (可选)

**响应**: `{ success, configs: [...] }`

---

## 核心方法

### DatabaseUtils (utils/db_utils.py)

| 方法 | 说明 |
|------|------|
| `list_global_configs(category, user_id, is_admin)` | 按权限列出配置 |
| `upsert_global_config(category, name, content, is_enabled, config_id, scope_type, scope_datasources, user_id)` | 创建/更新配置 |
| `delete_global_config(config_id)` | 删除配置 |
| `toggle_global_config(config_id, is_enabled)` | 切换启用状态 |
