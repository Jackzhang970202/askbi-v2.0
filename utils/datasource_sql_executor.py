"""
数据源 SQL 执行器
使用 datasource_manager 直连数据库执行 SQL，替代 MCP 方式
"""
from datasources.datasource_manager import datasource_manager
from typing import List, Dict, Any, Optional


def execute_sql(sql: str, datasource_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    执行 SQL 查询
    
    Args:
        sql: SQL 查询语句
        datasource_name: 数据源名称。如果为 None，则使用第一个可用的数据源
        
    Returns:
        查询结果列表
    """
    # 如果没有指定数据源，尝试获取第一个可用的数据源
    if datasource_name is None:
        datasources = datasource_manager.list_datasources()
        if not datasources:
            raise RuntimeError("没有可用的数据源。请先配置数据源。")
        # 获取第一个激活的数据源
        active_datasources = [ds for ds in datasources if ds.get('active', True)]
        if not active_datasources:
            raise RuntimeError("没有激活的数据源。")
        datasource_name = active_datasources[0]['name']
    
    # 获取数据源连接器
    try:
        connector = datasource_manager.get_connector(datasource_name)
    except Exception as e:
        raise RuntimeError(f"无法连接到数据源 '{datasource_name}': {str(e)}")
    
    # 执行 SQL
    try:
        result = connector.execute_query(sql)
        return result
    except Exception as e:
        raise RuntimeError(f"SQL 执行失败: {str(e)}")


# 为了兼容 mcp_bridge.run_sql 的调用方式
def run_sql(sql: str, datasource_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    执行 SQL 查询（兼容 mcp_bridge.run_sql 接口）
    
    Args:
        sql: SQL 查询语句
        datasource_name: 数据源名称（可选）
        
    Returns:
        查询结果列表
    """
    return execute_sql(sql, datasource_name)

