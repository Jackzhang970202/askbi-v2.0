# 后端设计文档

**版本**: v1.0
**模块**: Vega-Lite 图表引擎迁移 (vega-lite-migration)
**关联需求**: REQ-vega-lite-migration

---

## 业务流程

### Prompt 重写流程
读取 `prompt.py` → 删除原 ECHARTS_BAR/LINE/PIE_PROMPT 常量 → 定义 VEGALITE_SYSTEM_PROMPT → 定义 CHART_TYPE_SPECS 字典（10 种图表类型）→ 实现 `build_chart_prompt()` 函数

### 工作流图表生成流程
工作流执行到图表生成步骤 → 调用 `build_chart_prompt(data_sample, chart_type_hint)` 构建 prompt → 调用 LLM → LLM 输出 Vega-Lite JSON → 解析验证 JSON 合法性 → 写入 `chart` 字段 → 返回响应

### Agent 指令更新流程
更新 bi_chart_agent / askexcel_chart_agent 的 instructions → 引用新的 VEGALITE_SYSTEM_PROMPT → 移除 ECharts 相关指令

---

## 业务规则

| 规则 | 说明 | 校验方式 |
|------|------|----------|
| R001 | LLM 输出的 chart JSON 必须包含 `$schema` 字段 | 解析后校验 `$schema` 存在 |
| R002 | LLM 输出必须为纯 JSON，无 markdown 代码块包裹 | 正则去除 ```json 包裹后解析 |
| R003 | 图表数据通过 `data.values` 内联 | prompt 中约束 |
| R004 | 配色方案统一使用 category10 / tableau10 | VEGALITE_SYSTEM_PROMPT 中指定 |
| R005 | 图表标题和轴标签支持中文 | Vega-Lite config 中设置 font |
| R006 | 无需图表时返回 `{"chart_needed": false, "reason": "..."}` | prompt 中约束输出格式 |
| R007 | 10 种图表类型均有对应的 prompt 规格和示例 | CHART_TYPE_SPECS 完整性校验 |

---

## Prompt 设计

### prompt.py 模块结构

```python
# prompt.py 重写后的结构

VEGALITE_SYSTEM_PROMPT = """
你是一个专业的数据可视化图表生成器。根据用户的问题和查询结果数据，
生成符合 Vega-Lite v5 规范的 JSON 图表规格。

## 输出格式要求
- 输出纯 JSON，不要使用 markdown 代码块包裹
- JSON 必须包含 "$schema": "https://vega.github.io/schema/vega-lite/v5.json"
- 数据通过 "data": {"values": [...]} 内联
- 使用中文作为标题和轴标签
- 配色方案使用 "category10" 或 "tableau10"
- 默认图表宽度 600，高度 400

## 通用编码规则
- 时间字段使用 temporal 类型
- 数值字段使用 quantitative 类型
- 分类字段使用 nominal 类型
- tooltip 配置 {"content": "data"} 显示完整数据

## 图表类型选择指南
根据数据特征选择最合适的图表类型：
- 分类对比 → bar
- 趋势变化 → line
- 占比分布 → pie (arc mark)
- 连续分布 → area
- 相关性分析 → scatter
- 矩阵数据 → heatmap
- 层级数据 → treemap
- 多维度对比 → stacked_bar
- 增减分析 → waterfall
- 多维评价 → radar
"""

