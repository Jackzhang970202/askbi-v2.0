import secrets
from typing import Dict, Any, Optional
from fastapi import Request

# ---------------------------
# Token 缓存 (token -> user_info)
# ---------------------------
TOKEN_CACHE: Dict[str, Dict[str, Any]] = {}

def generate_token() -> str:
    """生成随机 token"""
    return secrets.token_hex(32)

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """从请求中获取当前用户信息"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return TOKEN_CACHE.get(token)
    return None

def require_auth(request: Request) -> Dict[str, Any]:
    """要求认证，返回用户信息或抛出异常"""
    user = get_current_user(request)
    if not user:
        raise Exception("未登录或登录已过期")
    return user

def require_admin(request: Request) -> Dict[str, Any]:
    """要求超级管理员权限（只有 admin 能用户管理）"""
    user = require_auth(request)
    if user.get('role') != 'admin':
        raise Exception("需要超级管理员权限")
    return user

def is_admin_or_manager(user: Optional[Dict[str, Any]]) -> bool:
    """判断是否是管理员（admin 或 manager），可查看所有数据"""
    if not user:
        return False
    role = user.get('role', '')
    return role in ['admin', 'manager']

