# 任务清单

**版本**: v1.0
**模块**: SSE 思考流水线 (sse-thinking-pipeline)
**关联需求**: REQ-sse-thinking-pipeline

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-sse-thinking-pipeline-ProgressService-001 | [后端] 重构 ProgressService 支持事件队列 | REQ-sse-thinking-pipeline-SSE推送 | P0 | 未开始 |
| TASK-sse-thinking-pipeline-工作流阶段事件-002 | [后端] 工作流集成阶段事件发射 | REQ-sse-thinking-pipeline-阶段定义 | P0 | 未开始 |
| TASK-sse-thinking-pipeline-SSE端点-003 | [后端] 实现 SSE 流式端点 | REQ-sse-thinking-pipeline-SSE推送 | P0 | 未开始 |
| TASK-sse-thinking-pipeline-代理路由-004 | [后端] Proxy Server SSE 代理路由 | REQ-sse-thinking-pipeline-SSE推送 | P0 | 未开始 |
| TASK-sse-thinking-pipeline-前端Hook-005 | [前端] 实现 useProgressStream Hook | REQ-sse-thinking-pipeline-SSE推送 | P0 | 未开始 |
| TASK-sse-thinking-pipeline-Pipeline组件-006 | [前端] 实现 ThinkingPipeline 组件 | REQ-sse-thinking-pipeline-Pipeline展示 | P0 | 未开始 |
| TASK-sse-thinking-pipeline-消息集成-007 | [前端] MessageItem 集成与历史回放 | REQ-sse-thinking-pipeline-历史回放 | P1 | 未开始 |

---

## 任务详情

### TASK-sse-thinking-pipeline-ProgressService-001 重构 ProgressService 支持事件队列

**关联需求**: REQ-sse-thinking-pipeline-SSE推送
**描述**: 重构 `utils/progress_service.py`，将现有 in-memory dict 存储改为 asyncio.Queue 事件队列。实现 `emit_stage_event()` 线程安全推送方法、`stream_events()` async generator、`cleanup()` 资源清理方法。在 `backend_api_agno.py` 启动时注入事件循环引用。
**技术要点**: asyncio.Queue 实例隔离，loop.call_soon_threadsafe() 线程安全，单例模式
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `utils/progress_service.py`
- `backend_api_agno.py`

**验收标准**:
- [ ] ProgressService 可为每个 chatid 创建独立事件队列
- [ ] emit_stage_event() 可在同步和异步上下文正常工作
- [ ] stream_events() 可流式返回事件并在终止事件后结束
- [ ] cleanup() 正确清理队列资源
- [ ] 事件循环引用在服务启动时正确注入

---

### TASK-sse-thinking-pipeline-工作流阶段事件-002 工作流集成阶段事件发射

**关联需求**: REQ-sse-thinking-pipeline-阶段定义
**描述**: 在 `bi_workflow.py` 和 `askexcel_workflow.py` 中新增 `_emit_stage()` 辅助方法，在 7 个 BI 阶段和 5 个 Excel 阶段的关键点调用。每个阶段开始（running）和完成（completed）时发射事件，异常时发射 error 事件，最后发射 __done__ 终止事件。
**技术要点**: 阶段状态转换（pending → running → completed/error），duration_ms 计算，metadata 数据存储
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/workflows/askexcel_workflow.py`

**验收标准**:
- [ ] BI 工作流正确发射 7 个阶段事件（understanding、knowledge_retrieval、sql_generation、execution_validation、chart_generation、report_generation、summary）
- [ ] Excel 工作流正确发射 5 个阶段事件（understanding、code_generation、execution_validation、chart_generation、report_generation）
- [ ] 阶段状态转换符合预期
- [ ] duration_ms 正确记录各阶段耗时
- [ ] metadata 正确存储阶段相关数据（SQL 语句、图表配置等）
- [ ] 异常时发射 __error__ 终止事件

---

### TASK-sse-thinking-pipeline-SSE端点-003 实现 SSE 流式端点

**关联需求**: REQ-sse-thinking-pipeline-SSE推送
**描述**: 在 `bi_api.py` 和 `excel_api.py` 新增 SSE 流式端点。`GET /progress/stream?chatid=X` 和 `GET /excel/progress/stream?chatid=X`，返回 `text/event-stream` 响应，使用 async generator 流式输出事件。支持 Bearer Token 认证，禁用缓存。
**技术要点**: FastAPI StreamingResponse，text/event-stream 格式，Bearer Token 认证，Cache-Control: no-cache
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/bi_api.py`
- `backend/ask/excel_api.py`

