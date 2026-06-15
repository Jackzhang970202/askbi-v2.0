# 非功能需求

**版本**: v1.0

---

## NFR-性能-响应时间

| 场景 | 要求 |
|------|------|
| API 响应 | < 2秒 (健康检查、列表查询等简单接口) |
| BI 问数 | 依赖 LLM 生成，通常 10-30秒 |
| Excel 问数 | 依赖 LLM + 代码执行，通常 15-45秒 |
| 报表生成 | 依赖 LLM + Excel 处理，通常 30-120秒 |
| 大屏生成 | 依赖数据处理+模板渲染，通常 15-60秒 |

## NFR-性能-并发

| 指标 | 说明 |
|------|------|
| 并发用户 | 支持多用户同时使用，Token 为内存缓存 |
| 单表数据量 | PostgreSQL 支持百万级数据，BI 问数 SQL 由 LLM 生成需关注性能 |
| Excel 文件大小 | 受 pandas 内存限制，建议单文件 < 50MB |

## NFR-安全-认证

| 项目 | 说明 |
|------|------|
| 认证方式 | Bearer Token (内存缓存，进程重启后失效) |
| Token 有效期 | 进程生命周期 (无过期机制) |
| 权限模型 | RBAC (admin / manager / user) |
| 密码存储 | SHA-256 哈希 (非 BCrypt，需后续改进) |
| 默认账户 | admin/admin123 (启动时自动创建) |

## NFR-安全-数据安全

| 项目 | 说明 |
|------|------|
| SQL 安全 | 仅允许 SELECT 查询，检测 INSERT/UPDATE/DELETE/ALTER/DROP/CREATE/TRUNCATE 并拦截 |
| 数据隔离 | 用户级 owner_id 隔离数据源、报表、大屏 |
| 跨角色可见 | admin/manager 可查看所有用户数据 |
| 脱敏功能 | 报表支持列级数据脱敏 |
| 路径安全 | 静态文件服务限制在指定目录内，防止路径穿越 |

## NFR-可用-兼容

| 项目 | 说明 |
|------|------|
| 浏览器 | Chrome / Firefox / Edge / Safari (最新2版本) |
| 分辨率 | ≥ 1366x768 |
| 大屏分辨率 | 2560x1440 (截图与预览) |

## NFR-维护-规范

| 项目 | 说明 |
|------|------|
| 代码规范 | Python 代码遵循 PEP 8 |
| 类型注解 | 后端使用 from __future__ import annotations |
| 模块解耦 | agents / workflows / api / services 分层清晰 |
| 配置管理 | 所有配置集中在 config.json，通过 config/ 模块读取 |

## NFR-可观测-进度推送

| 项目 | 说明 |
|------|------|
| 进度机制 | ProgressService 内存缓存 + 轮询 API |
| BI 进度 | /progress?chatid=&offset= 增量获取 |
| Excel 进度 | /excel/progress?chatid= 获取事件列表 |