CHART_TYPE_SPECS = {
    "bar": {
        "description": "柱状图，适用于分类数据的对比比较",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "各部门销售额对比",
            "mark": "bar",
            "data": {"values": [{"部门": "A", "销售额": 100}]},
            "encoding": {
                "x": {"field": "部门", "type": "nominal", "axis": {"labelAngle": 0}},
                "y": {"field": "销售额", "type": "quantitative"},
                "color": {"field": "部门", "type": "nominal", "legend": None},
                "tooltip": {"content": "data"}
            }
        }
    },
    "line": {
        "description": "折线图，适用于展示数据随时间的趋势变化",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "月度销售趋势",
            "mark": {"type": "line", "point": True},
            "data": {"values": [{"月份": "2026-01", "销售额": 100}]},
            "encoding": {
                "x": {"field": "月份", "type": "temporal"},
                "y": {"field": "销售额", "type": "quantitative"},
                "tooltip": {"content": "data"}
            }
        }
    },
    "pie": {
        "description": "饼图，适用于展示各部分占总体的比例分布",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "产品类别占比",
            "mark": {"type": "arc", "innerRadius": 0},
            "data": {"values": [{"类别": "A", "占比": 30}]},
            "encoding": {
                "theta": {"field": "占比", "type": "quantitative"},
                "color": {"field": "类别", "type": "nominal"},
                "tooltip": {"content": "data"}
            }
        }
    },
    "area": {
        "description": "面积图，适用于展示连续数据的累积分布",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "月度累积收入",
            "mark": {"type": "area", "opacity": 0.7},
            "data": {"values": [{"月份": "2026-01", "收入": 100}]},
            "encoding": {
                "x": {"field": "月份", "type": "temporal"},
                "y": {"field": "收入", "type": "quantitative"},
                "tooltip": {"content": "data"}
            }
        }
    },
    "scatter": {
        "description": "散点图，适用于分析两个数值变量之间的相关性",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "身高体重分布",
            "mark": "point",
            "data": {"values": [{"身高": 170, "体重": 65}]},
            "encoding": {
                "x": {"field": "身高", "type": "quantitative"},
                "y": {"field": "体重", "type": "quantitative"},
                "tooltip": {"content": "data"}
            }
        }
    },
    "heatmap": {
        "description": "热力图，适用于矩阵数据的密度和模式分析",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "每周各时段活跃度",
            "mark": "rect",
            "data": {"values": [{"星期": "周一", "时段": "上午", "活跃度": 80}]},
            "encoding": {
                "x": {"field": "时段", "type": "nominal"},
                "y": {"field": "星期", "type": "nominal"},
                "color": {"field": "活跃度", "type": "quantitative", "scale": {"scheme": "blues"}},
                "tooltip": {"content": "data"}
            }
        }
    },
    "treemap": {
        "description": "矩形树图，适用于展示层级结构中各部分的大小比例",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "部门人员分布",
            "mark": "rect",
            "data": {"values": [{"部门": "技术部", "人数": 50}]},
            "encoding": {
                "size": {"field": "人数", "type": "quantitative"},
                "color": {"field": "部门", "type": "nominal"},
                "tooltip": {"content": "data"}
            },
            "transform": [{"treemap": "人数", "groupby": ["部门"]}]
        }
    },
    "stacked_bar": {
        "description": "堆叠柱状图，适用于多维度分类数据的构成对比",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "各季度产品线销售构成",
            "mark": "bar",
            "data": {"values": [{"季度": "Q1", "产品线": "A", "销售额": 100}]},
            "encoding": {
                "x": {"field": "季度", "type": "nominal"},
                "y": {"field": "销售额", "type": "quantitative", "stack": True},
                "color": {"field": "产品线", "type": "nominal"},
                "tooltip": {"content": "data"}
            }
        }
    },
    "waterfall": {
        "description": "瀑布图，适用于展示数值的逐步增减变化过程",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "利润构成瀑布图",
            "data": {"values": [{"项目": "收入", "金额": 1000, "类型": "positive"}]},
            "transform": [
                {"window": [{"op": "sum", "field": "金额", "as": "cumsum"}]},
                {"calculate": "datum.cumsum - datum.金额", "as": "prev"}
            ],
            "layer": [
                {
                    "mark": {"type": "bar", "opacity": 0},
                    "encoding": {
                        "y": {"field": "prev", "type": "quantitative"}
                    }
                },
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "项目", "type": "nominal"},
                        "y": {"field": "金额", "type": "quantitative"},
                        "color": {"field": "类型", "type": "nominal", "scale": {"domain": ["positive", "negative"], "range": ["#4CAF50", "#F44336"]}},
                        "tooltip": {"content": "data"}
                    }
                }
            ]
        }
    },
    "radar": {
        "description": "雷达图，适用于多维度综合评价的可视化",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "员工能力评估",
            "data": {"values": [{"维度": "技术", "得分": 85, "人员": "张三"}]},
            "layer": [
                {
                    "mark": {"type": "line", "interpolate": "linear-closed"},
                    "encoding": {
                        "theta": {"field": "维度", "type": "nominal"},
                        "r": {"field": "得分", "type": "quantitative"},
                        "color": {"field": "人员", "type": "nominal"},
                        "tooltip": {"content": "data"}
                    }
                },
                {
                    "mark": {"type": "point"},
                    "encoding": {
                        "theta": {"field": "维度", "type": "nominal"},
                        "r": {"field": "得分", "type": "quantitative"},
                        "color": {"field": "人员", "type": "nominal"}
                    }
                }
            ]
        }
    }
}

