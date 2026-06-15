"""自定义流程: 执行 custom_flow 类型的步骤序列。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def execute_custom_flow(
    flow_config: Dict[str, Any],
    task: str,
    llm_call: Callable[[List[Dict[str, str]]], str],
    get_agent_instructions: Callable[[str], str],
    progress_callback: Optional[Callable] = None,
) -> str:
    """执行自定义流程: 按步骤序列依次调用智能体。

    Args:
        flow_config: 流程配置，包含 name 和 steps
        task: 原始任务描述
        llm_call: LLM 调用函数
        get_agent_instructions: 获取智能体指令的函数
        progress_callback: 进度回调

    Returns:
        所有步骤结果的拼接
    """
    steps = flow_config.get("steps", [])
    if not steps:
        raise ValueError("自定义流程没有定义步骤")

    step_results: List[str] = []

    for i, step in enumerate(steps):
        step_name = step.get("step_name", f"step_{i}")
        agent_name = step.get("agent_name")
        instruction = step.get("instruction", task)

        if not agent_name:
            raise ValueError(f"步骤 {step_name} 缺少 agent_name")

        if progress_callback:
            progress_callback(f"流程步骤: {step_name}", "custom_flow_step")

        try:
            instructions = get_agent_instructions(agent_name)
        except Exception as e:
            raise RuntimeError(f"加载智能体 {agent_name} 失败: {e}")

        # 注入前序步骤结果作为上下文
        prev_context = ""
        if step_results:
            prev_context = "前序步骤结果:\n" + "\n".join(step_results) + "\n\n"

        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"{prev_context}{instruction}"},
        ]
        result = llm_call(messages)
        step_results.append(f"[{step_name}]: {result}")

    return "\n".join(step_results)
