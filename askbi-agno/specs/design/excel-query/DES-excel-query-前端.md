# 前端设计文档

**版本**: v1.1
**模块**: Excel 问数 (excel-query)
**关联需求**: REQ-excel-query

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| Excel 问数页 | 主页面 | 聊天式交互 + 文件上传 | REQ-excel-query-自然语言分析 |
| Excel 会话列表 | Sidebar 侧边栏 | 列表 | REQ-excel-query-会话管理 |
| 文件预览页 | 主页面 | 数据表格 | REQ-excel-query-会话管理 |

---

## 问数页设计

### 页面结构
侧边栏（Excel 会话列表） → 主内容区（消息列表 + ChatInput 输入框 + 文件上传）

### 交互流程
1. 用户切换到 Excel 问数模式
2. 上传一个或多个 Excel 文件
3. 系统创建会话并返回 chat_id
4. 用户输入分析问题，并可选择是否需要分析解读
5. 轮询 `GET /excel/progress` 获取事件进度
6. 接收完整响应后展示统一回答结构与图表
7. 可切换到文件预览查看原始数据或处理后数据

### 组件
- **Sidebar**：显示 Excel 会话列表（文件名、文件数）
- **ChatInput**：文本输入、文件上传、分析解读开关
- **MessageItem**：展示用户消息与 AI 回复
  - `summary` 渲染主回答正文
  - `code` 折叠展示
  - `chart` 使用 `EChart` 渲染
  - `trace/result` 用于调试与扩展展示
- **文件预览**：展示 Excel 文件的 sheet、列名、前 50 行数据

### 主回答展示规范
`MessageItem` 展示顺序：
1. 问题结果、结论
2. 回答依据、佐证
3. 数据图表
4. 分析解读（存在时展示）

说明：
- 当前前端不拆解 `summary` 字段，而是直接渲染 Markdown
- 因此后端需确保 `summary` 文本内部顺序稳定、标题清晰
- 图表区块独立于正文渲染，通过 `chart` 字段控制

### 图表展示规范
- 当 `chart.chart_needed === false` 时，不渲染图表，仅保留正文
- 当 `chart` 为合法 ECharts option 且包含 `series` 时，渲染图表卡片
- 图表类型由后端生成，前端不做二次推断

### 文件预览规范
- 文件预览用于支撑回答依据核验，不与主回答混排
- 支持原始文件与处理后文件切换
- 支持按 sheet 维度展示数据

### 流式展示规范
- 流式正文来源为 `structuredData.summary`
- 历史回放正文来源为 `structuredData.summary`
- 若无结构化数据，则回退 `content`

### 接口
- `POST /excel/upload_file` — 上传文件
- `POST /excel/ask` — 发送问题
- `GET /excel/progress` — 事件进度
- `GET /excel/list_sessions` — 会话列表
- `GET /excel/sessions/{chat_id}/messages` — 历史消息
- `GET /excel/get_file_data` — 文件预览数据
- `GET /excel/delete_chat` — 删除会话
- `POST /excel/init_from_datasource` — 从数据源初始化

### 错误处理
- 文件上传失败：展示错误
- 代码执行失败：展示错误堆栈
- 图表配置无效：不渲染图表
- 文件不存在：展示错误
- 网络错误：统一错误提示
