"""Vega-Lite 图表生成 Prompt 与工具函数。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

VEGALITE_SYSTEM_PROMPT = """\
你是一个专业的数据可视化图表生成器。根据用户的问题和查询结果数据，生成符合 Vega-Lite v5 规范的 JSON 图表规格。

## 输出格式要求
- 输出纯 JSON，不要使用 markdown 代码块包裹
- JSON 必须包含 "$schema": "https://vega.github.io/schema/vega-lite/v5.json"
- 数据通过 "data": {"values": [...]} 内联
- 使用中文作为标题和轴标签
- 配色方案使用 "category10" 或 "tableau10"
- 默认图表宽度 600，高度 400
- 背景透明（config.view.transparent = true 或不设 background）

## 通用编码规则
- 时间字段使用 temporal 类型
- 数值字段使用 quantitative 类型
- 分类字段使用 nominal 类型
- tooltip 配置 {"content": "data"} 显示完整数据

## 图表类型选择指南
根据数据特征选择最合适的图表类型：
- 分类对比（<15 类） → bar
- 趋势变化（时间序列） → line
- 占比分布 → pie (arc mark)
- 连续累积分布 → area
- 相关性分析（两个数值变量） → scatter
- 矩阵数据（两个分类+一个数值） → heatmap
- 层级数据 → treemap
- 多维度构成对比 → stacked_bar
- 增减分析 → waterfall
- 多维评价（3+ 维度） → radar

