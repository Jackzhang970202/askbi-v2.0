"""
PostgreSQL 数据源连接器
"""
# 📅 2026.04.02 更新：延迟导入 psycopg2，避免在未安装时报错
from typing import Dict, Any, List, Optional
import json

# 延迟导入，只在需要时才导入
_psycopg2 = None
_psycopg2_extras = None

def _ensure_psycopg2():
    """确保 psycopg2 已导入"""
    global _psycopg2, _psycopg2_extras
    if _psycopg2 is None:
        try:
            import psycopg2 as ps2
            import psycopg2.extras as ps2_extras
            _psycopg2 = ps2
            _psycopg2_extras = ps2_extras
        except ImportError:
            raise ImportError("psycopg2 未安装。请运行: pip install psycopg2-binary")
    return _psycopg2, _psycopg2_extras


class PostgreSQLConnector:
    """PostgreSQL 数据库连接器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 PostgreSQL 连接器
        
        Args:
            config: 数据库配置字典，包含以下字段：
                - host: 主机地址
                - port: 端口号
                - dbname: 数据库名
                - user: 用户名
                - password: 密码
                - database_schema: 数据库模式（可选）
        """
        self.config = config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            psycopg2, psycopg2_extras = _ensure_psycopg2()
            self.conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                dbname=self.config['dbname'],
                user=self.config['user'],
                password=self.config['password']
            )
            self.cursor = self.conn.cursor(cursor_factory=psycopg2_extras.DictCursor)
            return True
        except Exception as e:
            raise Exception(f"PostgreSQL 连接失败: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试数据库连接
        
        Returns:
            包含连接测试结果的字典
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            # 执行简单查询测试连接
            self.cursor.execute("SELECT version();")
            version = self.cursor.fetchone()[0]
            
            return {
                "success": True,
                "message": "连接成功",
                "version": version
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接失败: {str(e)}"
            }
    
    def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取数据库表列表
        
        Args:
            schema: 数据库模式名（可选）
            
        Returns:
            表列表，每个表包含表名和模式名
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            if schema:
                query = """
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = %s
                    ORDER BY table_schema, table_name
                """
                self.cursor.execute(query, (schema,))
            else:
                query = """
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name
                """
                self.cursor.execute(query)
            
            results = self.cursor.fetchall()
            return [
                {
                    "schema": row[0],
                    "table": row[1],
                    "full_name": f"{row[0]}.{row[1]}"
                }
                for row in results
            ]
        except Exception as e:
            raise Exception(f"获取表列表失败: {str(e)}")
    
    def get_table_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息
        
        Args:
            schema: 数据库模式名
            table: 表名
            
        Returns:
            列信息列表
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            query = """
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """
            self.cursor.execute(query, (schema, table))
            results = self.cursor.fetchall()
            
            return [
                {
                    "name": row[0],
                    "type": row[1],
                    "max_length": row[2],
                    "nullable": row[3] == 'YES',
                    "default": row[4]
                }
                for row in results
            ]
        except Exception as e:
            raise Exception(f"获取列信息失败: {str(e)}")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询
        
        Args:
            query: SQL 查询语句
            params: 查询参数（可选）
            
        Returns:
            查询结果列表
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if self.cursor.description:
                results = self.cursor.fetchall()
                return [dict(row) for row in results]
            else:
                self.conn.commit()
                return []
        except Exception as e:
            if self.conn:
                self.conn.rollback()
            raise Exception(f"查询执行失败: {str(e)}")
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """支持上下文管理器"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()

    # 📅 2026.03.09 新增：跨 Schema 问数功能
    # 📝 变更说明：添加多 Schema 元数据获取方法

    def get_tables_for_schemas(self, schemas: List[str]) -> List[Dict[str, Any]]:
        """
        获取多个 Schema 的表列表

        Args:
            schemas: Schema 名称列表

        Returns:
            表列表，每个表包含表名、模式名和完整名称
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            if not schemas:
                return []

            # 构建 IN 查询
            placeholders = ','.join(['%s'] * len(schemas))
            query = f"""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema IN ({placeholders})
                ORDER BY table_schema, table_name
            """
            self.cursor.execute(query, tuple(schemas))
            results = self.cursor.fetchall()

            return [
                {
                    "schema": row[0],
                    "table": row[1],
                    "full_name": f"{row[0]}.{row[1]}"
                }
                for row in results
            ]
        except Exception as e:
            raise Exception(f"获取多 Schema 表列表失败: {str(e)}")

    def get_schemas_list(self) -> List[str]:
        """
        获取数据库中所有可用的 Schema 列表

        Returns:
            Schema 名称列表
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            query = """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """
            self.cursor.execute(query)
            results = self.cursor.fetchall()

            return [row[0] for row in results]
        except Exception as e:
            raise Exception(f"获取 Schema 列表失败: {str(e)}")

    def get_cross_schema_metadata(self, schemas: List[str]) -> Dict[str, Any]:
        """
        获取跨 Schema 的完整元数据

        Args:
            schemas: Schema 名称列表

        Returns:
            包含表名索引和详细元数据的字典
        """
        try:
            if not self.conn or self.conn.closed:
                self.connect()

            result = {
                "is_cross_schema": len(schemas) > 1,
                "schemas": schemas,
                "table_index": [],
                "tables": {}
            }

            # 获取所有表
            tables = self.get_tables_for_schemas(schemas)

            # 构建表名索引（轻量级）
            for table_info in tables:
                schema_name = table_info["schema"]
                table_name = table_info["table"]
                full_name = table_info["full_name"]

                # 获取表注释
                comment_query = """
                    SELECT obj_description((%s || '.' || %s)::regclass, 'pg_class')
                """
                try:
                    self.cursor.execute(comment_query, (schema_name, table_name))
                    comment_row = self.cursor.fetchone()
                    comment = comment_row[0] if comment_row and comment_row[0] else ""
                except:
                    comment = ""

                result["table_index"].append({
                    "full_name": full_name,
                    "schema": schema_name,
                    "table": table_name,
                    "comment": comment
                })

                # 获取列信息
                columns = self.get_table_columns(schema_name, table_name)

                # 获取样例数据
                sample_query = f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT 3'
                try:
                    self.cursor.execute(sample_query)
                    sample_rows = self.cursor.fetchall()
                    sample_data = [dict(row) for row in sample_rows]
                except:
                    sample_data = []

                result["tables"][full_name] = {
                    "schema": schema_name,
                    "table": table_name,
                    "comment": comment,
                    "columns": columns,
                    "sample_data": sample_data
                }

            return result
        except Exception as e:
            raise Exception(f"获取跨 Schema 元数据失败: {str(e)}")

