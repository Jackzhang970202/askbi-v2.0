#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部门维度考勤报表生成模块

📅 更新日期: 2026.03.24
📝 变更说明: 将 generate_dept_report.py 封装为可调用函数形式

数据源：
1. 考勤分析（人员明细）表 - 个人维度考勤分析结果
2. 考勤汇总表 - 补充部门归属信息

输出：部门维度考勤分析报表
"""

import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Dict, Any


# ============================================================
# JSON 序列化辅助函数
# ============================================================

def clean_for_json(obj):
    """清理数据使其可以 JSON 序列化"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return clean_for_json(obj.tolist())
    return obj


# ============================================================
# 配置区
# ============================================================

# 阈值参数（对应规则说明中的自由度参数）
THRESHOLD_LATE_CLOCK_IN = "08:25:00"    # 平均上班时间在此之后算"晚到"
THRESHOLD_EARLY_CLOCK_OUT = "17:45:00"  # 平均下班时间在此之前算"早走"
THRESHOLD_BUSINESS_TRIP_RATE = 0.5      # 出差率阈值 50%
THRESHOLD_LATE_COUNT = 2                # 迟到次数阈值
THRESHOLD_MAKEUP_COUNT = 2              # 补签次数阈值


# ============================================================
# 工具函数
# ============================================================

def time_str_to_seconds(t):
    """将时间字符串 (HH:MM:SS) 转换为秒数（保留小数秒精度）"""
    if pd.isna(t) or t is None:
        return np.nan
    if isinstance(t, datetime):
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1_000_000
    if isinstance(t, timedelta):
        return t.total_seconds()
    # datetime.time 不是 datetime 的子类，需单独处理
    from datetime import time as dt_time
    if isinstance(t, dt_time):
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1_000_000
    s = str(t).strip()
    parts = s.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 3600 + float(parts[1]) * 60
    return np.nan


def seconds_to_time_str(s):
    """将秒数转换为 HH:MM:SS 格式字符串"""
    if pd.isna(s) or s is None:
        return None
    s = int(round(s))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


# ============================================================
# 数据加载与预处理
# ============================================================

def preprocess(df_individual, df_summary):
    """
    预处理规则：
    D1: 通过工号关联考勤汇总表补充部门信息
    D2: 筛选计入部门人员
    """
    # 规则D1：部门信息填充
    # 个人明细的 一级部门 = 考勤汇总表.所属部门
    # 个人明细的 二级部门 = 考勤汇总表.一级部门
    # 先尝试从个人明细中读取，若为空则从汇总表补充

    # 标准化列名（处理可能的换行符）
    df_individual.columns = [c.replace("\n", "") for c in df_individual.columns]
    df_summary.columns = [c.replace("\n", "") for c in df_summary.columns]

    # 转换百分比字符串列为数值（如 "12.34%" -> 0.1234）
    pct_cols = ["周末出勤率", "下班一小时以上打卡率", "出差率（工作日）"]
    for col in pct_cols:
        if col in df_individual.columns:
            df_individual[col] = df_individual[col].apply(
                lambda x: float(str(x).replace('%', '')) / 100
                if pd.notna(x) and str(x).strip() != '' and '%' in str(x)
                else (x if isinstance(x, (int, float)) else np.nan)
            )

    # 构建工号到部门的映射
    dept_map = df_summary[["浪潮工号", "所属部门", "一级部门"]].drop_duplicates(subset="浪潮工号")
    dept_map = dept_map.rename(columns={
        "所属部门": "_汇总_一级部门",
        "一级部门": "_汇总_二级部门"
    })

    df = df_individual.merge(dept_map, on="浪潮工号", how="left")

    # 填充逻辑：个人明细中为空的，用汇总表补充
    df["一级部门"] = df["一级部门"].fillna(df["_汇总_一级部门"])
    df["二级部门"] = df["二级部门"].fillna(df["_汇总_二级部门"])

    # 删除临时列
    df.drop(columns=["_汇总_一级部门", "_汇总_二级部门"], inplace=True)

    # 将空字符串也视为缺失
    df["一级部门"] = df["一级部门"].replace("", np.nan)
    # 二级部门的空字符串保留（呈现形式中有空字符串的二级部门行）

    # 规则D2：筛选计入部门人员
    df_included = df[df["是否计入部门"] == "是"].copy()

    # 转换时间列为秒数
    df_included["_上班秒数"] = df_included["平均上班时间"].apply(time_str_to_seconds)
    df_included["_下班秒数"] = df_included["平均下班时间"].apply(time_str_to_seconds)

    return df_included


