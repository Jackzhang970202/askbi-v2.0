import json
import os
from pathlib import Path


def _find_project_root() -> Path:
    """
    查找项目根目录（以存在 config.json 为准），避免因为启动目录不同导致 FileNotFoundError。
    搜索顺序：
    1) 从当前文件所在目录向上搜索
    2) 从当前工作目录向上搜索
    """
    # 1) 以当前文件为起点向上找
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parent.parents]:
        if (p / "config.json").exists():
            return p

    # 2) 以 cwd 为起点向上找
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / "config.json").exists():
            return p

    # 兜底：回到“config/ 的上级目录”（即便不存在，也能给出明确路径）
    return here.parent.parent


def _get_config_path() -> Path:
    return _find_project_root() / "config.json"


def _get_rag_config_path() -> Path:
    return _find_project_root() / "config_rag.json"

def get_db_config():
    """
    获取数据库配置
    """
    try:
        config_path = _get_config_path()
        if not config_path.exists():
            print(f"[ERROR] Config file not found at: {config_path}")
            return {}
        with open(config_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        db_conf = conf.get("db_config", {})
        return db_conf
    except Exception as e:
        print(f"[ERROR] Failed to load db config: {e}")
        return {}


def db_config_missing() -> bool:
    """
    检查数据库配置是否缺失
    """
    db = get_db_config()
    return not all(k in db for k in ["host", "port", "dbname", "user", "password"])


def load_model_client():
    """
    加载模型客户端
    """
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    
    config_path = _get_config_path()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path} (cwd={Path.cwd().resolve()})")

    with open(config_path, "r", encoding="utf-8") as f:
        conf = json.load(f)
    
    return OpenAIChatCompletionClient(
        model=conf["model"],
        api_key=conf["api_key"],
        base_url=conf["base_url"],
        model_info={
            "vision": False,
            "function_calling": True,
            "json_output": True,
            "family": "unknown", 
            "multiple_system_messages": True,
            "temperature": 0.1,
            "max_tokens": 15000,
            "context_length": 15000 
        },
        extra_body={"enable_thinking": False}
    )


def load_rag_config():
    """
    加载RAG配置文件
    """
    try:
        rag_path = _get_rag_config_path()
        if not rag_path.exists():
            raise FileNotFoundError(f"RAG Config file not found at: {rag_path}")
            
        with open(rag_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        return conf
    except Exception as e:
        print(f"[WARN] Failed to load RAG config: {e}")
        return {
            "api_url": "",
            "model": "qwen3-max",
            "headers": {
                "Authorization": "Bearer ragflow-3_WrSnL0y4kD2Q8UMju6Uc4X4DNo_Ew8TXHOVk5RRSs",
                "Content-Type": "application/json"
            },
            "stream": False
        }

