from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from config.config_db import (
    TABLE_AGENTS,
    TABLE_CHAT_KNOWLEDGE,
    TABLE_CHAT_SESSION,
    TABLE_GENERAL_METADATA,
    TABLE_GLOBAL_CONFIGS,
    TABLE_MESSAGES,
    TABLE_MEMORY_EVENTS,
    TABLE_REPORTS,
    TABLE_REQUEST_RECORD,
    TABLE_SESSION_PROFILE_MEMORY,
    TABLE_SKILLS,
    TABLE_USERS,
    TABLE_WHITE_LIST,
    TABLE_TEAMS,
    TABLE_TEAM_MEMBERS,
    TABLE_USER_PROFILE_MEMORY,
)
from utils.pg_db_utils import PgDatabaseUtils


class DatabaseUtils(PgDatabaseUtils):
    """PostgreSQL 数据库工具类。"""

    def __init__(self, use_app_db: bool = False):
        super().__init__(use_app_db=use_app_db)

    def create_tables(self):
        self.connect()
        statements = [
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_USERS} (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CHAT_SESSION} (
                chat_id TEXT PRIMARY KEY,
                knowledge_id TEXT,
                datasource_name TEXT,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_GENERAL_METADATA} (
                metadata_id TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL REFERENCES {TABLE_CHAT_SESSION}(chat_id) ON DELETE CASCADE,
                general_content JSONB NOT NULL,
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_MESSAGES} (
                id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL REFERENCES {TABLE_CHAT_SESSION}(chat_id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT,
                structured_data JSONB,
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_REQUEST_RECORD} (
                record_id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL REFERENCES {TABLE_CHAT_SESSION}(chat_id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                knowledge_id TEXT,
                user_question TEXT NOT NULL,
                retrieved_knowledge JSONB NOT NULL,
                generated_sql TEXT,
                execution_result JSONB,
                round_number INTEGER DEFAULT 1,
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_CHAT_KNOWLEDGE} (
                datasource_name TEXT PRIMARY KEY,
                content TEXT,
                vocabulary JSONB DEFAULT '[]'::jsonb,
                reference_sql JSONB DEFAULT '[]'::jsonb,
                schema_data JSONB DEFAULT 'null'::jsonb,
                update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_GLOBAL_CONFIGS} (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                content JSONB NOT NULL,
                is_enabled BOOLEAN DEFAULT TRUE,
                scope_type TEXT DEFAULT 'universal',
                scope_datasources JSONB DEFAULT '[]'::jsonb,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                update_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, name, user_id)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_REPORTS} (
                id SERIAL PRIMARY KEY,
                report_id TEXT UNIQUE NOT NULL,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                report_type TEXT NOT NULL,
                detail_file TEXT,
                summary_file TEXT,
                original_file TEXT,
                file_path TEXT,
                desensitized_file TEXT,
                desensitize_columns JSONB,
                is_desensitized BOOLEAN DEFAULT FALSE,
                row_count INTEGER DEFAULT 0,
                column_count INTEGER DEFAULT 0,
                yellow_cells_count INTEGER DEFAULT 0,
                problem_count INTEGER DEFAULT 0,
                display_file_name TEXT,
                status TEXT DEFAULT 'success',
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_WHITE_LIST} (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                create_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_SKILLS} (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                instructions TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                binding_agents JSONB NOT NULL DEFAULT '[]'::jsonb,
                trigger_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
                priority INTEGER NOT NULL DEFAULT 0,
                scope_type TEXT NOT NULL DEFAULT 'universal',
                scope_datasources JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_by INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE SET NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_AGENTS} (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                base_instructions TEXT NOT NULL,
                model_config JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                bound_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
                tools JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                is_builtin BOOLEAN NOT NULL DEFAULT FALSE,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_by INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE SET NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 团队表
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_TEAMS} (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                mode TEXT NOT NULL DEFAULT 'coordinate',
                leader_config JSONB NOT NULL,
                max_iterations INTEGER DEFAULT 10,
                is_active BOOLEAN DEFAULT TRUE,
                created_by INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE SET NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 团队成员表
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_TEAM_MEMBERS} (
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL REFERENCES {TABLE_TEAMS}(id) ON DELETE CASCADE,
                member_key TEXT NOT NULL,
                member_type TEXT NOT NULL,
                ref_agent_name TEXT,
                ref_workflow TEXT,
                ref_team_id INTEGER,
                ref_custom_flow JSONB,
                role TEXT DEFAULT '',
                description TEXT DEFAULT '',
                capabilities JSONB DEFAULT '[]'::jsonb,
                can_delegate_to JSONB DEFAULT '[]'::jsonb,
                position JSONB,
                sort_order INTEGER DEFAULT 0,
                UNIQUE(team_id, member_key)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_USER_PROFILE_MEMORY} (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                memory_kind TEXT NOT NULL,
                profile_json JSONB,
                profile_text TEXT NOT NULL,
                summary TEXT,
                dedupe_key TEXT NOT NULL,
                source_chat_id TEXT,
                source_message_ids JSONB DEFAULT '[]'::jsonb,
                mem0_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, memory_kind, dedupe_key)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_SESSION_PROFILE_MEMORY} (
                id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL REFERENCES {TABLE_CHAT_SESSION}(chat_id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE CASCADE,
                memory_kind TEXT NOT NULL,
                profile_json JSONB,
                profile_text TEXT NOT NULL,
                summary TEXT,
                dedupe_key TEXT NOT NULL,
                source_message_ids JSONB DEFAULT '[]'::jsonb,
                expires_at TIMESTAMP,
                mem0_id TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(chat_id, memory_kind, dedupe_key)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_MEMORY_EVENTS} (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES {TABLE_USERS}(id) ON DELETE SET NULL,
                chat_id TEXT,
                memory_scope TEXT NOT NULL,
                memory_id INTEGER,
                event_type TEXT NOT NULL,
                event_payload JSONB DEFAULT '{{}}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]
        try:
            for statement in statements:
                self.cursor.execute(statement)
            self.conn.commit()
            # 为 askbi_agents / askbi_chat_session 表安全添加新列（幂等）
            self._ensure_agent_columns()
            self._ensure_chat_session_columns()
        except Exception:
            if self.conn:
                self.conn.rollback()
            raise

    def get_chat_history(self, chat_id: str, limit: int = 5, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conditions = ["chat_id = %s", "user_question IS NOT NULL", "execution_result IS NOT NULL"]
        params: List[Any] = [chat_id]
        if user_id is not None:
            conditions.append("user_id = %s")
            params.append(user_id)
        query = f"""
            SELECT user_question, execution_result
            FROM {TABLE_REQUEST_RECORD}
            WHERE {' AND '.join(conditions)}
            ORDER BY round_number DESC
            LIMIT %s
        """
        rows = self.execute_query(query, tuple(params + [limit]))
        history: List[Dict[str, Any]] = []
        for row in reversed(rows):
            answer_data = row.get("execution_result")
            if isinstance(answer_data, str):
                try:
                    answer_data = json.loads(answer_data)
                except Exception:
                    answer_data = {}
            if isinstance(answer_data, dict):
                answer = answer_data.get("result") or answer_data.get("summary") or str(answer_data)
            else:
                answer = str(answer_data)
            history.append({"question": row.get("user_question"), "answer": answer})
        return history

    def get_next_round_number(self, chat_id: str) -> int:
        query = f"SELECT COALESCE(MAX(round_number), 0) + 1 AS next_round FROM {TABLE_REQUEST_RECORD} WHERE chat_id = %s"
        rows = self.execute_query(query, (chat_id,))
        return int(rows[0]["next_round"]) if rows else 1

    def get_chat_knowledge(self, datasource_name: str) -> Optional[Dict[str, Any]]:
        row = self.get_datasource_knowledge(datasource_name)
        if not row:
            return None
        return {
            "content": row.get("content"),
            "vocabulary": row.get("vocabulary") or [],
            "reference_sql": row.get("reference_sql") or [],
            "schema_data": row.get("schema_data"),
        }

    def upsert_chat_knowledge(
        self,
        datasource_name: str,
        content: Optional[str] = None,
        vocabulary: Optional[List[Any]] = None,
        reference_sql: Optional[List[Any]] = None,
        schema_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        query = f"""
            INSERT INTO {TABLE_CHAT_KNOWLEDGE} (datasource_name, content, vocabulary, reference_sql, schema_data)
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            ON CONFLICT (datasource_name) DO UPDATE SET
                content = COALESCE(EXCLUDED.content, {TABLE_CHAT_KNOWLEDGE}.content),
                vocabulary = COALESCE(EXCLUDED.vocabulary, {TABLE_CHAT_KNOWLEDGE}.vocabulary),
                reference_sql = COALESCE(EXCLUDED.reference_sql, {TABLE_CHAT_KNOWLEDGE}.reference_sql),
                schema_data = COALESCE(EXCLUDED.schema_data, {TABLE_CHAT_KNOWLEDGE}.schema_data),
                update_time = CURRENT_TIMESTAMP
        """
        try:
            self.execute_query(
                query,
                (
                    datasource_name,
                    content,
                    json.dumps(vocabulary) if vocabulary is not None else None,
                    json.dumps(reference_sql) if reference_sql is not None else None,
                    json.dumps(schema_data) if schema_data is not None else None,
                ),
            )
            return True
        except Exception:
            return False

    def list_global_configs(
        self,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if category:
            conditions.append("category = %s")
            params.append(category)
        if not is_admin and user_id is not None:
            conditions.append("(user_id = %s OR user_id IS NULL)")
            params.append(user_id)
        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.execute_query(
            f"SELECT * FROM {TABLE_GLOBAL_CONFIGS}{where_clause} ORDER BY update_time DESC",
            tuple(params),
        )

    def upsert_global_config(
        self,
        category: str,
        name: str,
        content: Dict[str, Any],
        is_enabled: bool = True,
        config_id: Optional[int] = None,
        scope_type: str = "universal",
        scope_datasources: Optional[List[str]] = None,
        user_id: Optional[int] = None,
    ) -> bool:
        scope_datasources = scope_datasources or []
        try:
            if config_id:
                query = f"""
                    UPDATE {TABLE_GLOBAL_CONFIGS}
                    SET category = %s, name = %s, content = %s::jsonb, is_enabled = %s,
                        scope_type = %s, scope_datasources = %s::jsonb, update_time = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                self.execute_query(query, (category, name, json.dumps(content), is_enabled, scope_type, json.dumps(scope_datasources), config_id))
            else:
                query = f"""
                    INSERT INTO {TABLE_GLOBAL_CONFIGS} (category, name, content, is_enabled, scope_type, scope_datasources, user_id)
                    VALUES (%s, %s, %s::jsonb, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (category, name, user_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        is_enabled = EXCLUDED.is_enabled,
                        scope_type = EXCLUDED.scope_type,
                        scope_datasources = EXCLUDED.scope_datasources,
                        update_time = CURRENT_TIMESTAMP
                """
                self.execute_query(query, (category, name, json.dumps(content), is_enabled, scope_type, json.dumps(scope_datasources), user_id))
            return True
        except Exception:
            return False

    def delete_global_config(self, config_id: int) -> bool:
        try:
            self.execute_query(f"DELETE FROM {TABLE_GLOBAL_CONFIGS} WHERE id = %s", (config_id,))
            return True
        except Exception:
            return False

    def toggle_global_config(self, config_id: int, is_enabled: bool) -> bool:
        try:
            self.execute_query(f"UPDATE {TABLE_GLOBAL_CONFIGS} SET is_enabled = %s WHERE id = %s", (is_enabled, config_id))
            return True
        except Exception:
            return False

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def create_default_admin(self):
        if self.execute_query(f"SELECT id FROM {TABLE_USERS} WHERE username = %s", ("admin",)):
            return
        self.execute_query(
            f"INSERT INTO {TABLE_USERS} (username, password_hash, role) VALUES (%s, %s, %s)",
            ("admin", self._hash_password("admin123"), "admin"),
        )

    def create_user(self, username: str, password: str, role: str = "user") -> Dict[str, Any]:
        if self.execute_query(f"SELECT id FROM {TABLE_USERS} WHERE username = %s", (username,)):
            return {"success": False, "message": "用户名已存在"}
        try:
            self.execute_query(
                f"INSERT INTO {TABLE_USERS} (username, password_hash, role) VALUES (%s, %s, %s)",
                (username, self._hash_password(password), role),
            )
            return {"success": True, "message": "用户创建成功"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(
            f"SELECT id, username, role, create_time FROM {TABLE_USERS} WHERE username = %s AND password_hash = %s",
            (username, self._hash_password(password)),
        )
        return rows[0] if rows else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(
            f"SELECT id, username, role, create_time FROM {TABLE_USERS} WHERE id = %s",
            (user_id,),
        )
        return rows[0] if rows else None

    def list_users(self) -> List[Dict[str, Any]]:
        return self.execute_query(f"SELECT id, username, role, create_time FROM {TABLE_USERS} ORDER BY id ASC")

    def delete_user(self, user_id: int) -> bool:
        try:
            self.execute_query(f"DELETE FROM {TABLE_USERS} WHERE id = %s", (user_id,))
            return True
        except Exception:
            return False

    def update_user_password(self, user_id: int, new_password: str) -> bool:
        try:
            self.execute_query(
                f"UPDATE {TABLE_USERS} SET password_hash = %s WHERE id = %s",
                (self._hash_password(new_password), user_id),
            )
            return True
        except Exception:
            return False

    def insert_general_metadata(self, metadata_id: str, chat_id: str, general_content: Dict[str, Any]) -> bool:
        query = f"INSERT INTO {TABLE_GENERAL_METADATA} (metadata_id, chat_id, general_content) VALUES (%s, %s, %s::jsonb)"
        try:
            self.execute_query(query, (metadata_id, chat_id, json.dumps(general_content)))
            return True
        except Exception:
            return False

    def save_general_metadata(self, metadata_id: str, chat_id: str, general_content: Dict[str, Any]) -> bool:
        return self.insert_general_metadata(metadata_id, chat_id, general_content)

    def get_general_metadata(self, metadata_id: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_GENERAL_METADATA} WHERE metadata_id = %s LIMIT 1", (metadata_id,))
        return rows[0] if rows else None

    def get_metadata_by_chat_id(self, chat_id: str) -> List[Dict[str, Any]]:
        return self.execute_query(f"SELECT * FROM {TABLE_GENERAL_METADATA} WHERE chat_id = %s ORDER BY create_time DESC", (chat_id,))

    def save_report(
        self,
        report_id: str,
        user_id: int,
        report_type: str,
        detail_file: Optional[str] = None,
        summary_file: Optional[str] = None,
        original_file: Optional[str] = None,
        file_path: Optional[str] = None,
        desensitized_file: Optional[str] = None,
        row_count: int = 0,
        column_count: int = 0,
        yellow_cells_count: int = 0,
        problem_count: int = 0,
        display_file_name: Optional[str] = None,
    ) -> bool:
        query = f"""
            INSERT INTO {TABLE_REPORTS} (
                report_id, user_id, report_type, detail_file, summary_file, original_file, file_path,
                desensitized_file, row_count, column_count, yellow_cells_count, problem_count, display_file_name, is_desensitized, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.execute_query(
                query,
                (
                    report_id, user_id, report_type, detail_file, summary_file, original_file, file_path,
                    desensitized_file, row_count, column_count, yellow_cells_count, problem_count,
                    display_file_name, bool(desensitized_file), "success"
                ),
            )
            return True
        except Exception:
            return False

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_REPORTS} WHERE report_id = %s", (report_id,))
        return rows[0] if rows else None

    def update_report_desensitized(self, report_id: str, desensitized_file: str, is_desensitized: bool = True) -> bool:
        try:
            self.execute_query(
                f"UPDATE {TABLE_REPORTS} SET desensitized_file = %s, is_desensitized = %s WHERE report_id = %s",
                (desensitized_file, is_desensitized, report_id),
            )
            return True
        except Exception:
            return False

    def update_report_row_count(self, report_id: str, row_count: int) -> bool:
        try:
            self.execute_query(f"UPDATE {TABLE_REPORTS} SET row_count = %s WHERE report_id = %s", (row_count, report_id))
            return True
        except Exception:
            return False

    def update_report_name(self, report_id: str, display_file_name: str, user_id: Optional[int] = None) -> bool:
        try:
            if user_id is not None:
                self.execute_query(
                    f"UPDATE {TABLE_REPORTS} SET display_file_name = %s WHERE report_id = %s AND user_id = %s",
                    (display_file_name, report_id, user_id),
                )
            else:
                self.execute_query(
                    f"UPDATE {TABLE_REPORTS} SET display_file_name = %s WHERE report_id = %s",
                    (display_file_name, report_id),
                )
            return True
        except Exception:
            return False

    def delete_report(self, report_id: str, user_id: Optional[int] = None) -> bool:
        try:
            if user_id is not None:
                self.execute_query(f"DELETE FROM {TABLE_REPORTS} WHERE report_id = %s AND user_id = %s", (report_id, user_id))
            else:
                self.execute_query(f"DELETE FROM {TABLE_REPORTS} WHERE report_id = %s", (report_id,))
            return True
        except Exception:
            return False

    # ── Skills CRUD ──────────────────────────────────────────

    def list_skills(self, category: Optional[str] = None, active_only: bool = False) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if category:
            conditions.append("category = %s")
            params.append(category)
        if active_only:
            conditions.append("is_active = TRUE")
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.execute_query(
            f"SELECT * FROM {TABLE_SKILLS}{where} ORDER BY priority DESC, id ASC",
            tuple(params),
        )

    def get_skill(self, skill_id: int) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_SKILLS} WHERE id = %s", (skill_id,))
        return rows[0] if rows else None

    def get_skill_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_SKILLS} WHERE name = %s", (name,))
        return rows[0] if rows else None

    def create_skill(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[int]:
        try:
            rows = self.execute_query(
                f"""INSERT INTO {TABLE_SKILLS}
                    (name, description, instructions, category, is_builtin, is_active,
                     binding_agents, trigger_keywords, priority, scope_type, scope_datasources, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb, %s)
                    RETURNING id""",
                (
                    data["name"],
                    data.get("description", ""),
                    data["instructions"],
                    data.get("category", "general"),
                    data.get("is_builtin", False),
                    data.get("is_active", True),
                    json.dumps(data.get("binding_agents", [])),
                    json.dumps(data.get("trigger_keywords", [])),
                    data.get("priority", 0),
                    data.get("scope_type", "universal"),
                    json.dumps(data.get("scope_datasources", [])),
                    user_id,
                ),
            )
            return rows[0]["id"] if rows else None
        except Exception:
            return None

    def update_skill(self, skill_id: int, data: Dict[str, Any]) -> bool:
        sets: List[str] = ["updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = []
        for key in ("name", "description", "instructions", "category", "is_active",
                     "priority", "scope_type"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        for key in ("binding_agents", "trigger_keywords", "scope_datasources"):
            if key in data:
                sets.append(f"{key} = %s::jsonb")
                params.append(json.dumps(data[key]))
        if len(sets) == 1:
            return True
        params.append(skill_id)
        try:
            self.execute_query(
                f"UPDATE {TABLE_SKILLS} SET {', '.join(sets)} WHERE id = %s",
                tuple(params),
            )
            return True
        except Exception:
            return False

    def delete_skill(self, skill_id: int) -> bool:
        try:
            self.execute_query(f"DELETE FROM {TABLE_SKILLS} WHERE id = %s", (skill_id,))
            return True
        except Exception:
            return False

    def toggle_skill(self, skill_id: int, is_active: bool) -> bool:
        try:
            self.execute_query(
                f"UPDATE {TABLE_SKILLS} SET is_active = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (is_active, skill_id),
            )
            return True
        except Exception:
            return False

    # ── Agents CRUD ──────────────────────────────────────────

    def list_agents(self) -> List[Dict[str, Any]]:
        return self.execute_query(f"SELECT * FROM {TABLE_AGENTS} ORDER BY id ASC")

    def get_agent(self, agent_id: int) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_AGENTS} WHERE id = %s", (agent_id,))
        return rows[0] if rows else None

    def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_AGENTS} WHERE name = %s", (name,))
        return rows[0] if rows else None

    def create_agent(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[int]:
        try:
            rows = self.execute_query(
                f"""INSERT INTO {TABLE_AGENTS}
                    (name, display_name, description, base_instructions, model_config,
                     bound_skills, tools, is_builtin, is_active, created_by)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
                    RETURNING id""",
                (
                    data["name"],
                    data["display_name"],
                    data.get("description", ""),
                    data["base_instructions"],
                    json.dumps(data.get("model_config", {})),
                    json.dumps(data.get("bound_skills", [])),
                    json.dumps(data.get("tools", {})),
                    data.get("is_builtin", False),
                    data.get("is_active", True),
                    user_id,
                ),
            )
            return rows[0]["id"] if rows else None
        except Exception:
            return None

    def update_agent(self, agent_id: int, data: Dict[str, Any]) -> bool:
        sets: List[str] = ["updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = []
        for key in ("display_name", "description", "base_instructions", "is_active",
                     "agent_type", "file_path", "role_description"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        for key in ("model_config", "bound_skills", "tools", "capabilities"):
            if key in data:
                sets.append(f"{key} = %s::jsonb")
                params.append(json.dumps(data[key]))
        if len(sets) == 1:
            return True
        params.append(agent_id)
        try:
            self.execute_query(
                f"UPDATE {TABLE_AGENTS} SET {', '.join(sets)} WHERE id = %s",
                tuple(params),
            )
            return True
        except Exception:
            return False

    def delete_agent(self, agent_id: int) -> bool:
        try:
            self.execute_query(f"DELETE FROM {TABLE_AGENTS} WHERE id = %s", (agent_id,))
            return True
        except Exception:
            return False

    def _ensure_agent_columns(self):
        """幂等添加 askbi_agents 新列。"""
        new_cols = [
            ("agent_type", "TEXT DEFAULT 'specialist'"),
            ("file_path", "TEXT"),
            ("role_description", "TEXT DEFAULT ''"),
            ("capabilities", "JSONB DEFAULT '[]'::jsonb"),
        ]
        for col_name, col_type in new_cols:
            try:
                self.cursor.execute(
                    f"ALTER TABLE {TABLE_AGENTS} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                )
            except Exception:
                if self.conn:
                    self.conn.rollback()
        if self.conn:
            self.conn.commit()

    def _ensure_chat_session_columns(self):
        """幂等添加 askbi_chat_session 上下文字段。"""
        new_cols = [
            ("context_type", "TEXT DEFAULT 'general'"),
            ("context_ref_id", "TEXT"),
            ("context_ref_name", "TEXT"),
        ]
        for col_name, col_type in new_cols:
            try:
                self.cursor.execute(
                    f"ALTER TABLE {TABLE_CHAT_SESSION} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                )
            except Exception:
                if self.conn:
                    self.conn.rollback()
        if self.conn:
            self.conn.commit()

    # ── Teams CRUD ──────────────────────────────────────────

    def list_teams(self) -> List[Dict[str, Any]]:
        return self.execute_query(f"SELECT * FROM {TABLE_TEAMS} ORDER BY id ASC")

    def get_team(self, team_id: int) -> Optional[Dict[str, Any]]:
        rows = self.execute_query(f"SELECT * FROM {TABLE_TEAMS} WHERE id = %s", (team_id,))
        return rows[0] if rows else None

    def create_team(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Optional[int]:
        try:
            rows = self.execute_query(
                f"""INSERT INTO {TABLE_TEAMS}
                    (name, description, mode, leader_config, max_iterations, is_active, created_by)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s)
                    RETURNING id""",
                (
                    data["name"],
                    data.get("description", ""),
                    data.get("mode", "coordinate"),
                    json.dumps(data.get("leader_config", {})),
                    data.get("max_iterations", 10),
                    data.get("is_active", True),
                    user_id,
                ),
            )
            return rows[0]["id"] if rows else None
        except Exception:
            return None

    def update_team(self, team_id: int, data: Dict[str, Any]) -> bool:
        sets: List[str] = ["updated_at = CURRENT_TIMESTAMP"]
        params: List[Any] = []
        for key in ("name", "description", "mode", "max_iterations", "is_active"):
            if key in data:
                sets.append(f"{key} = %s")
                params.append(data[key])
        if "leader_config" in data:
            sets.append("leader_config = %s::jsonb")
            params.append(json.dumps(data["leader_config"]))
        if len(sets) == 1:
            return True
        params.append(team_id)
        try:
            self.execute_query(
                f"UPDATE {TABLE_TEAMS} SET {', '.join(sets)} WHERE id = %s",
                tuple(params),
            )
            return True
        except Exception:
            return False

    def delete_team(self, team_id: int) -> bool:
        try:
            self.execute_query(f"DELETE FROM {TABLE_TEAMS} WHERE id = %s", (team_id,))
            return True
        except Exception:
            return False

    # ── Team Members CRUD ──────────────────────────────────────

    def list_team_members(self, team_id: int) -> List[Dict[str, Any]]:
        return self.execute_query(
            f"SELECT * FROM {TABLE_TEAM_MEMBERS} WHERE team_id = %s ORDER BY sort_order ASC, id ASC",
            (team_id,),
        )

    def create_team_member(self, data: Dict[str, Any]) -> Optional[int]:
        try:
            rows = self.execute_query(
                f"""INSERT INTO {TABLE_TEAM_MEMBERS}
                    (team_id, member_key, member_type, ref_agent_name, ref_workflow,
                     ref_team_id, ref_custom_flow, role, description, capabilities,
                     can_delegate_to, position, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                    RETURNING id""",
                (
                    data["team_id"],
                    data["member_key"],
                    data["member_type"],
                    data.get("ref_agent_name"),
                    data.get("ref_workflow"),
                    data.get("ref_team_id"),
                    json.dumps(data.get("ref_custom_flow")) if data.get("ref_custom_flow") else None,
                    data.get("role", ""),
                    data.get("description", ""),
                    json.dumps(data.get("capabilities", [])),
                    json.dumps(data.get("can_delegate_to", [])),
                    json.dumps(data.get("position")) if data.get("position") else None,
                    data.get("sort_order", 0),
                ),
            )
            return rows[0]["id"] if rows else None
        except Exception:
            return None

    def delete_team_members(self, team_id: int) -> bool:
        try:
            self.execute_query(f"DELETE FROM {TABLE_TEAM_MEMBERS} WHERE team_id = %s", (team_id,))
            return True
        except Exception:
            return False

    def find_teams_referencing_sub_team(self, team_id: int) -> List[str]:
        """查找引用指定团队作为子团队的其他团队名称。"""
        rows = self.execute_query(
            f"""SELECT DISTINCT t.name
                FROM {TABLE_TEAM_MEMBERS} m
                JOIN {TABLE_TEAMS} t ON t.id = m.team_id
                WHERE m.ref_team_id = %s AND m.member_type = 'sub_team'""",
            (team_id,),
        )
        return [r["name"] for r in rows]


db_utils = DatabaseUtils()
