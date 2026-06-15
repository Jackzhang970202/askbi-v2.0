import os
import re
from typing import Set, List


def read_white_list_files(white_list_folder: str = "refer_list") -> Set[str]:
    """
    从refer_list文件夹读取白名单表名
    
    Args:
        white_list_folder: 白名单文件夹路径，默认为refer_list
        
    Returns:
        去重后的表名集合
    """
    table_names = set()
    
    # 检查文件夹是否存在
    if not os.path.exists(white_list_folder):
        print(f"[WARNING] 白名单文件夹 {white_list_folder} 不存在")
        return table_names
    
    # 遍历文件夹中的所有txt文件
    for filename in os.listdir(white_list_folder):
        if filename.endswith('.txt'):
            file_path = os.path.join(white_list_folder, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        # 跳过空行和注释行
                        if not line or line.startswith('#') or line.startswith('//'):
                            continue
                        
                        # 添加表名到集合中
                        table_names.add(line)
                        
            except Exception as e:
                print(f"[ERROR] 读取白名单文件 {file_path} 失败: {e}")
    
    print(f"[INFO] 从refer_list文件夹读取到 {len(table_names)} 个表名")
    return table_names


def validate_table_names_in_code(code: str, white_list_tables: Set[str]) -> List[str]:
    """
    验证代码中使用的表名是否在白名单中
    
    Args:
        code: 要验证的代码
        white_list_tables: 白名单表名集合
        
    Returns:
        不在白名单中的表名列表
    """
    # 改进的正则表达式匹配表名
    # 匹配 FROM 或 JOIN 后面的表名，排除Python导入语句
    table_pattern = r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)(?:\s|;|$)'
    
    found_tables = set()
    matches = re.findall(table_pattern, code, re.IGNORECASE)
    
    for match in matches:
        # 处理可能的表别名
        table_name = match.split()[0] if ' ' in match else match
        # 排除Python导入语句中的模块名
        if not (table_name.startswith('from ') or table_name.startswith('import ')):
            found_tables.add(table_name)
    
    # 检查不在白名单中的表名
    invalid_tables = []
    for table in found_tables:
        # 处理带模式名的表名（如 jiceng.community_small_places）
        # 只检查表名部分，忽略模式名
        table_name_only = table.split('.')[-1] if '.' in table else table
        
        if table_name_only not in white_list_tables:
            invalid_tables.append(table)
    
    return invalid_tables


def check_code_safety_with_white_list(code: str, white_list_folder: str = "refer_list") -> dict:
    """
    检查代码安全性（危险操作检查 + 白名单表名检查）
    
    Args:
        code: 要检查的代码
        white_list_folder: 白名单文件夹路径
        
    Returns:
        检查结果字典
    """
    result = {
        "safe": True,
        "dangerous_operations": [],
        "invalid_tables": [],
        "warnings": []
    }
    
    # 检查危险操作
    dangerous_keywords = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
        'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'UNION', 'INFORMATION_SCHEMA'
    ]
    
    code_upper = code.upper()
    for keyword in dangerous_keywords:
        if keyword in code_upper:
            result["dangerous_operations"].append(keyword)
            result["safe"] = False
    
    # 读取白名单表名
    white_list_tables = read_white_list_files(white_list_folder)
    
    # 验证表名
    invalid_tables = validate_table_names_in_code(code, white_list_tables)
    if invalid_tables:
        result["invalid_tables"] = invalid_tables
        result["safe"] = False
    
    # 如果没有危险操作且所有表都在白名单中，则认为是安全的
    if not result["dangerous_operations"] and not result["invalid_tables"]:
        result["safe"] = True
        result["warnings"].append("代码安全检查通过")
    
    return result


# 测试代码
if __name__ == "__main__":
    # 测试读取白名单文件
    tables = read_white_list_files()
    print(f"白名单表名: {tables}")
    
    # 测试表名验证
    test_code = """
    SELECT * FROM jiceng.community_building;
    JOIN jiceng.community_people ON community_building.id = community_people.building_id;
    """
    
    invalid = validate_table_names_in_code(test_code, tables)
    print(f"不在白名单中的表: {invalid}")
    
    # 测试安全性检查
    safety_result = check_code_safety_with_white_list(test_code)
    print(f"安全性检查结果: {safety_result}")