**验收标准**:
- [ ] `/progress/stream` 端点可正常建立 SSE 连接
- [ ] `/excel/progress/stream` 端点可正常建立 SSE 连接
- [ ] 响应格式符合 text/event-stream 规范
- [ ] Bearer Token 认证正常工作
- [ ] 事件流在 __done__ 或 __error__ 后正常关闭
- [ ] 连接断开后资源正确清理

---

### TASK-sse-thinking-pipeline-代理路由-004 Proxy Server SSE 代理路由

**关联需求**: REQ-sse-thinking-pipeline-SSE推送
**描述**: 在 `proxy_server.py` 新增 SSE 代理路由，透传后端 SSE 事件流。使用 httpx.AsyncClient 流式请求后端 SSE 端点，逐行转发事件到前端。保留认证头传递。
**技术要点**: httpx 流式请求，StreamingResponse 透传，认证头传递
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `proxy_server.py`

**验收标准**:
- [ ] 代理路由可正常转发 SSE 事件流
- [ ] Bearer Token 正确传递到后端
- [ ] 事件格式不被修改（透传）
- [ ] 连接断开正确传播

---

### TASK-sse-thinking-pipeline-前端Hook-005 实现 useProgressStream Hook

**关联需求**: REQ-sse-thinking-pipeline-SSE推送
**描述**: 新建 `useProgressStream.js` Hook，封装 SSE 连接逻辑。使用 fetch + ReadableStream 接收事件流，解析 JSON 事件，更新阶段状态。支持 Bearer Token 认证，AbortController 中断，自动重连（最多 3 次）。导出 stages、isStreaming、error 状态。
**技术要点**: fetch + ReadableStream API，TextDecoder 解码，AbortController 中断，断线重连逻辑
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/hooks/useProgressStream.js`

**验收标准**:
- [ ] Hook 可正常建立 SSE 连接并接收事件
- [ ] 事件正确解析并更新 stages 状态
- [ ] Bearer Token 认证正常传递
- [ ] AbortController 可正确中断连接
- [ ] 连接断开后自动重连（最多 3 次，间隔 3 秒）
- [ ] isStreaming 状态正确反映连接状态
- [ ] 错误正确捕获并设置到 error 状态

---

### TASK-sse-thinking-pipeline-Pipeline组件-006 实现 ThinkingPipeline 组件

**关联需求**: REQ-sse-thinking-pipeline-Pipeline展示
**描述**: 新建 `ThinkingPipeline.jsx` 组件，替代现有 `ThinkingProcess.jsx`。实现浅色卡片 + 垂直时间线布局，阶段定义配置（BI 7 阶段、Excel 5 阶段），状态指示（pending/running/completed/error），脉冲动画，SQL 语法高亮（highlight.js），详情展开/折叠，平滑滚动到可见区域。
**技术要点**: React 函数组件，CSS 动画（pulse、fade-in、slide-in），highlight.js SQL 高亮，scrollIntoView API
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/ThinkingPipeline.jsx`
- `frontend/src/components/ThinkingPipeline.css`

**验收标准**:
- [ ] 组件正确渲染 BI 和 Excel 阶段
- [ ] 阶段状态指示正确（图标、颜色、动画）
- [ ] 运行中阶段有脉冲动画
- [ ] 完成阶段显示耗时和勾选标记
- [ ] 错误阶段红色高亮
- [ ] 详情可正常展开/折叠
- [ ] SQL 代码语法高亮正确
- [ ] 新阶段出现时平滑滚动到可见区域
- [ ] 动画平滑无卡顿

---

### TASK-sse-thinking-pipeline-消息集成-007 MessageItem 集成与历史回放

**关联需求**: REQ-sse-thinking-pipeline-历史回放
**描述**: 在 `MessageItem.jsx` 集成 ThinkingPipeline 组件。实时消息使用 useProgressStream Hook 获取阶段事件，历史消息从 thoughts 字段解析阶段数据。在 `StreamingManager.js` 协调多个 SSE 连接，在 `App.jsx` 管理生命周期。
**技术要点**: 条件渲染（实时 vs 历史），thoughts JSON 解析，StreamingManager 连接管理，App.jsx 生命周期钩子
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/MessageItem.jsx`
- `frontend/src/services/StreamingManager.js`
- `frontend/src/App.jsx`

**验收标准**:
- [ ] 实时消息正确显示运行中的流水线
- [ ] 历史消息正确显示已完成的流水线
- [ ] thoughts 字段正确解析为阶段数据
- [ ] 无 thoughts 字段时不显示流水线
- [ ] StreamingManager 正确管理多个 SSE 连接
- [ ] App.jsx 组件卸载时正确清理连接
- [ ] 路由切换时不中断正在进行的 SSE 连接
