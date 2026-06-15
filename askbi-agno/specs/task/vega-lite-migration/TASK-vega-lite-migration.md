# 任务清单

**版本**: v1.0
**模块**: Vega-Lite 图表引擎迁移 (vega-lite-migration)
**关联需求**: REQ-vega-lite-migration

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-vega-lite-migration-Prompt重写-001 | [后端] 重写 prompt.py 为 Vega-Lite 规格 | REQ-vega-lite-migration-Prompt重写 | P0 | 未开始 |
| TASK-vega-lite-migration-后端图表-002 | [后端] 更新工作流与 Agent 图表生成逻辑 | REQ-vega-lite-migration-图表引擎替换 | P0 | 未开始 |
| TASK-vega-lite-migration-前端CDN-003 | [前端] 替换 index.html CDN 脚本 | REQ-vega-lite-migration-图表引擎替换 | P0 | 未开始 |
| TASK-vega-lite-migration-VegaChart组件-004 | [前端] 新建 VegaChart.jsx 并删除 EChart.jsx | REQ-vega-lite-migration-图表引擎替换 | P0 | 未开始 |
| TASK-vega-lite-migration-消息兼容-005 | [前端] MessageItem.jsx 图表格式检测与兼容 | REQ-vega-lite-migration-历史兼容 | P0 | 未开始 |
| TASK-vega-lite-migration-Agent更新-006 | [后端] 更新 bi_chart_agent 和 askexcel_chart_agent | REQ-vega-lite-migration-图表引擎替换 | P0 | 未开始 |

---

## 任务详情

### TASK-vega-lite-migration-Prompt重写-001 重写 prompt.py 为 Vega-Lite 规格

**关联需求**: REQ-vega-lite-migration-Prompt重写
**描述**: 重写 `prompt.py`，删除原 ECharts 相关 prompt 常量（ECHARTS_BAR_PROMPT、ECHARTS_LINE_PROMPT、ECHARTS_PIE_PROMPT），新增 VEGALITE_SYSTEM_PROMPT 常量（包含 Vega-Lite v5 JSON Schema 规范、编码规则、配色方案、输出格式约束）、CHART_TYPE_SPECS 字典（覆盖 bar/line/pie/area/scatter/heatmap/treemap/stacked_bar/waterfall/radar 共 10 种图表类型，每种包含 description 和 example）、`build_chart_prompt(data_sample, chart_type_hint)` 函数。
**技术要点**: Vega-Lite v5 JSON Schema 规范，各图表类型的最小可运行 JSON 示例，纯函数设计
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/prompt.py`

**验收标准**:
- [ ] 原 ECharts prompt 常量已删除
- [ ] VEGALITE_SYSTEM_PROMPT 包含完整的输出格式约束和编码规则
- [ ] CHART_TYPE_SPECS 覆盖 10 种图表类型，每种含 description 和合法 JSON 示例
- [ ] `build_chart_prompt()` 函数可根据数据样本动态生成 prompt
- [ ] 所有 JSON 示例均为合法的 Vega-Lite 规格

---

### TASK-vega-lite-migration-后端图表-002 更新工作流与 Agent 图表生成逻辑

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**描述**: 更新 `bi_workflow.py` 和 `askexcel_workflow.py` 中图表生成步骤的 prompt 构建方式，从直接引用 ECharts prompt 常量改为调用 `build_chart_prompt(data_sample)` 函数。更新 `chart_generator.py` 中 agent 的 instructions 引用为 Vega-Lite 相关指令。添加 `validate_vegalite_json()` 校验函数，对 LLM 输出的 JSON 进行软校验。
**技术要点**: 修改范围仅限图表生成步骤的 prompt 构建，不改变工作流整体结构和 Agent 编排逻辑
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/workflows/bi_workflow.py`
- `backend/ask/workflows/askexcel_workflow.py`
- `backend/ask/chart_generator.py`

**验收标准**:
- [ ] BI 问数工作流的图表生成步骤使用 `build_chart_prompt()` 构建 prompt
- [ ] Excel 分析工作流的图表生成步骤使用 `build_chart_prompt()` 构建 prompt
- [ ] chart_generator.py 中 agent instructions 已更新为 Vega-Lite 指令
- [ ] `validate_vegalite_json()` 函数可正确校验和解析 JSON
- [ ] 工作流整体结构和非图表步骤不受影响

---

