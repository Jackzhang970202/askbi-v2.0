# 任务清单

**版本**: v1.1
**模块**: BI 问数 (bi-query)
**关联需求**: REQ-bi-query

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-bi-query-输出结构-001 | [后端] 调整 BI 问数回答输出结构 | REQ-bi-query-自然语言问数 | P0 | 未开始 |
| TASK-bi-query-图表策略-002 | [后端] 调整 BI 图表生成与不出图分支 | REQ-bi-query-自然语言问数 | P0 | 未开始 |
| TASK-bi-query-分析解读-003 | [前后端] 增加分析解读开关与透传 | REQ-bi-query-自然语言问数 | P0 | 未开始 |
| TASK-bi-query-消息渲染-004 | [前端] 适配统一回答结构渲染 | REQ-bi-query-自然语言问数 | P0 | 未开始 |
| TASK-bi-query-历史兼容-005 | [前后端] 保持历史 structuredData 兼容 | REQ-bi-query-会话管理 | P1 | 未开始 |

---

## 任务详情

### TASK-bi-query-输出结构-001 调整 BI 问数回答输出结构

**关联需求**: REQ-bi-query-自然语言问数  
**描述**: 调整 `summary` 生成提示词与返回组装，使回答默认按“问题结果/结论 → 回答依据/佐证 → 数据图表说明”输出，并按开关决定是否追加“分析解读”。  
**技术要点**: `bi_workflow.py` 回答 prompt、`bi_api.py` 结构化响应组装  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/api/bi_api.py`

**验收标准**:
- [ ] `summary` 首段直接回答问题
- [ ] `summary` 包含依据/佐证部分
- [ ] 分析解读按开关控制

---

### TASK-bi-query-图表策略-002 调整 BI 图表生成与不出图分支

**关联需求**: REQ-bi-query-自然语言问数  
**描述**: 保证图表按用户要求或数据特征输出，数据不适合展示时明确返回 `chart_needed: false` 与原因。  
**技术要点**: 图表 prompt、ECharts option、空数据兜底  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/agents/bi_chart_agent.py`

**验收标准**:
- [ ] 合适数据时输出合法图表配置
- [ ] 不适合时返回不出图原因

---

### TASK-bi-query-分析解读-003 增加分析解读开关与透传

**关联需求**: REQ-bi-query-自然语言问数  
**描述**: 在提问输入、接口参数、工作流 prompt 中增加分析解读开关，默认关闭。  
**技术要点**: ChatInput 参数透传、API 请求体、workflow prompt 分支  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/ChatInput.jsx`
- `frontend/src/App.jsx`
- `backend/ask/api/bi_api.py`
- `backend/ask/workflows/bi_workflow.py`

**验收标准**:
- [ ] 前端可控制是否输出分析解读
- [ ] 后端收到参数后按规则生成内容

---

### TASK-bi-query-消息渲染-004 适配统一回答结构渲染

**关联需求**: REQ-bi-query-自然语言问数  
**描述**: 保持现有 Markdown 渲染方式不变，确保 `MessageItem`、流式展示、图表区域与新输出结构协同工作。  
**技术要点**: `structuredData.summary`、`chart` 渲染、流式展示  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/MessageItem.jsx`
- `frontend/src/components/EChart.jsx`
- `frontend/src/utils/StreamingManager.js`

**验收标准**:
- [ ] 正文顺序正确展示
- [ ] 图表独立渲染正常
- [ ] 历史消息与流式消息表现一致

---

### TASK-bi-query-历史兼容-005 保持历史 structuredData 兼容

**关联需求**: REQ-bi-query-会话管理  
**描述**: 保持历史消息读取与新消息写入兼容，不引入破坏性字段变更。  
**技术要点**: `structuredData` 兼容、消息回放  
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `backend/ask/api/bi_api.py`
- `frontend/src/App.jsx`
- `frontend/src/components/MessageItem.jsx`

**验收标准**:
- [ ] 新旧消息均可正常展示
- [ ] 不依赖新增字段才能渲染
