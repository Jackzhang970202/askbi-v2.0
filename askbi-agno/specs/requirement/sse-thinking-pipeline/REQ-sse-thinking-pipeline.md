# SSE 思考流水线模块 - 需求文档

**版本**: v1.0
**模块**: SSE 思考流水线 (sse-thinking-pipeline)

---

## REQ-sse-thinking-pipeline-SSE推送

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
将现有 HTTP 轮询进度机制替换为 SSE（Server-Sent Events）实时推送。后端使用 asyncio.Queue 为每个 chatid 维护事件队列，通过 SSE 端点实时推送结构化的阶段事件给前端。前端使用 fetch + ReadableStream（而非 EventSource）以支持 Bearer Token 认证。保留现有轮询端点以确保向后兼容。

### 前置条件
- 后端服务正常运行（FastAPI 端口 8002）
- 用户已登录并持有有效 Bearer Token
- 工作流（BI 问数或 Excel 分析）开始执行

### 输入
- chatid（会话标识）
- Bearer Token（用于 SSE 连接认证）

### 输出
- SSE 事件流，每个事件为结构化 JSON：
  ```json
  {
    "stage": "sql_generation",
    "status": "running",
    "message": "正在生成 SQL 查询...",
    "timestamp": 1234567890,
    "duration_ms": 1200,
    "metadata": {}
  }
  ```
- 终止事件：`stage="__done__"` 或 `stage="__error__"`

### 处理规则
1. 每个 chatid 维护独立的 asyncio.Queue 事件队列
2. 工作流各阶段调用 emit_stage_event() 推送结构化事件
3. SSE 端点使用 async generator 流式返回事件
4. 线程安全：非 async 上下文通过 loop.call_soon_threadsafe() 推送事件
5. 连接断开后自动清理队列资源
6. 保留 GET /progress?chatid=X&offset=0 轮询端点向后兼容

### 验收标准
- [ ] SSE 端点可正常建立连接并接收事件流
- [ ] 事件格式符合 JSON 规范
- [ ] Bearer Token 认证正常工作
- [ ] 连接断开后资源正确清理
- [ ] 原有轮询端点仍可正常工作

---

## REQ-sse-thinking-pipeline-Pipeline展示

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
将现有终端风格的思考过程 UI 重新设计为结构化流水线视图。使用浅色卡片设计 + 垂直时间线布局，每个阶段显示为独立卡片，包含图标、阶段名称、耗时、可折叠详情。支持平滑动画过渡，SQL 步骤支持语法高亮，错误状态红色高亮显示。

### 前置条件
- SSE 事件流正常推送
- 前端已加载聊天界面

### 输入
- SSE 阶段事件流（stage、status、message、duration_ms、metadata）
- 历史消息的 thoughts 数据（用于回放）

### 输出
- 结构化流水线 UI，包含：
  - 垂直时间线连接各阶段卡片
  - 每个阶段卡片：图标 + 名称 + 状态 + 耗时 + 可折叠详情
  - 运行中阶段的脉冲动画
  - 完成阶段的勾选标记
  - 错误阶段的红色高亮 + 错误信息
  - SQL 步骤的语法高亮代码块

### 处理规则
1. 阶段按时间顺序从上到下排列
2. 运行中阶段显示脉冲动画和旋转图标
3. 完成阶段显示勾选图标和耗时（如"1.2s"）
4. 错误阶段卡片边框和背景变为红色系
5. 点击阶段卡片可展开/折叠详情
6. SQL 代码使用 highlight.js 或 prism.js 进行语法高亮
7. 新阶段出现时平滑滚动到可见区域

### 验收标准
- [ ] 流水线 UI 正确渲染各阶段卡片
- [ ] 阶段状态变化时有平滑动画过渡
- [ ] 运行中阶段有脉冲动画效果
- [ ] 错误阶段红色高亮显示
- [ ] 阶段详情可正常展开/折叠
- [ ] SQL 代码语法高亮正确显示

---

