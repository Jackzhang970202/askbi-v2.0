import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

from utils.schema_generator import safe_refer_name


def load_schema_from_refer(refer_path: str, datasource_name: Optional[str] = None) -> Dict[str, Any]:
    """
    加载元数据（支持从数据库或文件读取）。
    """
    schema_data = {
        "tables": {},
        "timestamp": str(datetime.now().isoformat()),
        "white_list_used": False
    }
    
    # 1. 尝试从数据库加载
    if datasource_name:
        try:
            from utils.db_utils import db_utils
            knowledge = db_utils.get_chat_knowledge(datasource_name)
            if knowledge and knowledge.get('schema_data'):
                db_data = knowledge['schema_data']
                # 处理 JSON string 回退
                if isinstance(db_data, str):
                    try:
                        db_data = json.loads(db_data)
                    except json.JSONDecodeError:
                        db_data = None
                if isinstance(db_data, dict):
                    if 'tables' in db_data:
                        schema_data['tables'] = db_data['tables']
                    for key, value in db_data.items():
                        if key != 'tables':
                            schema_data[key] = value
                    print(f"[INFO] 成功从数据库加载元数据: {datasource_name}, 表数: {len(schema_data['tables'])}")
                    return schema_data
                else:
                    print(f"[WARN] schema_data 类型异常: {type(db_data)}, datasource_name={datasource_name}")
        except Exception as e:
            print(f"[WARNING] 从数据库加载元数据失败: {e}")
            import traceback
            traceback.print_exc()

    # 2. 回退到从文件系统加载 (兼容 Excel 和旧数据)
    if not os.path.exists(refer_path):
        return schema_data

    if datasource_name:
        datasource_folder = os.path.join(refer_path, safe_refer_name(datasource_name))

        if not os.path.exists(datasource_folder):
            print(f"[WARNING] Schema folder not found for datasource '{datasource_name}': {datasource_folder}")
            return schema_data

        # 查找该文件夹下的 JSON 文件
        schema_files = []
        for filename in os.listdir(datasource_folder):
            if filename.endswith(".json"):
                # 优先匹配 _metadata.json 或 session_mem_..._schema_data.json
                is_metadata = filename.endswith("_metadata.json")
                is_old_format = filename.startswith("session_mem_") and filename.endswith("_schema_data.json")

                file_path = os.path.join(datasource_folder, filename)
                if os.path.isfile(file_path):
                    # 给予优先级权重：metadata 最高，旧格式次之，其他最末
                    priority = 2 if is_metadata else (1 if is_old_format else 0)
                    schema_files.append((file_path, os.path.getmtime(file_path), priority))

        if not schema_files:
            print(f"[WARNING] No schema files found in folder: {datasource_folder}")
            return schema_data

        # 按优先级权重降序，同权重按修改时间降序，使用最新的文件
        schema_files.sort(key=lambda x: (x[2], x[1]), reverse=True)
        latest_file = schema_files[0][0]

        print(f"[INFO] Loading schema from datasource folder: {datasource_name}/{os.path.basename(latest_file)}")
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)

                # If the file has a 'tables' field, use it
                if 'tables' in file_content:
                    schema_data['tables'] = file_content['tables']
                    print(f"[INFO] Loaded {len(file_content['tables'])} tables from {os.path.basename(latest_file)}")

                # If the file has other fields, merge them as well
                for key, value in file_content.items():
                    if key != 'tables':
                        schema_data[key] = value
        except Exception as e:
            print(f"[ERROR] Failed to process file {latest_file}: {e}")
            import traceback
            traceback.print_exc()

        print(f"[INFO] Total tables loaded from refer folder: {len(schema_data['tables'])}")
        return schema_data
    
    # Otherwise, read all JSON files in the refer folder (backward compatibility)
    for filename in os.listdir(refer_path):
        if filename.endswith('.json'):
            file_path = os.path.join(refer_path, filename)
            print(f"[INFO] Processing schema file: {filename}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Read and parse the JSON file
                    file_content = json.load(f)
                    
                    # If the file has a 'tables' field, merge it into the schema_data
                    if 'tables' in file_content:
                        schema_data['tables'].update(file_content['tables'])
                        print(f"[INFO] Loaded {len(file_content['tables'])} tables from {filename}")
                    
                    # If the file has other fields, merge them as well
                    for key, value in file_content.items():
                        if key != 'tables':
                            schema_data[key] = value
            except Exception as e:
                print(f"[ERROR] Failed to process file {filename}: {e}")
    
    print(f"[INFO] Total tables loaded from refer folder: {len(schema_data['tables'])}")
    return schema_data