# ============================================================
# 部门结构与排序（动态获取）
# ============================================================

def extract_dept_structure(df_included):
    """
    从个人维度数据中动态提取部门结构

    📅 2026.04.07 新增：替代硬编码的DEPT_ORDER
    📝 变更说明：部门名称可能变化，改为动态从数据中提取

    Returns:
        dict: {一级部门名: [二级部门列表] 或 None}
    """
    dept_structure = {}
    for dept1 in df_included['一级部门'].unique():
        if pd.notna(dept1) and dept1 != '':
            sub_depts = df_included[df_included['一级部门'] == dept1]['二级部门'].unique().tolist()
            # 过滤空值，排序
            sub_depts = sorted([d for d in sub_depts if pd.notna(d) and d != ''])
            dept_structure[dept1] = sub_depts if sub_depts else None
    return dept_structure


# ============================================================
# 部门级聚合计算
# ============================================================

def calc_dept_stats(group):
    """计算单个部门（二级部门或仅有合计的一级部门）的各项指标"""
    if len(group) == 0:
        return {
            "部门人数": 0,
            "贡献时长": None,
            "周末出勤率": None,
            "下班一小时以上打卡率": None,
            "平均上班时间在8：25后人员": 0,
            "平均下班时间在15分钟内人员": 0,
            "平均上班时间": None,
            "平均下班时间": None,
            "平日贡献": None,
            "周末贡献": None,
            "法定节假日带薪贡献": None,
            "出差率": None,
            "月出差大于50%的人数": 0,
            "月出差大于50%的人数占比": None,
            "迟到次数大于2次人员": 0,
            "补签次数大于2次人员": 0,
        }

    count = len(group)

    # 均值类
    mean_contribution = group["贡献时长"].mean() if group["贡献时长"].notna().any() else None
    mean_weekend_rate = group["周末出勤率"].mean() if group["周末出勤率"].notna().any() else None
    mean_after_hour_rate = group["下班一小时以上打卡率"].mean() if group["下班一小时以上打卡率"].notna().any() else None
    mean_clock_in_sec = group["_上班秒数"].mean() if group["_上班秒数"].notna().any() else None
    mean_clock_out_sec = group["_下班秒数"].mean() if group["_下班秒数"].notna().any() else None
    mean_weekday_contrib = group["平时贡献"].mean() if group["平时贡献"].notna().any() else None
    mean_weekend_contrib = group["周末贡献"].mean() if group["周末贡献"].notna().any() else None
    mean_holiday_contrib = group["法定节假日带薪贡献"].mean() if group["法定节假日带薪贡献"].notna().any() else None
    mean_trip_rate = group["出差率（工作日）"].mean() if group["出差率（工作日）"].notna().any() else None

    # 计数类
    threshold_late_sec = time_str_to_seconds(THRESHOLD_LATE_CLOCK_IN)
    threshold_early_sec = time_str_to_seconds(THRESHOLD_EARLY_CLOCK_OUT)

    late_clock_in_count = int((group["_上班秒数"] > threshold_late_sec).sum())
    early_clock_out_count = int((group["_下班秒数"] <= threshold_early_sec).sum())
    high_trip_count = int((group["出差率（工作日）"] > THRESHOLD_BUSINESS_TRIP_RATE).sum())
    late_count = int((group["迟到次数"] > THRESHOLD_LATE_COUNT).sum())
    makeup_count = int((group["补签次数"] > THRESHOLD_MAKEUP_COUNT).sum())

    # 占比
    trip_ratio = high_trip_count / count if count > 0 else None

    return {
        "部门人数": count,
        "贡献时长": mean_contribution,
        "周末出勤率": mean_weekend_rate,
        "下班一小时以上打卡率": mean_after_hour_rate,
        "平均上班时间在8：25后人员": late_clock_in_count,
        "平均下班时间在15分钟内人员": early_clock_out_count,
        "平均上班时间": mean_clock_in_sec,
        "平均下班时间": mean_clock_out_sec,
        "平日贡献": mean_weekday_contrib,
        "周末贡献": mean_weekend_contrib,
        "法定节假日带薪贡献": mean_holiday_contrib,
        "出差率": mean_trip_rate,
        "月出差大于50%的人数": high_trip_count,
        "月出差大于50%的人数占比": trip_ratio,
        "迟到次数大于2次人员": late_count,
        "补签次数大于2次人员": makeup_count,
    }


