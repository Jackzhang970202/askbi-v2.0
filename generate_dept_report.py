"""
部门维度考勤报表生成脚本

数据源：
1. 考勤分析（人员明细）表 - 个人维度考勤分析结果
2. 考勤汇总表 - 补充部门归属信息

输出：部门维度考勤分析报表
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
# 配置区
# ============================================================
# 输入文件路径
INDIVIDUAL_REPORT_PATH = Path(__file__).parent / "考勤分析-个人维度-标准答案.xlsx"
SUMMARY_TABLE_PATH = Path(__file__).parent / "考勤模拟数据-二月汇总表.xlsx"

# 输出文件路径
OUTPUT_PATH = Path(__file__).parent / "部门维度分析结果.xlsx"

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

def load_data():
    """加载并预处理数据"""
    # 加载个人明细表
    df_individual = pd.read_excel(INDIVIDUAL_REPORT_PATH)

    # 加载考勤汇总表
    df_summary = pd.read_excel(SUMMARY_TABLE_PATH)

    return df_individual, df_summary


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
# 部门结构与排序
# ============================================================

# 按照 部门维度呈现形式.xlsx 的固定顺序
DEPT_ORDER = [
    ("纪检部", None),
    ("浪潮（山东）信息技术咨询服务有限公司", None),
    ("人力资源部", None),
    ("营销南区", ["中南销售处", "华东销售处", "西南销售处", "经理室", "数据推进处"]),
    ("综合办公室(安全管理部)", None),
    ("财务部", None),
    ("宏观经济数据事业部", ["产品处", "方案处", "无锡业务处", "经理室", "研发处", "交付处"]),
    ("模数工坊事业部", ["产品处", "方案处", "研发处", "经理室"]),
    ("浪潮(青岛)数据要素有限公司", ["交付部", "业务拓展部", "经理室", "方案部", "产品研发部"]),
    ("医疗健康营销部", ["商务支持处", "南区", "北区", "内蒙古区", ""]),
    ("天元大数据信用管理有限公司", ["项目交付部", "业务合规部", "模型研发部", "经理室", "类金融应用研发部", "解决方案部", "产品部", "征信平台研发部"]),
    ("总部中心", ["经理室", "销售业务处", "政策研究处"]),
    ("政务数据服务事业本部", ["经理室", "业务支撑部", "社会工作事业部", "基层数据服务事业部", "数字党建事业部"]),
    ("市场业务部", ["", "销售支持处", "市场处"]),
    ("大数据平台研发部", ["经理室", "AI研发处", "运维与安全处", "数据处", "用户体验处"]),
    ("科技创新部", None),
    ("运营与采购管理部", ["运营处", "", "采购处", "质量与项目管理处"]),
    ("营销北区", ["经理室", "中部销售处", "西部销售处", "北部销售处"]),
    ("山东浪潮智慧医疗科技有限公司", ["业务支持部", "智慧医卫事业部", "智煜互联网医院", "医疗智能事业部", "产品与项目管理部", "数智医疗重大项目部", "经理室"]),
    ("总经理室", None),
    ("法务合规与投资部", ["审计与法务合规处", "投资发展处"]),
    ("浪潮卓数（北京）大数据技术有限公司", ["业务一处", "业务三处", "经理室"]),
    ("北方健康医疗大数据科技有限公司", ["数据运营一部", "健康云事业部", "数据运营二部", "财务部", "人力与综合管理部", "经理室", "AI研发部", "创新场景事业部"]),
]


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


def generate_report(df_included):
    """生成部门维度报表，部门按合计贡献时长由高到低排序"""

    # 第一步：为每个一级部门生成数据块（二级部门行 + 合计行）
    dept_blocks = []  # 每个元素: (dept1_name, subtotal_stats, block_rows)

    for dept1_name, sub_depts in DEPT_ORDER:
        block_rows = []
        # 该一级部门所有人员
        dept1_group = df_included[df_included["一级部门"] == dept1_name]

        if sub_depts is None:
            # 无二级部门，仅输出合计行（直接用所有人员计算）
            stats = calc_dept_stats(dept1_group)
            stats["一级部门"] = dept1_name
            stats["二级部门"] = "合计"
            block_rows.append(stats)
            dept_blocks.append((dept1_name, stats, block_rows))
        else:
            # 有二级部门：先输出各二级部门行
            for sub_name in sub_depts:
                if sub_name == "":
                    mask = (df_included["一级部门"] == dept1_name) & (
                        df_included["二级部门"].isna() | (df_included["二级部门"] == "")
                    )
                else:
                    mask = (df_included["一级部门"] == dept1_name) & (df_included["二级部门"] == sub_name)
                group = df_included[mask]
                stats = calc_dept_stats(group)
                stats["一级部门"] = dept1_name
                stats["二级部门"] = sub_name
                block_rows.append(stats)

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


# ============================================================
# 输出格式化
# ============================================================

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
# 主流程
# ============================================================

def main():
    print("加载数据...")
    df_individual, df_summary = load_data()

    print("预处理...")
    df_included = preprocess(df_individual, df_summary)

    print(f"计入部门人员数: {len(df_included)}")
    print(f"一级部门分布: {df_included['一级部门'].value_counts(dropna=False).to_dict()}")

    print("生成部门维度报表...")
    rows = generate_report(df_included)

    print("格式化输出...")
    df_out = format_output(rows)

    print(f"输出行数: {len(df_out)}")
    print(df_out.to_string(index=False))

    # 写入Excel
    df_out.to_excel(OUTPUT_PATH, index=False, sheet_name="部门维度分析")
    print(f"\n报表已保存至: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
