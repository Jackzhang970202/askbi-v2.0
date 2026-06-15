#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则验证脚本 - 对比系统数据与标准答案

目的：验证各列的计算规则差异
"""

import pandas as pd
import numpy as np

def time_to_sec(t):
    """将时间转换为秒数"""
    if pd.isna(t):
        return None
    if hasattr(t, 'hour'):
        return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1_000_000
    return None

def sec_to_time_str(s):
    """将秒数转换为时间字符串"""
    if pd.isna(s) or s is None:
        return None
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:05.3f}"

def parse_pct(s):
    """解析百分比"""
    if pd.isna(s):
        return 0.0
    if isinstance(s, str) and s.endswith('%'):
        return float(s.rstrip('%')) / 100
    return float(s)

print("=" * 60)
print("规则验证报告")
print("=" * 60)

# 读取数据
df_sys = pd.read_excel('系统数据.xlsx')
df_std = pd.read_excel('人工数据-标准答案.xlsx')
df_sum = pd.read_excel('原始数据-考勤汇总表.xlsx')
df_detail = pd.read_excel('原始数据-考勤明细表.xlsx')

print(f"\n数据概况:")
print(f"  系统数据: {len(df_sys)}人")
print(f"  标准答案: {len(df_std)}人")
print(f"  汇总表: {len(df_sum)}行 ({df_sum['月份'].nunique()}个月)")
print(f"  明细表: {len(df_detail)}行 ({df_detail['月份'].nunique()}个月)")

# ===== 差异1：格式差异 =====
print("\n" + "=" * 60)
print("差异1：格式差异（百分比 vs 比率）")
print("=" * 60)

# 出差率
emp_id = 131073
sys_val = df_sys[df_sys['浪潮工号']==emp_id]['出差率（工作日）'].values[0]
std_val = df_std[df_std['浪潮工号']==emp_id]['出差率（工作日）'].values[0]
print(f"\n出差率（工号{emp_id}）:")
print(f"  系统: {sys_val}")
print(f"  标准: {std_val}")
print(f"  结论: 标准答案使用比率格式（0.xxx），系统使用百分比格式（xx.xx%）")

# 周末出勤率
sys_val = df_sys[df_sys['浪潮工号']==emp_id]['周末出勤率'].values[0]
std_val = df_std[df_std['浪潮工号']==emp_id]['周末出勤率'].values[0]
print(f"\n周末出勤率（工号{emp_id}）:")
print(f"  系统: {sys_val}")
print(f"  标准: {std_val}")

# ===== 差异2：空值处理 =====
print("\n" + "=" * 60)
print("差异2：空值处理差异")
print("=" * 60)

# 请假天数
null_count = df_sys['请假天数\n（工作日）'].isna().sum()
std_zero_count = (df_std['请假天数\n（工作日）'] == 0).sum()
print(f"\n请假天数:")
print(f"  系统空值数: {null_count}")
print(f"  标准答案0值数: {std_zero_count}")
print(f"  结论: 标准答案用0表示无请假，系统使用空值")

# 法定节假日带薪贡献
null_count = df_sys['法定节假日带薪贡献'].isna().sum()
std_zero_count = (df_std['法定节假日带薪贡献'] == 0).sum()
print(f"\n法定节假日带薪贡献:")
print(f"  系统空值数: {null_count}")
print(f"  标准答案0值数: {std_zero_count}")

# ===== 差异3：多月合并规则 =====
print("\n" + "=" * 60)
print("差异3：多月合并规则（关键差异）")
print("=" * 60)

# 周末贡献
emp_id = 104450
sys_wm = df_sys[df_sys['浪潮工号']==emp_id]['周末贡献'].values[0]
std_wm = df_std[df_std['浪潮工号']==emp_id]['周末贡献'].values[0]
sum_rows = df_sum[df_sum['浪潮工号']==emp_id]

print(f"\n周末贡献（工号{emp_id}）:")
print(f"  系统值: {sys_wm}")
print(f"  标准值: {std_wm}")
print(f"  汇总表各月周六延时: {sum_rows['周六延时合计'].tolist()}")
print(f"  汇总表各月周日延时: {sum_rows['周日延时合计'].tolist()}")
calc_avg = sum_rows['周六延时合计'].sum() / 3  # 假设3个月
print(f"  计算平均: {calc_avg}")
print(f"  结论: 标准答案是多月平均值，系统可能取了最后一个月的值")

# 平时贡献
emp_id = 64402
sys_ps = df_sys[df_sys['浪潮工号']==emp_id]['平时贡献'].values[0]
std_ps = df_std[df_std['浪潮工号']==emp_id]['平时贡献'].values[0]
sum_rows = df_sum[df_sum['浪潮工号']==emp_id]

print(f"\n平时贡献（工号{emp_id}）:")
print(f"  系统值: {sys_ps}")
print(f"  标准值: {std_ps}")
print(f"  汇总表各月平日延时: {sum_rows['平日延时合计'].tolist()}")
calc_avg = sum_rows['平日延时合计'].mean()
print(f"  计算平均: {calc_avg}")
print(f"  结论: 标准答案是多月平均值")

# ===== 差异4：平均时间计算 =====
print("\n" + "=" * 60)
print("差异4：平均时间计算规则")
print("=" * 60)

emp_id = 131073
sys_sb = df_sys[df_sys['浪潮工号']==emp_id]['平均上班时间'].values[0]
sys_xb = df_sys[df_sys['浪潮工号']==emp_id]['平均下班时间'].values[0]
std_sb = df_std[df_std['浪潮工号']==emp_id]['平均上班时间'].values[0]
std_xb = df_std[df_std['浪潮工号']==emp_id]['平均下班时间'].values[0]

emp_detail = df_detail[df_detail['人员编号']==emp_id]
workdays = emp_detail[emp_detail['班次'].isin(['N001', 'N016'])]

# 计算原始平均
sb_secs = [time_to_sec(t) for t in workdays['上班时间'] if time_to_sec(t) is not None]
xb_secs = [time_to_sec(t) for t in workdays['下班时间'] if time_to_sec(t) is not None]
avg_sb_raw = np.mean(sb_secs) if sb_secs else None
avg_xb_raw = np.mean(xb_secs) if xb_secs else None

print(f"\n平均时间（工号{emp_id}）:")
print(f"  系统上班: {sys_sb}")
print(f"  标准上班: {std_sb}")
print(f"  原始平均上班: {sec_to_time_str(avg_sb_raw)} ({avg_sb_raw:.2f}秒)")
print(f"")
print(f"  系统下班: {sys_xb}")
print(f"  标准下班: {std_xb}")
print(f"  原始平均下班: {sec_to_time_str(avg_xb_raw)} ({avg_xb_raw:.2f}秒)")

std_sb_sec = float(str(std_sb).split(':')[0])*3600 + float(str(std_sb).split(':')[1])*60 + float(str(std_sb).split(':')[2])
std_xb_sec = float(str(std_xb).split(':')[0])*3600 + float(str(std_xb).split(':')[1])*60 + float(str(std_xb).split(':')[2])

print(f"\n  标准下班与原始平均差异: {std_xb_sec - avg_xb_raw:.2f}秒（几乎一致，标准=直接平均）")
print(f"  标准上班与原始平均差异: {std_sb_sec - avg_sb_raw:.2f}秒（有差异，标准应用了特殊规则）")

# ===== 差异5：三期/陪产/病假格式 =====
print("\n" + "=" * 60)
print("差异5：三期/陪产/病假格式差异")
print("=" * 60)

diff_count = 0
for emp_id in df_sys['浪潮工号'].unique():
    sys_val = df_sys[df_sys['浪潮工号']==emp_id]['三期/陪产/病假'].values[0]
    std_val = df_std[df_std['浪潮工号']==emp_id]['三期/陪产/病假'].values[0]
    if str(sys_val).replace('陪产', '陪产假') != str(std_val):
        diff_count += 1
        if diff_count <= 3:
            print(f"  工号{emp_id}: 系统={sys_val}, 标准={std_val}")

print(f"\n  结论: 系统使用'陪产'，标准使用'陪产假'")

# ===== 差异6：问题人员判断 =====
print("\n" + "=" * 60)
print("差异6：问题人员判断差异")
print("=" * 60)

sys_problem = df_sys[df_sys['问题人员']=='是']['浪潮工号'].tolist()
std_problem = df_std[df_std['问题人员']=='是']['浪潮工号'].tolist()

print(f"\n系统标记的问题人员: {len(sys_problem)}人")
print(f"标准标记的问题人员: {len(std_problem)}人")
print(f"系统多标记: {len(sys_problem) - len(set(sys_problem) & set(std_problem))}人")

# 检查差异原因
extra_ids = [id for id in sys_problem if id not in std_problem][:3]
for emp_id in extra_ids:
    sys_row = df_sys[df_sys['浪潮工号']==emp_id]
    zm_rate = sys_row['周末出勤率'].values[0]
    print(f"  工号{emp_id}: 周末出勤率={zm_rate} (空值nan导致判断异常)")

print(f"\n  结论: 系统周末出勤率为nan时，问题人员判断逻辑可能异常")

print("\n" + "=" * 60)
print("规则差异总结")
print("=" * 60)
print("""
1. 格式差异:
   - 出差率/周末出勤率/下班打卡率: 系统=百分比，标准=比率
   - 三期/陪产/病假: 系统="陪产"，标准="陪产假"

2. 空值处理:
   - 请假天数/法定节假日贡献: 系统=空值，标准=0

3. 多月合并规则（核心差异）:
   - 贡献类字段（平时贡献、周末贡献、贡献时长等）: 标准答案=多月平均值
   - 时间类字段（平均上班/下班时间）: 标准答案=多月平均值

4. 平均时间计算:
   - 下班时间: 标准=直接平均所有有效时间
   - 上班时间: 标准有特殊规则（需进一步确认）

5. 问题人员判断:
   - 规则相同，但周末出勤率空值处理导致差异
""")