### TASK-vega-lite-migration-前端CDN-003 替换 index.html CDN 脚本

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**描述**: 修改 `frontend/index.html`，移除 ECharts CDN 脚本引用（`echarts@5/dist/echarts.min.js`），替换为 Vega 全家桶 CDN 脚本（vega@5、vega-lite@5、vega-embed@6），均使用 jsdelivr CDN 源。
**技术要点**: CDN 脚本加载顺序为 vega → vega-lite → vega-embed（存在依赖关系），加载后 `window.vega`、`window.vl`、`window.vegaEmbed` 可用
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/index.html`

**验收标准**:
- [ ] ECharts CDN 脚本已移除
- [ ] vega@5、vega-lite@5、vega-embed@6 CDN 脚本已按正确顺序添加
- [ ] 页面加载后 `window.vegaEmbed` 函数可用
- [ ] 无 ECharts 相关的全局变量残留

---

### TASK-vega-lite-migration-VegaChart组件-004 新建 VegaChart.jsx 并删除 EChart.jsx

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**描述**: 新建 `VegaChart.jsx` 组件（约 40 行），使用 `useRef` + `useEffect` 调用 `window.vegaEmbed` 渲染 Vega-Lite spec。配置 `actions: true` 启用导出菜单，`renderer: 'canvas'` 使用 canvas 渲染器。在 useEffect cleanup 中调用 `result.finalize()` 清理实例。完成后删除 `EChart.jsx`。
**技术要点**: vegaEmbed 异步调用与 cleanup，React ref 管理 DOM 容器，异常捕获
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/VegaChart.jsx`（新建）
- `frontend/src/components/EChart.jsx`（删除）

**验收标准**:
- [ ] VegaChart.jsx 可正确接收 spec prop 并渲染图表
- [ ] 图表切换时旧实例被正确清理（无内存泄漏）
- [ ] vegaEmbed 异常被捕获，不导致页面崩溃
- [ ] EChart.jsx 已删除
- [ ] 导出 PNG/SVG 菜单可用

---

### TASK-vega-lite-migration-消息兼容-005 MessageItem.jsx 图表格式检测与兼容

**关联需求**: REQ-vega-lite-migration-历史兼容
**描述**: 修改 `MessageItem.jsx` 中的图表渲染逻辑，将原 ECharts 特征检测（`chart.series`）替换为三段式检测：`isVegaLite()`（检测 `$schema` 或 `mark` 字段）→ 渲染 VegaChart 组件；`isEChartsLegacy()`（检测 `series`/`xAxis`/`yAxis` 且无 `$schema`）→ 渲染降级占位 UI（"图表引擎已升级，历史图表不再支持渲染"）；`isNoChart()`（检测 `chart_needed: false`）→ 不渲染。同步修改 `ReportManager.jsx` 中的图表渲染逻辑。
**技术要点**: 格式检测函数的准确性，降级占位 UI 的样式设计（虚线边框 + 提示文本 + 可选数据表格回退）
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `frontend/src/components/MessageItem.jsx`
- `frontend/src/components/ReportManager.jsx`

**验收标准**:
- [ ] 新 Vega-Lite 消息正常渲染图表
- [ ] 历史 ECharts 消息显示降级占位 UI
- [ ] 降级占位 UI 包含"图表引擎已升级"提示文本
- [ ] `chart_needed: false` 时不渲染图表区域
- [ ] ReportManager.jsx 中图表渲染逻辑同步更新
- [ ] 无 console 报错

---

### TASK-vega-lite-migration-Agent更新-006 更新 bi_chart_agent 和 askexcel_chart_agent

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**描述**: 更新 `bi_chart_agent.py` 和 `askexcel_chart_agent.py` 中 Agent 的 system prompt / instructions，将 ECharts option 格式指令替换为 VEGALITE_SYSTEM_PROMPT。确保 Agent 在调用 LLM 时使用新的 Vega-Lite 系统提示词生成图表规格。
**技术要点**: 仅修改 Agent 的 instructions 配置，不改变 Agent 创建方式和工作流编排
**优先级**: P0 | **状态**: 未开始

**涉及文件**:
- `backend/ask/agents/bi_chart_agent.py`
- `backend/ask/agents/askexcel_chart_agent.py`

**验收标准**:
- [ ] bi_chart_agent 的 instructions 引用 VEGALITE_SYSTEM_PROMPT
- [ ] askexcel_chart_agent 的 instructions 引用 VEGALITE_SYSTEM_PROMPT
- [ ] Agent 调用 LLM 时使用新的 Vega-Lite 提示词
- [ ] Agent 创建方式和编排逻辑不变
