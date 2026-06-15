#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多月部门维度考勤报表生成模块

📅 更新日期: 2026.04.07
📝 变更说明: 新增多月部门维度报表生成功能

数据源：
- 多月个人维度结果表（每人一行，已合并多月数据）

输出：
- 部门维度报表（动态获取部门结构）
- 按贡献时长排序
- 包含二级部门行、合计行、总计行
"""

import pandas as pd
import numpy as np
import math
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings('ignore')

# 调试输出
def log_debug(msg):
    print(f"[多月部门报表] {msg}")


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
# 配置参数
# ============================================================

# 阈值参数（与单月版本一致）
THRESHOLD_LATE_CLOCK_IN = "08:25:00"    # 平均上班时间在此之后算"晚到"
THRESHOLD_EARLY_CLOCK_OUT = "17:45:00"  # 平均下班时间在此之前算"早走"
THRESHOLD_BUSINESS_TRIP_RATE = 0.5      # 出差率阈值 50%
THRESHOLD_LATE_COUNT = 2                # 迟到次数阈值
THRESHOLD_MAKEUP_COUNT = 2              # 补签次数阈值


# ============================================================
# 工具函数
# ============================================================

def time_str_to_seconds(t):
    """将时间字符串 (HH:MM:SS) 转换为秒数"""
    if pd.isna(t) or t is None or t == '':
        return np.nan
    if isinstance(t, datetime):
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1_000_000
    if isinstance(t, timedelta):
        return t.total_seconds()
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


def parse_percentage(pct_str):
    """将百分比字符串转换为数值（如 '12.34%' -> 0.1234）"""
    if pd.isna(pct_str) or pct_str is None or pct_str == '':
        return np.nan
    if isinstance(pct_str, (int, float)):
        return float(pct_str)
    s = str(pct_str).strip()
    if s.endswith('%'):
        return float(s.rstrip('%')) / 100
    return float(s)


# ============================================================
# 部门结构动态提取
# ============================================================

def extract_dept_structure(df_included):
    """
    从个人维度数据中动态提取部门结构

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
# 数据预处理
# ============================================================

def preprocess(df_individual):
    """
    预处理多月个人维度数据

    Args:
        df_individual: 个人维度结果表（已合并多月数据）

    Returns:
        处理后的DataFrame
    """
    log_debug(f"预处理前列名: {list(df_individual.columns)}")

    # 标准化列名（处理换行符）
    df_individual.columns = [c.replace("\n", "") for c in df_individual.columns]

    log_debug(f"标准化后列名: {list(df_individual.columns)}")

    # 检查必需列是否存在
    required_cols = ['一级部门', '是否计入部门', '平均上班时间', '平均下班时间']
    missing_cols = [col for col in required_cols if col not in df_individual.columns]
    if missing_cols:
        log_debug(f"警告：缺少列: {missing_cols}")

    # 筛选计入部门人员
    if '是否计入部门' not in df_individual.columns:
        log_debug("错误：缺少'是否计入部门'列，无法筛选")
        # 如果没有该列，使用全部数据
        df_included = df_individual.copy()
    else:
        df_included = df_individual[df_individual["是否计入部门"] == "是"].copy()

    log_debug(f"筛选后人员数: {len(df_included)}")

    # 转换时间列为秒数
    if '平均上班时间' in df_included.columns:
        df_included["_上班秒数"] = df_included["平均上班时间"].apply(time_str_to_seconds)
    if '平均下班时间' in df_included.columns:
        df_included["_下班秒数"] = df_included["平均下班时间"].apply(time_str_to_seconds)

    # 转换百分比列为数值
    pct_cols = ["周末出勤率", "下班一小时以上打卡率", "出差率（工作日）"]
    for col in pct_cols:
        if col in df_included.columns:
            df_included[col] = df_included[col].apply(parse_percentage)

    return df_included


# ============================================================
# 部门级聚合计算
# ============================================================

