# 任务清单

**版本**: v1.1
**模块**: Excel 问数 (excel-query)
**关联需求**: REQ-excel-query

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-excel-query-输出结构-001 | [后端] 调整 Excel 问数回答输出结构 | REQ-excel-query-自然语言分析 | P0 | 未开始 |
| TASK-excel-query-图表策略-002 | [后端] 调整 Excel 图表生成与不出图分支 | REQ-excel-query-自然语言分析 | P0 | 未开始 |
| TASK-excel-query-分析解读-003 | [前后端] 增加分析解读开关与透传 | REQ-excel-query-自然语言分析 | P0 | 未开始 |
| TASK-excel-query-消息渲染-004 | [前端] 适配统一回答结构渲染 | REQ-excel-query-自然语言分析 | P0 | 未开始 |
| TASK-excel-query-依据核验-005 | [前端] 打通回答依据与文件预览联动 | REQ-excel-query-会话管理 | P1 | 未开始 |

---

## 任务详情

### TASK-excel-query-输出结构-001 调整 Excel 问数回答输出结构

**关联需求**: REQ-excel-query-自然语言分析  
**描述**: 调整 `summary` 生成提示词与返回组装，使回答默认按“问题结果/结论 → 回答依据/佐证 → 数据图表说明”输出，并按开关决定是否追加“分析解读”。  
**技术要点**: `askexcel_workflow.py` 回答 prompt、`excel_api.py` 结构化响应组装  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/askexcel_workflow.py`
- `backend/ask/api/excel_api.py`

**验收标准**:
- [ ] `summary` 首段直接回答问题
- [ ] `summary` 包含依据/佐证部分
- [ ] 分析解读按开关控制

---

### TASK-excel-query-图表策略-002 调整 Excel 图表生成与不出图分支

**关联需求**: REQ-excel-query-自然语言分析  
**描述**: 保证图表按用户要求或数据特征输出，数据不适合展示时明确返回 `chart_needed: false` 与原因。  
**技术要点**: 图表 prompt、ECharts option、空结果兜底  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/askexcel_workflow.py`
- `backend/ask/agents/askexcel_chart_agent.py`

**验收标准**:
- [ ] 合适数据时输出合法图表配置
- [ ] 不适合时返回不出图原因

---

### TASK-excel-query-分析解读-003 增加分析解读开关与透传

**关联需求**: REQ-excel-query-自然语言分析  
**描述**: 在提问输入、接口参数、工作流 prompt 中增加分析解读开关，默认关闭。  
**技术要点**: ChatInput 参数透传、API 请求体、workflow prompt 分支  
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/ChatInput.jsx`
- `frontend/src/App.jsx`
- `backend/ask/api/excel_api.py`
- `backend/ask/workflows/askexcel_workflow.py`

**验收标准**:
- [ ] 前端可控制是否输出分析解读
- [ ] 后端收到参数后按规则生成内容

---

### TASK-excel-query-消息渲染-004 适配统一回答结构渲染

**关联需求**: REQ-excel-query-自然语言分析  
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

### TASK-excel-query-依据核验-005 打通回答依据与文件预览联动

**关联需求**: REQ-excel-query-会话管理  
**描述**: 让用户能从回答中的依据部分回到文件预览，核验原始数据、sheet 与明细内容。  
**技术要点**: 文件预览接口、sheet 展示、原始/处理后切换  
**优先级**: P1 | **状态**: 未开始

**涉及文件**:
- `frontend/src/App.jsx`
- `frontend/src/services/api.js`
- `backend/ask/api/excel_api.py`

**验收标准**:
- [ ] 文件预览可支撑回答依据核验
- [ ] 原始文件与处理后文件可区分查看
