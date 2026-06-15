# Vega-Lite 图表引擎迁移模块 - 需求文档

**版本**: v1.0
**模块**: Vega-Lite 图表引擎迁移 (vega-lite-migration)

---

## REQ-vega-lite-migration-图表引擎替换

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
将系统当前的 ECharts 图表渲染引擎完整替换为 Vega-Lite，支持 10 种以上图表类型（柱状图、折线图、饼图、面积图、散点图、热力图、矩形树图、堆叠柱状图、瀑布图、雷达图），后端生成符合 Vega-Lite JSON Schema 规范的图表规格，前端通过 vega-embed 渲染图表。替换完成后，所有新生成的图表均使用 Vega-Lite 格式输出。

### 前置条件
- 现有 ECharts 图表功能正常运行
- 前端 index.html 当前加载 ECharts CDN 脚本
- 后端 prompt.py 中已定义 ECharts 相关的 prompt 常量

### 输入
- 用户自然语言问题（BI 问数或 Excel 分析）
- 查询结果数据

### 输出
- `chart` 字段：Vega-Lite JSON 规格对象（含 `$schema`、`mark`、`encoding` 等标准字段）
- 或 `{"chart_needed": false, "reason": "..."}` 表示无需图表

### 处理规则
1. 后端 prompt.py 重写为 Vega-Lite 系统提示词，包含图表类型规格说明和 JSON Schema 示例
2. 后端工作流中图表生成步骤使用新的 Vega-Lite prompt 替代原 ECharts prompt
3. 前端 index.html 中将 ECharts CDN 替换为 vega/vega-lite/vega-embed CDN
4. 新建 VegaChart.jsx 组件替代 EChart.jsx，使用 `window.vegaEmbed` 渲染
5. 支持的图表类型：bar（柱状图）、line（折线图）、pie（饼图，Vega-Lite 中使用 arc mark）、area（面积图）、scatter（散点图）、heatmap（热力图）、treemap（矩形树图）、stacked_bar（堆叠柱状图）、waterfall（瀑布图）、radar（雷达图，使用 layered arc）
6. LLM 在 prompt 引导下自主选择最佳图表类型

### 验收标准
- [ ] 后端 prompt.py 包含完整的 Vega-Lite 系统提示词和 10 种图表类型规格
- [ ] 后端工作流输出 chart 字段为合法 Vega-Lite JSON
- [ ] 前端正确加载 vega/vega-lite/vega-embed CDN 脚本
- [ ] VegaChart.jsx 通过 vegaEmbed 成功渲染各类型图表
- [ ] EChart.jsx 已删除，不再被任何组件引用
- [ ] 10 种图表类型均可正确生成和渲染

---

## REQ-vega-lite-migration-Prompt重写

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
重写 `prompt.py`，定义 VEGALITE_SYSTEM_PROMPT（包含 Vega-Lite JSON Schema 核心规范、通用编码规则、配色方案、响应式尺寸）和 CHART_TYPE_SPECS 字典（为每种图表类型提供 JSON 示例和适用场景说明），并提供 `build_chart_prompt(data_sample, chart_type_hint)` 函数，根据数据特征动态构建图表生成提示词。

### 前置条件
- 已确认需要支持的 10 种图表类型
- 已了解 Vega-Lite v5 JSON Schema 规范

### 输入
- `data_sample`: 查询结果数据样本（用于 LLM 理解数据结构）
- `chart_type_hint`: 可选的图表类型提示

### 输出
- 完整的图表生成 prompt 字符串（含系统指令 + 数据上下文 + JSON 输出格式约束）

### 处理规则
1. VEGALITE_SYSTEM_PROMPT 包含：Vega-Lite v5 schema URL、mark 类型说明、encoding channel 规则、配色方案（category10/tableau10）、标题和轴标签中文支持
2. CHART_TYPE_SPECS 为字典结构，键为图表类型名，值包含 `description`（适用场景）和 `example`（最小可运行 Vega-Lite JSON）
3. `build_chart_prompt()` 函数将系统提示词 + 数据样本 + 可选图表类型提示拼接为最终 prompt
4. 输出格式约束：LLM 必须输出纯 JSON（无 markdown 代码块包裹），JSON 必须包含 `$schema` 字段
5. prompt 中明确要求 LLM 在 JSON 中内联 `data.values` 字段承载实际数据

