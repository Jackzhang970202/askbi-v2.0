# 后端设计文档

**版本**: v1.0
**模块**: 用户认证 (auth)
**关联需求**: REQ-auth

---

## 业务流程

### 登录流程
接收用户名密码 → SHA-256 哈希比对 → 生成 token → 存入 TOKEN_CACHE → 返回 token + 用户信息

### 用户管理流程
管理员操作 → 验证 admin 权限 → CRUD 操作 → 返回结果

### 认证流程
解析 Authorization header → 提取 token → 查找 TOKEN_CACHE → 返回用户信息或 401

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | Token 为内存缓存 | TOKEN_CACHE 字典 |
| R002 | 密码使用 SHA-256 哈希 | hashlib.sha256 |
| R003 | 默认 admin 账户自动创建 | db_utils.create_default_admin() |
| R004 | 用户名唯一 | 数据库 UNIQUE 约束 |
| R005 | admin 可管理所有用户 | require_admin 检查 |
| R006 | 角色分三级: admin/manager/user | role 字段 |
| R007 | 删除用户 CASCADE 清理关联数据 | 外键 ON DELETE CASCADE |

---

## 数据表设计

### askbi_users

| 字段 | 类型 | 可空 | 默认值 | 说明 |
|------|------|------|--------|------|
| id | SERIAL | 否 | 自增 | 主键 |
| username | TEXT | 否 | - | 用户名 (UNIQUE) |
| password_hash | TEXT | 否 | - | SHA-256 哈希 |
| role | TEXT | 否 | 'user' | admin/manager/user |
| create_time | TIMESTAMP | 否 | CURRENT_TIMESTAMP | 创建时间 |

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 登录 | POST | /auth/login | REQ-auth-登录登出 |
| 登出 | POST | /auth/logout | REQ-auth-登录登出 |
| 当前用户 | GET | /auth/me | REQ-auth-登录登出 |
| 用户列表 | GET | /auth/users | REQ-auth-用户信息管理 |
| 创建用户 | POST | /auth/users | REQ-auth-用户信息管理 |
| 删除用户 | DELETE | /auth/users/{user_id} | REQ-auth-用户信息管理 |
| 修改密码 | PATCH | /auth/users/{user_id}/password | REQ-auth-用户信息管理 |

### POST /auth/login

**请求体**: `{ username, password }`

**响应**:
```json
{
  "success": true,
  "token": "abc123...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "create_time": "2026-01-01T00:00:00"
  }
}
```

### POST /auth/users

**请求体**: `{ username, password, role (默认 "user") }`

**响应**: `{ success, message }`

---

## 核心函数

### auth_utils.py

| 函数 | 说明 |
|------|------|
| `generate_token()` | 生成随机 token (secrets.token_hex(32)) |
| `get_current_user(request)` | 从 Authorization header 解析用户 |
| `require_auth(request)` | 要求认证，否则抛异常 |
| `require_admin(request)` | 要求 admin 权限，否则抛异常 |
| `is_admin_or_manager(user)` | 判断是否为 admin 或 manager |

### db_utils.py (用户相关)

| 方法 | 说明 |
|------|------|
| `create_default_admin()` | 创建默认 admin 账户 |
| `create_user(username, password, role)` | 创建用户 |
| `verify_user(username, password)` | 验证用户 |
| `get_user_by_id(user_id)` | 按 ID 获取用户 |
| `list_users()` | 列出所有用户 |
| `delete_user(user_id)` | 删除用户 |
| `update_user_password(user_id, new_password)` | 修改密码 |