def calc_dept_stats(group):
    """计算单个部门的各项指标"""
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

    # 均值类（安全访问列）
    def safe_mean(df, col):
        if col in df.columns and df[col].notna().any():
            return df[col].mean()
        return None

    mean_contribution = safe_mean(group, "贡献时长")
    mean_weekend_rate = safe_mean(group, "周末出勤率")
    mean_after_hour_rate = safe_mean(group, "下班一小时以上打卡率")
    mean_clock_in_sec = safe_mean(group, "_上班秒数")
    mean_clock_out_sec = safe_mean(group, "_下班秒数")
    mean_weekday_contrib = safe_mean(group, "平时贡献")
    mean_weekend_contrib = safe_mean(group, "周末贡献")
    mean_holiday_contrib = safe_mean(group, "法定节假日带薪贡献")
    mean_trip_rate = safe_mean(group, "出差率（工作日）")

    # 计数类（安全访问列）
    threshold_late_sec = time_str_to_seconds(THRESHOLD_LATE_CLOCK_IN)
    threshold_early_sec = time_str_to_seconds(THRESHOLD_EARLY_CLOCK_OUT)

    if "_上班秒数" in group.columns:
        late_clock_in_count = int((group["_上班秒数"] > threshold_late_sec).sum())
    else:
        late_clock_in_count = 0

    if "_下班秒数" in group.columns:
        early_clock_out_count = int((group["_下班秒数"] <= threshold_early_sec).sum())
    else:
        early_clock_out_count = 0

    # 出差率判断（数值比较）
    trip_rate_vals = group["出差率（工作日）"] if "出差率（工作日）" in group.columns else pd.Series()
    high_trip_count = int((trip_rate_vals > THRESHOLD_BUSINESS_TRIP_RATE).sum())

    if "迟到次数" in group.columns:
        late_count = int((group["迟到次数"] > THRESHOLD_LATE_COUNT).sum())
    else:
        late_count = 0

    if "补签次数" in group.columns:
        makeup_count = int((group["补签次数"] > THRESHOLD_MAKEUP_COUNT).sum())
    else:
        makeup_count = 0

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


# ============================================================
# 报表生成
# ============================================================

def generate_report_rows(df_included):
    """生成部门维度报表，按贡献时长排序"""

    # 动态提取部门结构
    dept_structure = extract_dept_structure(df_included)

    # 为每个一级部门生成数据块
    dept_blocks = []

    for dept1_name, sub_depts in dept_structure.items():
        block_rows = []
        dept1_group = df_included[df_included["一级部门"] == dept1_name]

        if sub_depts is None or len(sub_depts) == 0:
            # 无二级部门，仅输出合计行
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

            # 处理空二级部门的人员
            mask_empty = (df_included["一级部门"] == dept1_name) & (
                df_included["二级部门"].isna() | (df_included["二级部门"] == "")
            )
            if mask_empty.any():
                group_empty = df_included[mask_empty]
                stats_empty = calc_dept_stats(group_empty)
                stats_empty["一级部门"] = dept1_name
                stats_empty["二级部门"] = ""
                block_rows.append(stats_empty)

            # 合计行
            subtotal = calc_dept_stats(dept1_group)
            subtotal["一级部门"] = dept1_name
            subtotal["二级部门"] = "合计"
            block_rows.append(subtotal)
            dept_blocks.append((dept1_name, subtotal, block_rows))

    # 按贡献时长排序
    def sort_key(item):
        v = item[1].get("贡献时长")
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return 0
        return v

    dept_blocks.sort(key=sort_key, reverse=True)

    # 组装结果
    rows = []
    for dept1_name, subtotal, block_rows in dept_blocks:
        rows.extend(block_rows)

    # 总计行
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
        if col in df_out.columns:
            df_out[col] = df_out[col].apply(lambda x: round(x, 2) if pd.notna(x) else x)

    # 百分比列
    pct_cols = ["周末出勤率", "下班一小时以上打卡率", "出差率", "月出差大于50%的人数占比"]
    for col in pct_cols:
        if col in df_out.columns:
            df_out[col] = df_out[col].apply(lambda x: f"{x * 100:.2f}%" if pd.notna(x) else x)

    # 整数列
    int_cols = ["部门人数", "平均上班时间在8：25后人员", "平均下班时间在15分钟内人员",
                "月出差大于50%的人数", "迟到次数大于2次人员", "补签次数大于2次人员"]
    for col in int_cols:
        if col in df_out.columns:
            df_out[col] = df_out[col].apply(lambda x: int(x) if pd.notna(x) else x)

    return df_out


# ============================================================
# 主函数
# ============================================================

