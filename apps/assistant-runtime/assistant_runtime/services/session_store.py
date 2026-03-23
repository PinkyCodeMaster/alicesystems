from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from assistant_runtime.models import SessionMessage


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def create_session(self) -> str:
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        now = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO sessions (id, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (session_id, now, now),
            )
            connection.commit()
        return session_id

    def ensure_session(self, session_id: str | None) -> str:
        if not session_id:
            return self.create_session()

        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                now = _utc_now()
                connection.execute(
                    """
                    INSERT INTO sessions (id, created_at, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (session_id, now, now),
                )
                connection.commit()
        return session_id

    def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        mode: str | None = None,
        success: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionMessage:
        created_at = _utc_now()
        payload = json.dumps(metadata or {}, separators=(",", ":"))
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages (session_id, role, content, created_at, mode, success, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, role, content, created_at, mode, success, payload),
            )
            connection.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (created_at, session_id),
            )
            connection.commit()
            message_id = int(cursor.lastrowid)
        return SessionMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            created_at=created_at,
            mode=mode,
            success=success,
            metadata=metadata or {},
        )

    def list_messages(self, *, session_id: str, limit: int | None = None) -> list[SessionMessage]:
        query = """
            SELECT id, session_id, role, content, created_at, mode, success, metadata_json
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
        """
        params: list[Any] = [session_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()

        messages = [
            SessionMessage(
                id=int(row["id"]),
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
                mode=row["mode"],
                success=(None if row["success"] is None else bool(row["success"])),
                metadata=json.loads(row["metadata_json"] or "{}"),
            )
            for row in reversed(rows)
        ]
        return messages

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    mode TEXT NULL,
                    success INTEGER NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        with self._lock:
            connection = sqlite3.connect(self.path)
            connection.row_factory = sqlite3.Row
            return connection


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
