#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建数据库表的脚本
"""

from utils.db_utils import db_utils

def main():
    try:
        print("开始创建数据库表...")
        db_utils.create_tables()
        print("数据库表创建成功！")
    except Exception as e:
        print(f"数据库表创建失败: {e}")
    finally:
        db_utils.close()

if __name__ == "__main__":
    main()
