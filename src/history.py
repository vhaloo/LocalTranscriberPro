"""Persistent session history with a local index and portable folder log."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from platformdirs import user_data_dir


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    created_at: str
    title: str
    task: str
    text_path: str
    json_path: str
    model: str
    device: str
    duration_seconds: float
    segment_count: int
    word_count: int
    preview: str

    @classmethod
    def create(
        cls,
        *,
        title: str,
        task: str,
        text_path: Path,
        json_path: Path,
        model: str,
        device: str,
        segments: list[dict[str, Any]],
    ) -> SessionRecord:
        joined = " ".join(str(item.get("text", "")).strip() for item in segments).strip()
        duration = max((float(item.get("end", 0.0)) for item in segments), default=0.0)
        return cls(
            session_id=uuid.uuid4().hex,
            created_at=datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
            title=title,
            task=task,
            text_path=str(text_path.resolve()),
            json_path=str(json_path.resolve()),
            model=model,
            device=device,
            duration_seconds=duration,
            segment_count=len(segments),
            word_count=len(joined.split()),
            preview=joined[:280],
        )


class HistoryStore:
    def __init__(self, database_path: Path | None = None):
        data_dir = Path(user_data_dir("LocalTranscriberPro", "Vhaloo"))
        self.database_path = database_path or data_dir / "history.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    title TEXT NOT NULL,
                    task TEXT NOT NULL,
                    text_path TEXT NOT NULL UNIQUE,
                    json_path TEXT NOT NULL,
                    model TEXT NOT NULL,
                    device TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    segment_count INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    preview TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS sessions_created_at ON sessions(created_at DESC)"
            )

    def add(self, record: SessionRecord, folder_log: bool = True) -> None:
        values = asdict(record)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, created_at, title, task, text_path, json_path, model, device,
                 duration_seconds, segment_count, word_count, preview)
                VALUES (:session_id, :created_at, :title, :task, :text_path, :json_path,
                        :model, :device, :duration_seconds, :segment_count, :word_count, :preview)
                """,
                values,
            )
        if folder_log:
            log_path = Path(record.text_path).parent / "LocalTranscriberPro-history.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(values, ensure_ascii=False) + "\n")

    def list_sessions(self, limit: int = 250) -> list[SessionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [SessionRecord(**dict(row)) for row in rows]

    def index_existing(self, output_folder: Path) -> int:
        """Make exports from older versions visible without modifying them."""
        if not output_folder.exists():
            return 0
        with self._connect() as connection:
            indexed = connection.execute("SELECT text_path, task FROM sessions").fetchall()
            known = {row[0] for row in indexed}
            for text_value, task in indexed:
                text_path = Path(text_value)
                if task == "legacy" and text_path.exists():
                    created = datetime.fromtimestamp(
                        text_path.stat().st_mtime, tz=datetime.now().astimezone().tzinfo
                    ).isoformat(timespec="seconds")
                    connection.execute(
                        "UPDATE sessions SET created_at = ? WHERE text_path = ?",
                        (created, text_value),
                    )
        added = 0
        for json_path in sorted(output_folder.glob("*.json")):
            text_path = json_path.with_suffix(".txt")
            if str(text_path.resolve()) in known or not text_path.exists():
                continue
            try:
                segments = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            if not isinstance(segments, list):
                continue
            record = SessionRecord.create(
                title=text_path.stem,
                task="legacy",
                text_path=text_path,
                json_path=json_path,
                model="",
                device="",
                segments=segments,
            )
            self.add(record, folder_log=False)
            added += 1
        return added

    @staticmethod
    def load_segments(record: SessionRecord) -> list[dict[str, Any]]:
        data = json.loads(Path(record.json_path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("The history entry does not contain a segment list.")
        return data