## REQ-sse-thinking-pipeline-阶段定义

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
定义 BI 问数和 Excel 分析两种场景的标准阶段流程。BI 场景包含 7 个阶段，Excel 场景包含 5 个阶段。每个阶段有固定的 stage 标识符、默认图标、中文名称，并支持 status（pending/running/completed/error）、message、metadata 字段。

### 前置条件
- 工作流开始执行

### 输入
- 工作流类型（bi 或 excel）
- 各阶段执行状态

### 输出
- BI 场景 7 阶段：
  1. understanding（意图理解）
  2. knowledge_retrieval（知识检索）
  3. sql_generation（SQL 生成）
  4. execution_validation（执行验证）
  5. chart_generation（图表生成）
  6. report_generation（报告生成）
  7. summary（总结输出）
- Excel 场景 5 阶段：
  1. understanding（意图理解）
  2. code_generation（代码生成）
  3. execution_validation（执行验证）
  4. chart_generation（图表生成）
  5. report_generation（报告生成）

### 处理规则
1. 每个阶段初始状态为 pending，开始执行时变为 running，完成后变为 completed
2. 任意阶段失败时 status 变为 error，后续阶段标记为 skipped
3. metadata 字段存储阶段相关数据（如 sql_generation 的 SQL 语句、chart_generation 的图表配置）
4. duration_ms 在阶段完成时计算并填充
5. 阶段定义可配置，支持未来扩展

### 验收标准
- [ ] BI 场景正确推送 7 个阶段事件
- [ ] Excel 场景正确推送 5 个阶段事件
- [ ] 阶段状态转换符合预期（pending → running → completed/error）
- [ ] metadata 字段正确存储阶段数据
- [ ] duration_ms 正确记录阶段耗时

---

## REQ-sse-thinking-pipeline-历史回放

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P1

### 需求描述
历史消息加载时，从数据库存储的 thoughts 字段解析阶段事件，渲染已完成的流水线视图。用户可以查看历史问答的完整思考过程，包括每个阶段的耗时、状态和详情。

### 前置条件
- 历史消息已存储在 askbi_messages 表
- thoughts 字段包含阶段事件 JSON 数组

### 输入
- 历史消息记录（包含 thoughts 字段）

### 输出
- 已完成的流水线 UI（所有阶段显示为 completed 或 error 状态）

### 处理规则
1. 从 thoughts 字段解析阶段事件数组
2. 所有阶段显示为最终状态（completed/error/skipped）
3. 无运行中动画
4. 可正常展开/折叠详情
5. SQL 代码仍支持语法高亮

### 验收标准
- [ ] 历史消息正确渲染已完成的流水线
- [ ] 阶段详情可正常查看
- [ ] SQL 代码语法高亮正常
- [ ] 无 thoughts 字段时不显示流水线

---

## REQ-sse-thinking-pipeline-SQL高亮

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P1

### 需求描述
流水线中 SQL 生成和执行验证阶段的详情展开时，SQL 代码使用语法高亮显示。支持 PostgreSQL 和 MySQL 语法，使用轻量级代码高亮库（如 highlight.js 或 prism.js）。

### 前置条件
- 阶段 metadata 中包含 sql 字段
- 前端已加载代码高亮库

### 输入
- SQL 代码字符串（来自 metadata.sql）
- 数据库类型（postgresql 或 mysql，用于语法识别）

### 输出
- 语法高亮的 SQL 代码块
- 代码复制按钮（可选）

### 处理规则
1. 检测 SQL 代码存在性（metadata.sql 字段）
2. 根据数据库类型选择语法（默认 postgresql）
3. 使用 highlight.js 的 SQL 语言包进行高亮
4. 代码块支持横向滚动（长 SQL）
5. 可选提供复制按钮

### 验收标准
- [ ] SQL 代码语法高亮正确显示
- [ ] 支持 PostgreSQL 和 MySQL 语法
- [ ] 长 SQL 可横向滚动
- [ ] 无 SQL 时不显示代码块
