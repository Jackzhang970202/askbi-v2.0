from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.db_utils import db_utils


class SessionService:
    def create_or_update_session(
        self,
        chat_id: str,
        knowledge_id: str = "0",
        datasource_name: Optional[str] = None,
        user_id: Optional[int] = None,
        context_type: str = "general",
        context_ref_id: Optional[str] = None,
        context_ref_name: Optional[str] = None,
    ) -> bool:
        return db_utils.insert_chat_session(
            chat_id,
            knowledge_id,
            datasource_name,
            user_id,
            context_type,
            context_ref_id,
            context_ref_name,
        )

    def update_context(
        self,
        chat_id: str,
        context_type: str,
        context_ref_id: Optional[str] = None,
        context_ref_name: Optional[str] = None,
        datasource_name: Optional[str] = None,
    ) -> bool:
        return db_utils.update_chat_session_context(chat_id, context_type, context_ref_id, context_ref_name, datasource_name)

    def clear_context(self, chat_id: str) -> bool:
        return db_utils.clear_chat_session_context(chat_id)

    def normalize_context(self, session: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not session:
            return None
        context_type = session.get("context_type")
        if context_type:
            return session
        chat_id = str(session.get("chat_id", ""))
        datasource_name = session.get("datasource_name")
        if chat_id.startswith("excel_"):
            session["context_type"] = "excel"
            session["context_ref_name"] = datasource_name
        elif chat_id.startswith("team_"):
            session["context_type"] = "team"
            session["context_ref_name"] = datasource_name
        elif datasource_name and datasource_name != "__excel__":
            session["context_type"] = "bi"
            session["context_ref_name"] = datasource_name
        else:
            session["context_type"] = "general"
            session["context_ref_name"] = None
        session.setdefault("context_ref_id", None)
        return session

    def get_context_payload(self, session: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = self.normalize_context(session) or {}
        return {
            "type": normalized.get("context_type", "general"),
            "ref_id": normalized.get("context_ref_id"),
            "ref_name": normalized.get("context_ref_name"),
            "datasource_name": normalized.get("datasource_name"),
        }

    def is_excel_context(self, session: Optional[Dict[str, Any]]) -> bool:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_type") == "excel"

    def is_team_context(self, session: Optional[Dict[str, Any]]) -> bool:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_type") == "team"

    def is_bi_context(self, session: Optional[Dict[str, Any]]) -> bool:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_type") == "bi"

    def is_general_context(self, session: Optional[Dict[str, Any]]) -> bool:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_type") == "general"

    def get_context_type(self, session: Optional[Dict[str, Any]]) -> str:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_type", "general")

    def get_context_ref_name(self, session: Optional[Dict[str, Any]]) -> Optional[str]:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_ref_name")

    def get_context_ref_id(self, session: Optional[Dict[str, Any]]) -> Optional[str]:
        normalized = self.normalize_context(session) or {}
        return normalized.get("context_ref_id")

    def get_datasource_name(self, session: Optional[Dict[str, Any]]) -> Optional[str]:
        normalized = self.normalize_context(session) or {}
        return normalized.get("datasource_name")

    def get_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        return self.normalize_context(db_utils.get_safe_chat_session(chat_id))

    def list_sessions(self, user_id: Optional[int], is_admin: bool) -> List[Dict[str, Any]]:
        return [self.normalize_context(item) for item in db_utils.list_safe_chat_sessions_by_user(user_id, is_admin)]

    def save_message(self, chat_id: str, role: str, content: str, structured_data: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> bool:
        return db_utils.insert_message(chat_id, role, content, structured_data, user_id)

    def get_messages(self, chat_id: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return db_utils.get_chat_messages(chat_id, user_id)

    def save_request_record(
        self,
        chat_id: str,
        knowledge_id: str,
        user_question: str,
        retrieved_knowledge: Dict[str, Any],
        generated_sql: Optional[str],
        execution_result: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> bool:
        return db_utils.insert_request_record(
            chat_id=chat_id,
            knowledge_id=knowledge_id,
            user_question=user_question,
            retrieved_knowledge=retrieved_knowledge,
            generated_sql=generated_sql,
            execution_result=execution_result,
            round_number=db_utils.get_next_round_number(chat_id),
            user_id=user_id,
        )


session_service = SessionService()
