import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class ConversationRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL REFERENCES conversations(id), created_at TEXT NOT NULL, body TEXT NOT NULL);")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def list(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute("SELECT id,title,updated_at FROM conversations ORDER BY updated_at DESC LIMIT 100").fetchall()
        return [dict(zip(["id", "title", "updated_at"], row)) for row in rows]

    def get(self, conversation_id: str) -> dict | None:
        with self.connect() as connection:
            row = connection.execute("SELECT id,title,updated_at FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            if row is None:
                return None
            messages = connection.execute("SELECT body FROM messages WHERE conversation_id=? ORDER BY rowid", (conversation_id,)).fetchall()
        return {**dict(zip(["id", "title", "updated_at"], row)), "messages": [json.loads(message[0]) for message in messages]}

    def append(self, conversation_id: str | None, question: str, answer: dict) -> dict:
        timestamp = datetime.now(timezone.utc).isoformat()
        identifier = conversation_id or uuid4().hex
        message = {**answer, "id": uuid4().hex, "question": question, "created_at": timestamp, "conversation_id": identifier}
        with self.connect() as connection:
            if conversation_id and connection.execute("SELECT 1 FROM conversations WHERE id=?", (identifier,)).fetchone() is None:
                raise ValueError("Conversation not found. Start a new conversation.")
            connection.execute("INSERT INTO conversations(id,title,updated_at) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at", (identifier, question[:80], timestamp))
            connection.execute("INSERT INTO messages VALUES(?,?,?,?)", (message["id"], identifier, timestamp, json.dumps(message, ensure_ascii=False)))
        return message
