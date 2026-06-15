"""记忆管理：Agno MemoryManager + Mem0 + 业务画像记忆层"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from agno.db.sqlite import SqliteDb
from agno.memory.manager import MemoryManager
from agno.run import RunContext
from agno.tools.mem0 import Mem0Tools

from core import _load_config


def get_config() -> dict:
    return _load_config()


def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def get_memory_profile_store_config() -> dict:
    memory = get_config().get("memory", {})
    profile_store = memory.get("profile_store", {}) if isinstance(memory, dict) else {}
    return profile_store.copy() if isinstance(profile_store, dict) else {}


def _get_memory_config() -> dict:
    memory = get_config().get("memory", {})
    return memory if isinstance(memory, dict) else {}


def _to_psycopg2_url(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://") if url else url


def _default_memory_db_url() -> str:
    config = get_config()
    app_db = config.get("app_db_config") or {}
    if not app_db:
        return ""
    return f"postgresql://{app_db.get('user')}:{app_db.get('password')}@{app_db.get('host')}:{app_db.get('port')}/{app_db.get('dbname')}"


def _default_profile_store_config() -> dict:
    return {
        "provider": "postgres",
        "db_url": _default_memory_db_url(),
        "session_ttl_hours": 24,
        "enable_mem0_sync": True,
        "enable_event_logging": True,
    } if _default_memory_db_url() else {
        "provider": "sqlite",
        "db_path": str(get_data_dir() / "memory_profile.db"),
        "session_ttl_hours": 24,
        "enable_mem0_sync": True,
        "enable_event_logging": True,
    }


@dataclass(slots=True)
class MemoryIdentity:
    user_id: str | None = None
    session_id: str | None = None
    turn_id: str | None = None
    run_id: str | None = None


@dataclass(slots=True)
class MemoryRecord:
    id: str
    memory_type: str
    memory_kind: str
    profile_version: int
    profile_json: dict[str, Any]
    profile_text: str | None
    summary: str | None
    user_id: str | None
    session_id: str | None
    source_turn_id: str
    source_run_id: str | None
    dedupe_key: str
    status: str
    created_at: str
    updated_at: str
    last_accessed_at: str | None
    expires_at: str | None = None


@dataclass(slots=True)
class MemoryEvent:
    id: str
    memory_type: str
    memory_id: str | None
    user_id: str | None
    session_id: str | None
    turn_id: str
    run_id: str | None
    event_type: str
    payload_json: dict[str, Any] | None
    write_decision: str
    reason: str | None
    created_at: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _make_dedupe_key(scope_id: str, memory_kind: str, content: str) -> str:
    digest = hashlib.sha256(f"{scope_id}|{memory_kind}|{_normalize_text(content)}".encode("utf-8")).hexdigest()
    return digest


def _row_to_record(row: Any) -> MemoryRecord:
    raw = dict(row)
    return MemoryRecord(
        id=raw["id"],
        memory_type=raw["memory_type"],
        memory_kind=raw["memory_kind"],
        profile_version=raw["profile_version"],
        profile_json=json.loads(raw["profile_json"]) if isinstance(raw["profile_json"], str) else (raw["profile_json"] or {}),
        profile_text=raw["profile_text"],
        summary=raw["summary"],
        user_id=raw["user_id"],
        session_id=raw["session_id"],
        source_turn_id=raw["source_turn_id"],
        source_run_id=raw["source_run_id"],
        dedupe_key=raw["dedupe_key"],
        status=raw["status"],
        created_at=str(raw["created_at"]),
        updated_at=str(raw["updated_at"]),
        last_accessed_at=str(raw["last_accessed_at"]) if raw.get("last_accessed_at") else None,
        expires_at=str(raw["expires_at"]) if raw.get("expires_at") else None,
    )


class BaseProfileMemoryStore:
    def __init__(self, db_path: str | None = None, provider: str | None = None) -> None:
        config = get_memory_profile_store_config() or _default_profile_store_config()
        self.provider = provider or config.get("provider", "sqlite")
        self.session_ttl_hours = int(config.get("session_ttl_hours", 24))
        self.enable_event_logging = bool(config.get("enable_event_logging", True))
        self.db_url = config.get("db_url")
        self.db_path = None
        if self.provider == "sqlite":
            resolved_path = db_path or config.get("db_path") or str(get_data_dir() / "memory_profile.db")
            if not Path(resolved_path).is_absolute():
                resolved_path = str(get_data_dir() / Path(resolved_path).name)
            self.db_path = Path(resolved_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        elif self.provider not in {"postgres", "postgresql"}:
            raise ValueError(f"当前仅支持 sqlite/postgres profile_store，收到: {self.provider}")
        if self.provider in {"postgres", "postgresql"} and not self.db_url:
            raise ValueError("profile_store.db_url 未配置")
        self._init_tables()

    def _connect(self):
        if self.provider == "sqlite":
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        return psycopg2.connect(_to_psycopg2_url(self.db_url), cursor_factory=psycopg2.extras.RealDictCursor)

    def _placeholder(self) -> str:
        return "?" if self.provider == "sqlite" else "%s"

    def _sql(self, query: str) -> str:
        return query if self.provider == "sqlite" else query.replace("?", "%s")

    def _json_type(self) -> str:
        return "TEXT" if self.provider == "sqlite" else "JSONB"

    def _exec(self, conn, query: str, params: tuple = ()):
        cur = conn.cursor()
        cur.execute(self._sql(query), params)
        return cur

    def _init_tables(self) -> None:
        json_type = self._json_type()
        with self._connect() as conn:
            cur = conn.cursor()
            if self.provider == "sqlite":
                cur.executescript(f"""
                CREATE TABLE IF NOT EXISTS user_profile_memory (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NULL,
                    memory_kind TEXT NOT NULL,
                    profile_version INTEGER NOT NULL DEFAULT 1,
                    profile_json {json_type} NOT NULL,
                    profile_text TEXT NULL,
                    summary TEXT NULL,
                    source_turn_id TEXT NOT NULL,
                    source_run_id TEXT NULL,
                    dedupe_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed_at TEXT NULL,
                    expires_at TEXT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_user_profile_memory_user_dedupe ON user_profile_memory(user_id, dedupe_key);
                CREATE INDEX IF NOT EXISTS idx_user_profile_memory_user ON user_profile_memory(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_profile_memory_kind ON user_profile_memory(memory_kind);
                CREATE INDEX IF NOT EXISTS idx_user_profile_memory_status ON user_profile_memory(status);
                CREATE TABLE IF NOT EXISTS session_profile_memory (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    user_id TEXT NULL,
                    session_id TEXT NOT NULL,
                    memory_kind TEXT NOT NULL,
                    profile_version INTEGER NOT NULL DEFAULT 1,
                    profile_json {json_type} NOT NULL,
                    profile_text TEXT NULL,
                    summary TEXT NULL,
                    source_turn_id TEXT NOT NULL,
                    source_run_id TEXT NULL,
                    dedupe_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed_at TEXT NULL,
                    expires_at TEXT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_session_profile_memory_session_dedupe ON session_profile_memory(session_id, dedupe_key);
                CREATE INDEX IF NOT EXISTS idx_session_profile_memory_session ON session_profile_memory(session_id);
                CREATE INDEX IF NOT EXISTS idx_session_profile_memory_user ON session_profile_memory(user_id);
                CREATE INDEX IF NOT EXISTS idx_session_profile_memory_kind ON session_profile_memory(memory_kind);
                CREATE INDEX IF NOT EXISTS idx_session_profile_memory_status ON session_profile_memory(status);
                CREATE INDEX IF NOT EXISTS idx_session_profile_memory_expires_at ON session_profile_memory(expires_at);
                CREATE TABLE IF NOT EXISTS memory_events (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    memory_id TEXT NULL,
                    user_id TEXT NULL,
                    session_id TEXT NULL,
                    turn_id TEXT NOT NULL,
                    run_id TEXT NULL,
                    event_type TEXT NOT NULL,
                    payload_json {json_type} NULL,
                    write_decision TEXT NOT NULL,
                    reason TEXT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_memory_events_turn_type_event ON memory_events(turn_id, memory_type, event_type);
                CREATE INDEX IF NOT EXISTS idx_memory_events_user ON memory_events(user_id);
                CREATE INDEX IF NOT EXISTS idx_memory_events_session ON memory_events(session_id);
                CREATE INDEX IF NOT EXISTS idx_memory_events_created_at ON memory_events(created_at);
                """)
            else:
                cur.execute(f"""
                CREATE TABLE IF NOT EXISTS user_profile_memory (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NULL,
                    memory_kind TEXT NOT NULL,
                    profile_version INTEGER NOT NULL DEFAULT 1,
                    profile_json {json_type} NOT NULL,
                    profile_text TEXT NULL,
                    summary TEXT NULL,
                    source_turn_id TEXT NOT NULL,
                    source_run_id TEXT NULL,
                    dedupe_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed_at TEXT NULL,
                    expires_at TEXT NULL
                )
                """)
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_user_profile_memory_user_dedupe ON user_profile_memory(user_id, dedupe_key)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_profile_memory_user ON user_profile_memory(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_profile_memory_kind ON user_profile_memory(memory_kind)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_user_profile_memory_status ON user_profile_memory(status)")
                cur.execute(f"""
                CREATE TABLE IF NOT EXISTS session_profile_memory (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    user_id TEXT NULL,
                    session_id TEXT NOT NULL,
                    memory_kind TEXT NOT NULL,
                    profile_version INTEGER NOT NULL DEFAULT 1,
                    profile_json {json_type} NOT NULL,
                    profile_text TEXT NULL,
                    summary TEXT NULL,
                    source_turn_id TEXT NOT NULL,
                    source_run_id TEXT NULL,
                    dedupe_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed_at TEXT NULL,
                    expires_at TEXT NULL
                )
                """)
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_session_profile_memory_session_dedupe ON session_profile_memory(session_id, dedupe_key)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_profile_memory_session ON session_profile_memory(session_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_profile_memory_user ON session_profile_memory(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_profile_memory_kind ON session_profile_memory(memory_kind)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_profile_memory_status ON session_profile_memory(status)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_session_profile_memory_expires_at ON session_profile_memory(expires_at)")
                cur.execute(f"""
                CREATE TABLE IF NOT EXISTS memory_events (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    memory_id TEXT NULL,
                    user_id TEXT NULL,
                    session_id TEXT NULL,
                    turn_id TEXT NOT NULL,
                    run_id TEXT NULL,
                    event_type TEXT NOT NULL,
                    payload_json {json_type} NULL,
                    write_decision TEXT NOT NULL,
                    reason TEXT NULL,
                    created_at TEXT NOT NULL
                )
                """)
                cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_memory_events_turn_type_event ON memory_events(turn_id, memory_type, event_type)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_events_user ON memory_events(user_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_events_session ON memory_events(session_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_memory_events_created_at ON memory_events(created_at)")
            conn.commit()
            cur.close()

    def has_turn_event(self, turn_id: str, memory_type: str, event_type: str) -> bool:
        with self._connect() as conn:
            cur = self._exec(conn, "SELECT 1 FROM memory_events WHERE turn_id = ? AND memory_type = ? AND event_type = ? LIMIT 1", (turn_id, memory_type, event_type))
            row = cur.fetchone()
            cur.close()
            return row is not None

    def record_event(self, *, memory_type: str, identity: MemoryIdentity, event_type: str, write_decision: str, memory_id: str | None = None, payload: dict[str, Any] | None = None, reason: str | None = None) -> MemoryEvent | None:
        if not self.enable_event_logging:
            return None
        if not identity.turn_id:
            raise ValueError("record_event 需要 identity.turn_id")
        now = _utc_now_iso()
        event = MemoryEvent(id=str(uuid.uuid4()), memory_type=memory_type, memory_id=memory_id, user_id=identity.user_id, session_id=identity.session_id, turn_id=identity.turn_id, run_id=identity.run_id, event_type=event_type, payload_json=payload, write_decision=write_decision, reason=reason, created_at=now)
        with self._connect() as conn:
            cur = self._exec(conn, "INSERT INTO memory_events (id, memory_type, memory_id, user_id, session_id, turn_id, run_id, event_type, payload_json, write_decision, reason, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (event.id, event.memory_type, event.memory_id, event.user_id, event.session_id, event.turn_id, event.run_id, event.event_type, _json_dumps(event.payload_json) if event.payload_json is not None else None, event.write_decision, event.reason, event.created_at))
            cur.close()
            conn.commit()
        return event

    def _upsert_record(self, *, table_name: str, memory_type: str, scope_id: str, memory_kind: str, profile_json: dict[str, Any], profile_text: str, summary: str | None, identity: MemoryIdentity, expires_at: str | None = None) -> tuple[MemoryRecord, str]:
        now = _utc_now_iso()
        dedupe_key = _make_dedupe_key(scope_id, memory_kind, profile_text)
        key_column = "user_id" if table_name == "user_profile_memory" else "session_id"
        with self._connect() as conn:
            cur = self._exec(conn, f"SELECT * FROM {table_name} WHERE {key_column} = ? AND dedupe_key = ? LIMIT 1", (scope_id, dedupe_key))
            row = cur.fetchone()
            cur.close()
            if row is not None:
                record = _row_to_record(row)
                new_json_text = _json_dumps(profile_json)
                changed = new_json_text != _json_dumps(record.profile_json) or summary != record.summary
                decision = "updated" if changed else "merged"
                profile_version = record.profile_version + 1 if changed else record.profile_version
                cur = self._exec(conn, f"UPDATE {table_name} SET profile_version = ?, profile_json = ?, profile_text = ?, summary = ?, source_turn_id = ?, source_run_id = ?, updated_at = ?, last_accessed_at = ?, expires_at = COALESCE(?, expires_at), status = 'active' WHERE id = ?", (profile_version, new_json_text, profile_text, summary, identity.turn_id, identity.run_id, now, now, expires_at, record.id))
                cur.close()
                conn.commit()
                cur = self._exec(conn, f"SELECT * FROM {table_name} WHERE id = ?", (record.id,))
                updated = cur.fetchone()
                cur.close()
                return _row_to_record(updated), decision
            record_id = str(uuid.uuid4())
            cur = self._exec(conn, f"INSERT INTO {table_name} (id, memory_type, user_id, session_id, memory_kind, profile_version, profile_json, profile_text, summary, source_turn_id, source_run_id, dedupe_key, status, created_at, updated_at, last_accessed_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)", (record_id, memory_type, identity.user_id, identity.session_id, memory_kind, 1, _json_dumps(profile_json), profile_text, summary, identity.turn_id, identity.run_id, dedupe_key, now, now, now, expires_at))
            cur.close()
            conn.commit()
            cur = self._exec(conn, f"SELECT * FROM {table_name} WHERE id = ?", (record_id,))
            inserted = cur.fetchone()
            cur.close()
            return _row_to_record(inserted), "written"

    def upsert_user_profile(self, *, user_id: str, memory_kind: str, profile_json: dict[str, Any], profile_text: str, summary: str | None, identity: MemoryIdentity) -> tuple[MemoryRecord, str]:
        return self._upsert_record(table_name="user_profile_memory", memory_type="user_profile", scope_id=user_id, memory_kind=memory_kind, profile_json=profile_json, profile_text=profile_text, summary=summary, identity=identity)

    def upsert_session_profile(self, *, session_id: str, memory_kind: str, profile_json: dict[str, Any], profile_text: str, summary: str | None, identity: MemoryIdentity, expires_at: str | None = None) -> tuple[MemoryRecord, str]:
        return self._upsert_record(table_name="session_profile_memory", memory_type="session_profile", scope_id=session_id, memory_kind=memory_kind, profile_json=profile_json, profile_text=profile_text, summary=summary, identity=identity, expires_at=expires_at)

    def get_user_profiles(self, user_id: str) -> list[MemoryRecord]:
        with self._connect() as conn:
            cur = self._exec(conn, "SELECT * FROM user_profile_memory WHERE user_id = ? AND status = 'active' ORDER BY updated_at DESC", (user_id,))
            rows = cur.fetchall()
            cur.close()
        return [_row_to_record(row) for row in rows]

    def get_session_profiles(self, session_id: str, include_expired: bool = False) -> list[MemoryRecord]:
        now = _utc_now_iso()
        with self._connect() as conn:
            if include_expired:
                cur = self._exec(conn, "SELECT * FROM session_profile_memory WHERE session_id = ? ORDER BY updated_at DESC", (session_id,))
            else:
                cur = self._exec(conn, "SELECT * FROM session_profile_memory WHERE session_id = ? AND status = 'active' AND (expires_at IS NULL OR expires_at > ?) ORDER BY updated_at DESC", (session_id, now))
            rows = cur.fetchall()
            cur.close()
        return [_row_to_record(row) for row in rows]

    def list_events(self) -> list[MemoryEvent]:
        with self._connect() as conn:
            cur = self._exec(conn, "SELECT * FROM memory_events ORDER BY created_at ASC")
            rows = cur.fetchall()
            cur.close()
        return [MemoryEvent(id=row["id"], memory_type=row["memory_type"], memory_id=row["memory_id"], user_id=row["user_id"], session_id=row["session_id"], turn_id=row["turn_id"], run_id=row["run_id"], event_type=row["event_type"], payload_json=json.loads(row["payload_json"]) if isinstance(row["payload_json"], str) and row["payload_json"] else (row["payload_json"] or None), write_decision=row["write_decision"], reason=row["reason"], created_at=str(row["created_at"])) for row in rows]

    def expire_sessions(self, now: datetime | None = None) -> int:
        current = (now or _utc_now()).isoformat()
        with self._connect() as conn:
            cur = self._exec(conn, "UPDATE session_profile_memory SET status = 'expired', updated_at = ? WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?", (current, current))
            count = cur.rowcount
            cur.close()
            conn.commit()
            return count

    def clear_session(self, session_id: str) -> int:
        now = _utc_now_iso()
        with self._connect() as conn:
            cur = self._exec(conn, "UPDATE session_profile_memory SET status = 'archived', updated_at = ? WHERE session_id = ? AND status = 'active'", (now, session_id))
            count = cur.rowcount
            cur.close()
            conn.commit()
            return count


class BaseProfileMemory:
    memory_type = "base"

    def __init__(self, store: BaseProfileMemoryStore | None = None, mem0_tool: Mem0Tools | None = None) -> None:
        self.store = store or BaseProfileMemoryStore()
        self.mem0_tool = mem0_tool
        profile_store_cfg = get_memory_profile_store_config()
        self.enable_mem0_sync = bool(profile_store_cfg.get("enable_mem0_sync", True))

    def _ensure_identity(self, identity: MemoryIdentity, *, require_user: bool = False, require_session: bool = False) -> None:
        if require_user and not identity.user_id:
            raise ValueError("需要 identity.user_id")
        if require_session and not identity.session_id:
            raise ValueError("需要 identity.session_id")
        if not identity.turn_id:
            raise ValueError("需要 identity.turn_id")

    def _make_profile_text(self, *, scope: str, memory_kind: str, identity: MemoryIdentity, text: str) -> str:
        lines = [f"[scope={scope}]", f"[type={memory_kind}]"]
        if identity.user_id:
            lines.append(f"[user_id={identity.user_id}]")
        if identity.session_id:
            lines.append(f"[session_id={identity.session_id}]")
        lines.append(_normalize_text(text))
        return "\n".join(lines)

    def _make_profile_json(self, *, scope: str, memory_kind: str, identity: MemoryIdentity, text: str) -> dict[str, Any]:
        return {
            "scope": scope,
            "memory_kind": memory_kind,
            "user_id": identity.user_id,
            "session_id": identity.session_id,
            "text": _normalize_text(text),
        }

    def _sync_mem0(self, identity: MemoryIdentity, content: str) -> None:
        if not self.enable_mem0_sync or self.mem0_tool is None:
            return
        run_context = RunContext(
            run_id=identity.run_id or str(uuid.uuid4()),
            session_id=identity.session_id or str(uuid.uuid4()),
            user_id=identity.user_id or "anonymous",
        )
        self.mem0_tool.add_memory(run_context, content)

    def search(self, query: str, identity: MemoryIdentity, limit: int = 5) -> list[MemoryRecord]:
        raise NotImplementedError

    def build_context(self, query: str, identity: MemoryIdentity, limit: int = 5) -> str:
        records = self.search(query=query, identity=identity, limit=limit)
        if not records:
            return ""
        lines = []
        for item in records[:limit]:
            text = item.profile_text or item.summary or ""
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)


class UserProfileMemory(BaseProfileMemory):
    memory_type = "user_profile"

    def _remember(self, memory_kind: str, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        self._ensure_identity(identity, require_user=True)
        normalized = _normalize_text(text)
        if not normalized:
            self.store.record_event(memory_type=self.memory_type, identity=identity, event_type="skip", write_decision="skipped", payload={"memory_kind": memory_kind}, reason="empty_text")
            return None
        profile_text = self._make_profile_text(scope="user_profile", memory_kind=memory_kind, identity=identity, text=normalized)
        profile_json = self._make_profile_json(scope="user_profile", memory_kind=memory_kind, identity=identity, text=normalized)
        record, decision = self.store.upsert_user_profile(user_id=identity.user_id or "", memory_kind=memory_kind, profile_json=profile_json, profile_text=profile_text, summary=normalized, identity=identity)
        self.store.record_event(memory_type=self.memory_type, identity=identity, event_type="write", write_decision=decision, memory_id=record.id, payload={"memory_kind": memory_kind, "summary": normalized}, reason=None)
        self._sync_mem0(identity, profile_text)
        return record

    def remember_preference(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("preference", text, identity)

    def remember_background(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("background", text, identity)

    def remember_constraint(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("constraint", text, identity)

    def remember_goal(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("goal", text, identity)

    def search(self, query: str, identity: MemoryIdentity, limit: int = 5) -> list[MemoryRecord]:
        self._ensure_identity(identity, require_user=True)
        records = self.store.get_user_profiles(identity.user_id or "")
        normalized_query = _normalize_text(query).lower()
        if not normalized_query:
            return records[:limit]
        matched = [r for r in records if normalized_query in (r.profile_text or "").lower() or normalized_query in (r.summary or "").lower()]
        return (matched or records)[:limit]


class SessionProfileMemory(BaseProfileMemory):
    memory_type = "session_profile"

    def _expires_at(self) -> str:
        return (_utc_now() + timedelta(hours=self.store.session_ttl_hours)).isoformat()

    def _remember(self, memory_kind: str, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        self._ensure_identity(identity, require_session=True)
        normalized = _normalize_text(text)
        if not normalized:
            self.store.record_event(memory_type=self.memory_type, identity=identity, event_type="skip", write_decision="skipped", payload={"memory_kind": memory_kind}, reason="empty_text")
            return None
        profile_text = self._make_profile_text(scope="session_profile", memory_kind=memory_kind, identity=identity, text=normalized)
        profile_json = self._make_profile_json(scope="session_profile", memory_kind=memory_kind, identity=identity, text=normalized)
        record, decision = self.store.upsert_session_profile(session_id=identity.session_id or "", memory_kind=memory_kind, profile_json=profile_json, profile_text=profile_text, summary=normalized, identity=identity, expires_at=self._expires_at())
        self.store.record_event(memory_type=self.memory_type, identity=identity, event_type="write", write_decision=decision, memory_id=record.id, payload={"memory_kind": memory_kind, "summary": normalized}, reason=None)
        self._sync_mem0(identity, profile_text)
        return record

    def remember_goal(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("goal", text, identity)

    def remember_subject(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("subject", text, identity)

    def remember_decision(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("decision", text, identity)

    def remember_state(self, text: str, identity: MemoryIdentity) -> MemoryRecord | None:
        return self._remember("state", text, identity)

    def search(self, query: str, identity: MemoryIdentity, limit: int = 5) -> list[MemoryRecord]:
        self._ensure_identity(identity, require_session=True)
        records = self.store.get_session_profiles(identity.session_id or "")
        normalized_query = _normalize_text(query).lower()
        if not normalized_query:
            return records[:limit]
        matched = [r for r in records if normalized_query in (r.profile_text or "").lower() or normalized_query in (r.summary or "").lower()]
        return (matched or records)[:limit]

    def clear(self, session_id: str) -> int:
        return self.store.clear_session(session_id)


def create_memory_db(db_path: str | None = None) -> Any:
    """创建记忆数据库实例，严格从 config 读取 provider 与连接配置。"""
    config = get_config()
    mem_cfg = _get_memory_config() or {}
    provider = mem_cfg.get("db_provider", "sqlite")
    if provider == "sqlite":
        resolved_path = db_path
        if resolved_path is None:
            resolved_path = mem_cfg.get("db_path")
        if resolved_path is None:
            resolved_path = str(get_data_dir() / "memory.db")
        elif not Path(resolved_path).is_absolute():
            resolved_path = str(get_data_dir() / Path(resolved_path).name)
        Path(resolved_path).parent.mkdir(parents=True, exist_ok=True)
        return SqliteDb(db_file=resolved_path, memory_table=mem_cfg.get("memory_table", "agent_memories"))
    if provider in {"postgres", "postgresql"}:
        from agno.db.postgres import PostgresDb
        db_url = mem_cfg.get("db_url") or _default_memory_db_url()
        if not db_url:
            raise ValueError("memory.db_url 未配置")
        return PostgresDb(db_url=db_url, memory_table=mem_cfg.get("memory_table", "agent_memories"))
    raise ValueError(f"暂不支持的 memory.db_provider: {provider}")


def attach_memory(agent: Any, memory_manager: MemoryManager, db: Any, mem_cfg: dict) -> Any:
    agent.db = db
    agent.memory_manager = memory_manager
    agent.enable_agentic_memory = mem_cfg.get("enable_agentic_memory", True)
    agent.update_memory_on_run = mem_cfg.get("update_memory_on_run", True)
    return agent


def attach_mem0(agent: Any, tools: Mem0Tools) -> Any:
    if agent.tools is None:
        agent.tools = []
    agent.tools.append(tools)
    return agent


def create_agent_memory_bundle(db_path: str | None = None) -> tuple[Any, MemoryManager]:
    config = get_config()
    mem_cfg = _get_memory_config() or {}
    db = create_memory_db(db_path)
    manager = MemoryManager(db=db, update_memories=mem_cfg.get("update_memory_on_run", True), add_memories=mem_cfg.get("enable_agentic_memory", True))
    return db, manager


def attach_mem0(agent: Any, tools: Mem0Tools) -> Any:
    if agent.tools is None:
        agent.tools = []
    agent.tools.append(tools)
    return agent


def build_agent_memory(agent: Any, user_id: str | None = None, db_path: str | None = None) -> Any:
    mem_cfg = get_config()["memory"]
    provider = mem_cfg.get("provider", "memory_manager")
    if provider == "mem0":
        mode = mem_cfg.get("mem0_mode", "platform")
        if mode == "platform":
            api_key = mem_cfg.get("mem0_api_key")
            if not api_key:
                raise ValueError("Mem0 平台模式要求配置 memory.mem0_api_key")
            tools = Mem0Tools(api_key=api_key, user_id=user_id, infer=mem_cfg.get("mem0_infer", True))
            return attach_mem0(agent, tools)
        if mode == "oss":
            mem0_config = mem_cfg.get("mem0_config")
            if not isinstance(mem0_config, dict) or not mem0_config:
                raise ValueError("Mem0 开源模式要求配置 memory.mem0_config")
            tools = Mem0Tools(config=mem0_config, user_id=user_id, infer=mem_cfg.get("mem0_infer", True))
            return attach_mem0(agent, tools)
        raise ValueError(f"不支持的 memory.mem0_mode: {mode}")
    if provider != "memory_manager":
        raise ValueError(f"不支持的 memory.provider: {provider}")
    db, manager = create_agent_memory_bundle(db_path)
    return attach_memory(agent, manager, db, mem_cfg)


class MemoryPlugin:
    def __init__(self) -> None:
        self._config = {"memory": _get_memory_config()} if _get_memory_config() else {"memory": {}}

    def create_db(self, db_path: str | None = None) -> Any:
        return create_memory_db(db_path)

    def create_manager(self, db_path: str | None = None) -> MemoryManager:
        _, manager = create_agent_memory_bundle(db_path)
        return manager

    def create_bundle(self, db_path: str | None = None) -> tuple[Any, MemoryManager]:
        return create_agent_memory_bundle(db_path)

    def create_mem0_tools(self, user_id: str | None = None) -> Any:
        mem_cfg = self._config["memory"]
        mode = mem_cfg.get("mem0_mode", "platform")
        if mode == "platform":
            if not mem_cfg.get("mem0_api_key"):
                raise ValueError("Mem0 平台模式要求配置 memory.mem0_api_key")
            return Mem0Tools(api_key=mem_cfg["mem0_api_key"], user_id=user_id, infer=mem_cfg.get("mem0_infer", True))
        if mode == "oss":
            mem0_config = mem_cfg.get("mem0_config")
            if not isinstance(mem0_config, dict) or not mem0_config:
                raise ValueError("Mem0 开源模式要求配置 memory.mem0_config")
            history_db_path = mem0_config.get("history_db_path")
            if history_db_path:
                Path(history_db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            return Mem0Tools(config=mem0_config, user_id=user_id, infer=mem_cfg.get("mem0_infer", True))
        raise ValueError(f"不支持的 memory.mem0_mode: {mode}")

    def apply_memory_to_agent(self, agent: Any, user_id: str | None = None) -> Any:
        return build_agent_memory(agent, user_id=user_id)

    def create_profile_store(self, db_path: str | None = None) -> BaseProfileMemoryStore:
        return BaseProfileMemoryStore(db_path=db_path)

    def create_user_profile_memory(self, *, db_path: str | None = None, mem0_tool: Mem0Tools | None = None) -> UserProfileMemory:
        return UserProfileMemory(store=self.create_profile_store(db_path), mem0_tool=mem0_tool)

    def create_session_profile_memory(self, *, db_path: str | None = None, mem0_tool: Mem0Tools | None = None) -> SessionProfileMemory:
        return SessionProfileMemory(store=self.create_profile_store(db_path), mem0_tool=mem0_tool)
