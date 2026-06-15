"""团队上下文: 共享对话历史、中间结果、交互记录。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class TeamContext:
    """团队执行上下文，存储成员交互历史和中间结果。"""

    def __init__(self):
        self._interactions: List[Dict[str, Any]] = []
        self._member_results: Dict[str, List[str]] = {}

    def add_interaction(self, member_key: str, task: str, result: str) -> None:
        """记录一次成员交互。"""
        self._interactions.append({
            "member_key": member_key,
            "task": task,
            "result": result,
        })
        if member_key not in self._member_results:
            self._member_results[member_key] = []
        self._member_results[member_key].append(result)

    def get_relevant_history(self, member_key: str) -> str:
        """获取与指定成员相关的历史交互摘要。"""
        parts = []
        for i, interaction in enumerate(self._interactions):
            if interaction["member_key"] == member_key:
                parts.append(f"[第{i+1}轮] 任务: {interaction['task'][:100]}...\n结果: {interaction['result'][:200]}...")
        return "\n".join(parts) if parts else ""

    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有交互记录。"""
        return list(self._interactions)

    def get_member_result(self, member_key: str) -> Optional[str]:
        """获取指定成员的最新结果。"""
        results = self._member_results.get(member_key)
        return results[-1] if results else None

    def summary(self) -> str:
        """生成所有交互的摘要。"""
        parts = []
        for interaction in self._interactions:
            parts.append(f"[{interaction['member_key']}]: {interaction['result'][:300]}")
        return "\n---\n".join(parts)
