# 后端设计文档

**版本**: v1.0
**模块**: 报表生成 (report)
**关联需求**: REQ-report

---

## 业务流程

### 报表生成流程
接收文件上传 → 查找报表规则 → 保存源文件 → 调用对应生成器 → 保存报表文件 → 记录元数据 → 返回结果

### 报表管理流程
列表查询 (按用户过滤) → 预览 (读取 Excel) → 下载 (文件流) → 删除 (清理目录+记录)

### 脱敏流程
读取原始文件 → 检测/应用脱敏配置 → 保存脱敏文件 → 更新数据库 → 切换时删除/恢复

### 报表问数流程
查找报表文件 → 创建 Excel 问数会话 → 复制文件 → 调用 Excel 问数接口

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | 报表规则从全局配置加载 | db_utils.list_global_configs("report_rule") |
| R002 | 报表文件按用户隔离存储 | report_files/user_{id}/{report_id}/ |
| R003 | 脱敏文件名包含"脱敏"标识 | 文件名约定 |
| R004 | 四种报表类型对应不同生成器 | report_type 路由分发 |
| R005 | 报表问数复用 Excel 问数流程 | 调用 excel_api.ask_api |
| R006 | NaN/Inf 值在 JSON 响应中清理 | _clean_json_rows 函数 |
| R007 | 用户仅可查看自己的报表 | user_id 过滤 |

---

## 数据表设计

复用 askbi_reports 表，report_type 区分报表类型:
- report_type = '人事考勤报表' / '部门维度考勤报表' / '多月个人维度报表' / '多月部门维度报表' / 'dashboard'

---

## 接口设计

### 接口清单

| 接口 | 方法 | 路径 | 关联需求 |
|------|------|------|----------|
| 生成报表 | POST | /report/generate | REQ-report-生成报表 |
| 报表列表 | GET | /report/list | REQ-report-报表管理 |
| 下载报表 | GET | /report/download/{report_id} | REQ-report-报表管理 |
| 删除报表 | DELETE | /report/{report_id} | REQ-report-报表管理 |
| 重命名报表 | PUT | /report/{report_id}/rename | REQ-report-报表管理 |
| 预览数据 | GET | /report/preview/{report_id} | REQ-report-报表管理 |
| 全量数据 | GET | /report/full-data/{report_id} | REQ-report-报表管理 |
| 更新数据 | PUT | /report/update/{report_id} | REQ-report-报表管理 |
| 脱敏切换 | POST | /report/desensitize | REQ-report-数据脱敏 |
| 脱敏方法列表 | GET | /report/desensitize/methods | REQ-report-数据脱敏 |
| 脱敏预览 | GET | /report/desensitize/preview?report_id= | REQ-report-数据脱敏 |
| 报表问数 | POST | /report/ask-question | REQ-report-报表问数 |
| 创建问数会话 | POST | /report/create | REQ-report-报表问数 |
| AI 改表 | POST | /report/ai-edit | REQ-report-AI改表 (占位) |
| ReportRunner 生成 | POST | /reports/generate | REQ-report-ReportRunner报表 |
| 会话报表下载 | GET | /reports/download/{chat_id}/{filename} | REQ-report-报表会话管理 |
| 会话报表列表 | GET | /reports/list/{chat_id} | REQ-report-报表会话管理 |

### POST /report/generate

**请求类型**: multipart/form-data

**参数**: detail_file, summary_file, report_type, rule (可选), report_name

**响应**:
```json
{
  "success": true,
  "report_id": "report_xxx",
  "report_type": "人事考勤报表",
  "row_count": 100,
  "column_count": 15,
  "yellow_cells_count": 5,
  "problem_count": 3,
  "summary_text": "...",
  "preview_data": [...],
  "columns": [...],
  "file_path": "/path/to/report",
  "display_file_name": "人力考勤报表.xlsx"
}
```

---

## 核心类

### ReportGenerator (core/report_generator.py)
- generate_hr_attendance_report — 人事考勤报表

### DeptReportGenerator (core/dept_report_generator.py)
- generate_dept_report — 部门维度考勤报表

### MultiMonthReportGenerator (core/multi_month_report_generator.py)
- generate_multi_month_report_from_raw — 多月个人维度报表

### MultiMonthDeptReportGenerator (core/multi_month_dept_report_generator.py)
- generate_multi_month_dept_report_from_raw — 多月部门维度报表

### Desensitize (utils/desensitize.py)
- auto_detect_column_desensitize — 自动检测敏感列
- desensitize_dataframe_by_columns — 按列配置脱敏
- get_available_desensitize_methods — 获取可用脱敏方法列表
