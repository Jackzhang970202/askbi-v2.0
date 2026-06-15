from typing import List
import re


def extract_sql_from_python(code: str) -> List[str]:
    """
    Extract SQL statements from a Python script.
    Looks for sql = "...", query = "...", or run_sql("...") patterns.
    Returns a list of SQL statements.
    """
    if not code:
        return []
    
    sql_statements = []
    
    # 首先尝试匹配 run_sql(...) 模式
    # 使用捕获组获取引号类型，然后匹配对应的闭合引号
    run_sql_pattern = r'run_sql\s*\(\s*(["\'\"]{1,3})(.*?)\1\s*\)'
    run_sql_matches = re.finditer(run_sql_pattern, code, re.DOTALL | re.IGNORECASE)
    
    for match in run_sql_matches:
        sql = match.group(2).strip()
        if sql:
            sql_statements.append(sql)
    
    if sql_statements:
        return sql_statements
    
    # 然后尝试匹配 sql = ... 或 query = ... 模式
    var_pattern = r'(?:sql|query)\s*=\s*(["\'\"]{1,3})(.*?)\1'
    var_match = re.search(var_pattern, code, re.DOTALL | re.IGNORECASE)
    if var_match:
        sql = var_match.group(2).strip()
        if sql:
            return [sql]
    
    # Pattern 4: If code itself looks like SQL (starts with SELECT)
    if code.strip().upper().startswith("SELECT"):
        return [code.strip()]

    return []  # Return empty list if no SQL found instead of the whole code


def extract_tables_from_sql(sql_code: str) -> List[str]:
    """
    Extract table names from SQL code.
    Handles 'FROM table', 'JOIN table', 'FROM "schema"."table"' etc.
    """
    if not sql_code:
        return []
    
    tables = []
    # Pattern to match FROM/JOIN followed by table name
    # Table name can be identifier, "identifier", identifier.identifier, "id"."id"
    # Regex: (FROM|JOIN)\s+([a-zA-Z0-9_"./]+)
    # Note: This is a simplified regex and might match subqueries alias or functions, but sufficient for simple cases
    pattern = re.compile(r'(?:FROM|JOIN)\s+((?:[a-zA-Z0-9_"]+(?:\.[a-zA-Z0-9_"]+)?))', re.IGNORECASE)
    matches = pattern.findall(sql_code)
    
    for table in matches:
        # Clean up quotes
        clean_table = table.replace('"', '').strip()
        if clean_table and clean_table.upper() not in ['SELECT', 'WHERE', 'GROUP', 'ORDER', 'LIMIT', 'LATERAL']:
            if clean_table not in tables:
                tables.append(clean_table)
    return tables
