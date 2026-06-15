# 任务清单

**版本**: v1.0
**模块**: 数据大屏 (dashboard)
**关联需求**: REQ-dashboard

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-dashboard-生成-001 | [后端] 实现大屏生成 API | REQ-dashboard-生成大屏 | P0 | 已完成 |
| TASK-dashboard-模板-002 | [后端] 实现大屏模板渲染与资源内联 | REQ-dashboard-生成大屏 | P0 | 已完成 |
| TASK-dashboard-管理API-003 | [后端] 实现大屏管理 API | REQ-dashboard-大屏管理 | P0 | 已完成 |
| TASK-dashboard-截图-004 | [后端] 实现 Playwright 截图 | REQ-dashboard-截图功能 | P1 | 已完成 |
| TASK-dashboard-前端列表-005 | [前端] 实现大屏列表与生成表单 | REQ-dashboard-大屏管理 | P0 | 已完成 |
| TASK-dashboard-前端预览-006 | [前端] 实现大屏预览 | REQ-dashboard-大屏管理 | P0 | 已完成 |

---

## 任务详情

### TASK-dashboard-生成-001 大屏生成 API

**关联需求**: REQ-dashboard-生成大屏
**描述**: 实现 /dashboard/generate 路由，处理文件上传与数据解析
**技术要点**: 文件上传, 数据解析, 月份提取
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`
- `dashboard_preview/generate_dashboard.py`

**验收标准**:
- [ ] 文件正确保存
- [ ] 数据正确解析
- [ ] 月份正确提取
- [ ] 元数据正确记录

---

### TASK-dashboard-模板-002 模板渲染与资源内联

**关联需求**: REQ-dashboard-生成大屏
**描述**: 将模板 CSS/JS/数据内联到 HTML，生成自包含文件
**技术要点**: 模板字符串替换, 文件读写
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`
- `dashboard_preview/style4_business_cyan/`

**验收标准**:
- [ ] HTML 为自包含文件
- [ ] 可在浏览器直接打开
- [ ] 图表正常渲染

---

### TASK-dashboard-管理API-003 大屏管理 API

**关联需求**: REQ-dashboard-大屏管理
**描述**: 实现大屏列表/静态资源/删除路由
**技术要点**: 静态文件服务, 路径安全, mimetypes
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 列表按用户过滤
- [ ] 静态资源正确返回
- [ ] 路径穿越被阻止

---

### TASK-dashboard-截图-004 Playwright 截图

**关联需求**: REQ-dashboard-截图功能
**描述**: 使用 Playwright 对大屏进行高质量截图
**技术要点**: Playwright, Chromium, viewport 设置
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 截图分辨率 2560x1440
- [ ] 标题可自定义
- [ ] 返回有效 PNG

---

### TASK-dashboard-前端列表-005 大屏列表与生成表单

**关联需求**: REQ-dashboard-大屏管理
**描述**: 实现大屏列表页面与生成表单
**技术要点**: React, 文件上传
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/` (新增大屏管理组件)

**验收标准**:
- [ ] 列表正确加载
- [ ] 生成表单正常
- [ ] 删除确认正常

---

### TASK-dashboard-前端预览-006 大屏预览

**关联需求**: REQ-dashboard-大屏管理
**描述**: 实现大屏预览功能 (iframe 或新窗口)
**技术要点**: iframe 嵌入 / 新窗口打开
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/` (大屏预览组件)

**验收标准**:
- [ ] 大屏正常显示
- [ ] 图表交互正常
- [ ] 截图下载正常
