from __future__ import annotations

import json
import os
from pathlib import Path

from agno.models.openai import OpenAIChat
import openai

if not hasattr(openai, "NOT_GIVEN"):
    try:
        from openai._types import NOT_GIVEN as _NOT_GIVEN
        openai.NOT_GIVEN = _NOT_GIVEN
    except Exception:
        pass


def _load_config() -> dict:
    config_path = Path(__file__).resolve().parent.parent / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_model() -> OpenAIChat:
    config = _load_config()
    # 环境变量优先（Docker 模式）
    return OpenAIChat(
        id=os.environ.get("ASKBI_MODEL", config.get("model", "qwen3.6-plus")),
        api_key=os.environ.get("ASKBI_API_KEY", config.get("api_key", "")),
        base_url=os.environ.get("ASKBI_BASE_URL", config.get("base_url", "")),
        temperature=0.1,
    )
