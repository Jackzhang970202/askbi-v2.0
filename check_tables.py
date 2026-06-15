#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库表是否创建成功的脚本
"""

import sys
from utils.db_utils import db_utils

def main():
    print(f"Python版本: {sys.version}")
    print(f"当前工作目录: {sys.path}")
    print(f"模块搜索路径: {sys.path}")
    
    try:
        print("开始检查数据库表...")
        
        # 查询所有表
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """
        
        print("执行查询...")
        tables = db_utils.execute_query(query)
        
        print(f"查询结果: {tables}")
        
        print("数据库中存在的表:")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        # 检查我们需要的表是否都存在
        required_tables = ['askbi_white_list', 'askbi_chat_session', 
                          'askbi_general_metadata', 'askbi_request_record']
        
        print("\n检查所需表是否存在:")
        for table in required_tables:
            if any(t['table_name'] == table for t in tables):
                print(f"  ✓ {table} - 存在")
            else:
                print(f"  ✗ {table} - 不存在")
        
    except Exception as e:
        print(f"检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_utils.close()

if __name__ == "__main__":
    main()
