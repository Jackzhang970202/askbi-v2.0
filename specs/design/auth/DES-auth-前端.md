# 前端设计文档

**版本**: v1.0
**模块**: 用户认证 (auth)
**关联需求**: REQ-auth

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 登录页 | /login | 登录表单 | REQ-auth-登录登出 |
| 用户管理 | 弹窗/页面 | 列表 + 表单 | REQ-auth-用户信息管理 |

---

## 登录页设计

### 页面结构
居中的登录表单: 用户名输入框 + 密码输入框 + 登录按钮

### 交互流程
1. 用户输入用户名密码
2. 调用 POST /auth/login
3. 登录成功: 保存 token (localStorage/sessionStorage)
4. 登录失败: 显示错误信息
5. 登录后跳转到主页面

### 组件: LoginPage
- 用户名输入
- 密码输入 (type=password)
- 登录按钮
- 错误提示

### 认证状态管理
- Token 存储在 localStorage 或内存中
- 请求时自动附加 Authorization: Bearer {token} header
- 401 响应自动跳转登录页

---

## 用户管理设计

### 页面结构
操作按钮 (创建用户) → 数据表格 (用户名、角色、创建时间、操作)

### 交互流程
1. 加载用户列表 (GET /auth/users)
2. 仅 admin 可见
3. 点击"创建用户"打开表单
4. 填写用户名、密码、角色
5. 提交创建
6. 列表刷新

### 行操作
- **修改密码**: 输入新密码，提交
- **删除用户**: 确认删除

### 组件
- **UserManager**: 用户管理组件
- **Modal**: 创建用户/修改密码弹窗

### 接口
- POST /auth/login — 登录
- POST /auth/logout — 登出
- GET /auth/me — 获取当前用户
- GET /auth/users — 用户列表 (admin)
- POST /auth/users — 创建用户 (admin)
- DELETE /auth/users/{user_id} — 删除用户 (admin)
- PATCH /auth/users/{user_id}/password — 修改密码 (admin)

### 权限控制
- 用户管理仅 admin 可见
- 非 admin 访问用户管理显示权限不足
