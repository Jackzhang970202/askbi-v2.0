#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schema生成器 - 根据数据源生成schema元数据文件
支持PostgreSQL和MySQL，参照update_refer_from_list.py的逻辑
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional
from datasources.datasource_manager import datasource_manager


def read_white_list_files(white_list_folder: str = "refer_list") -> set:
    """
    从refer_list文件夹读取所有txt文件中的表名，返回去重后的表名集合
    
    Args:
        white_list_folder: 白名单文件夹路径
        
    Returns:
        set: 去重后的表名集合
    """
    white_list_tables = set()
    
    # 检查文件夹是否存在
    if not os.path.exists(white_list_folder):
        print(f"[INFO] 白名单文件夹不存在: {white_list_folder}，将扫描所有表")
        return white_list_tables
    
    # 查找所有txt文件
    txt_files = glob.glob(os.path.join(white_list_folder, "*.txt"))
    
    if not txt_files:
        print(f"[INFO] 在白名单文件夹中未找到txt文件: {white_list_folder}，将扫描所有表")
        return white_list_tables
    
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    table_name = line.strip()
                    if table_name and not table_name.startswith('#'):  # 跳过空行和注释行
                        white_list_tables.add(table_name)
            print(f"[INFO] 从文件 {os.path.basename(txt_file)} 读取了表名")
        except Exception as e:
            print(f"[ERROR] 读取白名单文件失败 {txt_file}: {e}")
    
    print(f"[INFO] 总共读取了 {len(white_list_tables)} 个白名单表名")
    return white_list_tables


