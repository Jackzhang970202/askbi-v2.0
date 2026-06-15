#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新refer文件夹脚本 - Agno版本

功能：
1. 清空refer文件夹下的所有数据源子文件夹
2. 根据datasources_config.json中的所有数据库类型数据源
3. 从每个数据源获取真实表结构和字段信息，生成元数据到refer文件夹

用法：
python update_refer_from_list.py
或
python update_refer_from_list.py <datasource_name>  # 只生成指定数据源
"""

import os
import sys
import json
import shutil
from pathlib import Path

# 确保可以导入项目模块
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.schema_generator import generate_schema_for_datasource, save_schema_to_refer, read_white_list_files
from datasources.datasource_manager import datasource_manager


def clear_refer_folder(refer_folder: str = "refer") -> bool:
    """清空refer文件夹"""
    try:
        if not os.path.exists(refer_folder):
            os.makedirs(refer_folder)
            print(f"[INFO] refer文件夹不存在，已创建: {refer_folder}")
            return True
        for name in os.listdir(refer_folder):
            path = os.path.join(refer_folder, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
                print(f"[INFO] 删除: {name}")
            except Exception as e:
                print(f"[ERROR] 删除失败 {path}: {e}")
        print(f"[INFO] refer文件夹已清空")
        return True
    except Exception as e:
        print(f"[ERROR] 清空失败: {e}")
        return False


def main():
    print("=" * 50)
    print("开始更新refer文件夹 - Agno版本")
    print("=" * 50)

    refer_folder = "refer"
    target_name = sys.argv[1] if len(sys.argv) > 1 else None

    # 1. 清空refer文件夹
    print("\n[步骤1] 清空refer文件夹...")
    if not clear_refer_folder(refer_folder):
        print("[ERROR] 清空失败，程序终止")
        return

    # 2. 获取数据源列表
    print("\n[步骤2] 获取数据源列表...")
    all_datasources = datasource_manager.list_datasources()
    if not all_datasources:
        print("[ERROR] 没有找到任何数据源，程序终止")
        return

    # 过滤：只处理数据库类型数据源，如果指定了名称则只处理该数据源
    datasources_to_process = []
    for ds in all_datasources:
        ds_name = ds.get("name") or ds.get("datasource_name")
        ds_type = ds.get("type", "").lower()
        if ds_type in ("pgsql", "postgresql", "mysql"):
            if target_name is None or ds_name == target_name:
                datasources_to_process.append(ds)

    if target_name and not datasources_to_process:
        print(f"[ERROR] 未找到数据源 '{target_name}' 或该数据源不是数据库类型")
        return

    if not datasources_to_process:
        print("[ERROR] 没有找到任何数据库类型的数据源，程序终止")
        return

    print(f"[INFO] 将处理 {len(datasources_to_process)} 个数据源: {[d.get('name') or d.get('datasource_name') for d in datasources_to_process]}")

    # 3. 为每个数据源生成元数据并保存到refer
    print("\n[步骤3] 生成元数据并保存到refer文件夹...")
    total_tables = 0
    success_count = 0
    error_count = 0

    for ds in datasources_to_process:
        ds_name = ds.get("name") or ds.get("datasource_name")
        ds_type = ds.get("type", "").lower()
        print(f"\n--- 处理数据源: {ds_name} ({ds_type}) ---")

        try:
            schema_data = generate_schema_for_datasource(ds_name)
            table_count = len(schema_data.get("tables", {}))

            if table_count == 0:
                print(f"[WARN] 数据源 '{ds_name}' 中没有找到表，跳过")
                error_count += 1
                continue

            save_path = save_schema_to_refer(ds_name, schema_data, refer_base=refer_folder)
            total_tables += table_count
            success_count += 1
            print(f"[OK] {ds_name}: {table_count} 个表 -> {save_path}")

        except Exception as e:
            error_count += 1
            print(f"[ERROR] 数据源 '{ds_name}' 处理失败: {e}")

    print("\n" + "=" * 50)
    print("更新完成！")
    print(f"- 成功: {success_count} 个数据源")
    print(f"- 失败: {error_count} 个数据源")
    print(f"- 总表数: {total_tables}")
    print(f"- refer文件夹: {refer_folder}")
    print("=" * 50)


if __name__ == "__main__":
    main()
