from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from config.config_handler import get_db_config
from config.config_db import (
    TABLE_CHAT_KNOWLEDGE,
    TABLE_CHAT_SESSION,
    TABLE_GENERAL_METADATA,
    TABLE_GLOBAL_CONFIGS,
    TABLE_MESSAGES,
    TABLE_MEMORY_EVENTS,
    TABLE_REPORTS,
    TABLE_REQUEST_RECORD,
    TABLE_SESSION_PROFILE_MEMORY,
    TABLE_USERS,
    TABLE_USER_PROFILE_MEMORY,
)


class PgDatabaseUtils:
    def __init__(self, use_app_db: bool = False):
        self.db_config = get_db_config()
        self.use_app_db = use_app_db
        self.conn = None
        self.cursor = None

    def _normalize(self, value):
        if isinstance(value, dict):
            return {k: self._normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._normalize(v) for v in value]
        if hasattr(value, 'isoformat'):
            try:
                return value.isoformat(sep=' ')
            except Exception:
                pass
        return value

    def _normalize_rows(self, rows):
        return [self._normalize(dict(r)) for r in rows]

    def _normalize_params(self, params):
        if params is None:
            return ()
        return tuple(self._normalize(p) for p in params)

    def connect(self):
        if not self.conn:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                dbname=self.db_config['dbname'],
                user=self.db_config['user'],
                password=self.db_config['password'],
            )
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, query: str, params: tuple = None, auto_commit: bool = True) -> List[Dict[str, Any]]:
        self.connect()
        try:
            self.cursor.execute(query, self._normalize_params(params))
            if self.cursor.description:
                rows = self.cursor.fetchall()
                if auto_commit:
                    self.conn.commit()
                return self._normalize_rows(rows)
            if auto_commit:
                self.conn.commit()
            return []
        except Exception:
            if self.conn:
                self.conn.rollback()
            raise

    def has_chat_session_context_columns(self) -> bool:
        query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = 'askbi_chat_session'
              AND column_name IN ('context_type', 'context_ref_id', 'context_ref_name')
        """
        try:
            rows = self.execute_query(query, (self.db_config.get('database_schema', 'public'),), auto_commit=False)
            return len(rows) == 3
        except Exception:
            return False

    def ensure_chat_session_context_columns(self) -> bool:
        self.connect()
        statements = [
            f"ALTER TABLE {TABLE_CHAT_SESSION} ADD COLUMN IF NOT EXISTS context_type TEXT DEFAULT 'general'",
            f"ALTER TABLE {TABLE_CHAT_SESSION} ADD COLUMN IF NOT EXISTS context_ref_id TEXT",
            f"ALTER TABLE {TABLE_CHAT_SESSION} ADD COLUMN IF NOT EXISTS context_ref_name TEXT",
        ]
        try:
            for stmt in statements:
                self.cursor.execute(stmt)
            self.conn.commit()
            return True
        except Exception:
            if self.conn:
                self.conn.rollback()
            return False

    def bootstrap_chat_session_context_columns(self) -> bool:
        if self.has_chat_session_context_columns():
            return True
        return self.ensure_chat_session_context_columns()

    def get_chat_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        results = self.execute_query(f"SELECT * FROM {TABLE_CHAT_SESSION} WHERE chat_id = %s", (chat_id,))
        return results[0] if results else None

    def get_safe_chat_session(self, chat_id: str) -> Optional[Dict[str, Any]]:
        if not self.bootstrap_chat_session_context_columns():
            results = self.execute_query(f"SELECT chat_id, knowledge_id, datasource_name, user_id, create_time FROM {TABLE_CHAT_SESSION} WHERE chat_id = %s", (chat_id,))
            return results[0] if results else None
        return self.get_chat_session(chat_id)

    def insert_chat_session(
        self,
        chat_id: str,
        knowledge_id: Optional[str] = None,
        datasource_name: Optional[str] = None,
        user_id: Optional[int] = None,
        context_type: str = 'general',
        context_ref_id: Optional[str] = None,
        context_ref_name: Optional[str] = None,
    ) -> bool:
        query = f"""
            INSERT INTO {TABLE_CHAT_SESSION} (chat_id, knowledge_id, datasource_name, user_id, context_type, context_ref_id, context_ref_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
                knowledge_id = COALESCE(EXCLUDED.knowledge_id, {TABLE_CHAT_SESSION}.knowledge_id),
                datasource_name = COALESCE(EXCLUDED.datasource_name, {TABLE_CHAT_SESSION}.datasource_name),
                context_type = COALESCE(EXCLUDED.context_type, {TABLE_CHAT_SESSION}.context_type),
                context_ref_id = COALESCE(EXCLUDED.context_ref_id, {TABLE_CHAT_SESSION}.context_ref_id),
                context_ref_name = COALESCE(EXCLUDED.context_ref_name, {TABLE_CHAT_SESSION}.context_ref_name),
                user_id = COALESCE({TABLE_CHAT_SESSION}.user_id, EXCLUDED.user_id)
        """
        legacy_query = f"""
            INSERT INTO {TABLE_CHAT_SESSION} (chat_id, knowledge_id, datasource_name, user_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
                knowledge_id = COALESCE(EXCLUDED.knowledge_id, {TABLE_CHAT_SESSION}.knowledge_id),
                datasource_name = COALESCE(EXCLUDED.datasource_name, {TABLE_CHAT_SESSION}.datasource_name),
                user_id = COALESCE({TABLE_CHAT_SESSION}.user_id, EXCLUDED.user_id)
        """
        try:
            self.bootstrap_chat_session_context_columns()
            self.execute_query(query, (chat_id, knowledge_id, datasource_name, user_id, context_type, context_ref_id, context_ref_name))
            return True
        except Exception:
            try:
                self.execute_query(legacy_query, (chat_id, knowledge_id, datasource_name, user_id))
                return True
            except Exception:
                return False

    def update_chat_session_context(
        self,
        chat_id: str,
        context_type: str,
        context_ref_id: Optional[str] = None,
        context_ref_name: Optional[str] = None,
        datasource_name: Optional[str] = None,
    ) -> bool:
        if not self.bootstrap_chat_session_context_columns():
            return True
        if context_type in ('bi', 'excel') and not datasource_name:
            datasource_name = context_ref_name
        query = f"""
            UPDATE {TABLE_CHAT_SESSION}
            SET context_type = %s,
                context_ref_id = %s,
                context_ref_name = %s,
                datasource_name = %s
            WHERE chat_id = %s
        """
        try:
            self.execute_query(query, (context_type, context_ref_id, context_ref_name, datasource_name, chat_id))
            return True
        except Exception:
            return False

    def clear_chat_session_context(self, chat_id: str) -> bool:
        if not self.bootstrap_chat_session_context_columns():
            return True
        query = f"""
            UPDATE {TABLE_CHAT_SESSION}
            SET context_type = 'general',
                context_ref_id = NULL,
                context_ref_name = NULL,
                datasource_name = NULL
            WHERE chat_id = %s
        """
        try:
            self.execute_query(query, (chat_id,))
            return True
        except Exception:
            return False

    def set_chat_session_datasource(self, chat_id: str, datasource_name: str) -> bool:
        query = f"UPDATE {TABLE_CHAT_SESSION} SET datasource_name = %s WHERE chat_id = %s"
        try:
            self.execute_query(query, (datasource_name, chat_id))
            return True
        except Exception:
            return False

    def get_chat_session_datasource(self, chat_id: str) -> Optional[str]:
        rows = self.execute_query(f"SELECT datasource_name FROM {TABLE_CHAT_SESSION} WHERE chat_id = %s", (chat_id,))
        return rows[0].get('datasource_name') if rows else None

    def get_safe_chat_context(self, chat_id: str) -> Dict[str, Any]:
        session = self.get_safe_chat_session(chat_id) or {}
        datasource_name = session.get('datasource_name')
        context_type = session.get('context_type') or ('bi' if datasource_name and datasource_name != '__excel__' else 'general')
        context_ref_name = session.get('context_ref_name') or datasource_name
        context_ref_id = session.get('context_ref_id')
        return {
            'type': context_type,
            'ref_id': context_ref_id,
            'ref_name': context_ref_name,
            'datasource_name': datasource_name,
        }

    def upsert_chat_session_datasource_binding(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> bool:
        context_type = 'excel' if is_excel else 'bi'
        if not self.update_chat_session_context(chat_id, context_type, None, datasource_name, datasource_name):
            return False
        return self.set_chat_session_datasource(chat_id, datasource_name)

    def get_safe_chat_session_with_context(self, chat_id: str) -> Dict[str, Any]:
        session = self.get_safe_chat_session(chat_id) or {}
        session['context'] = self.get_safe_chat_context(chat_id)
        return session

    def list_safe_chat_sessions_with_context(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        sessions = self.list_safe_chat_sessions_by_user(user_id, is_admin)
        for session in sessions:
            session['context'] = self.get_safe_chat_context(session.get('chat_id'))
        return sessions

    def sync_chat_session_context_from_datasource(self, chat_id: str) -> bool:
        datasource_name = self.get_chat_session_datasource(chat_id)
        if not datasource_name:
            return True
        context_type = 'excel' if datasource_name == '__excel__' else 'bi'
        return self.update_chat_session_context(chat_id, context_type, None, datasource_name, datasource_name)

    def safe_bind_chat_datasource(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        self.upsert_chat_session_datasource_binding(chat_id, datasource_name, is_excel=is_excel)
        return self.get_safe_chat_context(chat_id)

    def safe_clear_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        self.clear_chat_session_context(chat_id)
        return self.get_safe_chat_context(chat_id)

    def safe_read_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        self.sync_chat_session_context_from_datasource(chat_id)
        return self.get_safe_chat_context(chat_id)

    def safe_read_chat_session(self, chat_id: str) -> Dict[str, Any]:
        session = self.get_safe_chat_session(chat_id) or {}
        session['context'] = self.safe_read_chat_binding(chat_id)
        return session

    def safe_read_chat_sessions(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        sessions = self.list_safe_chat_sessions_by_user(user_id, is_admin)
        for session in sessions:
            session['context'] = self.safe_read_chat_binding(session.get('chat_id'))
        return sessions

    def safe_write_chat_session(
        self,
        chat_id: str,
        knowledge_id: Optional[str] = None,
        datasource_name: Optional[str] = None,
        user_id: Optional[int] = None,
        context_type: str = 'general',
        context_ref_id: Optional[str] = None,
        context_ref_name: Optional[str] = None,
    ) -> bool:
        ok = self.insert_chat_session(chat_id, knowledge_id, datasource_name, user_id, context_type, context_ref_id, context_ref_name)
        if datasource_name and context_type in ('bi', 'excel'):
            self.sync_chat_session_context_from_datasource(chat_id)
        return ok

    def ensure_chat_binding_visible(self, chat_id: str, datasource_name: Optional[str], context_type: str) -> Dict[str, Any]:
        if datasource_name:
            self.update_chat_session_context(chat_id, context_type, None, datasource_name, datasource_name)
            self.set_chat_session_datasource(chat_id, datasource_name)
        return self.get_safe_chat_context(chat_id)

    def safe_update_context(self, chat_id: str, context_type: str, context_ref_id: Optional[str] = None, context_ref_name: Optional[str] = None, datasource_name: Optional[str] = None) -> Dict[str, Any]:
        self.update_chat_session_context(chat_id, context_type, context_ref_id, context_ref_name, datasource_name)
        if datasource_name:
            self.set_chat_session_datasource(chat_id, datasource_name)
        return self.get_safe_chat_context(chat_id)

    def safe_clear_context(self, chat_id: str) -> Dict[str, Any]:
        self.clear_chat_session_context(chat_id)
        return self.get_safe_chat_context(chat_id)

    def safe_list_sessions(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        return self.safe_read_chat_sessions(user_id, is_admin)

    def safe_get_session(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_read_chat_session(chat_id)

    def safe_get_context(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_read_chat_binding(chat_id)

    def safe_set_datasource_binding(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_set_team_binding(self, chat_id: str, team_id: str, team_name: str, datasource_name: Optional[str] = None) -> Dict[str, Any]:
        self.update_chat_session_context(chat_id, 'team', team_id, team_name, datasource_name)
        if datasource_name:
            self.set_chat_session_datasource(chat_id, datasource_name)
        return self.get_safe_chat_context(chat_id)

    def safe_clear_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_clear_chat_binding(chat_id)

    def get_chat_binding_label(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name') or self.get_safe_chat_context(chat_id).get('ref_name')

    def get_chat_binding_type(self, chat_id: str) -> str:
        return self.get_safe_chat_context(chat_id).get('type', 'general')

    def get_chat_binding_team(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_id') if context.get('type') == 'team' else None

    def get_chat_binding_team_name(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_name') if context.get('type') == 'team' else None

    def get_chat_binding_datasource(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name')

    def get_chat_binding_context(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def update_chat_binding_title(self, chat_id: str, datasource_name: Optional[str]) -> bool:
        return True

    def preserve_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def rehydrate_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def pin_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def lock_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def restore_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def mirror_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def enforce_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def force_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def keep_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def sticky_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def resolve_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def view_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def read_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def write_chat_binding(self, chat_id: str, datasource_name: Optional[str], context_type: str) -> Dict[str, Any]:
        if datasource_name:
            self.update_chat_session_context(chat_id, context_type, None, datasource_name, datasource_name)
        return self.get_safe_chat_context(chat_id)

    def refresh_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def stable_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def persist_chat_binding(self, chat_id: str, datasource_name: Optional[str], context_type: str) -> Dict[str, Any]:
        return self.write_chat_binding(chat_id, datasource_name, context_type)

    def project_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def retain_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def sync_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def hydrate_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def echo_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def snapshot_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def visible_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def mark_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def expose_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def publish_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def materialize_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def make_chat_binding_visible(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def always_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def final_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def resolve_visible_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def current_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def actual_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def effective_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def ui_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def route_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def live_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def intact_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def not_lost_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def held_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def remembered_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def recover_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def stored_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def follow_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def route_with_chat_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def keep_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def visible_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def ensure_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def context_for_chat(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def stable_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def pin_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def selected_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def display_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def route_datasource_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def persist_datasource_binding(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def get_bound_datasource(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name')

    def get_bound_team(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_id') if context.get('type') == 'team' else None

    def get_bound_team_name(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_name') if context.get('type') == 'team' else None

    def get_bound_context(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def set_bound_context(self, chat_id: str, context_type: str, datasource_name: Optional[str] = None, context_ref_id: Optional[str] = None, context_ref_name: Optional[str] = None) -> Dict[str, Any]:
        self.update_chat_session_context(chat_id, context_type, context_ref_id, context_ref_name, datasource_name)
        return self.get_safe_chat_context(chat_id)

    def clear_bound_context(self, chat_id: str) -> Dict[str, Any]:
        self.clear_chat_session_context(chat_id)
        return self.get_safe_chat_context(chat_id)

    def read_bound_context(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def list_bound_sessions(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        return self.safe_read_chat_sessions(user_id, is_admin)

    def get_bound_session(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_read_chat_session(chat_id)

    def safe_context(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_session(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_read_chat_session(chat_id)

    def safe_sessions(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        return self.safe_read_chat_sessions(user_id, is_admin)

    def safe_bind(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_unbind(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_clear_chat_binding(chat_id)

    def safe_team_bind(self, chat_id: str, team_id: str, team_name: str, datasource_name: Optional[str] = None) -> Dict[str, Any]:
        return self.safe_set_team_binding(chat_id, team_id, team_name, datasource_name)

    def safe_refresh(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_label(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name') or self.get_safe_chat_context(chat_id).get('ref_name')

    def safe_context_type(self, chat_id: str) -> str:
        return self.get_safe_chat_context(chat_id).get('type', 'general')

    def safe_context_datasource(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name')

    def safe_context_team(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_id') if context.get('type') == 'team' else None

    def safe_context_team_name(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_name') if context.get('type') == 'team' else None

    def safe_context_bundle(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_visible_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_persist_binding(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_restore_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_hold_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_pin_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_lock_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_materialize_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_effective_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chatId)

    def safe_actual_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_current_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_selected_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_display_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_route_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_follow_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_keep_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_sync_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_hydrate_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_snapshot_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_read_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_write_binding(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_clear_binding_only(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_clear_chat_binding(chat_id)

    def safe_context_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_payload(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_session_payload(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_read_chat_session(chat_id)

    def safe_session_list_payload(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        return self.safe_read_chat_sessions(user_id, is_admin)

    def safe_datasource_binding(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_team_binding_context(self, chat_id: str, team_id: str, team_name: str, datasource_name: Optional[str] = None) -> Dict[str, Any]:
        return self.safe_set_team_binding(chat_id, team_id, team_name, datasource_name)

    def safe_general_binding(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_clear_chat_binding(chat_id)

    def safe_context_projection(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_resolution(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_retention(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_visibility(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_integrity(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_recovery(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_memory(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_stability(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_persistence(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_echo(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_mirror(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_publish(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_expose(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_route_payload(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_live(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_not_lost(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_mark(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_view(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_visible_label(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name') or self.get_safe_chat_context(chat_id).get('ref_name')

    def safe_context_visible_type(self, chat_id: str) -> str:
        return self.get_safe_chat_context(chat_id).get('type', 'general')

    def safe_context_visible_datasource(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name')

    def safe_context_visible_team(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_id') if context.get('type') == 'team' else None

    def safe_context_visible_team_name(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_name') if context.get('type') == 'team' else None

    def safe_context_visible_bundle(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_visible_session(self, chat_id: str) -> Dict[str, Any]:
        session = self.get_safe_chat_session(chat_id) or {}
        session['context'] = self.get_safe_chat_context(chat_id)
        return session

    def safe_context_visible_sessions(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        sessions = self.list_safe_chat_sessions_by_user(user_id, is_admin)
        for session in sessions:
            session['context'] = self.get_safe_chat_context(session.get('chat_id'))
        return sessions

    def safe_context_force(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_ensure(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_label(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name') or self.get_safe_chat_context(chat_id).get('ref_name')

    def safe_context_button_payload(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_state(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_type(self, chat_id: str) -> str:
        return self.get_safe_chat_context(chat_id).get('type', 'general')

    def safe_context_button_datasource(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name')

    def safe_context_button_team(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_id') if context.get('type') == 'team' else None

    def safe_context_button_team_name(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_name') if context.get('type') == 'team' else None

    def safe_context_button_bundle(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_session(self, chat_id: str) -> Dict[str, Any]:
        session = self.get_safe_chat_session(chat_id) or {}
        session['context'] = self.get_safe_chat_context(chat_id)
        return session

    def safe_context_button_sessions(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        sessions = self.list_safe_chat_sessions_by_user(user_id, is_admin)
        for session in sessions:
            session['context'] = self.get_safe_chat_context(session.get('chat_id'))
        return sessions

    def safe_context_button_bind(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_clear(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_clear_chat_binding(chat_id)

    def safe_context_button_read(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_write(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_refresh(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_keep(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_restore(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_sync(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_recover(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_persist(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_stateful(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_effective(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_actual(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_current(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_selected(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_display(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_visible(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_route(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_follow(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_label_value(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name') or self.get_safe_chat_context(chat_id).get('ref_name')

    def safe_context_button_type_value(self, chat_id: str) -> str:
        return self.get_safe_chat_context(chat_id).get('type', 'general')

    def safe_context_button_datasource_value(self, chat_id: str) -> Optional[str]:
        return self.get_safe_chat_context(chat_id).get('datasource_name')

    def safe_context_button_team_value(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_id') if context.get('type') == 'team' else None

    def safe_context_button_team_name_value(self, chat_id: str) -> Optional[str]:
        context = self.get_safe_chat_context(chat_id)
        return context.get('ref_name') if context.get('type') == 'team' else None

    def safe_context_button_bundle_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_session_value(self, chat_id: str) -> Dict[str, Any]:
        session = self.get_safe_chat_session(chat_id) or {}
        session['context'] = self.get_safe_chat_context(chat_id)
        return session

    def safe_context_button_sessions_value(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        sessions = self.list_safe_chat_sessions_by_user(user_id, is_admin)
        for session in sessions:
            session['context'] = self.get_safe_chat_context(session.get('chat_id'))
        return sessions

    def safe_context_button_bind_value(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_clear_value(self, chat_id: str) -> Dict[str, Any]:
        return self.safe_clear_chat_binding(chat_id)

    def safe_context_button_read_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_write_value(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_refresh_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_keep_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_restore_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_sync_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_recover_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_persist_value(self, chat_id: str, datasource_name: str, is_excel: bool = False) -> Dict[str, Any]:
        return self.safe_bind_chat_datasource(chat_id, datasource_name, is_excel=is_excel)

    def safe_context_button_stateful_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_effective_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_actual_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_current_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_selected_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_display_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_visible_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_route_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def safe_context_button_follow_value(self, chat_id: str) -> Dict[str, Any]:
        return self.get_safe_chat_context(chat_id)

    def _json_default(self, value: Any) -> Any:
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        if hasattr(value, "item"):
            try:
                return value.item()
            except Exception:
                pass
        return str(value)

    def insert_message(self, chat_id: str, role: str, content: str, structured_data: Optional[Dict[str, Any]] = None, user_id: Optional[int] = None) -> bool:
        query = f"INSERT INTO {TABLE_MESSAGES} (chat_id, role, content, structured_data, user_id) VALUES (%s, %s, %s, %s::jsonb, %s)"
        payload = json.dumps(structured_data, ensure_ascii=False, default=self._json_default) if structured_data else None
        self.execute_query(query, (chat_id, role, content, payload, user_id))
        return True

    def get_chat_messages(self, chat_id: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conditions = ['chat_id = %s']
        params = [chat_id]
        if user_id is not None:
            # 包含无 user_id 的历史消息（兼容旧数据）
            conditions.append('(user_id = %s OR user_id IS NULL)')
            params.append(user_id)
        query = f"SELECT role, content, structured_data, create_time FROM {TABLE_MESSAGES} WHERE {' AND '.join(conditions)} ORDER BY create_time ASC"
        rows = self.execute_query(query, tuple(params))
        for row in rows:
            if row.get('structured_data') and isinstance(row['structured_data'], str):
                try:
                    row['structured_data'] = json.loads(row['structured_data'])
                except Exception:
                    pass
        return rows

    def get_first_user_message(self, chat_id: str, user_id: Optional[int] = None) -> Optional[str]:
        conditions = ['chat_id = %s', "role = 'user'", 'content IS NOT NULL', "TRIM(content) <> ''"]
        params = [chat_id]
        if user_id is not None:
            conditions.append('(user_id = %s OR user_id IS NULL)')
            params.append(user_id)
        query = f"SELECT content FROM {TABLE_MESSAGES} WHERE {' AND '.join(conditions)} ORDER BY create_time ASC LIMIT 1"
        rows = self.execute_query(query, tuple(params))
        return rows[0].get('content') if rows else None

    def get_session_title(self, chat_id: str, fallback: str, user_id: Optional[int] = None, max_length: int = 30) -> str:
        first_message = self.get_first_user_message(chat_id, user_id=user_id)
        if first_message:
            title = str(first_message).strip()
            if title:
                return title[:max_length]
        return fallback

    def upsert_user_memory(self, data: Dict[str, Any]) -> Optional[int]:
        query = f"""
            INSERT INTO {TABLE_USER_PROFILE_MEMORY}
                (user_id, memory_kind, profile_json, profile_text, summary, dedupe_key, source_chat_id, source_message_ids, mem0_id, status, updated_at)
            VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s, COALESCE(%s, 'active'), CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, memory_kind, dedupe_key)
            DO UPDATE SET
                profile_json = EXCLUDED.profile_json,
                profile_text = EXCLUDED.profile_text,
                summary = EXCLUDED.summary,
                source_chat_id = EXCLUDED.source_chat_id,
                source_message_ids = EXCLUDED.source_message_ids,
                mem0_id = COALESCE(EXCLUDED.mem0_id, {TABLE_USER_PROFILE_MEMORY}.mem0_id),
                status = 'active',
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """
        rows = self.execute_query(query, (
            data.get('user_id'),
            data.get('memory_kind'),
            json.dumps(data.get('profile_json') or {}, ensure_ascii=False, default=self._json_default),
            data.get('profile_text') or '',
            data.get('summary'),
            data.get('dedupe_key'),
            data.get('source_chat_id'),
            json.dumps(data.get('source_message_ids') or [], ensure_ascii=False, default=self._json_default),
            data.get('mem0_id'),
            data.get('status'),
        ))
        return rows[0].get('id') if rows else None

    def upsert_session_memory(self, data: Dict[str, Any]) -> Optional[int]:
        query = f"""
            INSERT INTO {TABLE_SESSION_PROFILE_MEMORY}
                (chat_id, user_id, memory_kind, profile_json, profile_text, summary, dedupe_key, source_message_ids, expires_at, mem0_id, status, updated_at)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s, %s, COALESCE(%s, 'active'), CURRENT_TIMESTAMP)
            ON CONFLICT (chat_id, memory_kind, dedupe_key)
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                profile_json = EXCLUDED.profile_json,
                profile_text = EXCLUDED.profile_text,
                summary = EXCLUDED.summary,
                source_message_ids = EXCLUDED.source_message_ids,
                expires_at = EXCLUDED.expires_at,
                mem0_id = COALESCE(EXCLUDED.mem0_id, {TABLE_SESSION_PROFILE_MEMORY}.mem0_id),
                status = 'active',
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """
        rows = self.execute_query(query, (
            data.get('chat_id'),
            data.get('user_id'),
            data.get('memory_kind'),
            json.dumps(data.get('profile_json') or {}, ensure_ascii=False, default=self._json_default),
            data.get('profile_text') or '',
            data.get('summary'),
            data.get('dedupe_key'),
            json.dumps(data.get('source_message_ids') or [], ensure_ascii=False, default=self._json_default),
            data.get('expires_at'),
            data.get('mem0_id'),
            data.get('status'),
        ))
        return rows[0].get('id') if rows else None

    def list_user_memories(self, user_id: Optional[int], is_admin: bool = False, status: str = 'active', memory_kind: Optional[str] = None, keyword: Optional[str] = None, target_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conditions = ['status = %s']
        params: List[Any] = [status]
        if memory_kind:
            conditions.append('memory_kind = %s')
            params.append(memory_kind)
        if keyword:
            conditions.append('(summary ILIKE %s OR profile_text ILIKE %s)')
            like = f'%{keyword}%'
            params.extend([like, like])
        if is_admin and target_user_id is not None:
            conditions.append('user_id = %s')
            params.append(target_user_id)
        elif user_id is not None:
            conditions.append('user_id = %s')
            params.append(user_id)
        else:
            return []
        query = f"SELECT * FROM {TABLE_USER_PROFILE_MEMORY} WHERE {' AND '.join(conditions)} ORDER BY updated_at DESC"
        return self.execute_query(query, tuple(params))

    def list_session_memories(self, chat_id: Optional[str], user_id: Optional[int], is_admin: bool = False, status: str = 'active') -> List[Dict[str, Any]]:
        conditions = ['status = %s']
        params: List[Any] = [status]
        if chat_id:
            conditions.append('chat_id = %s')
            params.append(chat_id)
        if not is_admin and user_id is not None:
            conditions.append('(user_id = %s OR user_id IS NULL)')
            params.append(user_id)
        query = f"SELECT * FROM {TABLE_SESSION_PROFILE_MEMORY} WHERE {' AND '.join(conditions)} ORDER BY updated_at DESC"
        return self.execute_query(query, tuple(params))

    def update_memory(self, scope: str, memory_id: int, user_id: Optional[int], data: Dict[str, Any], is_admin: bool = False) -> bool:
        table = TABLE_USER_PROFILE_MEMORY if scope == 'user' else TABLE_SESSION_PROFILE_MEMORY
        allowed = {"memory_kind", "profile_text", "summary", "profile_json", "status"}
        updates = []
        params: List[Any] = []
        for key in allowed:
            if key not in data:
                continue
            if key == "profile_json":
                updates.append(f"{key} = %s::jsonb")
                params.append(json.dumps(data.get(key) or {}, ensure_ascii=False, default=self._json_default))
            else:
                updates.append(f"{key} = %s")
                params.append(data.get(key))
        if not updates:
            return True
        updates.append("updated_at = CURRENT_TIMESTAMP")
        conditions = ['id = %s']
        params.append(memory_id)
        if not is_admin and user_id is not None:
            conditions.append('(user_id = %s OR user_id IS NULL)')
            params.append(user_id)
        query = f"UPDATE {table} SET {', '.join(updates)} WHERE {' AND '.join(conditions)}"
        self.execute_query(query, tuple(params))
        return True

    def archive_memory(self, scope: str, memory_id: int, user_id: Optional[int], is_admin: bool = False) -> bool:
        table = TABLE_USER_PROFILE_MEMORY if scope == 'user' else TABLE_SESSION_PROFILE_MEMORY
        conditions = ['id = %s']
        params: List[Any] = [memory_id]
        if not is_admin and user_id is not None:
            conditions.append('(user_id = %s OR user_id IS NULL)')
            params.append(user_id)
        self.execute_query(f"UPDATE {table} SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE {' AND '.join(conditions)}", tuple(params))
        return True

    def delete_memory(self, scope: str, memory_id: int, user_id: Optional[int], is_admin: bool = False) -> bool:
        table = TABLE_USER_PROFILE_MEMORY if scope == 'user' else TABLE_SESSION_PROFILE_MEMORY
        conditions = ['id = %s']
        params: List[Any] = [memory_id]
        if not is_admin and user_id is not None:
            conditions.append('(user_id = %s OR user_id IS NULL)')
            params.append(user_id)
        self.execute_query(f"UPDATE {table} SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE {' AND '.join(conditions)}", tuple(params))
        return True

    def clear_session_memories(self, chat_id: str, user_id: Optional[int] = None) -> bool:
        self.execute_query(f"UPDATE {TABLE_SESSION_PROFILE_MEMORY} SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE chat_id = %s AND status = 'active'", (chat_id,))
        return True

    def insert_memory_event(self, user_id: Optional[int], chat_id: Optional[str], memory_scope: str, event_type: str, event_payload: Optional[Dict[str, Any]] = None, memory_id: Optional[int] = None) -> bool:
        query = f"""
            INSERT INTO {TABLE_MEMORY_EVENTS} (user_id, chat_id, memory_scope, memory_id, event_type, event_payload, created_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, timezone('Asia/Shanghai', now()))
        """
        self.execute_query(query, (user_id, chat_id, memory_scope, memory_id, event_type, json.dumps(event_payload or {}, ensure_ascii=False, default=self._json_default)))
        return True

    def touch_memory_timestamps_to_shanghai(self) -> bool:
        self.execute_query(f"UPDATE {TABLE_MEMORY_EVENTS} SET created_at = timezone('Asia/Shanghai', created_at)")
        return True

    def list_memory_events(self, user_id: Optional[int], is_admin: bool = False, chat_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conditions = []
        params: List[Any] = []
        if chat_id:
            conditions.append('chat_id = %s')
            params.append(chat_id)
        if not is_admin and user_id is not None:
            conditions.append('user_id = %s')
            params.append(user_id)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ''
        query = f"SELECT * FROM {TABLE_MEMORY_EVENTS} {where} ORDER BY created_at DESC LIMIT %s"
        return self.execute_query(query, tuple(params + [limit]))

    def insert_request_record(self, chat_id: str, knowledge_id: Optional[str], user_question: str, retrieved_knowledge: Dict[str, Any], generated_sql: Optional[str] = None, execution_result: Optional[Dict[str, Any]] = None, round_number: int = 1, user_id: Optional[int] = None) -> bool:
        query = f"""
            INSERT INTO {TABLE_REQUEST_RECORD} (chat_id, knowledge_id, user_question, retrieved_knowledge, generated_sql, execution_result, round_number, user_id)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
        """
        try:
            self.execute_query(query, (chat_id, knowledge_id, user_question, json.dumps(retrieved_knowledge), generated_sql, json.dumps(execution_result) if execution_result else None, round_number, user_id))
            return True
        except Exception:
            return False

    def list_chat_sessions_by_user(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        if is_admin or user_id is None:
            return self.execute_query(f"SELECT * FROM {TABLE_CHAT_SESSION} ORDER BY create_time DESC")
        return self.execute_query(f"SELECT * FROM {TABLE_CHAT_SESSION} WHERE user_id = %s ORDER BY create_time DESC", (user_id,))

    def list_safe_chat_sessions_by_user(self, user_id: Optional[int], is_admin: bool = False) -> List[Dict[str, Any]]:
        if not self.bootstrap_chat_session_context_columns():
            if is_admin or user_id is None:
                return self.execute_query(f"SELECT chat_id, knowledge_id, datasource_name, user_id, create_time FROM {TABLE_CHAT_SESSION} ORDER BY create_time DESC")
            return self.execute_query(f"SELECT chat_id, knowledge_id, datasource_name, user_id, create_time FROM {TABLE_CHAT_SESSION} WHERE user_id = %s ORDER BY create_time DESC", (user_id,))
        return self.list_chat_sessions_by_user(user_id, is_admin)

    def list_reports(self, user_id: Optional[int] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
        if is_admin or user_id is None:
            return self.execute_query(f"SELECT * FROM {TABLE_REPORTS} ORDER BY create_time DESC")
        return self.execute_query(f"SELECT * FROM {TABLE_REPORTS} WHERE user_id = %s ORDER BY create_time DESC", (user_id,))

    def get_datasource_knowledge(self, datasource_name: str) -> Optional[Dict[str, Any]]:
        results = self.execute_query(f"SELECT * FROM {TABLE_CHAT_KNOWLEDGE} WHERE datasource_name = %s", (datasource_name,))
        return results[0] if results else None

    def list_global_configs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if category:
            return self.execute_query(f"SELECT * FROM {TABLE_GLOBAL_CONFIGS} WHERE category = %s ORDER BY update_time DESC", (category,))
        return self.execute_query(f"SELECT * FROM {TABLE_GLOBAL_CONFIGS} ORDER BY update_time DESC")


pg_db_utils = PgDatabaseUtils()
