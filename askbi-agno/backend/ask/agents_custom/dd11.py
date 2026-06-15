# 自动生成 - 通过管理页面修改，请勿手动编辑
from openai import OpenAI
from core import _load_config

INSTRUCTIONS = """
11
"""


def run(user_input: str, context: dict = None) -> str:
    """执行智能体任务。"""
    conf = _load_config()
    client = OpenAI(api_key=conf["api_key"], base_url=conf["base_url"], timeout=90.0)
    model = conf["model"]

    system_prompt = INSTRUCTIONS
    if context and context.get("skill_prompt"):
        system_prompt = f"{system_prompt}\n{context['skill_prompt']}"

    messages = [{"role": "system", "content": system_prompt}]
    if context and context.get("history"):
        messages.extend(context["history"])
    messages.append({"role": "user", "content": user_input})

    result = client.chat.completions.create(
        model=model, messages=messages, temperature=0.1,
        extra_body={"enable_thinking": False},
    )
    return (result.choices[0].message.content or "").strip()
