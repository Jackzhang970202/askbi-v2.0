# 用户认证模块 - 需求文档

**版本**: v1.0
**模块**: 用户认证 (auth)

---

## REQ-auth-登录登出

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
用户通过用户名和密码登录，获取 Bearer Token；支持登出操作使 Token 失效。

### 前置条件
- 用户已注册 (admin 默认自动创建)

### 输入
- 登录: username, password
- 登出: Authorization header

### 输出
- 登录: {success, token, user}
- 登出: {success, message}

### 处理规则
1. 登录时验证 username 与 password_hash (SHA-256)
2. 验证成功生成随机 token (secrets.token_hex(32))
3. token 与用户信息存入 TOKEN_CACHE 内存字典
4. 返回 token 与用户信息 (id, username, role, create_time)
5. 登出时从 TOKEN_CACHE 中移除对应 token
6. 登出无需 token (但支持带 token 的登出)

### 验收标准
- [ ] 正确用户名密码登录返回 token 与用户信息
- [ ] 错误用户名密码返回 401
- [ ] 登出后 token 失效
- [ ] 默认 admin/admin123 可登录

---

## REQ-auth-用户信息管理

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
管理员可创建用户、删除用户、修改用户密码；用户可查看自己的信息。

### 前置条件
- 操作人具有 admin 权限 (创建/删除/改密码)
- 用户已登录

### 输入
- 创建: username, password, role (默认 user)
- 列表: 无
- 删除: user_id
- 修改密码: user_id, new_password
- 当前用户: 无

### 输出
- 创建: {success, message}
- 列表: 用户列表
- 删除: {success, message}
- 修改密码: {success, message}
- 当前用户: 用户信息

### 处理规则
1. 创建用户时检查用户名不重复
2. 密码使用 SHA-256 哈希存储
3. 角色只能是 admin/manager/user
4. 列表返回所有用户 (仅 admin)
5. 删除用户时 CASCADE 清理关联会话、消息、记录
6. 修改密码仅 admin 可操作
7. 当前用户接口返回 401 如果未登录

### 验收标准
- [ ] 创建用户成功且可登录
- [ ] 重复用户名创建失败
- [ ] 删除用户后无法用该用户登录
- [ ] 修改密码后旧密码失效
- [ ] 非 admin 无法操作用户管理
- [ ] 未登录访问 /auth/me 返回 401

---

## REQ-auth-RBAC权限

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
系统支持三种角色: admin (超级管理员)、manager (管理者)、user (普通用户)，不同角色有不同的数据可见范围。

### 前置条件
- 用户已登录

### 输入
- 用户角色 (从 token 解析)

### 输出
- 数据可见性取决于角色

### 处理规则
1. admin: 可查看所有用户的数据源、会话、报表、大屏
2. manager: 同 admin，可查看所有数据
3. user: 仅可查看自己创建的数据
4. is_admin_or_manager() 函数判断是否有全局查看权限
5. require_admin() 函数限制仅 admin 可执行的操作
6. 数据创建时关联 user_id，查询时根据角色过滤

### 验收标准
- [ ] admin 可查看所有用户数据
- [ ] manager 可查看所有数据
- [ ] user 仅可查看自己的数据
- [ ] 管理员操作 (用户管理) 仅 admin 可执行

---

## REQ-auth-白名单

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P2

### 需求描述
系统维护 SQL 表级白名单，用于控制 BI 问数时可查询的数据库表。

### 前置条件
- 管理员操作

### 输入
- username (添加到白名单)

### 输出
- 白名单状态

### 处理规则
1. 白名单存储在 askbi_white_list 表
2. username 唯一 (UNIQUE 约束)
3. 通过 white_list_utils 管理
4. 白名单用户可访问 refer_list 文件夹中定义的表
5. 用于 BI 问数时的 SQL 安全补充控制

### 验收标准
- [ ] 用户可加入白名单
- [ ] 白名单用户唯一
- [ ] 白名单与 SQL 表访问控制关联