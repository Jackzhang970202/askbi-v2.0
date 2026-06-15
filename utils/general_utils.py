import re
import textwrap
import asyncio
from typing import Any


def print_banner(title: str, border: str = "="):
    """
    打印横幅
    """
    width = 80
    print("\n" + f" {title} ".center(width, border) + "\n")


def extract_python_code(text: str):
    """
    提取Python代码
    """
    pattern = re.compile(r"```(?:python)?\s*([\s\S]*?)```", re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(text)
    return [m.strip() for m in matches if m.strip()]


def check_sql_safety(sql_code: str) -> bool:
    """
    检查SQL代码是否安全，只允许SELECT查询
    """
    # 定义不允许的SQL关键词
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE'
    ]
    
    # 转换为小写进行不区分大小写的检查
    sql_lower = sql_code.lower()
    
    # 检查是否包含危险关键词
    for keyword in dangerous_keywords:
        if keyword.lower() in sql_lower:
            print(f"[SECURITY] 检测到危险SQL关键词: {keyword}")
            return False
    
    # 检查是否以SELECT开头（允许SELECT查询）
    if not sql_lower.strip().startswith('select'):
        print("[SECURITY] SQL语句必须以SELECT开头")
        return False
    
    return True


def check_python_code_safety(code: str) -> bool:
    """
    检查Python代码中的SQL语句是否安全
    """
    # 定义不允许的SQL关键词
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE'
    ]
    
    # 转换为小写进行不区分大小写的检查
    code_lower = code.lower()
    
    # 检查是否包含危险关键词
    for keyword in dangerous_keywords:
        if keyword.lower() in code_lower:
            print(f"[SECURITY] 检测到危险SQL关键词: {keyword}")
            return False
    
    return True


def reply_to_text(reply) -> str:
    """
    将回复转换为文本
    """
    if isinstance(reply, str):
        return reply
    for attr in ("content", "text"):
        try:
            value = getattr(reply, attr)
            if isinstance(value, str) and value:
                return value
        except Exception:
            pass
    try:
        messages = getattr(reply, "messages", None)
        if isinstance(messages, (list, tuple)):
            parts = []
            for m in messages:
                source = getattr(m, "source", "")
                if source == "user":
                    continue
                for attr in ("content", "text"):
                    v = getattr(m, attr, None)
                    if isinstance(v, str) and v:
                        parts.append(v)
                        break
                else:
                    parts.append(str(m))
            if parts:
                return "\n".join(parts)
    except Exception:
        pass
    try:
        return str(reply)
    except Exception:
        return ""


async def connectivity_preflight(model_client) -> None:
    """
    模型连接性测试
    """
    from autogen_agentchat.agents import AssistantAgent
    
    print_banner("Preflight: model connectivity test")
    probe = AssistantAgent(
        name="probe",
        model_client=model_client,
        system_message="You are a helpful assistant. Reply with a short 'pong'."
    )
    try:
        reply = await probe.run(task="ping")
        print(f"[PRELIGHT] success")
    except Exception as e:
        print(f"[WARN] Preflight failed: {e}")
