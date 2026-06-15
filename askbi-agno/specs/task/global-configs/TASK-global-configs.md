# 任务清单

**版本**: v1.0
**模块**: 全局配置 (global-configs)
**关联需求**: REQ-global-configs

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-global-configs-API-001 | [后端] 实现全局配置 CRUD API | REQ-global-configs-配置CRUD | P0 | 已完成 |
| TASK-global-configs-权限-002 | [后端] 实现用户权限过滤 | REQ-global-configs-配置CRUD | P0 | 已完成 |
| TASK-global-configs-报表规则-003 | [后端] 实现报表规则加载逻辑 | REQ-global-configs-报表规则 | P0 | 已完成 |
| TASK-global-configs-前端列表-004 | [前端] 实现配置列表与编辑界面 | REQ-global-configs-配置CRUD | P0 | 已完成 |

---

## 任务详情

### TASK-global-configs-API-001 全局配置 CRUD API

**关联需求**: REQ-global-configs-配置CRUD
**描述**: 实现 /global_configs 的 CRUD 路由
**技术要点**: FastAPI, db_utils, JSONB 处理
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] GET/POST/DELETE/PATCH 路由正常
- [ ] upsert 操作正确 (创建/更新)
- [ ] 切换启用状态正常

---

### TASK-global-configs-权限-002 用户权限过滤

**关联需求**: REQ-global-configs-配置CRUD
**描述**: 实现按用户角色的配置可见性控制
**技术要点**: is_admin_or_manager, user_id 过滤
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`
- `utils/db_utils.py`

**验收标准**:
- [ ] admin/manager 查看所有配置
- [ ] 普通用户仅看自己的或全局配置

---

### TASK-global-configs-报表规则-003 报表规则加载

**关联需求**: REQ-global-configs-报表规则
**描述**: 报表生成时正确加载匹配的 rule 配置
**技术要点**: category 过滤, name 匹配, is_enabled 判断
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`
- `core/report_generator.py` (相关调用)

**验收标准**:
- [ ] 报表生成找到匹配的 rule
- [ ] 未找到返回错误
- [ ] 用户 rule 可覆盖配置

---

### TASK-global-configs-前端列表-004 配置列表与编辑界面

**关联需求**: REQ-global-configs-配置CRUD
**描述**: 实现全局配置列表与编辑表单
**技术要点**: React, JSON 编辑器, 分类过滤
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/` (新建配置管理组件)

**验收标准**:
- [ ] 按 category 过滤
- [ ] JSON 内容可编辑
- [ ] 启用/禁用切换正常
- [ ] 创建/删除正常
