"""
全局知识模块 - 为所有智能体提供共享知识
从knowledge文件夹读取所有文件内容作为全局知识
"""

import os
import glob
from utils.db_utils import db_utils

def get_global_knowledge(datasource_name: str = None):
    """从数据库读取已启用的全局配置并格式化"""
    try:
        # 从数据库获取所有已启用的配置
        configs = db_utils.list_global_configs()
        enabled_configs = [c for c in configs if c.get('is_enabled')]
        
        # 根据数据源过滤
        if datasource_name:
            enabled_configs = [
                c for c in enabled_configs 
                if c.get('scope_type') == 'universal' or datasource_name in (c.get('scope_datasources') or [])
            ]
        else:
            # 如果没有指定数据源，通常只返回通用的，或者返回全部（取决于业务逻辑，这里我们返回全部但优先通用）
            pass
        
        if not enabled_configs:
            # 如果数据库为空，尝试保留原有的文件读取逻辑作为备份/迁移过渡
            return get_global_knowledge_from_files()

        vocabulary = []
        knowledge = []
        reference_sql = []

        for c in enabled_configs:
            cat = c.get('category')
            name = c.get('name')
            content = c.get('content')
            
            if cat == 'vocabulary':
                vocabulary.append(f"- {name}: {content}")
            elif cat == 'knowledge':
                knowledge.append(f"## {name}\n{content}")
            elif cat == 'sql':
                reference_sql.append(f"-- {name}\n{content}")

        final_content = ""
        if vocabulary:
            final_content += "\n# 全局业务词汇映射:\n" + "\n".join(vocabulary) + "\n"
        if knowledge:
            final_content += "\n# 全局业务知识规则:\n" + "\n".join(knowledge) + "\n"
        if reference_sql:
            final_content += "\n# 全局参考 SQL 逻辑:\n" + "\n".join(reference_sql) + "\n"

        return final_content
    except Exception as e:
        print(f"读取全局配置失败: {e}")
        return get_global_knowledge_from_files()

def get_global_knowledge_from_files():
    """实时读取knowledge文件夹下的所有文件内容"""
    knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
    knowledge_content = ""
    
    if not os.path.exists(knowledge_dir):
        return ""

    # 读取所有文件
    for file_path in glob.glob(os.path.join(knowledge_dir, '*')):
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        knowledge_content += f"\n# 来自 {os.path.basename(file_path)} 的知识:\n{content}\n"
            except Exception as e:
                print(f"警告: 无法读取文件 {file_path}: {e}")
    
    return knowledge_content
