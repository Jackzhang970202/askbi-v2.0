"""
人力资源效能分析大屏数据生成脚本（双文件版）
用法: python generate_dashboard.py --personal <个人维度Excel> --dept <部门维度Excel> [--month 月份]

功能：根据个人维度和部门维度两个Excel文件生成大屏所需的data.js数据文件

示例:
  python generate_dashboard.py --personal 个人维度.xlsx --dept 部门维度.xlsx
  python generate_dashboard.py --personal 个人维度.xlsx --dept 部门维度.xlsx --month 2026年2月
"""

import pandas as pd
import json
import sys
import os
from datetime import datetime, time as dt_time

# 个人维度列映射
PERSONAL_COLUMN_MAPPING = {
    '浪潮工号': 'empId',
    '员工工号': 'empId',
    '工号': 'empId',
    '职工姓名': 'name',
    '姓名': 'name',
    '所属单位': 'unit',
    '一级部门': 'dept1',
    '二级部门': 'dept2',
    '考勤地': 'location',
    '考勤地点': 'location',
    '应出勤天数': 'shouldAttend',
    '应出勤': 'shouldAttend',
    '打卡天数': 'actualAttend',
    '实际出勤天数': 'actualAttend',
    '实出勤': 'actualAttend',
    '出差天数(工作日)': 'bizTripDays',
    '出差天数': 'bizTripDays',
    '出差率(工作日)': 'bizTripRate',
    '出差率(%)': 'bizTripRate',
    '出差率': 'bizTripRate',
    '迟到次数': 'lateTimes',
    '请假天数(工作日)': 'leaveDays',
    '请假天数': 'leaveDays',
    '补签次数': 'makeupTimes',
    '平均上班时间': 'avgClockIn',
    '平均上班打卡时间': 'avgClockIn',
    '平均下班时间': 'avgClockOut',
    '平均下班打卡时间': 'avgClockOut',
    '周末出勤率': 'weekendRate',
    '周末出勤率(%)': 'weekendRate',
    '下班一小时以上打卡率': 'afterWorkRate',
    '下班一小时以上打卡率(%)': 'afterWorkRate',
    '平时贡献': 'normalContrib',
    '平时贡献时长': 'normalContrib',
    '周末贡献': 'weekendContrib',
    '周末贡献时长': 'weekendContrib',
    '法定节假日带薪贡献': 'holidayContrib',
    '节假日贡献时长': 'holidayContrib',
    '贡献时长': 'totalContrib',
    '总贡献时长': 'totalContrib',
    '总贡献': 'totalContrib',
    '是否计入部门': 'countInDept',
    '问题人员': 'isProblem',
    '是否问题人员': 'isProblem',
    '三期/陪产/病假': 'sanqiType',
    '三期天数': 'sanqiDays',
}

# 部门维度列映射
DEPT_COLUMN_MAPPING = {
    '一级部门': 'dept1',
    '二级部门': 'dept2',
    '部门人数': 'headcount',
    '人数': 'headcount',
    '贡献时长': 'totalContrib',
    '周末出勤率': 'weekendRate',
    '周末出勤率(%)': 'weekendRate',
    '下班一小时以上打卡率': 'afterWorkRate',
    '下班一小时以上打卡率(%)': 'afterWorkRate',
    '出差率': 'bizTripRate',
    '出差率(%)': 'bizTripRate',
    '月出差大于50%的人数占比': 'highBizTripRatio',
    '迟到次数大于2次人员': 'lateOver2Count',
    '迟到次数大于2次': 'lateOver2Count',
}


# 需要作为百分比数值（0~100）处理的字段
PERCENT_FIELDS = {'bizTripRate', 'weekendRate', 'afterWorkRate', 'highBizTripRatio'}


def parse_percent_value(value, field_name):
    """解析百分比值，确保返回 0~100 范围的数值。
    处理三种情况：
    1. 字符串 "12.34%" → 12.34
    2. 小数 0.1234（Excel百分比格式底层值）→ 12.34
    3. 已经是百分比数值 12.34 → 12.34
    """
    if field_name not in PERCENT_FIELDS:
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.endswith('%'):
            try:
                return float(value[:-1])
            except ValueError:
                return 0
        try:
            value = float(value)
        except ValueError:
            return 0
    if isinstance(value, (int, float)):
        # 小数形式（如 0.1234）转为百分比（12.34）
        # 注意：值<=1时认为是小数形式（包括1.0表示100%）
        if -1 <= value <= 1 and value != 0:
            return round(value * 100, 2)
        return value
    return 0