def generate_multi_month_dept_report_from_raw(
    detail_file_path: str,
    summary_file_path: str,
    output_file_path: str
) -> Dict[str, Any]:
    """
    从原始明细表和汇总表生成多月部门维度考勤报表

    流程：
    1. 先生成多月个人维度报表
    2. 基于个人维度结果生成部门维度报表

    参数:
        detail_file_path: 多月考勤明细表文件路径
        summary_file_path: 多月考勤汇总表文件路径
        output_file_path: 输出Excel文件路径

    返回:
        {
            "success": bool,
            "message": str,
            "summary_text": str,
            "output_file": str,
            "row_count": int,
            "column_count": int,
            "preview_data": list,
            "columns": list
        }
    """
    try:
        import tempfile
        import shutil

        log_debug("开始生成多月部门维度报表...")

        # 创建临时文件存放个人维度结果
        temp_dir = tempfile.mkdtemp()

        try:
            temp_individual = os.path.join(temp_dir, "multi_month_individual.xlsx")

            # 先生成多月个人维度报表
            log_debug("步骤1: 生成多月个人维度报表...")
            from core.multi_month_report_generator import generate_multi_month_report_from_raw
            individual_result = generate_multi_month_report_from_raw(
                detail_file_path, summary_file_path, temp_individual
            )
            log_debug(f"多月个人维度报表生成完成，成功: {individual_result.get('success')}")

            if not individual_result.get("success"):
                return {
                    "success": False,
                    "message": f"多月个人维度报表生成失败: {individual_result.get('message')}",
                    "output_file": None,
                    "row_count": 0,
                    "column_count": 0,
                    "preview_data": [],
                    "columns": []
                }

            # 基于个人维度结果生成部门维度报表
            log_debug("步骤2: 基于个人维度结果生成部门维度报表...")
            result = generate_multi_month_dept_report(temp_individual, output_file_path)
            log_debug(f"部门维度报表生成完成，成功: {result.get('success')}")

            # 补充月份数量信息
            if result.get("success"):
                result["month_count"] = individual_result.get("month_count", 0)

            return result

        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"多月部门维度报表生成失败: {str(e)}",
            "output_file": None,
            "row_count": 0,
            "column_count": 0,
            "preview_data": [],
            "columns": [],
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def generate_multi_month_dept_report(
    individual_file_path: str,
    output_file_path: str
) -> Dict[str, Any]:
    """
    生成多月部门维度考勤报表

    参数:
        individual_file_path: 多月个人维度结果表文件路径（每人一行）
        output_file_path: 输出Excel文件路径

    返回:
        {
            "success": bool,
            "message": str,
            "summary_text": str,
            "output_file": str,
            "row_count": int,
            "column_count": int,
            "preview_data": list,
            "columns": list
        }
    """
    try:
        # 加载个人维度数据
        df_individual = pd.read_excel(individual_file_path)

        # 预处理
        df_included = preprocess(df_individual)

        included_count = len(df_included)

        # 生成部门维度报表
        rows = generate_report_rows(df_included)

        # 格式化输出
        df_out = format_output(rows)

        # 输出列
        columns_order = df_out.columns.tolist()

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        # 写入Excel
        df_out.to_excel(output_file_path, index=False, sheet_name="部门维度分析")

        # 预览数据
        preview_df = df_out.head(10)
        preview_data = preview_df.to_dict(orient='records')
        preview_data = clean_for_json(preview_data)

        # 汇总信息
        dept1_count = df_included['一级部门'].nunique()
        total_rows = len(df_out)
        summary_lines = [
            f"✓ 多月部门维度报表生成成功",
            f"  计入部门人员数: {included_count}",
            f"  一级部门数: {dept1_count}",
            f"  输出行数: {total_rows}（含合计行和总计行）"
        ]
        summary_text = "\n".join(summary_lines)

        return {
            "success": True,
            "message": f"多月部门维度报表生成成功，共{total_rows}行",
            "summary_text": summary_text,
            "output_file": output_file_path,
            "row_count": total_rows,
            "column_count": len(columns_order),
            "preview_data": preview_data,
            "columns": columns_order
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"多月部门维度报表生成失败: {str(e)}",
            "output_file": None,
            "row_count": 0,
            "column_count": 0,
            "preview_data": [],
            "columns": [],
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# ============================================================
# 兼容脚本执行模式
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        result = generate_multi_month_dept_report(input_file, output_file)
    else:
        print("用法: python multi_month_dept_report_generator.py <个人维度结果表> <输出文件>")
        sys.exit(1)

    if result['success']:
        print(f"✓ {result['message']}")
        print(result['summary_text'])
    else:
        print(f"✗ {result['message']}")
        if 'traceback' in result:
            print(result['traceback'])