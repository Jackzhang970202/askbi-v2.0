"""
Excel 数据源连接器（虚拟，用于统一管理配置）
"""
from typing import Dict, Any, List, Optional

class ExcelConnector:
    """Excel 虚拟连接器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Excel 连接器
        
        Args:
            config: 配置字典
        """
        self.config = config
    
    def connect(self):
        """Excel 不需要建立实际连接"""
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """
        测试 Excel 连接（始终成功）
        """
        return {
            "success": True,
            "message": "Excel 配置有效"
        }
    
    def get_tables(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Excel 不需要表列表"""
        return []
    
    def get_table_columns(self, schema: str, table: str) -> List[Dict[str, Any]]:
        """Excel 不需要列信息"""
        return []
    
    def close(self):
        """Excel 不需要关闭"""
        pass

