# 后端设计文档

**版本**: v1.0
**模块**: 数据大屏 (dashboard)
**关联需求**: REQ-dashboard

---

## 业务流程

### 大屏生成流程
接收文件上传 → 保存源文件 → 解析个人维度数据 → 解析部门维度数据 → 提取月份 → 生成 data.js → 渲染模板 HTML → 内联资源 → 保存 → 记录元数据

### 大屏管理流程
列表查询 → 静态资源服务 → 截图 → 删除

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 大屏文件按用户隔离存储 | dashboard_files/user_{id}/{dashboard_id}/ |
| R002 | 大屏 HTML 为独立自包含文件 | CSS/JS/数据全部内联 |
| R003 | 静态文件服务限制在目录内 | 路径穿越检测 (realpath 前缀检查) |
| R004 | 截图使用 Playwright Chromium | 2560x1440 视口 |
| R005 | 月份优先从文件名提取 | 正则匹配 YYYY年M月 |
| R006 | 大屏类型为 dashboard | report_type = 'dashboard' |

---

## 数据表设计

复用 askbi_reports 表:
- report_type = 'dashboard'
- detail_file: 个人维度文件名
- summary_file: 空 (大屏不需要汇总表)
- original_file: 生成的 HTML 文件名

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 生成大屏 | POST | /dashboard/generate | REQ-dashboard-生成大屏 |
| 大屏列表 | GET | /dashboard/list | REQ-dashboard-大屏管理 |
| 静态资源 | GET | /dashboard/static/{dashboard_id}/{path} | REQ-dashboard-大屏管理 |
| 截图 | GET | /dashboard/static/{dashboard_id}/screenshot | REQ-dashboard-截图功能 |
| 删除大屏 | DELETE | /dashboard/{dashboard_id} | REQ-dashboard-大屏管理 |

### POST /dashboard/generate

**请求类型**: multipart/form-data

**参数**: personal_file, dept_file, month (可选)

**响应**:
```json
{
  "success": true,
  "dashboard_id": "dashboard_xxx",
  "row_count": 100,
  "month": "2026年05月",
  "display_file_name": "人力资源效能分析大屏_2026年05月"
}
```

---

## 核心类

### generate_dashboard (dashboard_preview/generate_dashboard.py)
- generate_data_from_both — 解析个人+部门维度数据
- save_data_js — 生成 data.js 数据文件

### 大屏模板 (dashboard_preview/style4_business_cyan/)
- index.html — 大屏 HTML 模板
- css/style.css — 样式
- js/dashboard.js — 交互逻辑
- shared/echarts.min.js — ECharts 库
- shared/data.js — 数据文件 (生成时替换)
