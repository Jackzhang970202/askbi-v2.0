from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("askbi.memory_service")

from backend.ask.services.memory_extractor import memory_extractor
from backend.ask.services.mem0_sync_service import mem0_sync_service
from utils.db_utils import db_utils


class MemoryService:
    def build_context(self, user_id: Optional[int], chat_id: Optional[str], mode: str = "") -> str:
        parts: list[str] = []
        query = f"会话={chat_id or ''}; 模式={mode}; 请返回与当前问题最相关的用户画像与会话记忆"
        logger.info("memory context search start: chat_id=%s user_id=%s mode=%s", chat_id, user_id, mode)
        results = mem0_sync_service.search(user_id=user_id, chat_id=chat_id, query=query)
        logger.info("memory context search result count=%s", len(results))
        if results:
            parts.append("## Mem0 检索记忆")
            for item in results[:8]:
                text = item.get("memory") or item.get("text") or item.get("content") or json.dumps(item, ensure_ascii=False)
                parts.append(f"- {text}")
        if chat_id:
            session_memories = db_utils.list_session_memories(chat_id, user_id=user_id, is_admin=False, status="active")
            if session_memories:
                parts.append("## 会话记忆映射")
                for item in session_memories[:8]:
                    parts.append(f"- [{item.get('memory_kind')}] {item.get('profile_text')}")
        if user_id is not None:
            user_memories = db_utils.list_user_memories(user_id=user_id, status="active")
            if user_memories:
                parts.append("## 用户画像映射")
                for item in user_memories[:8]:
                    parts.append(f"- [{item.get('memory_kind')}] {item.get('profile_text')}")
        if not parts:
            return ""
        return "\n".join(parts)[:4000]

    def apply_to_question(self, question: str, user_id: Optional[int], chat_id: Optional[str], mode: str = "") -> str:
        context = self.build_context(user_id, chat_id, mode)
        if not context:
            return question
        return f"{context}\n\n## 当前用户问题\n{question}"

    def schedule_extract_after_turn(self, payload: Dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.extract_after_turn(payload))
        except RuntimeError:
            try:
                asyncio.run(self.extract_after_turn(payload))
            except Exception:
                pass

    async def extract_after_turn(self, payload: Dict[str, Any]) -> None:
        await asyncio.to_thread(self._extract_after_turn_sync, payload)

    def _extract_after_turn_sync(self, payload: Dict[str, Any]) -> None:
        user_id = payload.get("user_id")
        chat_id = payload.get("chat_id")
        try:
            logger.info("memory extract start: chat_id=%s user_id=%s mode=%s", chat_id, user_id, payload.get("mode"))
            extracted = memory_extractor.extract_after_turn(payload)
            logger.info("memory extract result: user=%s session=%s", len(extracted.get("user_memories", [])), len(extracted.get("session_memories", [])))
            for item in extracted.get("user_memories", []):
                if user_id is None:
                    continue
                item.update({
                    "user_id": user_id,
                    "source_chat_id": chat_id,
                    "source_message_ids": payload.get("source_message_ids") or [],
                })
                logger.info("memory user write start: kind=%s summary=%s", item.get("memory_kind"), item.get("summary"))
                mem0_id = mem0_sync_service.write_memory(item)
                if not mem0_id:
                    raise RuntimeError("mem0 用户画像写入失败")
                logger.info("memory user write success: mem0_id=%s", mem0_id)
                item["mem0_id"] = mem0_id
                memory_id = db_utils.upsert_user_memory(item)
                db_utils.insert_memory_event(user_id, chat_id, "user", "upsert", item, memory_id)
            for item in extracted.get("session_memories", []):
                if not chat_id:
                    continue
                item.update({
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "source_message_ids": payload.get("source_message_ids") or [],
                })
                logger.info("memory session write start: kind=%s summary=%s chat_id=%s", item.get("memory_kind"), item.get("summary"), chat_id)
                mem0_id = mem0_sync_service.write_memory(item)
                if not mem0_id:
                    raise RuntimeError("mem0 会话记忆写入失败")
                logger.info("memory session write success: mem0_id=%s chat_id=%s", mem0_id, chat_id)
                item["mem0_id"] = mem0_id
                memory_id = db_utils.upsert_session_memory(item)
                db_utils.insert_memory_event(user_id, chat_id, "session", "upsert", item, memory_id)
        except Exception as exc:
            logger.exception("memory extract failed: chat_id=%s user_id=%s", chat_id, user_id)
            try:
                db_utils.insert_memory_event(user_id, chat_id, "memory", "error", {"error": str(exc)})
            except Exception:
                pass

    def list_user_memories(self, user: Dict[str, Any], status: str = "active", memory_kind: Optional[str] = None, keyword: Optional[str] = None, target_user_id: Optional[int] = None) -> list[dict[str, Any]]:
        is_admin = user.get("role") in ("admin", "manager")
        return db_utils.list_user_memories(user.get("id"), is_admin=is_admin, status=status, memory_kind=memory_kind, keyword=keyword, target_user_id=target_user_id)

    def list_session_memories(self, chat_id: str, user: Dict[str, Any], status: str = "active") -> list[dict[str, Any]]:
        is_admin = user.get("role") in ("admin", "manager")
        return db_utils.list_session_memories(chat_id, user.get("id"), is_admin=is_admin, status=status)

    def update_memory(self, scope: str, memory_id: int, user: Dict[str, Any], data: Dict[str, Any]) -> bool:
        is_admin = user.get("role") in ("admin", "manager")
        if scope == "user":
            items = db_utils.list_user_memories(user.get("id"), is_admin=is_admin)
            target = next((item for item in items if item.get("id") == memory_id), None)
            if target and target.get("mem0_id"):
                payload = {**target, **data, "user_id": user.get("id")}
                if not mem0_sync_service.update_memory(target.get("mem0_id"), payload):
                    raise RuntimeError("mem0 用户画像更新失败")
            ok = db_utils.update_memory(scope, memory_id, user.get("id"), data, is_admin=is_admin)
            db_utils.insert_memory_event(user.get("id"), None, scope, "update", {"id": memory_id, "data": data})
            return ok
        chat_id = data.get("chat_id")
        if not chat_id:
            raise ValueError("session 记忆更新需要 chat_id")
        return self.update_session_memory(memory_id, chat_id, user, data)

    def update_session_memory(self, memory_id: int, chat_id: str, user: Dict[str, Any], data: Dict[str, Any]) -> bool:
        is_admin = user.get("role") in ("admin", "manager")
        items = db_utils.list_session_memories(chat_id, user.get("id"), is_admin=is_admin, status="active")
        target = next((item for item in items if item.get("id") == memory_id), None)
        if target and target.get("mem0_id"):
            payload = {**target, **data, "user_id": user.get("id"), "chat_id": chat_id}
            if not mem0_sync_service.update_memory(target.get("mem0_id"), payload):
                raise RuntimeError("mem0 会话记忆更新失败")
        ok = db_utils.update_memory("session", memory_id, user.get("id"), data, is_admin=is_admin)
        db_utils.insert_memory_event(user.get("id"), chat_id, "session", "update", {"id": memory_id, "data": data})
        return ok

    def archive_memory(self, scope: str, memory_id: int, user: Dict[str, Any]) -> bool:
        is_admin = user.get("role") in ("admin", "manager")
        ok = db_utils.archive_memory(scope, memory_id, user.get("id"), is_admin=is_admin)
        db_utils.insert_memory_event(user.get("id"), None, scope, "archive", {"id": memory_id})
        return ok

    def delete_memory(self, scope: str, memory_id: int, user: Dict[str, Any]) -> bool:
        is_admin = user.get("role") in ("admin", "manager")
        ok = db_utils.delete_memory(scope, memory_id, user.get("id"), is_admin=is_admin)
        db_utils.insert_memory_event(user.get("id"), None, scope, "delete", {"id": memory_id})
        return ok

    def clear_session_memory(self, chat_id: str, user_id: Optional[int] = None) -> bool:
        ok = db_utils.clear_session_memories(chat_id, user_id=user_id)
        db_utils.insert_memory_event(user_id, chat_id, "session", "archive", {"chat_id": chat_id, "reason": "session_deleted"})
        return ok

    def list_events(self, user: Dict[str, Any], chat_id: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
        is_admin = user.get("role") in ("admin", "manager")
        return db_utils.list_memory_events(user.get("id"), is_admin=is_admin, chat_id=chat_id, limit=limit)


memory_service = MemoryService()
