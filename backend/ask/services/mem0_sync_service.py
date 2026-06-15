from __future__ import annotations

import json
from typing import Any, Dict, Optional

from agno.run import RunContext
from components.memory import MemoryPlugin


class Mem0SyncService:
    def __init__(self) -> None:
        self.plugin = MemoryPlugin()
        self._tools: dict[str, Any] = {}

    def _tool(self, user_id: str | None):
        key = user_id or "anonymous"
        if key not in self._tools:
            self._tools[key] = self.plugin.create_mem0_tools(user_id=key)
        return self._tools[key]

    def write_memory(self, memory: Dict[str, Any]) -> Optional[str]:
        user_id = str(memory.get("user_id") or "anonymous")
        session_id = str(memory.get("chat_id") or memory.get("session_id") or "session")
        content = str(memory.get("profile_text") or "").strip()
        if not content:
            return None
        tool = self._tool(user_id)
        run_context = RunContext(run_id=session_id, session_id=session_id, user_id=user_id)
        result = tool.add_memory(run_context, content)
        if isinstance(result, dict):
            return str(result.get("id") or result.get("memory_id") or result.get("uuid") or "") or "generated"
        if isinstance(result, str):
            text = result.strip()
            if not text:
                return None
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    return str(data.get("id") or data.get("memory_id") or data.get("uuid") or "") or "generated"
                return "generated"
            except Exception:
                return "generated"
        return "generated"

    def search(self, user_id: int | None, chat_id: str | None, query: str) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        tool = self._tool(str(user_id or "anonymous"))
        run_context = RunContext(run_id=chat_id or "session", session_id=chat_id or "session", user_id=str(user_id or "anonymous"))
        result = tool.search_memory(run_context, query)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
        if isinstance(result, str):
            try:
                data = json.loads(result)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
            except Exception:
                return []
        return []

    def update_memory(self, mem0_id: str, memory: Dict[str, Any]) -> bool:
        tool = self._tool(str(memory.get("user_id") or "anonymous"))
        updater = getattr(tool, "update_memory", None)
        if not callable(updater):
            return False
        run_context = RunContext(run_id=str(memory.get("chat_id") or memory.get("session_id") or "session"), session_id=str(memory.get("chat_id") or memory.get("session_id") or "session"), user_id=str(memory.get("user_id") or "anonymous"))
        updater(run_context, mem0_id, str(memory.get("profile_text") or ""))
        return True

    def delete_memory(self, mem0_id: str, user_id: str | None = None, session_id: str | None = None) -> bool:
        tool = self._tool(user_id or "anonymous")
        deleter = getattr(tool, "delete_memory", None)
        if not callable(deleter):
            return False
        run_context = RunContext(run_id=session_id or "session", session_id=session_id or "session", user_id=user_id or "anonymous")
        deleter(run_context, mem0_id)
        return True


mem0_sync_service = Mem0SyncService()
