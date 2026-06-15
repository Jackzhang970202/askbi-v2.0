"""
数据源管理器
统一管理不同数据源的连接和操作
"""
from typing import Dict, Any, Optional, List
from datasources.pgsql import PostgreSQLConnector
from datasources.mysql import MySQLConnector
from datasources.excel import ExcelConnector
import json
import os
import shutil
from pathlib import Path


class DataSourceManager:
    """数据源管理器"""
    
    # 支持的数据源类型
    SUPPORTED_TYPES = {
        'pgsql': PostgreSQLConnector,
        'postgresql': PostgreSQLConnector,
        'mysql': MySQLConnector,
        'excel': ExcelConnector
    }
    
    def __init__(self, config_file: str = "datasources_config.json"):
        """
        初始化数据源管理器
        
        Args:
            config_file: 数据源配置文件路径
        """
        self.config_file = config_file
        self.config_path = Path(config_file)
        self.datasources = self._load_config()
        self.active_connections = {}  # 存储活跃连接
    
    def _load_config(self) -> Dict[str, Any]:
        """加载数据源配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载数据源配置失败: {e}")
                return {}
        return {}
    
    def _save_config(self):
        """保存数据源配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.datasources, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据源配置失败: {e}")
    
    def add_datasource(self, name: str, type: str, config: Dict[str, Any], knowledge_id: str = "0", owner_id: Optional[int] = None) -> Dict[str, Any]:
        """
        添加或修改数据源
        
        Args:
            name: 数据源名称
            type: 数据源类型（pgsql, mysql, excel）
            config: 数据源配置
            knowledge_id: 关联的外接知识库 ID
            owner_id: 所有者 ID
            
        Returns:
            操作结果
        """
        if not name or not name.strip():
            return {
                "success": False,
                "message": "数据源名称不能为空"
            }
        
        name = name.strip()
        
        if type not in self.SUPPORTED_TYPES:
            return {
                "success": False,
                "message": f"不支持的数据源类型: {type}"
            }
        
        # 验证配置
        if type != 'excel':
            required_fields = ['host', 'port', 'dbname', 'user', 'password']
            for field in required_fields:
                if field not in config:
                    return {
                        "success": False,
                        "message": f"缺少必需配置字段: {field}"
                    }
        
        # 测试连接 (非 Excel 类型)
        if type != 'excel':
            connector_class = self.SUPPORTED_TYPES[type]
            try:
                connector = connector_class(config)
                test_result = connector.test_connection()
                connector.close()
                
                if not test_result['success']:
                    return test_result
            except Exception as e:
                return {
                    "success": False,
                    "message": f"连接测试失败: {str(e)}"
                }
        
        # 增加存储键隔离 (user_{id}:name)
        storage_key = f"user_{owner_id}:{name}" if owner_id else name
        
        # 保存配置
        # 📅 2026.03.09 新增：跨 Schema 问数功能
        # 📝 变更说明：添加跨 Schema 模式标识
        is_cross_schema = False
        if type in ('pgsql', 'postgresql'):
            schemas = config.get('schemas', [])
            is_cross_schema = len(schemas) > 1

        self.datasources[storage_key] = {
            "type": type,
            "config": config,
            "knowledge_id": knowledge_id,
            "owner_id": owner_id,
            "created_at": str(Path().cwd()),
            "active": True,
            "is_cross_schema": is_cross_schema  # 跨 Schema 模式标识
        }
        self._save_config()
        
        return {
            "success": True,
            "message": "数据源添加成功",
            "name": storage_key,
            "display_name": name
        }
    
    def remove_datasource(self, name: str) -> Dict[str, Any]:
        """
        删除数据源
        
        Args:
            name: 数据源名称
            
        Returns:
            操作结果
        """
        if name not in self.datasources:
            return {
                "success": False,
                "message": f"数据源不存在: {name}"
            }
        
        # 关闭活跃连接
        if name in self.active_connections:
            try:
                self.active_connections[name].close()
            except:
                pass
            del self.active_connections[name]
        
        # 如果是 Excel 类型，清理对应的文件目录
        ds = self.datasources.get(name)
        if ds and ds.get('type') == 'excel':
            file_dir = ds.get('config', {}).get('file_dir')
            if file_dir and os.path.exists(file_dir):
                try:
                    shutil.rmtree(file_dir)
                    print(f"成功删除 Excel 数据源目录: {file_dir}")
                except Exception as e:
                    print(f"删除 Excel 数据源目录失败: {e}")

        # 清理对应的元数据目录 (refer/{name})
        from utils.schema_generator import safe_refer_name
        refer_dir = os.path.join("refer", safe_refer_name(name))
        if os.path.exists(refer_dir):
            try:
                shutil.rmtree(refer_dir)
                print(f"成功删除元数据目录: {refer_dir}")
            except Exception as e:
                print(f"删除元数据目录失败: {e}")

        # 删除配置
        del self.datasources[name]
        self._save_config()
        
        return {
            "success": True,
            "message": "数据源删除成功"
        }
    
    def get_datasource(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取数据源配置
        
        Args:
            name: 数据源名称
            
        Returns:
            数据源配置或 None
        """
        return self.datasources.get(name)
    
    def list_datasources(self) -> List[Dict[str, Any]]:
        """
        列出所有数据源
        
        Returns:
            数据源列表
        """
        results = []
        for storage_key, ds in self.datasources.items():
            # 处理可能的无效数据项
            if not isinstance(ds, dict):
                continue
            
            # 提取显示名称 (去掉 user_x: 前缀)
            display_name = storage_key
            if ":" in storage_key:
                display_name = storage_key.split(":", 1)[1]
                
            item = {
                "name": storage_key, # 唯一键，用于所有 API 调用
                "display_name": display_name, # 友好名称，用于 UI 展示
                "type": ds.get('type', 'unknown'),
                "knowledge_id": ds.get('knowledge_id', '0'),
                "owner_id": ds.get('owner_id'),
                "active": ds.get('active', True),
                "config": {}
            }
            
            ds_config = ds.get('config', {})
            if ds.get('type') != 'excel':
                item["config"] = {
                    "host": ds_config.get('host'),
                    "port": ds_config.get('port'),
                    "dbname": ds_config.get('dbname'),
                    "user": ds_config.get('user'),
                    "database_schema": ds_config.get('database_schema')
                }
            else:
                # 对于 Excel，直接使用整个 config
                item["config"] = ds_config
            results.append(item)
        return results
    
    def get_connector(self, name: str):
        """
        获取数据源连接器
        
        Args:
            name: 数据源名称
            
        Returns:
            数据源连接器实例
        """
        if name not in self.datasources:
            raise Exception(f"数据源不存在: {name}")
        
        ds_config = self.datasources[name]
        connector_class = self.SUPPORTED_TYPES[ds_config['type']]
        
        # 如果已有活跃连接，直接返回
        if name in self.active_connections:
            conn = self.active_connections[name]
            # 检查连接是否有效
            try:
                if hasattr(conn, 'conn'):
                    if conn.conn is not None:
                        # PostgreSQL
                        if hasattr(conn.conn, 'closed') and not conn.conn.closed:
                            return conn
                        # MySQL
                        elif hasattr(conn, '_is_connected') and conn._is_connected():
                            return conn
            except:
                pass
        
        # 创建新连接
        connector = connector_class(ds_config['config'])
        connector.connect()
        self.active_connections[name] = connector
        
        return connector
    
    def test_datasource(self, name: str) -> Dict[str, Any]:
        """
        测试数据源连接
        
        Args:
            name: 数据源名称
            
        Returns:
            测试结果
        """
        try:
            connector = self.get_connector(name)
            result = connector.test_connection()
            return result
        except Exception as e:
            return {
                "success": False,
                "message": f"测试失败: {str(e)}"
            }
    
    def get_tables(self, name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取数据源的表列表
        
        Args:
            name: 数据源名称
            schema: 数据库模式（可选）
            
        Returns:
            表列表
        """
        connector = self.get_connector(name)
        return connector.get_tables(schema)
    
    def get_table_columns(self, name: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息
        
        Args:
            name: 数据源名称
            schema: 数据库模式
            table: 表名
            
        Returns:
            列信息列表
        """
        connector = self.get_connector(name)
        return connector.get_table_columns(schema, table)

    def update_datasource_files(self, name: str, file_dir: str, files: List[str], file_configs: Dict[str, Any], skip_preprocess: bool = False) -> Dict[str, Any]:
        """
        更新 Excel 数据源的文件列表和配置

        Args:
            name: 数据源名称
            file_dir: 文件存储目录
            files: 文件名列表
            file_configs: 文件配置字典
            skip_preprocess: 是否跳过预处理（报表数据使用）

        Returns:
            操作结果
        """
        if name not in self.datasources:
            return {"success": False, "message": f"数据源不存在: {name}"}

        if self.datasources[name]['type'] != 'excel':
            return {"success": False, "message": f"数据源 {name} 不是 Excel 类型"}

        self.datasources[name]['config']['file_dir'] = file_dir
        self.datasources[name]['config']['files'] = files
        self.datasources[name]['config']['file_configs'] = file_configs
        # 📅 2026.03.19 新增：支持报表数据跳过预处理
        self.datasources[name]['config']['skip_preprocess'] = skip_preprocess
        self._save_config()

        return {"success": True, "message": "文件列表更新成功"}

    def update_datasource_knowledge_id(self, name: str, knowledge_id: str) -> Dict[str, Any]:
        """
        更新数据源关联的知识库 ID

        Args:
            name: 数据源名称
            knowledge_id: 新的知识库 ID

        Returns:
            操作结果
        """
        if name not in self.datasources:
            return {"success": False, "message": f"数据源不存在: {name}"}

        self.datasources[name]['knowledge_id'] = knowledge_id
        self._save_config()

        return {"success": True, "message": "知识库 ID 更新成功"}

    # 📅 2026.03.09 新增：跨 Schema 问数功能
    # 📝 变更说明：添加跨 Schema 相关方法

    def is_cross_schema(self, name: str) -> bool:
        """
        检查数据源是否为跨 Schema 模式

        Args:
            name: 数据源名称

        Returns:
            是否为跨 Schema 模式
        """
        ds = self.datasources.get(name)
        if ds:
            return ds.get('is_cross_schema', False)
        return False

    def get_datasource_schemas(self, name: str) -> List[str]:
        """
        获取数据源配置的 Schema 列表

        Args:
            name: 数据源名称

        Returns:
            Schema 名称列表
        """
        ds = self.datasources.get(name)
        if ds and ds.get('type') in ('pgsql', 'postgresql'):
            config = ds.get('config', {})

            # 如果是跨 Schema 模式且没有显式指定 schemas，则从数据库自动获取所有 Schema
            if config.get('is_cross_schema', False) and not config.get('schemas'):
                # 从数据库动态获取所有 Schema
                try:
                    connector = self.get_connector(name)
                    if hasattr(connector, 'get_schemas_list'):
                        schemas = connector.get_schemas_list()
                        logger.info(f"[跨 Schema] 自动获取到 {len(schemas)} 个 Schema: {schemas}")
                        return schemas
                except Exception as e:
                    logger.warning(f"[跨 Schema] 自动获取 Schema 失败，使用默认值：{e}")
                    return ['public']

            # 单 Schema 模式或已显式指定 schemas
            schemas = config.get('schemas')
            if schemas:
                return schemas
            return [config.get('database_schema', 'public')]
        return []

    def get_cross_schema_metadata(self, name: str) -> Dict[str, Any]:
        """
        获取跨 Schema 数据源的完整元数据

        Args:
            name: 数据源名称

        Returns:
            包含表名索引和详细元数据的字典
        """
        ds = self.datasources.get(name)
        if not ds:
            raise Exception(f"数据源不存在: {name}")

        if ds.get('type') not in ('pgsql', 'postgresql'):
            raise Exception(f"数据源 {name} 不是 PostgreSQL 类型")

        connector = self.get_connector(name)
        schemas = self.get_datasource_schemas(name)

        if hasattr(connector, 'get_cross_schema_metadata'):
            return connector.get_cross_schema_metadata(schemas)
        else:
            raise Exception("连接器不支持跨 Schema 元数据获取")


# 全局数据源管理器实例
datasource_manager = DataSourceManager()