def find_column_mapping(df_columns, mapping_config):
    """根据DataFrame的列名，自动匹配映射配置。优先精确匹配，再模糊匹配。"""
    result = {}
    remaining_cols = list(df_columns)

    # 辅助函数：去除所有空白字符（包括换行符）
    def normalize(s):
        return ''.join(s.split())

    # 第一轮：精确匹配
    for col in list(remaining_cols):
        col_stripped = col.strip()
        col_normalized = normalize(col)
        for excel_name, field_name in mapping_config.items():
            if excel_name == col_stripped or normalize(excel_name) == col_normalized:
                result[col] = field_name
                remaining_cols.remove(col)
                break

    # 第二轮：模糊匹配（未匹配到的列）
    for col in remaining_cols:
        col_normalized = normalize(col)
        for excel_name, field_name in mapping_config.items():
            excel_normalized = normalize(excel_name)
            if excel_normalized != col_normalized:
                # 只允许配置名包含在列名中（不反向），且配置名长度>=3避免过于短的匹配
                if len(excel_normalized) >= 3 and excel_normalized in col_normalized:
                    result[col] = field_name
                    break

    return result


def process_personal_data(excel_path, column_mapping=None):
    """处理个人维度Excel数据"""
    df = pd.read_excel(excel_path)
    print(f"读取个人维度Excel: {excel_path}")
    print(f"共 {len(df)} 行数据")
    print(f"列名: {df.columns.tolist()}")

    if column_mapping is None:
        column_mapping = find_column_mapping(df.columns, PERSONAL_COLUMN_MAPPING)

    print(f"\n个人维度匹配到的列映射:")
    for excel_col, field in column_mapping.items():
        print(f"  {excel_col} -> {field}")

    result = []
    for idx, row in df.iterrows():
        item = {'id': idx + 1}
        for excel_col, field_name in column_mapping.items():
            if excel_col in df.columns:
                value = row[excel_col]
                if pd.isna(value):
                    if field_name in ['isProblem', 'countInDept']:
                        value = '否'
                    elif field_name in ['sanqiType']:
                        value = ''
                    elif field_name in ['name', 'empId', 'location', 'avgClockIn', 'avgClockOut', 'unit', 'dept1', 'dept2']:
                        value = ''
                    else:
                        value = 0
                else:
                    # 处理时间类型
                    if isinstance(value, dt_time):
                        value = value.strftime('%H:%M:%S')
                    elif hasattr(value, 'strftime'):
                        value = str(value)
                    if field_name not in ['name', 'empId', 'location', 'avgClockIn', 'avgClockOut', 'isProblem', 'countInDept', 'unit', 'dept1', 'dept2']:
                        value = parse_percent_value(value, field_name)
                        if not isinstance(value, (int, float)):
                            try:
                                value = float(value)
                                if value == int(value):
                                    value = int(value)
                            except:
                                pass
                item[field_name] = value

        # 补充缺失字段的默认值
        defaults = {
            'empId': f'E{idx+1}', 'name': f'员工{idx+1}', 'location': '未知',
            'unit': '', 'dept1': '', 'dept2': '',
            'shouldAttend': 20, 'actualAttend': 20,
            'bizTripDays': 0, 'bizTripRate': 0,
            'lateTimes': 0, 'leaveDays': 0, 'makeupTimes': 0,
            'avgClockIn': '08:30:00', 'avgClockOut': '18:00:00',
            'weekendRate': 0, 'afterWorkRate': 0,
            'normalContrib': 0, 'weekendContrib': 0, 'holidayContrib': 0, 'totalContrib': 0,
            'countInDept': '是', 'isProblem': '否', 'sanqiType': '', 'sanqiDays': 0
        }
        for field, default in defaults.items():
            if field not in item:
                item[field] = default

        # 计算总贡献（如果没有）
        if 'totalContrib' not in column_mapping.values():
            item['totalContrib'] = item.get('normalContrib', 0) + item.get('weekendContrib', 0) + item.get('holidayContrib', 0)

        # 计算出差率（如果没有）
        if item.get('bizTripRate', 0) == 0 and item.get('bizTripDays', 0) > 0 and item.get('shouldAttend', 0) > 0:
            item['bizTripRate'] = round(item['bizTripDays'] / item['shouldAttend'] * 100, 2)

        result.append(item)

    return result