def get_table_structure_pgsql(connector, schema: str, table_name: str) -> dict:
    """
    获取PostgreSQL表的完整结构信息，包括字段、类型、注释等
    
    Args:
        connector: PostgreSQL连接器
        schema: 模式名
        table_name: 表名
        
    Returns:
        dict: 表结构信息
    """
    try:
        print(f"[DEBUG] 开始获取PostgreSQL表结构: {schema}.{table_name}")
        
        # 获取字段信息
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        columns_result = connector.execute_query(query, (schema, table_name))
        print(f"[DEBUG] 获取到 {len(columns_result)} 个列")
        
        if not columns_result:
            print(f"[WARNING] 表 {schema}.{table_name} 没有列信息")
            return None
        
        # 获取字段注释（PostgreSQL特有）
        comment_query = """
            SELECT 
                a.attname as column_name,
                d.description as column_comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid
            LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = a.attnum
            WHERE n.nspname = %s AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attnum
        """
        comments_result = connector.execute_query(comment_query, (schema, table_name))
        comments = {row['column_name']: row.get('column_comment') for row in comments_result if row.get('column_comment')}
        print(f"[DEBUG] 获取到 {len(comments)} 个列注释")
        
        # 获取表注释
        table_comment_query = """
            SELECT obj_description(c.oid) as table_comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relname = %s AND c.relkind = 'r'
        """
        table_comment_result = connector.execute_query(table_comment_query, (schema, table_name))
        table_comment = table_comment_result[0].get('table_comment') if table_comment_result and table_comment_result[0].get('table_comment') else f"{table_name} 表"
        print(f"[DEBUG] 表注释: {table_comment}")
        
        # 获取样本数据（最多5行）
        try:
            sample_data = connector.execute_query(f'SELECT * FROM "{schema}"."{table_name}" LIMIT 5')
        except Exception as e1:
            print(f"[DEBUG] 带引号查询失败: {e1}，尝试不带引号")
            try:
                sample_data = connector.execute_query(f"SELECT * FROM {schema}.{table_name} LIMIT 5")
            except Exception as e2:
                print(f"[WARNING] 获取样本数据失败: {e2}")
                sample_data = []
        
        print(f"[DEBUG] 获取到 {len(sample_data)} 行样本数据")
        
        # 格式化字段信息
        formatted_columns = []
        for col in columns_result:
            column_info = {
                "name": col.get('column_name', ''),
                "type": col.get('data_type', ''),
                "comment": comments.get(col.get('column_name', '')) if comments.get(col.get('column_name', '')) else None
            }
            
            # 添加类型特定信息
            if col.get('character_maximum_length'):
                column_info['length'] = col['character_maximum_length']
            if col.get('numeric_precision'):
                column_info['precision'] = col['numeric_precision']
            if col.get('numeric_scale'):
                column_info['scale'] = col['numeric_scale']
            
            formatted_columns.append(column_info)
        
        result = {
            "comment": table_comment,
            "columns": formatted_columns,
            "sample_data": sample_data,
            "schema": schema
        }
        print(f"[DEBUG] 成功构建表结构，列数: {len(formatted_columns)}, 样本数据: {len(sample_data)}")
        return result
        
    except Exception as e:
        print(f"[ERROR] 获取表 {schema}.{table_name} 结构失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_table_structure_mysql(connector, schema: str, table_name: str) -> dict:
    """
    获取MySQL表的完整结构信息，包括字段、类型、注释等
    
    Args:
        connector: MySQL连接器
        schema: 数据库名
        table_name: 表名
        
    Returns:
        dict: 表结构信息
    """
    try:
        # 获取字段信息
        query = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale,
                column_comment
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        columns_result = connector.execute_query(query, (schema, table_name))
        
        # 获取表注释
        table_comment_query = """
            SELECT table_comment
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """
        table_comment_result = connector.execute_query(table_comment_query, (schema, table_name))
        table_comment = table_comment_result[0].get('table_comment') if table_comment_result and table_comment_result[0].get('table_comment') else f"{table_name} 表"
        
        # 获取样本数据（最多5行）
        sample_data = connector.execute_query(f"SELECT * FROM `{schema}`.`{table_name}` LIMIT 5")
        
        # 格式化字段信息
        formatted_columns = []
        for col in columns_result:
            column_info = {
                "name": col['column_name'],
                "type": col['data_type'],
                "comment": col.get('column_comment') if col.get('column_comment') else None
            }
            
            # 添加类型特定信息
            if col.get('character_maximum_length'):
                column_info['length'] = col['character_maximum_length']
            if col.get('numeric_precision'):
                column_info['precision'] = col['numeric_precision']
            if col.get('numeric_scale'):
                column_info['scale'] = col['numeric_scale']
            
            formatted_columns.append(column_info)
        
        return {
            "comment": table_comment,
            "columns": formatted_columns,
            "sample_data": sample_data,
            "schema": schema
        }
        
    except Exception as e:
        print(f"[ERROR] 获取表 {schema}.{table_name} 结构失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_schema_for_datasource(datasource_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
    """
    为指定数据源生成schema数据
    
    Args:
        datasource_name: 数据源名称
        schema: 数据库模式名（可选，如果不提供则使用数据源配置中的默认值）
        
    Returns:
        dict: 生成的schema数据，格式与 session_mem_*_schema_data.json 一致
    """
    try:
        # 获取数据源连接器
        connector = datasource_manager.get_connector(datasource_name)
        
        # 获取数据源配置
        datasource_config = datasource_manager.get_datasource(datasource_name)
        if not datasource_config:
            raise Exception(f"数据源 '{datasource_name}' 不存在")
        
        datasource_type = datasource_config['type'].lower()
        
        # 如果没有指定schema，尝试从配置中获取
        # 优先使用用户填入的 database_schema 字段
        if not schema:
            config = datasource_config['config']
            schema = config.get('database_schema')
            # 如果没有 database_schema，对于PostgreSQL可以使用默认的 public，MySQL使用dbname
            if not schema:
                if datasource_type in ['pgsql', 'postgresql']:
                    schema = 'public'  # PostgreSQL默认schema
                else:
                    schema = config.get('dbname')  # MySQL使用数据库名
        
        if not schema:
            raise Exception(f"无法确定数据库模式，请指定schema参数")
        
        print(f"[INFO] 数据源类型: {datasource_type}, 模式: {schema}")
        
        # 读取白名单（如果有）
        white_list_tables = read_white_list_files("refer_list")
        
        # 获取所有表
        print(f"[DEBUG] 开始获取表列表，数据源: {datasource_name}, schema: {schema}")
        all_tables = datasource_manager.get_tables(datasource_name, schema)
        print(f"[DEBUG] 获取到 {len(all_tables) if all_tables else 0} 个表")
        if all_tables:
            print(f"[DEBUG] 前3个表示例: {all_tables[:3]}")
        
        if not all_tables:
            print(f"[WARNING] 数据源 '{datasource_name}' 在模式 '{schema}' 中没有找到表")
            print(f"[DEBUG] 尝试不指定schema获取所有表...")
            all_tables = datasource_manager.get_tables(datasource_name, None)
            if all_tables:
                print(f"[DEBUG] 不指定schema时获取到 {len(all_tables)} 个表")
                # 如果配置中有schema，过滤出该schema的表
                if schema:
                    all_tables = [t for t in all_tables if t.get('schema') == schema]
                    print(f"[DEBUG] 过滤后剩余 {len(all_tables)} 个表")
        
        if not all_tables:
            print(f"[ERROR] 数据源 '{datasource_name}' 中没有找到任何表")
            return {"tables": {}}
        
        # 如果白名单不为空，只处理白名单中的表
        if white_list_tables:
            # 提取表名（去掉schema前缀）
            table_names = {t.get('table', t.get('table_name', '')) for t in all_tables}
            print(f"[DEBUG] 表名集合: {list(table_names)[:5]}...")
            print(f"[DEBUG] 白名单表名: {list(white_list_tables)[:5]}...")
            # 过滤出在白名单中的表
            filtered_tables = [t for t in all_tables if t.get('table', t.get('table_name', '')) in white_list_tables]
            print(f"[INFO] 白名单模式: 从 {len(all_tables)} 个表中筛选出 {len(filtered_tables)} 个表")
            tables_to_process = filtered_tables
        else:
            # 扫描所有表
            print(f"[INFO] 扫描所有表: 共 {len(all_tables)} 个表")
            tables_to_process = all_tables
        
        refer_data = {"tables": {}}
        success_count = 0
        error_count = 0
        
        # 根据数据库类型选择不同的处理函数
        if datasource_type in ['pgsql', 'postgresql']:
            get_table_structure_func = get_table_structure_pgsql
        elif datasource_type == 'mysql':
            get_table_structure_func = get_table_structure_mysql
        else:
            raise Exception(f"不支持的数据源类型: {datasource_type}")
        
        # 遍历所有表，获取表结构
        print(f"[DEBUG] 开始处理 {len(tables_to_process)} 个表")
        for idx, table_info in enumerate(tables_to_process):
            print(f"[DEBUG] 处理第 {idx+1}/{len(tables_to_process)} 个表: {table_info}")
            table_schema = table_info.get('schema', schema)
            table_name = table_info.get('table', table_info.get('table_name'))
            
            if not table_name:
                print(f"[WARNING] 表信息中没有表名: {table_info}")
                continue
                
            full_table_name = f"{table_schema}.{table_name}"
            
            try:
                print(f"[INFO] 处理表: {full_table_name}")
                
                # 根据数据库类型获取表结构
                table_structure = get_table_structure_func(connector, table_schema, table_name)
                
                if table_structure:
                    refer_data["tables"][full_table_name] = table_structure
                    success_count += 1
                    print(f"[INFO] 成功获取表结构: {full_table_name} (列数: {len(table_structure.get('columns', []))}, 样本数据: {len(table_structure.get('sample_data', []))}行)")
                else:
                    error_count += 1
                    print(f"[ERROR] 获取表结构失败: {full_table_name} (返回None)")
                
            except Exception as e:
                error_count += 1
                print(f"[ERROR] 处理表失败: {full_table_name}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[INFO] 处理完成: 成功 {success_count} 个表，失败 {error_count} 个表")
        return refer_data
        
    except Exception as e:
        print(f"[ERROR] 生成schema数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def safe_refer_name(datasource_name: str) -> str:
    return datasource_name.replace(":", "_")


def save_schema_to_refer(datasource_name: str, schema_data: Dict[str, Any], refer_base: str = "refer") -> str:
    """
    保存schema数据到refer文件夹
    对于同一数据源，会删除旧的schema文件，只保留最新的
    """
    try:
        # 获取绝对路径以确保稳定性
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        refer_dir = os.path.join(current_dir, refer_base)
        safe_name = safe_refer_name(datasource_name)
        datasource_folder = os.path.join(refer_dir, safe_name)
        
        if not os.path.exists(datasource_folder):
            os.makedirs(datasource_folder, exist_ok=True)
            print(f"[INFO] 创建数据源文件夹: {datasource_folder}")
        else:
            # 清理旧文件
            old_files = glob.glob(os.path.join(datasource_folder, "*_metadata.json")) + \
                        glob.glob(os.path.join(datasource_folder, "session_mem_*_schema_data.json"))
            for old_file in old_files:
                try:
                    os.remove(old_file)
                except Exception:
                    pass
        
        # 统一文件名：{safe_name}_metadata.json 供 get_schema_metadata 接口使用
        filename = f"{safe_name}_metadata.json"
        file_path = os.path.join(datasource_folder, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schema_data, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"[INFO] Schema数据已保存到: {file_path}")
        return file_path
        
    except Exception as e:
        print(f"[ERROR] 保存schema数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise
