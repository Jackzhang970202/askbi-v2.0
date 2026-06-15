# 检查清单

**版本**: v1.0
**模块**: Vega-Lite 图表引擎迁移 (vega-lite-migration)
**关联需求**: REQ-vega-lite-migration

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-vega-lite-migration-JSON有效性-001 | Vega-Lite JSON 输出有效性 | REQ-vega-lite-migration-Prompt重写 | 阻塞 | 未开始 |
| CHK-vega-lite-migration-图表覆盖-002 | 10 种图表类型覆盖 | REQ-vega-lite-migration-图表引擎替换 | 阻塞 | 未开始 |
| CHK-vega-lite-migration-前端渲染-003 | 前端渲染正确性 | REQ-vega-lite-migration-图表引擎替换 | 阻塞 | 未开始 |
| CHK-vega-lite-migration-历史兼容-004 | 历史消息兼容降级 | REQ-vega-lite-migration-历史兼容 | 阻塞 | 未开始 |
| CHK-vega-lite-migration-导出功能-005 | 导出功能可用 | REQ-vega-lite-migration-交互增强 | 重要 | 未开始 |
| CHK-vega-lite-migration-CDN加载-006 | CDN 加载成功 | REQ-vega-lite-migration-图表引擎替换 | 阻塞 | 未开始 |

---

## 检查项详情

### CHK-vega-lite-migration-JSON有效性-001 Vega-Lite JSON 输出有效性

**关联需求**: REQ-vega-lite-migration-Prompt重写
**目的**: 验证后端 LLM 生成的图表 JSON 为合法的 Vega-Lite 规格
**方法**: 端到端问数测试 + JSON Schema 校验
**等级**: 阻塞

**检查步骤**:
1. 发送 BI 问数问题（如"各部门销售额对比"），获取响应
2. 提取响应中 `structuredData.chart` 字段
3. 验证 JSON 包含 `$schema` 字段且值为 `https://vega.github.io/schema/vega-lite/v5.json`
4. 验证 JSON 包含 `mark` 字段
5. 验证 JSON 包含 `data.values` 字段且为数组
6. 使用 Vega-Lite 在线编辑器（https://vega.github.io/editor/）粘贴 JSON 确认可渲染
7. 对不适合图表的问题（如"数据库有哪些表"），验证返回 `chart_needed: false`

**预期结果**:
- 所有图表类问题的响应 JSON 均为合法 Vega-Lite 规格
- JSON 无 markdown 代码块包裹
- 非图表问题返回 `chart_needed: false`

---

### CHK-vega-lite-migration-图表覆盖-002 10 种图表类型覆盖

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**目的**: 验证 10 种图表类型均可被正确生成
**方法**: 针对性提问触发各图表类型
**等级**: 阻塞

**检查步骤**:
1. 提问触发柱状图（bar）：如"各部门人数对比"
2. 提问触发折线图（line）：如"近 12 个月营收趋势"
3. 提问触发饼图（pie/arc）：如"产品类别占比"
4. 提问触发面积图（area）：如"月度累积收入变化"
5. 提问触发散点图（scatter）：如"身高与体重的关系"
6. 提问触发热力图（heatmap）：如"每周各时段活跃度"
7. 提问触发矩形树图（treemap）：如"部门人员分布"
8. 提问触发堆叠柱状图（stacked_bar）：如"各季度产品线销售构成"
9. 提问触发瀑布图（waterfall）：如"利润构成增减分析"
10. 提问触发雷达图（radar）：如"员工多维度能力评估"
11. 对每种图表类型检查返回 JSON 中的 `mark` 字段是否与预期类型匹配

**预期结果**:
- 10 种图表类型均可被 LLM 正确生成
- 每种图表的 mark 类型符合预期（bar/line/arc/area/point/rect 等）
- 各图表 JSON 在 Vega-Lite 编辑器中可正常渲染

---

### CHK-vega-lite-migration-前端渲染-003 前端渲染正确性

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**目的**: 验证前端 VegaChart 组件可正确渲染各类 Vega-Lite 图表
**方法**: 端到端 UI 测试
**等级**: 阻塞

**检查步骤**:
1. 在聊天页面发送图表类问题，等待响应
2. 确认消息区域中图表正确渲染（非空白、非错误）
3. 确认图表包含标题、轴标签、图例等元素
4. 确认图表标题和轴标签为中文
5. 确认图表尺寸合理（默认约 600x400）
6. 确认 tooltip 在鼠标悬停时正确显示数据
7. 在报表管理页面确认图表同样正确渲染
8. 检查浏览器 console 无 VegaLite 相关报错

**预期结果**:
- 图表在聊天页和报表页均正确渲染
- 图表元素完整（标题、轴、图例、tooltip）
- 无 console 错误

---

### CHK-vega-lite-migration-历史兼容-004 历史消息兼容降级

**关联需求**: REQ-vega-lite-migration-历史兼容
**目的**: 验证历史 ECharts 格式消息在新版本中优雅降级
**方法**: 加载包含历史 ECharts 消息的会话
**等级**: 阻塞

**检查步骤**:
1. 打开一个包含历史 ECharts 图表消息的会话
2. 确认历史 ECharts 消息显示降级占位 UI
3. 确认占位 UI 包含"图表引擎已升级"文本
4. 确认无 JavaScript 渲染错误
5. 确认新发送的消息中 Vega-Lite 图表正常渲染
6. 确认 `chart_needed: false` 的消息不渲染图表区域
7. 确认历史数据库记录未被修改

**预期结果**:
- 历史 ECharts 消息显示友好的降级提示
- 新 Vega-Lite 消息正常渲染
- 无渲染错误，数据库无变更

---

### CHK-vega-lite-migration-导出功能-005 导出功能可用

**关联需求**: REQ-vega-lite-migration-交互增强
**目的**: 验证 vega-embed 内置的导出和交互功能正常工作
**方法**: UI 交互测试
**等级**: 重要

**检查步骤**:
1. 渲染一个 Vega-Lite 图表
2. 点击图表右上角的 "..." 操作菜单
3. 确认菜单中包含 "Export PNG"、"Export SVG"、"View Source" 选项
4. 点击 "Export PNG"，确认成功下载 PNG 图片
5. 点击 "Export SVG"，确认成功下载 SVG 图片
6. 鼠标悬停图表数据点，确认 tooltip 正确显示
7. 对散点图/柱状图尝试点击数据点，确认高亮交互生效

**预期结果**:
- 导出菜单正常显示
- PNG/SVG 文件可成功下载且内容正确
- tooltip 显示完整数据字段
- 点击交互正常工作

---

### CHK-vega-lite-migration-CDN加载-006 CDN 加载成功

**关联需求**: REQ-vega-lite-migration-图表引擎替换
**目的**: 验证前端 CDN 脚本正确加载且全局变量可用
**方法**: 浏览器控制台检查
**等级**: 阻塞

**检查步骤**:
1. 打开前端页面，按 F12 进入开发者工具
2. 在 Console 中执行 `typeof window.vega`，确认返回 `'object'`
3. 执行 `typeof window.vl`，确认返回 `'object'`
4. 执行 `typeof window.vegaEmbed`，确认返回 `'function'`
5. 确认 Network 面板中 vega/vega-lite/vega-embed 脚本请求状态为 200
6. 确认无 ECharts 相关脚本请求
7. 确认 `typeof window.echarts` 返回 `'undefined'`

**预期结果**:
- vega、vl、vegaEmbed 全局变量正确加载
- 无 ECharts 残留
- CDN 资源加载无 404 或超时
