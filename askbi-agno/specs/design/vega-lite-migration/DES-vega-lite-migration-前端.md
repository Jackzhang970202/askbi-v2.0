# 前端设计文档

**版本**: v1.0
**模块**: Vega-Lite 图表引擎迁移 (vega-lite-migration)
**关联需求**: REQ-vega-lite-migration

---

## 页面清单

| 页面 | 路由 | 变更类型 | 关联需求 |
|------|------|----------|----------|
| 聊天页 | `#/chat` → MessageItem 图表区域 | 组件替换 | REQ-vega-lite-migration-图表引擎替换 |
| 报表管理 | `#/reports` → ReportManager 图表区域 | 组件替换 | REQ-vega-lite-migration-图表引擎替换 |

---

## 页面设计

### CDN 脚本替换（index.html）

#### 移除脚本
```html
<!-- 移除 -->
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
```

#### 新增脚本
```html
<!-- 新增 Vega-Lite 全家桶 -->
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
```

#### 加载验证
- `window.vega` 对象存在
- `window.vl` 对象存在（vega-lite）
- `window.vegaEmbed` 函数存在

---

### VegaChart 组件设计

#### 组件规格

| 属性 | 值 |
|------|------|
| 文件名 | `VegaChart.jsx` |
| 预估行数 | 约 40 行 |
| 依赖 | `window.vegaEmbed`（CDN 全局变量） |
| 替代 | `EChart.jsx`（82 行，删除） |

#### Props 接口

| Prop | 类型 | 必填 | 说明 |
|------|------|------|------|
| spec | object | 是 | Vega-Lite JSON 规格对象 |
| className | string | 否 | 容器 CSS 类名 |

#### 组件逻辑
1. 使用 `useRef` 创建图表容器 DOM 引用
2. 使用 `useEffect` 在 spec 变化时调用 `window.vegaEmbed(containerRef, spec, options)`
3. vegaEmbed options 配置：
   - `actions: true`：启用导出 PNG/SVG/View Source 菜单
   - `renderer: 'canvas'`：使用 canvas 渲染器
   - `theme: undefined`：使用默认主题
4. 在 useEffect cleanup 中调用 `result.finalize()` 清理前一个图表实例
5. 渲染一个 `<div ref={containerRef} className={className} />` 作为图表容器
6. 捕获 vegaEmbed 异常，渲染错误回退 UI

#### 伪代码

```jsx
import { useRef, useEffect } from 'react';

export default function VegaChart({ spec, className }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!spec || !containerRef.current || !window.vegaEmbed) return;
    let viewResult;
    window.vegaEmbed(containerRef.current, spec, {
      actions: true,
      renderer: 'canvas'
    }).then(result => {
      viewResult = result;
    }).catch(err => {
      console.error('VegaLite render error:', err);
    });
    return () => {
      if (viewResult) viewResult.finalize();
    };
  }, [spec]);

  return <div ref={containerRef} className={className} />;
}
```

---

### MessageItem.jsx 图表检测逻辑修改

#### 当前逻辑（ECharts）
```jsx
// 当前检测方式
if (chart && chart.series) {
  // 渲染 EChart 组件
}
```

#### 修改后逻辑（Vega-Lite + 兼容降级）
```jsx
// 新检测方式
function isVegaLite(chart) {
  return chart && (chart.$schema || chart.mark);
}

function isEChartsLegacy(chart) {
  return chart && !chart.$schema && (chart.series || chart.xAxis || chart.yAxis);
}

function isNoChart(chart) {
  return chart && chart.chart_needed === false;
}
```

#### 渲染分发逻辑
1. `isVegaLite(chart)` → 渲染 `<VegaChart spec={chart} />`
2. `isEChartsLegacy(chart)` → 渲染降级占位 UI（"图表引擎已升级，历史图表不再支持渲染"）
3. `isNoChart(chart)` → 不渲染图表区域
4. 其他情况 → 不渲染图表区域

#### 降级占位 UI 设计
- 外框: 虚线边框，浅灰色背景，圆角，高度 200px，flex 居中
- 图标: 信息提示图标（可使用 unicode 字符 ⓘ）
- 主文本: "图表引擎已升级"（字体 14px，灰色）
- 副文本: "历史图表不再支持渲染，请重新提问以获取新图表"（字体 12px，浅灰色）
- 数据回退: 若 `structuredData` 中包含 `tables` 数据，以简易表格形式展示原始数据

---

### ReportManager.jsx 图表区域修改

#### 修改点
1. 将 `import EChart from './EChart'` 替换为 `import VegaChart from './VegaChart'`
2. 报表中图表渲染区域使用 `<VegaChart spec={chartData} />` 替代 `<EChart option={chartData} />`
3. 添加与 MessageItem.jsx 相同的格式检测逻辑，对历史 ECharts 报表显示降级占位

---

### 文件删除

| 文件 | 操作 | 原因 |
|------|------|------|
| `frontend/src/components/EChart.jsx` | 删除 | 被 VegaChart.jsx 完全替代 |

删除前确认无其他文件引用 `EChart.jsx`（通过 grep `import.*EChart` 验证）。

---

## 组件关系

```
MessageItem.jsx
  ├── isVegaLite → VegaChart.jsx (新)
  ├── isEChartsLegacy → 降级占位 UI (内联)
  └── isNoChart → 不渲染

ReportManager.jsx
  ├── Vega-Lite 数据 → VegaChart.jsx (新)
  └── ECharts 历史数据 → 降级占位 UI (内联)
```

---

## 接口

- `GET /chat/{chat_id}/messages` — 加载消息列表（响应格式不变，`structuredData.chart` 内容由后端决定）
- 无新增接口，无接口参数变更

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| CDN 脚本加载失败 | vegaEmbed 不存在时降级为不渲染图表，console 输出警告 |
| Vega-Lite JSON 解析失败 | vegaEmbed catch 捕获，显示空白图表区域，console 输出错误 |
| 历史 ECharts 消息 | 显示降级占位 UI，不尝试渲染 |
| chart 字段为空或 null | 不渲染图表区域 |
