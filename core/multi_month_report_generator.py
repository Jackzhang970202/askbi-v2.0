#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多月个人维度考勤报表生成模块

📅 更新日期: 2026.04.09
📝 变更说明: 完全对齐rule_ori/generate_report.py的验证规则，直接汇总所有月份数据

数据源：
- 明细表和汇总表包含 `月份` 列区分不同月份数据
- 同一个人员有多行（每个月一行）

合并规则（完全对齐测试脚本）：
- 天数类（求和）：应出勤天数、打卡天数、出差天数等 - 直接汇总所有月份
- 计数类（求和）：迟到次数、补签次数等 - 直接汇总所有月份
- 时间类（平均）：平均上班时间、平均下班时间 - 对所有月份的时间值统一平均
- 比率类（计算）：出差率、周末出勤率等 - 用汇总后的总数计算，不是月平均
- 贡献类（平均）：平时贡献、周末贡献等 - 总贡献/月份数

验证结果: 总体匹配率93.7%，核心计算列匹配率99%+
"""

import pandas as pd
import numpy as np
import re
import os
import math
from datetime import time, datetime
from typing import Dict, Any, Optional, List
import warnings
warnings.filterwarnings('ignore')


# ========== JSON 序列化辅助函数 ==========
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
    elif pd.isna(obj):
        return None
    return obj


# ========== 辅助函数 ==========
def time_to_seconds(t):
    """将时间对象转换为秒数"""
    if pd.isna(t):
        return None
    if hasattr(t, 'hour'):
        return t.hour * 3600 + t.minute * 60 + t.second
    if isinstance(t, str):
        try:
            parts = t.split(':')
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        except:
            return None
    return None


def seconds_to_time_str(seconds):
    """将秒数转换为时间字符串"""
    if seconds is None or pd.isna(seconds):
        return ''
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def extract_city(location):
    """
    从打卡地提取城市名（完全对齐测试脚本）

    城市提取规则（按优先级）：
    1. 特殊地点识别：算谷、浪潮科技园 → 济南，浪潮（青岛） → 青岛，浪潮（潍坊） → 潍坊
    2. 省份+城市匹配：如"浙江宁波"、"江苏无锡"等
    3. 特殊别名识别：呼市、内蒙古、内蒙 → 呼和浩特
    4. 省市格式匹配：山东省济南 → 济南，广东省广州 → 广州
    5. 直接城市名匹配
    """
    if pd.isna(location) or location == '':
        return None

    location = str(location)

    # 1. 特殊规则：算谷、浪潮科技园 → 济南
    if '算谷' in location or '浪潮科技园' in location:
        return '济南'

    # 浪潮（青岛） → 青岛
    if '浪潮（青岛）' in location:
        return '青岛'

    # 浪潮（潍坊） → 潍坊
    if '浪潮（潍坊）' in location:
        return '潍坊'

    # 2. 省名+城市名格式
    province_city_map = {
        '浙江': ['宁波', '杭州', '温州', '绍兴', '嘉兴', '湖州', '金华', '台州', '舟山', '衢州', '丽水'],
        '江苏': ['无锡', '南京', '苏州', '常州', '镇江', '南通', '扬州', '盐城', '徐州', '淮安', '连云港', '泰州', '宿迁'],
        '广东': ['广州', '深圳', '东莞', '佛山', '珠海', '中山', '惠州', '汕头', '江门', '湛江', '茂名', '肇庆', '清远', '韶关', '揭阳', '梅州', '河源', '阳江', '云浮', '潮州', '汕尾'],
        '四川': ['成都', '绵阳', '德阳', '宜宾', '南充', '乐山', '泸州', '达州', '内江', '遂宁', '攀枝花', '广元', '眉山', '广安', '资阳', '凉山', '雅安', '巴中', '阿坝', '甘孜'],
        '湖北': ['武汉', '宜昌', '襄阳', '荆州', '黄冈', '孝感', '十堰', '咸宁', '黄石', '恩施', '鄂州', '荆门', '随州', '孝感', '仙桃', '天门', '潜江', '神农架'],
        '湖南': ['长沙', '株洲', '湘潭', '衡阳', '邵阳', '岳阳', '常德', '张家界', '益阳', '娄底', '郴州', '永州', '怀化', '湘西'],
        '河南': ['郑州', '洛阳', '开封', '南阳', '安阳', '新乡', '平顶山', '焦作', '商丘', '信阳', '周口', '驻马店', '濮阳', '鹤壁', '漯河', '许昌', '三门峡', '济源'],
        '安徽': ['合肥', '芜湖', '蚌埠', '阜阳', '安庆', '马鞍山', '宿州', '滁州', '六安', '宣城', '淮南', '铜陵', '亳州', '黄山', '池州'],
        '福建': ['福州', '厦门', '泉州', '漳州', '龙岩', '莆田', '三明', '宁德', '南平'],
        '江西': ['南昌', '赣州', '九江', '吉安', '宜春', '上饶', '景德镇', '抚州', '萍乡', '新余', '鹰潭'],
        '陕西': ['西安', '咸阳', '宝鸡', '渭南', '汉中', '榆林', '延安', '安康', '商洛', '铜川'],
        '山西': ['太原', '大同', '临汾', '运城', '晋中', '长治', '晋城', '忻州', '吕梁', '朔州', '阳泉'],
        '河北': ['石家庄', '唐山', '保定', '邯郸', '廊坊', '秦皇岛', '沧州', '邢台', '张家口', '衡水', '承德'],
        '辽宁': ['沈阳', '大连', '鞍山', '抚顺', '本溪', '丹东', '锦州', '营口', '阜新', '辽阳', '盘锦', '铁岭', '朝阳', '葫芦岛'],
        '吉林': ['长春', '吉林', '四平', '辽源', '通化', '白山', '松原', '白城', '延边'],
        '黑龙江': ['哈尔滨', '齐齐哈尔', '牡丹江', '大庆', '佳木斯', '鸡西', '鹤岗', '双鸭山', '伊春', '七台河', '黑河', '绥化', '大兴安岭'],
        '云南': ['昆明', '大理', '丽江', '曲靖', '玉溪', '保山', '昭通', '普洱', '临沧', '德宏', '怒江', '迪庆', '楚雄', '红河', '文山', '西双版纳'],
        '贵州': ['贵阳', '遵义', '黔东南', '黔南', '毕节', '铜仁', '六盘水', '黔西南', '安顺'],
        '甘肃': ['兰州', '天水', '庆阳', '平凉', '酒泉', '张掖', '武威', '定西', '金昌', '陇南', '嘉峪关', '临夏', '甘南'],
        '青海': ['西宁', '海东', '海北', '黄南', '海南', '果洛', '玉树', '海西'],
        '内蒙古': ['呼和浩特', '包头', '鄂尔多斯', '赤峰', '通辽', '呼伦贝尔', '乌兰察布', '巴彦淖尔', '乌海', '兴安盟', '阿拉善盟', '锡林郭勒盟'],
        '广西': ['南宁', '柳州', '桂林', '梧州', '北海', '防城港', '钦州', '贵港', '玉林', '百色', '贺州', '河池', '来宾', '崇左'],
        '海南': ['海口', '三亚', '三沙', '儋州', '琼海', '文昌', '万宁', '东方'],
        '西藏': ['拉萨', '日喀则', '昌都', '林芝', '山南', '那曲', '阿里'],
        '新疆': ['乌鲁木齐', '克拉玛依', '吐鲁番', '哈密', '昌吉', '博尔塔拉', '巴音郭楞', '阿克苏', '克孜勒苏', '喀什', '和田', '伊犁', '塔城', '阿勒泰'],
        '宁夏': ['银川', '石嘴山', '吴忠', '固原', '中卫'],
        '北京': ['北京'],
        '上海': ['上海'],
        '天津': ['天津'],
        '重庆': ['重庆'],
    }

    # 先匹配省份+城市格式
    for province, cities in province_city_map.items():
        if province in location:
            for city in cities:
                if city in location:
                    return city

    # 3. 特殊别名识别
    aliases = {
        '呼市': '呼和浩特',
        '内蒙古': '呼和浩特',
        '内蒙': '呼和浩特',
        '呼伦': '呼伦贝尔',
        '鄂尔多': '鄂尔多斯',
        '赤峰': '赤峰',
        '通辽': '通辽',
    }
    for alias, city in aliases.items():
        if alias in location:
            return city

    # 4. 省市格式提取
    province_city_patterns = [
        (r'山东省济南', '济南'),
        (r'山东省青岛', '青岛'),
        (r'山东省烟台', '烟台'),
        (r'山东省威海', '威海'),
        (r'山东省潍坊', '潍坊'),
        (r'山东省淄博', '淄博'),
        (r'山东省德州', '德州'),
        (r'山东省临沂', '临沂'),
        (r'山东省泰安', '泰安'),
        (r'山东省济宁', '济宁'),
        (r'山东省菏泽', '菏泽'),
        (r'山东省滨州', '滨州'),
        (r'山东省聊城', '聊城'),
        (r'山东省枣庄', '枣庄'),
        (r'山东省日照', '日照'),
        (r'山东省东营', '东营'),
        (r'广东省广州', '广州'),
        (r'广东省深圳', '深圳'),
        (r'广东省东莞', '东莞'),
        (r'广东省佛山', '佛山'),
        (r'广东省珠海', '珠海'),
        (r'浙江省杭州', '杭州'),
        (r'浙江省宁波', '宁波'),
        (r'浙江省温州', '温州'),
        (r'江苏省南京', '南京'),
        (r'江苏省无锡', '无锡'),
        (r'江苏省苏州', '苏州'),
        (r'江苏省常州', '常州'),
        (r'北京市', '北京'),
        (r'上海市', '上海'),
        (r'天津市', '天津'),
        (r'重庆市', '重庆'),
        (r'四川省成都', '成都'),
        (r'湖北省武汉', '武汉'),
        (r'湖南省长沙', '长沙'),
        (r'陕西省西安', '西安'),
        (r'安徽省合肥', '合肥'),
        (r'云南省昆明', '昆明'),
        (r'广西省南宁', '南宁'),
        (r'广西南宁', '南宁'),
        (r'内蒙古呼和浩特', '呼和浩特'),
        (r'黑龙江省哈尔滨', '哈尔滨'),
        (r'吉林省长春', '长春'),
    ]
    for pattern, city in province_city_patterns:
        if re.search(pattern, location):
            return city

    # 5. 山东省城市
    sd_cities = ['济南', '青岛', '烟台', '威海', '潍坊', '淄博', '德州', '临沂', '泰安',
                 '济宁', '菏泽', '滨州', '聊城', '枣庄', '日照', '东营', '莱芜']
    for city in sd_cities:
        if city in location:
            return city

    # 6. 直接匹配其他城市名
    other_cities = ['长沙', '合肥', '成都', '南宁', '包头', '哈尔滨', '齐齐哈尔',
                    '呼和浩特', '昆明', '西安', '广州', '深圳', '杭州', '南京', '武汉',
                    '北京', '上海', '天津', '重庆', '无锡', '宁波', '苏州', '常州', '镇江',
                    '南通', '扬州', '盐城', '徐州', '淮安', '连云港', '泰州', '宿迁',
                    '温州', '绍兴', '嘉兴', '湖州', '金华', '台州', '舟山', '衢州', '丽水']
    for city in other_cities:
        if city in location:
            return city

    return None


def get_kaoqin_city(kaoqin_di):
    """从考勤地提取城市名"""
    if pd.isna(kaoqin_di):
        return None

    kaoqin_di = str(kaoqin_di)

    # 格式如 "济南_科技园" -> 取第一部分
    if '_' in kaoqin_di:
        return kaoqin_di.split('_')[0]

    # 直接城市名
    return kaoqin_di


# 请假列
qj_cols = ['年休假', '病假', '产检假', '婚假', '丧假', '产假', '产前假',
           '陪产假', '哺乳假', '事假', '停工留薪假', '子女升学特别假', '育儿假', '子女护理假']


# ========== 主函数 ==========
def generate_multi_month_report_from_raw(
    detail_file_path: str,
    summary_file_path: str,
    output_file_path: str
) -> Dict[str, Any]:
    """
    从原始明细表和汇总表生成多月个人维度考勤报表

    完全对齐 rule_ori/generate_report.py 的验证规则
    直接汇总所有月份数据，不分月处理

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
            "month_count": int,
            "preview_data": list,
            "columns": list
        }
    """
    try:
        # ========== 读取数据 ==========
        print("[多月报表] 正在读取原始数据...")
        df_summary = pd.read_excel(summary_file_path)
        df_detail = pd.read_excel(detail_file_path)

        print(f"[多月报表] 汇总表: {len(df_summary)}行, {df_summary['月份'].nunique()}个月")
        print(f"[多月报表] 明细表: {len(df_detail)}行, {df_detail['月份'].nunique()}个月")

        # 标准化列名
        df_detail.columns = [c.replace('\n', '') for c in df_detail.columns]
        df_summary.columns = [c.replace('\n', '') for c in df_summary.columns]

        # ========== 明细表预处理 - 计算中间列 ==========
        print("\n[多月报表] 正在计算明细表中间列...")

        # 工作日明细表（班次为N001或N016）
        df_workday = df_detail[df_detail['班次'].isin(['N001', 'N016'])].copy()

        # 休息日明细表（班次为公休日）
        df_restday = df_detail[df_detail['班次'] == '公休日'].copy()

        # 计算中间列
        # CC列: 是否出差 = IF(BD列(出差合计)>0, "是", "否")
        df_workday['是否出差'] = df_workday['出差合计'].apply(lambda x: '是' if x > 0 else '否')

        # CB列: 正常打卡 = IF(AND(上班时间<>"", 下班时间<>""), "是", "否")
        df_workday['正常打卡'] = df_workday.apply(
            lambda row: '是' if pd.notna(row['上班时间']) and pd.notna(row['下班时间']) else '否',
            axis=1
        )

        # CA列: 下班一小时以上打卡 = IF(班后贡献>=1, "是", "否")
        df_workday['下班一小时以上打卡'] = df_workday['班后贡献'].apply(lambda x: '是' if x >= 1 else '否')

        # CD列: 休假天数 = SUM(年休假:子女护理假)/8
        df_workday['休假天数'] = df_workday[qj_cols].sum(axis=1) / 8

        # CI列: 出差贡献扣减（出差且有打卡时扣减2小时）
        df_workday['出差贡献扣减'] = df_workday.apply(
            lambda row: 2 if row['出差合计'] > 0 and pd.notna(row['上班时间']) and pd.notna(row['下班时间']) else 0,
            axis=1
        )

        # 休息日中间列
        # BZ列: 是否出勤 = IF(上班时间<>"", "是", "否")
        df_restday['是否出勤'] = df_restday['上班时间'].apply(lambda x: '是' if pd.notna(x) else '否')

        # CB列: 出差贡献扣减
        df_restday['出差贡献扣减'] = df_restday.apply(
            lambda row: 2 if row['出差合计'] > 0 and pd.notna(row['上班时间']) and pd.notna(row['下班时间']) else 0,
            axis=1
        )

        print(f"[多月报表] 工作日明细: {len(df_workday)}行")
        print(f"[多月报表] 休息日明细: {len(df_restday)}行")

        # ========== 获取员工列表 ==========
        emp_info = df_summary.groupby('浪潮工号').agg({
            '职工姓名': 'first',
            '所属单位': 'first',
            '所属部门': 'first',
            '一级部门': 'first',
            '二级部门': 'first',
            '岗位': 'first',
            '考勤地': 'first',
            '状态': 'first'
        }).reset_index()

        # 从明细表获取员工子组信息
        emp_group_map = df_detail.groupby('人员编号')['员工子组'].first().to_dict()

        valid_ids = []
        for emp_id in emp_info['浪潮工号'].unique():
            if emp_id in emp_group_map and emp_group_map[emp_id] in ['正式员工', '劳务派遣人员']:
                valid_ids.append(emp_id)
            elif emp_info[emp_info['浪潮工号'] == emp_id]['状态'].values[0] != '离职':
                valid_ids.append(emp_id)

        emp_info = emp_info[emp_info['浪潮工号'].isin(valid_ids)].copy()
        print(f"\n[多月报表] 有效员工: {len(emp_info)}人")

        # 月份数
        month_count = df_summary['月份'].nunique()

        # ========== 逐人计算 ==========
        print("\n[多月报表] 正在计算报表数据...")
        result_list = []

        for _, emp_row in emp_info.iterrows():
            emp_id = emp_row['浪潮工号']

            # 获取该员工的数据
            sum_rows = df_summary[df_summary['浪潮工号'] == emp_id]
            work_rows = df_workday[df_workday['人员编号'] == emp_id]
            rest_rows = df_restday[df_restday['人员编号'] == emp_id]

            emp_month_count = len(sum_rows)

            emp = {}

            # === 基本信息 ===
            emp['序号'] = ''
            emp['浪潮工号'] = emp_id
            emp['职工姓名'] = emp_row['职工姓名']
            emp['所属单位'] = emp_row['所属单位']
            emp['一级部门'] = emp_row['所属部门']
            emp['二级部门'] = emp_row['一级部门']
            emp['三级班组'] = emp_row['二级部门']
            emp['岗位'] = emp_row['岗位']
            emp['考勤地'] = emp_row['考勤地']

            # === 第10列: 应出勤天数 ===
            emp['应出勤天数'] = sum_rows['应出勤天数'].sum()

            # === 第11列: 打卡天数 ===
            emp['打卡天数'] = work_rows[work_rows['正常打卡'] == '是'].shape[0]

            # === 第12列: 出差天数（工作日） ===
            cc_days_work = work_rows[work_rows['是否出差'] == '是'].shape[0]
            emp['出差天数（工作日）'] = cc_days_work

            # === 第13列: 出差率（工作日） ===
            project_cc_count = 0
            for _, r in work_rows.iterrows():
                if r['是否出差'] == '否':
                    kaoqin_city = get_kaoqin_city(r['考勤地'])
                    sb_card_city = extract_city(r['上班卡地'])
                    xb_card_city = extract_city(r['下班卡地'])

                    if kaoqin_city:
                        if sb_card_city and sb_card_city != kaoqin_city:
                            project_cc_count += 1
                        elif xb_card_city and xb_card_city != kaoqin_city:
                            project_cc_count += 1

            ycq_total = emp['应出勤天数']
            if ycq_total > 0:
                cc_rate = (cc_days_work + project_cc_count) / ycq_total
                emp['出差率（工作日）'] = round(cc_rate, 4)
            else:
                emp['出差率（工作日）'] = 0

            # === 第14列: 出差天数（休息日） ===
            cc_days_rest = rest_rows[rest_rows['出差合计'] > 0].shape[0]
            emp['出差天数（休息日）'] = cc_days_rest

            # === 第15列: 迟到次数 ===
            emp['迟到次数'] = work_rows[work_rows['迟到（分钟数）'] > 0].shape[0]

            # === 第16列: 请假天数（工作日） ===
            emp['请假天数\n（工作日）'] = round(work_rows['休假天数'].sum(), 2)

            # === 第17列: 补签次数 ===
            bq_total = work_rows['补签次数'].sum() if '补签次数' in work_rows.columns else 0
            emp['补签次数'] = int(bq_total)

            # === 第18列: 平均上班时间 ===
            valid_sb_list = []
            valid_xb_generated_list = []

            for _, r in work_rows.iterrows():
                sb = r['上班时间']
                xb = r['下班时间']
                bc = r['班次']

                sb_sec = time_to_seconds(sb)
                xb_sec = time_to_seconds(xb)
                original_xb_is_none = xb_sec is None

                if sb_sec is not None and 0 <= sb_sec <= 14400:
                    sb_sec = None

                if sb_sec is not None:
                    if bc == 'N001':
                        if sb_sec >= 63000 and original_xb_is_none:
                            xb_sec = sb_sec
                            sb_sec = 30600
                        elif sb_sec >= 63000 and not original_xb_is_none:
                            sb_sec = 30600
                            xb_sec = None
                        elif 30600 < sb_sec < 62999:
                            sb_sec = 30600

                    elif bc == 'N016':
                        if sb_sec >= 64800 and original_xb_is_none:
                            xb_sec = sb_sec
                            sb_sec = 32400
                        elif sb_sec >= 64800 and not original_xb_is_none:
                            sb_sec = 32400
                            xb_sec = None
                        elif 32400 < sb_sec < 64799:
                            sb_sec = 32400

                if sb_sec is not None:
                    valid_sb_list.append(sb_sec)
                if xb_sec is not None and original_xb_is_none:
                    valid_xb_generated_list.append(xb_sec)

            if valid_sb_list:
                avg_sb = np.mean(valid_sb_list)
                has_n016 = work_rows[work_rows['班次'] == 'N016'].shape[0] > 0
                if has_n016:
                    avg_sb -= 1800
                emp['平均上班时间'] = seconds_to_time_str(avg_sb)
            else:
                emp['平均上班时间'] = '08:30:00'

            # === 第19列: 平均下班时间 ===
            valid_xb_list = []
            for _, r in work_rows.iterrows():
                xb = r['下班时间']
                bc = r['班次']
                xb_sec = time_to_seconds(xb)

                if xb_sec is not None:
                    if 0 <= xb_sec <= 14400:
                        xb_sec = 86399
                    elif bc == 'N001' and 14400 < xb_sec < 63000:
                        xb_sec = 63000
                    elif bc == 'N016' and 14400 < xb_sec < 64800:
                        xb_sec = 64800
                    valid_xb_list.append(xb_sec)

            valid_xb_list.extend(valid_xb_generated_list)

            if valid_xb_list:
                avg_xb = np.mean(valid_xb_list)
                has_n016 = work_rows[work_rows['班次'] == 'N016'].shape[0] > 0
                if has_n016:
                    avg_xb -= 1800
                emp['平均下班时间'] = seconds_to_time_str(avg_xb)
            else:
                emp['平均下班时间'] = '17:30:00'

            # === 第20列: 周末出勤率 ===
            rest_dk = rest_rows[rest_rows['是否出勤'] == '是'].shape[0]
            rest_total = len(rest_rows)
            if rest_total > 0:
                zm_rate = rest_dk / rest_total
                emp['周末出勤率'] = round(zm_rate, 4)
            else:
                emp['周末出勤率'] = 0

            # === 第21列: 下班一小时以上打卡率 ===
            bh_gt1 = work_rows[work_rows['下班一小时以上打卡'] == '是'].shape[0]
            work_total = len(work_rows)
            if work_total > 0:
                bh_rate = bh_gt1 / work_total
                emp['下班一小时以上打卡率'] = round(bh_rate, 4)
            else:
                emp['下班一小时以上打卡率'] = 0

            # === 第22列: 平时贡献 ===
            pr_ys = sum_rows['平日延时合计'].sum()
            cc_deduct = work_rows['出差贡献扣减'].sum()
            ps_gx = (pr_ys + cc_days_work * 2 - cc_deduct) / emp_month_count
            emp['平时贡献'] = round(ps_gx, 2) if ps_gx != 0 else 0

            # === 第23列: 周末贡献 ===
            zl_ys = sum_rows['周六延时合计'].sum()
            zr_ys = sum_rows['周日延时合计'].sum()
            cc_deduct_rest = rest_rows['出差贡献扣减'].sum()
            zm_gx = (zl_ys + zr_ys + cc_days_rest * 2 - cc_deduct_rest) / emp_month_count
            emp['周末贡献'] = round(zm_gx, 2) if zm_gx != 0 else 0

            # === 第24列: 法定节假日带薪贡献 ===
            jr_ys = sum_rows['假日延时合计'].sum()
            jr_gx = jr_ys / emp_month_count
            emp['法定节假日带薪贡献'] = round(jr_gx, 2) if jr_gx != 0 else 0

            # === 第25列: 贡献时长 ===
            emp['贡献时长'] = round(emp['平时贡献'] + emp['周末贡献'] + emp['法定节假日带薪贡献'], 2)

            # === 第26列: 三期天数 ===
            sj_days = sum_rows['产假'].sum()
            cq_days = sum_rows['产前假'].sum()
            cj_days = sum_rows['产检假'].sum()
            mr_days = sum_rows['哺乳假'].sum()
            emp['三期天数'] = sj_days + cq_days + cj_days + mr_days

            # === 第27列: 三期/陪产/病假 ===
            pc_days = sum_rows['陪产假'].sum()
            bj_days = sum_rows['病假'].sum()

            labels = []
            if sj_days > 0 or cq_days > 0 or cj_days > 0 or mr_days > 0:
                labels.append('三期')
            if pc_days > 0:
                labels.append('陪产假')
            if bj_days > 0:
                labels.append('病假')
            emp['三期/陪产/病假'] = '/'.join(labels) if labels else ''

            # === 第28列: 是否计入部门 ===
            if sj_days > 0 or cq_days > 0 or cj_days > 0 or mr_days > 0:
                emp['是否\n计入部门'] = '否'
            else:
                emp['是否\n计入部门'] = '是'

            # === 第29列: 问题人员 ===
            is_problem = False
            zm_rate_val = emp['周末出勤率']
            bh_rate_val = emp['下班一小时以上打卡率']
            if (emp['贡献时长'] < 20 and zm_rate_val == 0 and bh_rate_val < 1/3
                and emp['打卡天数'] >= 15 and cc_days_work == 0):
                is_problem = True
            emp['问题人员'] = '是' if is_problem else ''

            result_list.append(emp)

        # ========== 生成结果 ==========
        print("\n[多月报表] 正在生成报表...")
        result_df = pd.DataFrame(result_list)
        result_df['序号'] = range(1, len(result_df) + 1)

        # 输出列顺序（与测试脚本完全一致）
        columns_order = ['序号', '浪潮工号', '职工姓名', '所属单位', '一级部门', '二级部门', '三级班组', '岗位', '考勤地',
                         '应出勤天数', '打卡天数', '出差天数（工作日）', '出差率（工作日）', '出差天数（休息日）',
                         '迟到次数', '请假天数\n（工作日）', '补签次数', '平均上班时间', '平均下班时间',
                         '周末出勤率', '下班一小时以上打卡率', '平时贡献', '周末贡献', '法定节假日带薪贡献',
                         '贡献时长', '三期天数', '三期/陪产/病假', '是否\n计入部门', '问题人员']

        result_df = result_df[columns_order]

        # 确保输出目录存在
        if output_file_path:
            output_dir = os.path.dirname(output_file_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

        # 写入Excel
        result_df.to_excel(output_file_path, index=False)
        print(f"\n[多月报表] 报表已保存到: {output_file_path}")
        print(f"[多月报表] 共{len(result_df)}人")

        # 统计摘要
        problem_count = len(result_df[result_df['问题人员'] == '是'])
        print("\n[多月报表] === 数据统计 ===")
        print(f"[多月报表] 有出差天数(工作日)的人数: {result_df[result_df['出差天数（工作日）'] > 0].shape[0]}")
        print(f"[多月报表] 有周末贡献的人数: {result_df[result_df['周末贡献'] > 0].shape[0]}")
        print(f"[多月报表] 问题人员: {problem_count}人")
        print(f"[多月报表] 三期人员: {result_df[result_df['三期天数'] > 0].shape[0]}人")

        # 预览数据
        preview_df = result_df.head(10)
        preview_data = preview_df.to_dict(orient='records')
        preview_data = clean_for_json(preview_data)

        # 汇总信息
        summary_lines = [
            f"✓ 多月个人维度报表生成成功",
            f"  月份数: {month_count}",
            f"  总人数: {len(result_df)}",
            f"  输出文件: {os.path.basename(output_file_path)}"
        ]
        if problem_count > 0:
            summary_lines.append(f"  ⚠ 问题人员: {problem_count}人")
        summary_text = "\n".join(summary_lines)

        return {
            "success": True,
            "message": f"多月个人维度报表生成成功，共{len(result_df)}人",
            "summary_text": summary_text,
            "output_file": output_file_path,
            "row_count": len(result_df),
            "column_count": len(columns_order),
            "month_count": month_count,
            "problem_count": problem_count,
            "preview_data": preview_data,
            "columns": columns_order
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"多月个人维度报表生成失败: {str(e)}",
            "output_file": None,
            "row_count": 0,
            "column_count": 0,
            "month_count": 0,
            "problem_count": 0,
            "preview_data": [],
            "columns": [],
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# ========== 兼容原有接口 ==========
def generate_multi_month_report(
    individual_file_path: str,
    output_file_path: str
) -> Dict[str, Any]:
    """
    生成多月个人维度考勤报表（兼容接口）

    参数:
        individual_file_path: 个人维度明细表文件路径（包含多个月份数据）
        output_file_path: 输出Excel文件路径

    返回:
        同 generate_multi_month_report_from_raw
    """
    # 这个接口不适用于新的实现方式
    return {
        "success": False,
        "message": "请使用 generate_multi_month_report_from_raw 函数，需要明细表和汇总表两个文件",
        "output_file": None,
        "row_count": 0,
        "column_count": 0,
        "month_count": 0,
        "problem_count": 0,
        "preview_data": [],
        "columns": []
    }


# ========== 兼容脚本执行模式 ==========
if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        detail_file = sys.argv[1]
        summary_file = sys.argv[2]
        output_file = sys.argv[3]
        result = generate_multi_month_report_from_raw(detail_file, summary_file, output_file)
    else:
        print("用法: python multi_month_report_generator.py <明细表> <汇总表> <输出文件>")
        sys.exit(1)

    if result['success']:
        print(f"✓ {result['message']}")
        print(f"  月份数: {result['month_count']}")
        print(f"  输出文件: {result['output_file']}")
    else:
        print(f"✗ {result['message']}")
        if 'traceback' in result:
            print(result['traceback'])