# 前端设计文档

**版本**: v1.1
**模块**: BI 问数 (bi-query)
**关联需求**: REQ-bi-query

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| BI 问数页 | 主页面 | 聊天式交互 | REQ-bi-query-自然语言问数 |
| BI 会话列表 | Sidebar 侧边栏 | 列表 | REQ-bi-query-会话管理 |
| BI 会话消息 | 主页面 | 消息列表 | REQ-bi-query-会话管理 |

---

## 问数页设计

### 页面结构
侧边栏（会话列表） → 主内容区（消息列表 + ChatInput 输入框）

### 交互流程
1. 用户选择或创建 BI 会话
2. 调用 `POST /create_chat` 创建会话
3. 用户输入问题，并可选择是否需要分析解读
4. 调用 `POST /ask` 发送问题
5. 轮询 `GET /progress` 获取进度文本展示
6. 接收完整响应后展示统一回答结构与图表
7. 刷新会话列表

### 组件
- **Sidebar**：显示 BI 会话列表，支持切换与删除
- **ChatInput**：文本输入、发送问题、分析解读开关
- **MessageItem**：展示用户消息与 AI 回复
  - `summary` 渲染主回答正文
  - `sql` 代码块折叠展示
  - `chart` 使用 `EChart` 渲染
  - `thoughts` 使用 `ThinkingProcess` 展示
- **SchemaViewer**：数据源元数据查看

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

### 流式展示规范
- 流式正文来源为 `structuredData.summary`
- 历史回放正文来源为 `structuredData.summary`
- 若无结构化数据，则回退 `content`

### 接口
- `POST /create_chat` — 创建会话
- `POST /ask` — 发送问题
- `GET /progress` — 进度轮询
- `GET /bi/sessions` — 会话列表
- `GET /bi/sessions/{chat_id}/messages` — 历史消息
- `DELETE /bi/sessions/{chat_id}` — 删除会话

### 错误处理
- SQL 生成失败：展示错误信息
- SQL 执行失败：展示错误信息
- 图表配置无效：不渲染图表
- 网络错误：统一错误提示
