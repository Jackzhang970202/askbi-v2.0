# 检查清单

**版本**: v1.0
**模块**: SSE 思考流水线 (sse-thinking-pipeline)
**关联需求**: REQ-sse-thinking-pipeline

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-sse-thinking-pipeline-连通性-001 | SSE 事件流连通性 | REQ-sse-thinking-pipeline-SSE推送 | 阻塞 | 未开始 |
| CHK-sse-thinking-pipeline-格式-002 | 阶段事件格式正确性 | REQ-sse-thinking-pipeline-SSE推送 | 阻塞 | 未开始 |
| CHK-sse-thinking-pipeline-渲染-003 | Pipeline UI 渲染 | REQ-sse-thinking-pipeline-Pipeline展示 | 阻塞 | 未开始 |
| CHK-sse-thinking-pipeline-实时-004 | 实时进度更新 | REQ-sse-thinking-pipeline-Pipeline展示 | 阻塞 | 未开始 |
| CHK-sse-thinking-pipeline-回放-005 | 历史消息回放 | REQ-sse-thinking-pipeline-历史回放 | 重要 | 未开始 |
| CHK-sse-thinking-pipeline-高亮-006 | SQL 语法高亮 | REQ-sse-thinking-pipeline-SQL高亮 | 重要 | 未开始 |

---

## 检查项详情

### CHK-sse-thinking-pipeline-连通性-001 SSE 事件流连通性

**关联需求**: REQ-sse-thinking-pipeline-SSE推送
**目的**: 验证 SSE 端点可正常建立连接并接收事件流
**方法**: 端到端测试
**等级**: 阻塞

**检查步骤**:
1. 发送 BI 问数请求触发工作流
2. 立即调用 `GET /progress/stream?chatid=X` 建立 SSE 连接
3. 观察事件流是否持续到达
4. 等待工作流完成，确认收到 `stage="__done__"` 事件
5. 确认 SSE 连接正常关闭

**预期结果**:
- SSE 连接成功建立，返回 `text/event-stream` Content-Type
- 事件流持续到达，无中断
- 收到 `__done__` 终止事件后连接正常关闭
- 无资源泄漏（队列正确清理）

---

### CHK-sse-thinking-pipeline-格式-002 阶段事件格式正确性

**关联需求**: REQ-sse-thinking-pipeline-SSE推送
**目的**: 验证 SSE 事件 JSON 格式符合规范
**方法**: 事件格式校验
**等级**: 阻塞

**检查步骤**:
1. 建立 SSE 连接并接收事件
2. 解析每个事件的 JSON 数据
3. 验证必需字段存在：stage、status、message、timestamp、duration_ms、metadata
4. 验证 status 值合法：pending、running、completed、error
5. 验证 timestamp 为毫秒级时间戳
6. 验证 metadata 为对象类型

**预期结果**:
- 所有事件包含 6 个必需字段
- status 值在合法范围内
- timestamp 为数字类型且为毫秒级
- metadata 为对象（可为空对象）
- 无 JSON 解析错误

---

### CHK-sse-thinking-pipeline-渲染-003 Pipeline UI 渲染

**关联需求**: REQ-sse-thinking-pipeline-Pipeline展示
**目的**: 验证 Pipeline 组件正确渲染各阶段卡片和时间线
**方法**: 手动 UI 测试
**等级**: 阻塞

**检查步骤**:
1. 发送 BI 问数请求，触发流水线渲染
2. 检查阶段卡片是否按顺序显示（7 个 BI 阶段）
3. 检查每个卡片是否包含：图标、阶段名称、状态指示
4. 检查垂直时间线是否正确连接各阶段
5. 检查浅色卡片样式是否正确（白色背景、圆角、阴影）

**预期结果**:
- 7 个阶段卡片按顺序垂直排列
- 时间线线条正确连接各阶段
- 卡片样式符合设计规范
- 无布局错乱或重叠

---

### CHK-sse-thinking-pipeline-实时-004 实时进度更新

**关联需求**: REQ-sse-thinking-pipeline-Pipeline展示
**目的**: 验证阶段状态变化时 UI 实时更新并有动画效果
**方法**: 实时观察 UI 变化
**等级**: 阻塞

**检查步骤**:
1. 发送 BI 问数请求
2. 观察第一个阶段（understanding）从 pending → running → completed 的状态变化
3. 检查 running 状态时是否有脉冲动画
4. 检查 completed 状态时是否显示耗时（如"1.2s"）和勾选标记
5. 观察后续阶段依次变为 running 和 completed
6. 检查新阶段出现时是否有淡入/滑入动画
7. 检查是否自动滚动到新阶段

**预期结果**:
- 阶段状态变化实时反映在 UI 上
- running 阶段有脉冲动画效果
- completed 阶段显示耗时和勾选标记
- 新阶段出现时有平滑动画
- 自动滚动到新阶段
- 动画平滑无卡顿

---

### CHK-sse-thinking-pipeline-回放-005 历史消息回放

**关联需求**: REQ-sse-thinking-pipeline-历史回放
**目的**: 验证历史消息正确渲染已完成的流水线
**方法**: 加载历史消息
**等级**: 重要

**检查步骤**:
1. 确保已有完成的历史问答记录
2. 刷新页面或切换到历史会话
3. 检查历史消息是否显示已完成的流水线
4. 检查所有阶段是否为 completed 或 error 状态
5. 检查是否无运行中动画
6. 点击阶段卡片，检查详情是否可展开
7. 检查无 thoughts 字段的消息是否不显示流水线

**预期结果**:
- 历史消息正确渲染完整流水线
- 所有阶段显示最终状态（completed/error）
- 无脉冲动画或 loading 状态
- 详情可正常展开/折叠
- 无 thoughts 字段时不显示流水线组件

---

### CHK-sse-thinking-pipeline-高亮-006 SQL 语法高亮

**关联需求**: REQ-sse-thinking-pipeline-SQL高亮
**目的**: 验证 SQL 代码在流水线详情中正确语法高亮
**方法**: 展开 SQL 阶段详情
**等级**: 重要

**检查步骤**:
1. 触发包含 SQL 生成的 BI 问数
2. 等待 sql_generation 阶段完成
3. 点击展开 sql_generation 阶段详情
4. 检查 SQL 代码是否语法高亮（关键字、字符串、数字等不同颜色）
5. 检查长 SQL 是否可横向滚动
6. 发送 Excel 分析请求（无 SQL），检查是否无 SQL 代码块

**预期结果**:
- SQL 代码语法高亮正确显示
- 关键字（SELECT、FROM、WHERE 等）颜色区分
- 长 SQL 可横向滚动，不换行
- 无 SQL 字段时不显示代码块
- 代码块样式与浅色卡片设计协调

---

