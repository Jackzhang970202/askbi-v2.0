# 前端设计文档

**版本**: v1.0
**模块**: 报表生成 (report)
**关联需求**: REQ-report

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 报表列表 | 主页面 | 列表 | REQ-report-报表管理 |
| 报表生成 | 弹窗/页面 | 表单 + 文件上传 | REQ-report-生成报表 |
| 报表预览 | 主页面 | 数据表格 | REQ-report-报表管理 |
| 报表编辑 | 弹窗 | 表单 (脱敏配置/数据编辑) | REQ-report-数据脱敏 |
| 报表问数 | 主页面 | 聊天式交互 | REQ-report-报表问数 |

---

## 报表列表页设计

### 页面结构
操作按钮 (新建报表) → 数据表格 (报表名称、类型、状态、创建时间、操作)

### 交互流程
1. 加载报表列表 (GET /report/list)
2. 点击"新建"打开报表生成表单
3. 上传明细表与汇总表
4. 选择报表类型
5. 提交生成，等待结果
6. 列表刷新

### 行操作
- **预览**: 打开预览弹窗，展示前10行数据
- **下载**: 下载报表文件 (可选脱敏版本)
- **脱敏**: 打开脱敏配置，切换脱敏状态
- **问数**: 基于报表创建问数会话
- **重命名**: 修改展示文件名
- **删除**: 确认删除

---

## 脱敏配置设计

### 页面结构
列列表 → 每列脱敏方式选择 (无/隐藏/部分隐藏/哈希) → 预览 → 确认

### 交互流程
1. 打开脱敏预览 (GET /report/desensitize/preview)
2. 系统自动检测敏感列 (auto_detect_column_desensitize)
3. 用户调整脱敏方式
4. 获取可用脱敏方法列表 (GET /report/desensitize/methods)
5. 提交脱敏 (POST /report/desensitize)
6. 预览脱敏效果

### 组件
- **ReportEditor**: 报表编辑弹窗，含脱敏配置
- **ReportManager**: 报表列表管理

### 接口
- POST /report/generate — 生成报表
- GET /report/list — 报表列表
- GET /report/download/{report_id} — 下载
- DELETE /report/{report_id} — 删除
- PUT /report/{report_id}/rename — 重命名
- GET /report/preview/{report_id} — 预览
- POST /report/desensitize — 脱敏切换
- GET /report/desensitize/methods — 脱敏方法
- GET /report/desensitize/preview — 脱敏列预览
- POST /report/ask-question — 报表问数
- POST /report/create — 创建问数会话
