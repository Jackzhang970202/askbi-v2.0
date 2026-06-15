#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据脱敏工具

📅 新增日期: 2026.03.19
📝 变更说明: 新增报表数据脱敏处理功能

支持的脱敏方法：
- name_mask: 姓名脱敏（保留姓，名用*替换）
- prefix_mask: 前缀保留脱敏（保留前N位，后用*替换）
- phone_mask: 手机号脱敏（保留前3后4位）
- id_card_mask: 身份证号脱敏（保留前6后4位）
- bank_card_mask: 银行卡号脱敏（保留后4位）
- full_mask: 完全脱敏（整体替换为***）
"""

import pandas as pd
import re
from typing import Dict, List, Any, Optional


def mask_name(value: Any, show_surname: bool = True) -> str:
    """
    姓名脱敏：保留姓，名用*替换

    示例: 张三 -> 张*
    """
    if pd.isna(value) or value == '':
        return ''

    value = str(value).strip()
    if not value:
        return ''

    if len(value) == 1:
        return value
    elif len(value) == 2:
        return value[0] + '*'
    else:
        return value[0] + '*' * (len(value) - 1)


def mask_prefix(value: Any, show_prefix: int = 3) -> str:
    """
    前缀保留脱敏：保留前N位，后用*替换

    示例: EMP00123, show_prefix=3 -> EMP*****
    """
    if pd.isna(value) or value == '':
        return ''

    value = str(value).strip()
    if not value:
        return ''

    if len(value) <= show_prefix:
        return value

    return value[:show_prefix] + '*' * (len(value) - show_prefix)


def mask_phone(value: Any, show_prefix: int = 3, show_suffix: int = 4) -> str:
    """
    手机号脱敏：保留前N位和后M位

    示例: 13812345678 -> 138****5678
    """
    if pd.isna(value) or value == '':
        return ''

    value = str(value).strip()
    if not value:
        return ''

    # 移除非数字字符
    digits = re.sub(r'\D', '', value)

    if len(digits) < show_prefix + show_suffix:
        return '*' * len(value)

    return digits[:show_prefix] + '*' * (len(digits) - show_prefix - show_suffix) + digits[-show_suffix:]


def mask_id_card(value: Any, show_prefix: int = 6, show_suffix: int = 4) -> str:
    """
    身份证号脱敏：保留前N位和后M位

    示例: 370102199001011234 -> 370102********1234
    """
    if pd.isna(value) or value == '':
        return ''

    value = str(value).strip()
    if not value:
        return ''

    # 移除非数字和X字符
    cleaned = re.sub(r'[^0-9Xx]', '', value)

    if len(cleaned) < show_prefix + show_suffix:
        return '*' * len(value)

    return cleaned[:show_prefix] + '*' * (len(cleaned) - show_prefix - show_suffix) + cleaned[-show_suffix:]


def mask_bank_card(value: Any, show_suffix: int = 4) -> str:
    """
    银行卡号脱敏：保留后N位

    示例: 6222021234567890 -> ************7890
    """
    if pd.isna(value) or value == '':
        return ''

    value = str(value).strip()
    if not value:
        return ''

    # 移除非数字字符
    digits = re.sub(r'\D', '', value)

    if len(digits) <= show_suffix:
        return '*' * len(value)

    return '*' * (len(digits) - show_suffix) + digits[-show_suffix:]


def mask_full(value: Any) -> str:
    """
    完全脱敏：整体替换为***
    """
    if pd.isna(value) or value == '':
        return ''

    return '***'


# 脱敏方法映射
DESENSITIZE_METHODS = {
    'name_mask': mask_name,
    'prefix_mask': mask_prefix,
    'phone_mask': mask_phone,
    'id_card_mask': mask_id_card,
    'bank_card_mask': mask_bank_card,
    'full_mask': mask_full,
}


def desensitize_value(value: Any, method: str, params: Optional[Dict] = None) -> Any:
    """
    对单个值进行脱敏处理

    Args:
        value: 原始值
        method: 脱敏方法名称
        params: 脱敏参数

    Returns:
        脱敏后的值
    """
    if pd.isna(value) or value == '' or value is None:
        return value

    params = params or {}

    if method not in DESENSITIZE_METHODS:
        # 未知方法，使用完全脱敏
        return mask_full(value)

    return DESENSITIZE_METHODS[method](value, **params)


def desensitize_dataframe(
    df: pd.DataFrame,
    config: Dict[str, Any]
) -> pd.DataFrame:
    """
    对 DataFrame 进行脱敏处理

    Args:
        df: 原始 DataFrame
        config: 脱敏配置，格式如下：
            {
                "desensitize_fields": [
                    {"column_name": "姓名", "method": "name_mask", "params": {"show_surname": true}},
                    {"column_name": "工号", "method": "prefix_mask", "params": {"show_prefix": 3}},
                    {"column_name": "手机号", "method": "phone_mask", "params": {"show_prefix": 3, "show_suffix": 4}}
                ],
                "default_method": "full_mask",
                "excluded_fields": ["序号", "出勤天数", "迟到次数"]
            }

    Returns:
        脱敏后的 DataFrame
    """
    if df is None or df.empty:
        return df

    df_result = df.copy()

    # 获取配置
    desensitize_fields = config.get('desensitize_fields', [])
    default_method = config.get('default_method', 'full_mask')
    excluded_fields = set(config.get('excluded_fields', []))

    # 构建列名到脱敏配置的映射
    field_config_map = {}
    for field_config in desensitize_fields:
        col_name = field_config.get('column_name')
        if col_name:
            field_config_map[col_name] = {
                'method': field_config.get('method', default_method),
                'params': field_config.get('params', {})
            }

    # 遍历所有列进行脱敏
    for col in df_result.columns:
        if col in excluded_fields:
            continue

        if col in field_config_map:
            # 使用指定配置
            method = field_config_map[col]['method']
            params = field_config_map[col]['params']
            df_result[col] = df_result[col].apply(
                lambda v: desensitize_value(v, method, params)
            )

    return df_result


def desensitize_dataframe_by_columns(
    df: pd.DataFrame,
    column_config: Dict[str, str]
) -> pd.DataFrame:
    """
    按列配置对 DataFrame 进行脱敏处理

    📅 2026.03.19 新增
    📝 变更说明：支持列级别脱敏配置

    Args:
        df: 原始 DataFrame
        column_config: 列脱敏配置，格式：{"列名": "脱敏方法"}
            脱敏方法可选值：
            - "name_mask": 姓名脱敏（保留姓）
            - "phone_mask": 手机号脱敏
            - "id_card_mask": 身份证号脱敏
            - "bank_card_mask": 银行卡号脱敏
            - "prefix_mask": 前缀保留脱敏
            - "full_mask": 完全脱敏
            - "none": 不脱敏

    Returns:
        脱敏后的 DataFrame
    """
    if df is None or df.empty:
        return df

    df_result = df.copy()

    for col in df_result.columns:
        method = column_config.get(col, "none")
        if method and method != "none":
            df_result[col] = df_result[col].apply(
                lambda v: desensitize_value(v, method, {})
            )

    return df_result


def get_available_desensitize_methods() -> List[Dict[str, str]]:
    """
    获取可用的脱敏方法列表

    📅 2026.03.19 新增
    📝 变更说明：新增获取脱敏方法列表接口

    Returns:
        脱敏方法列表
    """
    return [
        {"id": "none", "name": "不脱敏", "description": "保持原数据不变"},
        {"id": "name_mask", "name": "姓名脱敏", "description": "保留姓氏，名用*替换，如：张三→张*"},
        {"id": "phone_mask", "name": "手机号脱敏", "description": "保留前3后4位，如：138****5678"},
        {"id": "id_card_mask", "name": "身份证脱敏", "description": "保留前6后4位，如：370102****1234"},
        {"id": "bank_card_mask", "name": "银行卡脱敏", "description": "保留后4位，如：****7890"},
        {"id": "prefix_mask", "name": "前缀保留", "description": "保留前3位，后面用*替换"},
        {"id": "full_mask", "name": "完全脱敏", "description": "替换为***"},
    ]


def auto_detect_column_desensitize(columns: List[str]) -> Dict[str, str]:
    """
    自动检测列的脱敏方法

    📅 2026.03.19 新增
    📝 变更说明：根据列名自动推荐脱敏方法

    Args:
        columns: 列名列表

    Returns:
        自动检测的脱敏配置
    """
    config = {}

    for col in columns:
        col_lower = col.lower()

        # 姓名相关
        if '姓名' in col or 'name' in col_lower:
            config[col] = "name_mask"
        # 手机号相关
        elif '手机' in col or '电话' in col or 'phone' in col_lower or 'mobile' in col_lower:
            config[col] = "phone_mask"
        # 身份证相关
        elif '身份证' in col or 'id_card' in col_lower or '证件' in col:
            config[col] = "id_card_mask"
        # 银行卡相关
        elif '银行卡' in col or '卡号' in col or 'bank' in col_lower:
            config[col] = "bank_card_mask"
        # 工号相关
        elif '工号' in col or 'emp' in col_lower or '员工' in col:
            config[col] = "prefix_mask"
        else:
            config[col] = "none"

    return config


def get_default_desensitize_config() -> Dict[str, Any]:
    """
    获取默认的脱敏配置（人事考勤报表）

    Returns:
        默认脱敏配置
    """
    return {
        "desensitize_fields": [
            {"column_name": "职工姓名", "method": "name_mask", "params": {"show_surname": True}},
            {"column_name": "浪潮工号", "method": "prefix_mask", "params": {"show_prefix": 3}},
        ],
        "default_method": "full_mask",
        "excluded_fields": [
            "序号", "所属单位", "一级部门", "二级部门", "岗位", "考勤地",
            "应出勤天数", "打卡天数", "出差天数（工作日）", "出差率（工作日）",
            "出差天数（休息日）", "迟到次数", "请假天数\n（工作日）", "补签次数",
            "平均上班时间", "平均下班时间", "周末出勤率", "下班一小时以上打卡率",
            "平时贡献", "周末贡献", "法定节假日带薪贡献", "贡献时长",
            "三期天数", "三期/陪产/病假", "是否\n计入部门", "问题人员"
        ]
    }


# 单元测试
if __name__ == "__main__":
    # 测试各种脱敏方法
    print("=== 脱敏功能测试 ===")

    print("\n1. 姓名脱敏:")
    print(f"   张三 -> {mask_name('张三')}")
    print(f"   欧阳修 -> {mask_name('欧阳修')}")

    print("\n2. 前缀保留脱敏:")
    print(f"   EMP00123 -> {mask_prefix('EMP00123', 3)}")

    print("\n3. 手机号脱敏:")
    print(f"   13812345678 -> {mask_phone('13812345678')}")

    print("\n4. 身份证号脱敏:")
    print(f"   370102199001011234 -> {mask_id_card('370102199001011234')}")

    print("\n5. 银行卡号脱敏:")
    print(f"   6222021234567890 -> {mask_bank_card('6222021234567890')}")

    print("\n6. DataFrame 脱敏测试:")
    test_df = pd.DataFrame({
        '职工姓名': ['张三', '李四', '王五'],
        '浪潮工号': ['EMP001', 'EMP002', 'EMP003'],
        '应出勤天数': [22, 22, 21]
    })
    print("   原始数据:")
    print(test_df.to_string(index=False))

    config = get_default_desensitize_config()
    masked_df = desensitize_dataframe(test_df, config)
    print("\n   脱敏后数据:")
    print(masked_df.to_string(index=False))