def process_dept_data(excel_path, column_mapping=None):
    """处理部门维度Excel数据"""
    df = pd.read_excel(excel_path)
    print(f"\n读取部门维度Excel: {excel_path}")
    print(f"共 {len(df)} 行数据")
    print(f"列名: {df.columns.tolist()}")

    if column_mapping is None:
        column_mapping = find_column_mapping(df.columns, DEPT_COLUMN_MAPPING)

    print(f"\n部门维度匹配到的列映射:")
    for excel_col, field in column_mapping.items():
        print(f"  {excel_col} -> {field}")

    # 处理层级结构：NaN的一级部门继承上一行
    dept1_col = None
    for col, field in column_mapping.items():
        if field == 'dept1':
            dept1_col = col
            break

    result = []
    last_dept1 = ''
    for idx, row in df.iterrows():
        item = {'id': idx + 1}
        for excel_col, field_name in column_mapping.items():
            if excel_col in df.columns:
                value = row[excel_col]
                if pd.isna(value):
                    if field_name == 'dept1':
                        value = last_dept1  # 继承上一行的一级部门
                    elif field_name in ['dept2']:
                        value = ''
                    else:
                        value = 0
                else:
                    if field_name == 'dept1':
                        last_dept1 = str(value).strip()
                    # 处理时间类型
                    if isinstance(value, dt_time):
                        value = value.strftime('%H:%M:%S')
                    elif hasattr(value, 'strftime'):
                        value = str(value)
                    if field_name not in ['dept1', 'dept2', 'lateOver2Count']:
                        value = parse_percent_value(value, field_name)
                        if not isinstance(value, (int, float)):
                            try:
                                value = float(value)
                                if value == int(value):
                                    value = int(value)
                            except:
                                pass
                    else:
                        value = str(value).strip()
                item[field_name] = value

        # 补充缺失字段的默认值
        defaults = {
            'dept1': '', 'dept2': '', 'headcount': 0,
            'totalContrib': 0, 'weekendRate': 0, 'afterWorkRate': 0,
            'bizTripRate': 0, 'highBizTripRatio': 0, 'lateOver2Count': '0'
        }
        for field, default in defaults.items():
            if field not in item:
                item[field] = default

        result.append(item)

    return result


def generate_data_from_both(personal_path, dept_path, month=None):
    """从两个Excel文件生成大屏数据"""
    personal_data = process_personal_data(personal_path)
    dept_data = process_dept_data(dept_path)
    return personal_data, dept_data, month


def save_data_js(personal_data, dept_data, output_dir, month=None):
    """保存data.js文件（双数据源）"""
    js_content = (
        f"const PERSONAL_DATA = {json.dumps(personal_data, ensure_ascii=False, indent=2)};\n\n"
        f"const DEPT_DATA = {json.dumps(dept_data, ensure_ascii=False, indent=2)};\n"
    )

    shared_dir = os.path.join(output_dir, 'shared')
    os.makedirs(shared_dir, exist_ok=True)

    data_js_path = os.path.join(shared_dir, 'data.js')
    with open(data_js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    # JSON备份
    data_json_path = os.path.join(shared_dir, 'data.json')
    with open(data_json_path, 'w', encoding='utf-8') as f:
        json.dump({'personal': personal_data, 'dept': dept_data}, f, ensure_ascii=False, indent=2)

    print(f"\n生成完成:")
    print(f"  {data_js_path}")
    print(f"  {data_json_path}")

    if month:
        print(f"\n月份标识: {month}")

    return data_js_path


# 兼容旧接口（单文件模式 - 仅处理个人维度）
def generate_data_from_excel(excel_path, column_mapping=None, month=None):
    """兼容旧接口：单文件模式"""
    data = process_personal_data(excel_path, column_mapping)
    return data, month


def main():
    import argparse
    parser = argparse.ArgumentParser(description='人力资源效能分析大屏数据生成工具（双文件版）')
    parser.add_argument('--personal', required=True, help='个人维度Excel文件路径')
    parser.add_argument('--dept', required=True, help='部门维度Excel文件路径')
    parser.add_argument('--month', help='数据月份，如"2026年2月"')
    parser.add_argument('--output', default=None, help='输出目录，默认为当前dashboard_preview目录')

    args = parser.parse_args()

    for path in [args.personal, args.dept]:
        if not os.path.exists(path):
            print(f"错误: 文件不存在 {path}")
            sys.exit(1)

    output_dir = args.output or os.path.dirname(os.path.abspath(__file__))

    personal_data, dept_data, month = generate_data_from_both(args.personal, args.dept, args.month)

    # 尝试从文件名提取月份
    if month is None:
        import re
        for path in [args.personal, args.dept]:
            match = re.search(r'(\d{4}年\d{1,2}月)', os.path.basename(path))
            if match:
                month = match.group(1)
                break
        if month is None:
            month = datetime.now().strftime('%Y年%m月')

    save_data_js(personal_data, dept_data, output_dir, month)

    print(f"\n大屏数据已生成，个人维度 {len(personal_data)} 条，部门维度 {len(dept_data)} 条")
    print(f"运行 python server.py 启动大屏预览")


if __name__ == '__main__':
    main()