## 不生成图表的情况
如果数据不适合可视化（如单条标量、文本结果、无结构化数值），请输出：
{"chart_needed": false, "reason": "说明原因"}"""

CHART_TYPE_SPECS: Dict[str, Dict[str, Any]] = {
    "bar": {
        "description": "柱状图，适用于分类数据的对比比较",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "各部门销售额对比",
            "width": 600, "height": 400,
            "mark": "bar",
            "data": {"values": [{"部门": "A", "销售额": 100}]},
            "encoding": {
                "x": {"field": "部门", "type": "nominal", "axis": {"labelAngle": 0}},
                "y": {"field": "销售额", "type": "quantitative"},
                "color": {"field": "部门", "type": "nominal", "legend": None},
                "tooltip": {"content": "data"},
            },
        },
    },
    "line": {
        "description": "折线图，适用于展示数据随时间的趋势变化",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "月度销售趋势",
            "width": 600, "height": 400,
            "mark": {"type": "line", "point": True},
            "data": {"values": [{"月份": "2026-01", "销售额": 100}]},
            "encoding": {
                "x": {"field": "月份", "type": "temporal"},
                "y": {"field": "销售额", "type": "quantitative"},
                "tooltip": {"content": "data"},
            },
        },
    },
    "pie": {
        "description": "饼图，适用于展示各部分占总体的比例分布",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "产品类别占比",
            "width": 400, "height": 400,
            "mark": {"type": "arc", "innerRadius": 0},
            "data": {"values": [{"类别": "A", "占比": 30}]},
            "encoding": {
                "theta": {"field": "占比", "type": "quantitative"},
                "color": {"field": "类别", "type": "nominal"},
                "tooltip": {"content": "data"},
            },
        },
    },
    "area": {
        "description": "面积图，适用于展示连续数据的累积分布",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "月度累积收入",
            "width": 600, "height": 400,
            "mark": {"type": "area", "opacity": 0.7},
            "data": {"values": [{"月份": "2026-01", "收入": 100}]},
            "encoding": {
                "x": {"field": "月份", "type": "temporal"},
                "y": {"field": "收入", "type": "quantitative"},
                "tooltip": {"content": "data"},
            },
        },
    },
    "scatter": {
        "description": "散点图，适用于分析两个数值变量之间的相关性",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "身高体重分布",
            "width": 600, "height": 400,
            "mark": "point",
            "data": {"values": [{"身高": 170, "体重": 65}]},
            "encoding": {
                "x": {"field": "身高", "type": "quantitative"},
                "y": {"field": "体重", "type": "quantitative"},
                "tooltip": {"content": "data"},
            },
        },
    },
    "heatmap": {
        "description": "热力图，适用于矩阵数据的密度和模式分析",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "每周各时段活跃度",
            "width": 600, "height": 400,
            "mark": "rect",
            "data": {"values": [{"星期": "周一", "时段": "上午", "活跃度": 80}]},
            "encoding": {
                "x": {"field": "时段", "type": "nominal"},
                "y": {"field": "星期", "type": "nominal"},
                "color": {"field": "活跃度", "type": "quantitative", "scale": {"scheme": "blues"}},
                "tooltip": {"content": "data"},
            },
        },
    },
    "treemap": {
        "description": "矩形树图，适用于展示层级结构中各部分的大小比例",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "部门人员分布",
            "width": 600, "height": 400,
            "mark": "rect",
            "data": {"values": [{"部门": "技术部", "人数": 50}]},
            "encoding": {
                "size": {"field": "人数", "type": "quantitative"},
                "color": {"field": "部门", "type": "nominal"},
                "tooltip": {"content": "data"},
            },
            "transform": [{"treemap": "人数", "groupby": ["部门"]}],
        },
    },
    "stacked_bar": {
        "description": "堆叠柱状图，适用于多维度分类数据的构成对比",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "各季度产品线销售构成",
            "width": 600, "height": 400,
            "mark": "bar",
            "data": {"values": [{"季度": "Q1", "产品线": "A", "销售额": 100}]},
            "encoding": {
                "x": {"field": "季度", "type": "nominal"},
                "y": {"field": "销售额", "type": "quantitative", "stack": True},
                "color": {"field": "产品线", "type": "nominal"},
                "tooltip": {"content": "data"},
            },
        },
    },
    "waterfall": {
        "description": "瀑布图，适用于展示数值的逐步增减变化过程",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "利润构成瀑布图",
            "width": 600, "height": 400,
            "data": {"values": [{"项目": "收入", "金额": 1000, "类型": "positive"}]},
            "transform": [
                {"window": [{"op": "sum", "field": "金额", "as": "cumsum"}]},
                {"calculate": "datum.cumsum - datum.金额", "as": "prev"},
            ],
            "layer": [
                {
                    "mark": {"type": "bar", "opacity": 0},
                    "encoding": {"y": {"field": "prev", "type": "quantitative"}},
                },
                {
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "项目", "type": "nominal"},
                        "y": {"field": "金额", "type": "quantitative"},
                        "color": {
                            "field": "类型", "type": "nominal",
                            "scale": {"domain": ["positive", "negative"], "range": ["#4CAF50", "#F44336"]},
                        },
                        "tooltip": {"content": "data"},
                    },
                },
            ],
        },
    },
    "radar": {
        "description": "雷达图，适用于多维度综合评价的可视化",
        "example": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "员工能力评估",
            "width": 400, "height": 400,
            "data": {"values": [{"维度": "技术", "得分": 85, "人员": "张三"}]},
            "layer": [
                {
                    "mark": {"type": "line", "interpolate": "linear-closed"},
                    "encoding": {
                        "theta": {"field": "维度", "type": "nominal"},
                        "r": {"field": "得分", "type": "quantitative"},
                        "color": {"field": "人员", "type": "nominal"},
                        "tooltip": {"content": "data"},
                    },
                },
                {
                    "mark": {"type": "point"},
                    "encoding": {
                        "theta": {"field": "维度", "type": "nominal"},
                        "r": {"field": "得分", "type": "quantitative"},
                        "color": {"field": "人员", "type": "nominal"},
                    },
                },
            ],
        },
    },
}


def _json_safe(value: Any):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except Exception:
            pass
    if hasattr(value, 'quantize'):
        try:
            return float(value)
        except Exception:
            return str(value)
    return value


def build_chart_prompt(data_sample: List[Dict[str, Any]], chart_type_hint: Optional[str] = None) -> str:
    """根据数据样本和可选图表类型提示，构建完整的图表生成 prompt。"""
    prompt = VEGALITE_SYSTEM_PROMPT
    prompt += "\n\n## 当前查询数据\n"
    prompt += f"数据样本（前 20 条）：\n{json.dumps(_json_safe(data_sample[:20]), ensure_ascii=False, indent=2)}\n"

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


def validate_vegalite_json(chart_json: str | dict) -> Dict[str, Any]:
    """校验 LLM 输出的 Vega-Lite JSON。

    Returns:
        解析后的 dict。校验失败时返回 {"chart_needed": False, "reason": "..."}
    """
    if isinstance(chart_json, dict):
        if chart_json.get("chart_needed") is False:
            return chart_json
        if "$schema" in chart_json or "mark" in chart_json:
            return chart_json
        return {"chart_needed": False, "reason": "缺少 $schema 或 mark 字段"}

    if not isinstance(chart_json, str):
        return {"chart_needed": False, "reason": f"不支持的类型: {type(chart_json)}"}

    text = chart_json.strip()
    # 去除 markdown 代码块包裹
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("Vega-Lite JSON 解析失败: %s", e)
        return {"chart_needed": False, "reason": f"JSON 解析失败: {e}"}

    if isinstance(parsed, dict):
        if parsed.get("chart_needed") is False:
            return parsed
        if "$schema" in parsed or "mark" in parsed:
            return parsed
        return {"chart_needed": False, "reason": "缺少 $schema 或 mark 字段"}

    return {"chart_needed": False, "reason": "JSON 顶层必须为对象"}
