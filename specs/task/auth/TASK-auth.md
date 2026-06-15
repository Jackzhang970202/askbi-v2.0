# 任务清单

**版本**: v1.0
**模块**: 用户认证 (auth)
**关联需求**: REQ-auth

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-auth-认证工具-001 | [后端] 实现认证工具函数 | REQ-auth-登录登出 | P0 | 已完成 |
| TASK-auth-用户表-002 | [后端] 实现用户表与 CRUD | REQ-auth-用户信息管理 | P0 | 已完成 |
| TASK-auth-API-003 | [后端] 实现认证 API 路由 | REQ-auth-登录登出 | P0 | 已完成 |
| TASK-auth-用户管理API-004 | [后端] 实现用户管理 API | REQ-auth-用户信息管理 | P0 | 已完成 |
| TASK-auth-前端登录-005 | [前端] 实现登录页面 | REQ-auth-登录登出 | P0 | 已完成 |
| TASK-auth-前端状态-006 | [前端] 实现认证状态管理 | REQ-auth-登录登出 | P0 | 已完成 |
| TASK-auth-前端管理-007 | [前端] 实现用户管理界面 | REQ-auth-用户信息管理 | P0 | 已完成 |

---

## 任务详情

### TASK-auth-认证工具-001 认证工具函数

**关联需求**: REQ-auth-登录登出
**描述**: 实现 Token 生成/缓存、用户获取、权限判断
**技术要点**: secrets.token_hex, 内存字典, request header 解析
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `utils/auth_utils.py`

**验收标准**:
- [ ] Token 生成随机性
- [ ] Token 缓存查找正确
- [ ] 角色判断正确

---

### TASK-auth-用户表-002 用户表与 CRUD

**关联需求**: REQ-auth-用户信息管理
**描述**: 实现用户表创建与 CRUD 方法
**技术要点**: PostgreSQL DDL, SHA-256 哈希, CASCADE
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `utils/db_utils.py`
- `config/config_db.py`

**验收标准**:
- [ ] 用户表正确创建
- [ ] 默认 admin 账户自动创建
- [ ] CRUD 操作正常

---

### TASK-auth-API-003 认证 API 路由

**关联需求**: REQ-auth-登录登出
**描述**: 实现登录/登出/当前用户路由
**技术要点**: SHA-256 密码验证, Token 管理
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 登录成功返回 token
- [ ] 错误凭据返回 401
- [ ] 登出后 token 失效
- [ ] 当前用户信息正确

---

### TASK-auth-用户管理API-004 用户管理 API

**关联需求**: REQ-auth-用户信息管理
**描述**: 实现用户列表/创建/删除/密码修改路由
**技术要点**: admin 权限校验
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 仅 admin 可访问
- [ ] 用户 CRUD 正常
- [ ] 密码修改后旧密码失效

---

### TASK-auth-前端登录-005 登录页面

**关联需求**: REQ-auth-登录登出
**描述**: 实现登录表单页面
**技术要点**: React 表单, 错误提示
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/LoginPage.jsx`

**验收标准**:
- [ ] 登录表单正常
- [ ] 错误提示正确
- [ ] 登录成功跳转

---

### TASK-auth-前端状态-006 认证状态管理

**关联需求**: REQ-auth-登录登出
**描述**: 实现前端认证状态管理 (token 存储、请求拦截)
**技术要点**: localStorage, fetch/axios 拦截器
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/main.jsx`
- `frontend/src/utils/StreamingManager.js`

**验收标准**:
- [ ] Token 正确存储
- [ ] 请求自动附加 token
- [ ] 401 自动跳转登录

---

### TASK-auth-前端管理-007 用户管理界面

**关联需求**: REQ-auth-用户信息管理
**描述**: 实现用户管理界面 (仅 admin 可见)
**技术要点**: React, 权限控制, 表单
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/UserManager.jsx`

**验收标准**:
- [ ] 仅 admin 可见
- [ ] 用户列表正常
- [ ] 创建/删除/改密码正常
