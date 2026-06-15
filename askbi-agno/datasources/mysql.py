"""
MySQL 数据源连接器
"""
# 📅 2026.04.02 更新：延迟导入 pymysql，避免在未安装时报错
from typing import Dict, Any, List, Optional

# 延迟导入，只在需要时才导入
_pymysql = None

def _ensure_pymysql():
    """确保 pymysql 已导入"""
    global _pymysql
    if _pymysql is None:
        try:
            import pymysql as pm
            _pymysql = pm
        except ImportError:
            raise ImportError("pymysql 未安装。请运行: pip install pymysql")
    return _pymysql


class MySQLConnector:
    """MySQL 数据库连接器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 MySQL 连接器
        
        Args:
            config: 数据库配置字典，包含以下字段：
                - host: 主机地址
                - port: 端口号
                - dbname: 数据库名
                - user: 用户名
                - password: 密码
        """
        self.config = config
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            pymysql = _ensure_pymysql()
            # 使用默认的 TupleCursor，我们手动转换为字典以确保最大的兼容性和可控性
            self.conn = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['dbname'],
                user=self.config['user'],
                password=self.config['password'],
                charset='utf8mb4'
            )
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            raise Exception(f"MySQL 连接失败: {str(e)}")
    
    def _is_connected(self):
        """检查连接是否有效"""
        try:
            if self.conn is None:
                return False
            self.conn.ping(reconnect=False)
            return True
        except:
            return False

    def _fetch_all_as_dict(self):
        """
        将当前游标中的结果集转换为字典列表。
        字段名强制转换为小写，以避免不同操作系统/配置下的大小写差异。
        """
        if not self.cursor.description:
            return []
        # 获取列名并转为小写
        columns = [col[0].lower() for col in self.cursor.description]
        results = []
        for row in self.cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试数据库连接
        
        Returns:
            包含连接测试结果的字典
        """
        try:
            if not self._is_connected():
                self.connect()
            
            # 执行简单查询测试连接
            self.cursor.execute("SELECT VERSION() as version")
            # 这里我们也使用安全转换，虽然只有一行
            columns = [col[0].lower() for col in self.cursor.description]
            row = self.cursor.fetchone()
            result = dict(zip(columns, row)) if row else {}
            
            version = result.get('version', "Unknown")
            
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
            schema: 数据库名
            
        Returns:
            表列表
        """
        try:
            if not self._is_connected():
                self.connect()
            
            db_name = schema or self.config['dbname']
            # 使用 information_schema 获取表信息，不使用别名以减少不确定性
            query = """
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
                ORDER BY table_schema, table_name
            """
            self.cursor.execute(query, (db_name,))
            rows = self._fetch_all_as_dict()
            
            return [
                {
                    "schema": row.get('table_schema'),
                    "table": row.get('table_name'),
                    "full_name": f"{row.get('table_schema')}.{row.get('table_name')}"
                }
                for row in rows
            ]
        except Exception as e:
            raise Exception(f"获取表列表失败: {str(e)}")
    
    def get_table_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """
        获取表的列信息
        
        Args:
            schema: 数据库名
            table: 表名
            
        Returns:
            列信息列表
        """
        try:
            if not self._is_connected():
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
            rows = self._fetch_all_as_dict()
            
            return [
                {
                    "name": row.get('column_name'),
                    "type": row.get('data_type'),
                    "max_length": row.get('character_maximum_length'),
                    "nullable": row.get('is_nullable') == 'YES',
                    "default": row.get('column_default')
                }
                for row in rows
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
            if not self._is_connected():
                self.connect()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if self.cursor.description:
                return self._fetch_all_as_dict()
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