def aggregate_subtotal(sub_stats_list):
    """
    规则D4：合计行计算 - 各二级部门值的简单平均/求和
    计数类：SUM
    均值类：MEAN（不加权）
    占比类：合计人数/合计部门人数
    """
    if not sub_stats_list:
        return calc_dept_stats(pd.DataFrame())

    count_cols = ["部门人数", "平均上班时间在8：25后人员", "平均下班时间在15分钟内人员",
                  "月出差大于50%的人数", "迟到次数大于2次人员", "补签次数大于2次人员"]
    mean_cols = ["贡献时长", "周末出勤率", "下班一小时以上打卡率",
                 "平均上班时间", "平均下班时间", "平日贡献", "周末贡献",
                 "法定节假日带薪贡献", "出差率"]

    result = {}

    # 计数类：求和
    for col in count_cols:
        result[col] = sum(s[col] for s in sub_stats_list)

    # 均值类：各二级部门均值的简单平均
    for col in mean_cols:
        vals = [s[col] for s in sub_stats_list if s[col] is not None and not (isinstance(s[col], float) and np.isnan(s[col]))]
        result[col] = np.mean(vals) if vals else None

    # 占比类
    total_people = result["部门人数"]
    total_high_trip = result["月出差大于50%的人数"]
    result["月出差大于50%的人数占比"] = total_high_trip / total_people if total_people > 0 else None

    return result


def _generate_report_rows(df_included):
    """生成部门维度报表，部门按合计贡献时长由高到低排序"""

    # 动态提取部门结构（替代硬编码DEPT_ORDER）
    dept_structure = extract_dept_structure(df_included)

    # 第一步：为每个一级部门生成数据块（二级部门行 + 合计行）
    dept_blocks = []  # 每个元素: (dept1_name, subtotal_stats, block_rows)

    for dept1_name, sub_depts in dept_structure.items():
        block_rows = []
        # 该一级部门所有人员
        dept1_group = df_included[df_included["一级部门"] == dept1_name]

        if sub_depts is None or len(sub_depts) == 0:
            # 无二级部门，仅输出合计行（直接用所有人员计算）
            stats = calc_dept_stats(dept1_group)
            stats["一级部门"] = dept1_name
            stats["二级部门"] = "合计"
            block_rows.append(stats)
            dept_blocks.append((dept1_name, stats, block_rows))
        else:
            # 有二级部门：先输出各二级部门行
            for sub_name in sub_depts:
                mask = (df_included["一级部门"] == dept1_name) & (df_included["二级部门"] == sub_name)
                group = df_included[mask]
                stats = calc_dept_stats(group)
                stats["一级部门"] = dept1_name
                stats["二级部门"] = sub_name
                block_rows.append(stats)

            # 处理空二级部门的人员（二级部门为空或NaN）
            mask_empty = (df_included["一级部门"] == dept1_name) & (
                df_included["二级部门"].isna() | (df_included["二级部门"] == "")
            )
            if mask_empty.any():
                group_empty = df_included[mask_empty]
                stats_empty = calc_dept_stats(group_empty)
                stats_empty["一级部门"] = dept1_name
                stats_empty["二级部门"] = ""
                block_rows.append(stats_empty)

            # 合计行：直接用该一级部门所有人员计算（均值按人头加权）
            subtotal = calc_dept_stats(dept1_group)
            subtotal["一级部门"] = dept1_name
            subtotal["二级部门"] = "合计"
            block_rows.append(subtotal)
            dept_blocks.append((dept1_name, subtotal, block_rows))

    # 第二步：按合计贡献时长由高到低排序（None视为0）
    def sort_key(item):
        v = item[1].get("贡献时长")
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return 0
        return v

    dept_blocks.sort(key=sort_key, reverse=True)

    # 第三步：按排序后顺序组装结果
    rows = []
    for dept1_name, subtotal, block_rows in dept_blocks:
        rows.extend(block_rows)

    # 总计行：用全部人员计算
    grand_total = calc_dept_stats(df_included)
    grand_total["一级部门"] = "总计"
    grand_total["二级部门"] = ""
    rows.append(grand_total)

    return rows