def build_chart_prompt(data_sample: list, chart_type_hint: str = None) -> str:
    """
    根据数据样本和可选的图表类型提示，构建完整的图表生成 prompt。

    Args:
        data_sample: 查询结果数据样本（字典列表）
        chart_type_hint: 可选的图表类型提示（如 "bar", "line"）

    Returns:
        完整的图表生成 prompt 字符串
    """
    prompt = VEGALITE_SYSTEM_PROMPT
    prompt += "\n\n## 当前查询数据\n"
    prompt += f"数据样本（前 20 条）：\n{json.dumps(data_sample[:20], ensure_ascii=False, indent=2)}\n"

    if chart_type_hint and chart_type_hint in CHART_TYPE_SPECS:
        spec = CHART_TYPE_SPECS[chart_type_hint]
        prompt += f"\n## 推荐图表类型：{chart_type_hint}\n"
        prompt += f"适用场景：{spec['description']}\n"
        prompt += f"参考规格：\n{json.dumps(spec['example'], ensure_ascii=False, indent=2)}\n"
    else:
        prompt += "\n## 可用图表类型参考\n"
        for chart_type, spec in CHART_TYPE_SPECS.items():
            prompt += f"- {chart_type}: {spec['description']}\n"

    prompt += "\n请根据数据特征选择最合适的图表类型，生成完整的 Vega-Lite JSON。"
    return prompt
```

### 图表类型推荐逻辑

| 数据特征 | 推荐图表类型 | 判断依据 |
|----------|-------------|----------|
| 分类 + 数值（<15 类） | bar | 少量分类对比 |
| 时间序列 + 数值 | line | 趋势分析 |
| 分类 + 数值（占比场景） | pie | 总和为 100% 或明确要求占比 |
| 时间序列 + 累积数值 | area | 连续累积分布 |
| 两个数值维度 | scatter | 相关性分析 |
| 两个分类 + 一个数值 | heatmap | 矩阵密度 |
| 层级结构 | treemap | 构成比例 |
| 分类 + 子分类 + 数值 | stacked_bar | 多维构成对比 |
| 增减项 + 数值 | waterfall | 增减过程 |
| 多维度评价（3+ 维度） | radar | 综合评价 |

注：图表类型最终由 LLM 根据 prompt 中的数据和类型指南自主决定，推荐逻辑仅作为 chart_type_hint 辅助参考。

---

## 工作流修改设计

### bi_workflow.py 修改

修改图表生成步骤的 prompt 构建方式：

```python
# 修改前（ECharts）
chart_prompt = ECHARTS_BAR_PROMPT  # 或 LINE/PIE

# 修改后（Vega-Lite）
from prompt import build_chart_prompt
chart_prompt = build_chart_prompt(data_sample=query_result, chart_type_hint=None)
```

涉及修改点：
- 导入语句：`from prompt import build_chart_prompt` 替代原 ECharts prompt 导入
- 图表生成步骤：将 `chart_prompt` 替换为 `build_chart_prompt()` 的返回值
- 不修改工作流整体结构和其他步骤

### askexcel_workflow.py 修改

与 bi_workflow.py 相同的修改模式：
- 导入 `build_chart_prompt`
- 图表生成步骤使用新的 prompt 构建函数

### chart_generator.py 修改

- 更新 agent instructions 为 Vega-Lite 相关指令
- 移除 autogen agent 中 ECharts 专用的 prompt 模板引用
- 保留 agent 调用 LLM 的核心逻辑不变

### bi_chart_agent.py 修改

- 更新 agent 的 system prompt 为 VEGALITE_SYSTEM_PROMPT
- 移除 ECharts option 格式相关的指令

### askexcel_chart_agent.py 修改

- 同 bi_chart_agent.py，更新 system prompt
- 移除 ECharts 相关指令

---

## 核心函数

### build_chart_prompt(data_sample, chart_type_hint)

| 参数 | 类型 | 说明 |
|------|------|------|
| data_sample | list[dict] | 查询结果数据样本 |
| chart_type_hint | str / None | 可选图表类型提示 |

返回值：完整的图表生成 prompt 字符串，包含系统指令 + 数据上下文 + 类型指南。

### validate_vegalite_json(chart_json)

| 参数 | 类型 | 说明 |
|------|------|------|
| chart_json | str / dict | LLM 输出的图表 JSON |

返回值：解析后的 Vega-Lite dict，校验失败时返回 `{"chart_needed": False, "reason": "JSON 解析失败"}`。

校验逻辑：
1. 若输入为字符串，尝试 JSON 解析
2. 去除可能的 markdown 代码块包裹（```json ... ```）
3. 检查是否存在 `$schema` 或 `mark` 字段
4. 若校验失败，记录日志并返回降级结果

---

## 设计约束

1. prompt.py 重写仅影响图表生成相关的 prompt 内容，不改变 SQL 生成、报告生成等其他 prompt
2. 工作流修改范围控制在图表生成步骤的 prompt 构建，不改变工作流的 Agent 编排和任务调度逻辑
3. `build_chart_prompt()` 函数为纯函数，无副作用，易于测试
4. CHART_TYPE_SPECS 中的 JSON 示例均为可独立运行的合法 Vega-Lite 规格
5. 图表 JSON 校验为软校验（warn + fallback），不阻塞主流程