### 验收标准
- [ ] VEGALITE_SYSTEM_PROMPT 包含完整的 Vega-Lite 规范和输出格式约束
- [ ] CHART_TYPE_SPECS 覆盖 10 种图表类型，每种含 description 和 example
- [ ] `build_chart_prompt()` 函数可根据输入动态生成 prompt
- [ ] prompt 输出的 JSON 示例均为合法 Vega-Lite 规格
- [ ] 原 ECharts 相关的 prompt 常量（ECHARTS_BAR/LINE/PIE_PROMPT）已移除

---

## REQ-vega-lite-migration-历史兼容

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P0

### 需求描述
迁移完成后，历史会话中已存在的 ECharts 格式图表消息（chart 字段包含 `series`、`xAxis`、`yAxis` 等 ECharts 特征字段）在前端展示时应优雅降级，显示"图表引擎已升级"占位提示，不产生渲染错误。新消息中的 Vega-Lite 图表正常渲染。

### 前置条件
- 历史会话消息存储在 PostgreSQL（askbi_messages 表）
- 历史消息的 `structuredData.chart` 字段为 ECharts option JSON 格式
- 新消息的 `structuredData.chart` 字段为 Vega-Lite JSON 格式

### 输入
- 消息中的 `chart` 字段（可能是 ECharts 或 Vega-Lite 格式）

### 输出
- Vega-Lite 图表正常渲染
- ECharts 旧图表显示降级占位提示

### 处理规则
1. 前端通过检测 chart 对象是否包含 `$schema` 或 `mark` 字段来判断是否为 Vega-Lite 格式
2. 若检测到 ECharts 特征（包含 `series`、`xAxis`、`yAxis` 等字段且不含 `$schema`），显示降级占位 UI
3. 降级占位 UI 包含提示文本"图表引擎已升级，历史图表不再支持渲染"和数据表格回退（展示原始数据）
4. 若 chart 字段为 `{"chart_needed": false}` 则不渲染图表区域
5. 不修改历史数据库记录，仅在前端展示层做兼容

### 验收标准
- [ ] 新 Vega-Lite 格式消息正常渲染图表
- [ ] 旧 ECharts 格式消息显示降级占位提示而非渲染错误
- [ ] 降级占位 UI 包含可读的提示文本
- [ ] `chart_needed: false` 时不渲染图表区域
- [ ] 历史数据库记录未被修改

---

## REQ-vega-lite-migration-交互增强

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P1

### 需求描述
利用 Vega-Lite 和 vega-embed 的内置交互能力，为图表提供开箱即用的增强功能：导出 PNG/SVG 图片、悬停工具提示（tooltip）、数据点选择高亮。无需额外开发自定义交互逻辑。

### 前置条件
- VegaChart.jsx 组件已使用 vegaEmbed 渲染图表
- vega-embed 默认提供 actions 菜单（Export PNG/SVG/View Source）

### 输入
- 已渲染的 Vega-Lite 图表

### 输出
- 图表右上角或底部的导出操作菜单
- 悬停时显示数据详情的 tooltip
- 点击/框选时的数据点高亮效果

### 处理规则
1. vegaEmbed 调用时启用 `actions: true`，保留默认导出菜单（PNG/SVG/Source）
2. Vega-Lite spec 中统一配置 `tooltip: {"content": "data"}` 以显示完整数据字段
3. 对适合交互的图表类型（scatter、bar、line）在 encoding 中添加 `selection` 配置实现点击高亮
4. 导出文件名默认为 `chart-{timestamp}`
5. tooltip 内容格式化为中文标签 + 数值

### 验收标准
- [ ] 图表可通过导出菜单下载为 PNG 图片
- [ ] 图表可通过导出菜单下载为 SVG 图片
- [ ] 鼠标悬停时显示数据详情 tooltip
- [ ] 散点图/柱状图支持点击高亮
- [ ] tooltip 内容为中文标签