def format_output(rows):
    """格式化输出为DataFrame"""
    output_cols = [
        "一级部门", "二级部门", "部门人数", "贡献时长", "周末出勤率",
        "下班一小时以上打卡率", "平均上班时间在8：25后人员", "平均下班时间在15分钟内人员",
        "平均上班时间", "平均下班时间", "平日贡献", "周末贡献",
        "法定节假日带薪贡献", "出差率", "月出差大于50%的人数",
        "月出差大于50%的人数占比", "迟到次数大于2次人员", "补签次数大于2次人员"
    ]

    df_out = pd.DataFrame(rows, columns=output_cols)

    # 格式化时间列
    df_out["平均上班时间"] = df_out["平均上班时间"].apply(seconds_to_time_str)
    df_out["平均下班时间"] = df_out["平均下班时间"].apply(seconds_to_time_str)

    # 格式化数值列（保留2位小数）
    numeric_round2 = ["贡献时长", "平日贡献", "周末贡献", "法定节假日带薪贡献"]
    for col in numeric_round2:
        df_out[col] = df_out[col].apply(lambda x: round(x, 2) if pd.notna(x) else x)

    # 百分比列：转为百分数字符串，保留小数点后两位（如 "12.34%"）
    pct_cols = ["周末出勤率", "下班一小时以上打卡率", "出差率", "月出差大于50%的人数占比"]
    for col in pct_cols:
        df_out[col] = df_out[col].apply(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else x)

    # 整数列
    int_cols = ["部门人数", "平均上班时间在8：25后人员", "平均下班时间在15分钟内人员",
                "月出差大于50%的人数", "迟到次数大于2次人员", "补签次数大于2次人员"]
    for col in int_cols:
        df_out[col] = df_out[col].apply(lambda x: int(x) if pd.notna(x) else x)

    return df_out


# ============================================================
# 对外接口
# ============================================================

def generate_dept_report(
    detail_file_path: str,
    summary_file_path: str,
    output_file_path: str
) -> Dict[str, Any]:
    """
    生成部门维度考勤报表

    参数:
        detail_file_path: 个人维度明细表文件路径
        summary_file_path: 考勤汇总表文件路径
        output_file_path: 输出Excel文件路径

    返回:
        {
            "success": bool,
            "message": str,
            "summary_text": str,
            "output_file": str,
            "row_count": int,
            "column_count": int,
            "yellow_cells_count": int,
            "problem_count": int,
            "preview_data": list,
            "columns": list
        }
    """
    try:
        # 加载数据
        df_individual = pd.read_excel(detail_file_path)
        df_summary = pd.read_excel(summary_file_path)

        # 预处理
        df_included = preprocess(df_individual, df_summary)

        included_count = len(df_included)

        # 生成部门维度报表
        rows = _generate_report_rows(df_included)

        # 格式化输出
        df_out = format_output(rows)

        # 写入Excel
        df_out.to_excel(output_file_path, index=False, sheet_name="部门维度分析")

        # 输出列
        columns_order = df_out.columns.tolist()

        # 预览数据（前10行）
        preview_df = df_out.head(10)
        preview_data = preview_df.to_dict(orient='records')
        preview_data = clean_for_json(preview_data)

        # 汇总信息（动态计算一级部门数）
        dept1_count = df_included['一级部门'].nunique()
        total_rows = len(df_out)
        summary_lines = [
            f"✓ 部门维度报表生成成功",
            f"  计入部门人员数: {included_count}",
            f"  一级部门数: {dept1_count}",
            f"  输出行数: {total_rows}（含合计行和总计行）"
        ]
        summary_text = "\n".join(summary_lines)

        return {
            "success": True,
            "message": f"部门维度报表生成成功，共{total_rows}行",
            "summary_text": summary_text,
            "output_file": output_file_path,
            "row_count": total_rows,
            "column_count": len(columns_order),
            "yellow_cells_count": 0,
            "problem_count": 0,
            "preview_data": preview_data,
            "columns": columns_order
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"部门维度报表生成失败: {str(e)}",
            "output_file": None,
            "row_count": 0,
            "column_count": 0,
            "yellow_cells_count": 0,
            "problem_count": 0,
            "preview_data": [],
            "columns": [],
            "error": str(e),
            "traceback": traceback.format_exc()
        }
