# 任务清单

**版本**: v1.0
**模块**: 报表生成 (report)
**关联需求**: REQ-report

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-report-人事报表-001 | [后端] 实现人事考勤报表生成器 | REQ-report-生成报表 | P0 | 已完成 |
| TASK-report-部门报表-002 | [后端] 实现部门维度报表生成器 | REQ-report-生成报表 | P0 | 已完成 |
| TASK-report-多月个人-003 | [后端] 实现多月个人报表生成器 | REQ-report-生成报表 | P0 | 已完成 |
| TASK-report-多月部门-004 | [后端] 实现多月部门报表生成器 | REQ-report-生成报表 | P0 | 已完成 |
| TASK-report-生成API-005 | [后端] 实现报表生成 API 路由 | REQ-report-生成报表 | P0 | 已完成 |
| TASK-report-管理API-006 | [后端] 实现报表管理 API | REQ-report-报表管理 | P0 | 已完成 |
| TASK-report-脱敏-007 | [后端] 实现数据脱敏功能 | REQ-report-数据脱敏 | P1 | 已完成 |
| TASK-report-问数-008 | [后端] 实现报表问数功能 | REQ-report-报表问数 | P1 | 已完成 |
| TASK-report-前端列表-009 | [前端] 实现报表列表与管理界面 | REQ-report-报表管理 | P0 | 已完成 |
| TASK-report-前端脱敏-010 | [前端] 实现脱敏配置界面 | REQ-report-数据脱敏 | P1 | 已完成 |
| TASK-report-配置-011 | [后端] 实现报表配置管理 | REQ-report-报表配置 | P1 | 已完成 |
| TASK-report-Runner-012 | [后端] 实现 ReportRunner 报表生成 | REQ-report-ReportRunner报表 | P0 | 已完成 |
| TASK-report-会话-013 | [后端] 实现报表会话管理 API | REQ-report-报表会话管理 | P1 | 已完成 |
| TASK-report-AI改表-014 | [后端] 实现 AI 改表功能 | REQ-report-AI改表 | P2 | 进行中 |

---

## 任务详情

### TASK-report-人事报表-001 人事考勤报表生成器

**关联需求**: REQ-report-生成报表
**描述**: 实现 ReportGenerator.generate_hr_attendance_report
**技术要点**: pandas 数据处理, Excel 写入, 规则解析
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `core/report_generator.py`

**验收标准**:
- [ ] 正确解析明细表与汇总表
- [ ] 按规则生成报表
- [ ] 标黄与问题计数正确

---

### TASK-report-部门报表-002 部门维度报表生成器

**关联需求**: REQ-report-生成报表
**描述**: 实现 DeptReportGenerator.generate_dept_report
**技术要点**: pandas 按部门聚合
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `core/dept_report_generator.py`

**验收标准**:
- [ ] 部门维度聚合正确
- [ ] 统计指标计算正确

---

### TASK-report-多月个人-003 多月个人报表生成器

**关联需求**: REQ-report-生成报表
**描述**: 实现 MultiMonthReportGenerator.generate_multi_month_report_from_raw
**技术要点**: 多月数据合并, 个人维度聚合
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `core/multi_month_report_generator.py`

**验收标准**:
- [ ] 多月数据正确合并
- [ ] 个人维度统计正确

---

### TASK-report-多月部门-004 多月部门报表生成器

**关联需求**: REQ-report-生成报表
**描述**: 实现 MultiMonthDeptReportGenerator.generate_multi_month_dept_report_from_raw
**技术要点**: 多月+部门维度聚合
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `core/multi_month_dept_report_generator.py`

**验收标准**:
- [ ] 多月+部门聚合正确

---

### TASK-report-生成API-005 报表生成 API

**关联需求**: REQ-report-生成报表
**描述**: 实现 /report/generate 路由
**技术要点**: 文件上传, 规则查找, 生成器路由
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 四种报表类型正确路由
- [ ] 文件保存到用户目录
- [ ] 元数据记录正确

---

### TASK-report-管理API-006 报表管理 API

**关联需求**: REQ-report-报表管理
**描述**: 实现报表列表/预览/下载/删除/重命名等路由
**技术要点**: 文件流返回, Excel 预览, NaN 清理
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 列表按用户过滤
- [ ] 下载文件正确
- [ ] 预览数据 NaN 处理正确

---

### TASK-report-脱敏-007 数据脱敏功能

**关联需求**: REQ-report-数据脱敏
**描述**: 实现列级脱敏功能，含自动检测与多种脱敏方法
**技术要点**: 列类型检测, 脱敏算法 (隐藏/部分隐藏/哈希)
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `utils/desensitize.py`
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 自动检测敏感列
- [ ] 脱敏方法正确应用
- [ ] 脱敏文件正确保存

---

### TASK-report-问数-008 报表问数功能

**关联需求**: REQ-report-报表问数
**描述**: 实现基于报表的问数功能，复用 Excel 问数流程
**技术要点**: 文件复制, 会话创建, API 调用
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 报表文件正确复制到问数会话
- [ ] 问数功能正常工作

---

### TASK-report-前端列表-009 报表列表与管理界面

**关联需求**: REQ-report-报表管理
**描述**: 实现报表列表页面，含生成、预览、下载、删除
**技术要点**: React, 文件上传, 数据表格
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/ReportManager.jsx`
- `frontend/src/components/ReportEditor.jsx`

**验收标准**:
- [ ] 列表正确加载
- [ ] 报表生成表单正常
- [ ] 预览与下载正常

---

### TASK-report-前端脱敏-010 脱敏配置界面

**关联需求**: REQ-report-数据脱敏
**描述**: 实现脱敏配置弹窗，含列选择与脱敏方法选择
**技术要点**: 表单组件, 数据预览
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/ReportEditor.jsx`

**验收标准**:
- [ ] 脱敏方法列表正确展示
- [ ] 列配置界面友好
- [ ] 预览效果实时更新
