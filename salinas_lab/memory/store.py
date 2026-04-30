from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, Field

MEMORY_DELIMITER = "\n§\n"


class MemoryLayer(StrEnum):
    ACTIVE = "active"
    PASSIVE = "passive"
    LONG_TERM = "long_term"


class MemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    layer: MemoryLayer
    text: str
    source: str
    session_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class MemoryStore:
    """Three-layer file memory for the Lab.

    Active memory is per-session JSONL, passive memory is an append-only observation log, and
    long-term memory is curated Markdown using a Hermes-style delimiter.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        load_dotenv()
        memory_root: Path | str = root if root is not None else os.getenv("SALINAS_MEMORY_DIR", "memory")
        self.root = Path(memory_root)
        self.active_dir = self.root / "active"
        self.passive_path = self.root / "passive" / "observations.jsonl"
        self.long_term_path = self.root / "long_term" / "MEMORY.md"
        self.user_path = self.root / "long_term" / "USER.md"
        self._ensure()

    def _ensure(self) -> None:
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.passive_path.parent.mkdir(parents=True, exist_ok=True)
        self.long_term_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.long_term_path.exists():
            self.long_term_path.write_text("", encoding="utf-8")
        if not self.user_path.exists():
            self.user_path.write_text("", encoding="utf-8")

    def record_active(self, session_id: str, text: str, source: str, tags: list[str] | None = None) -> MemoryRecord:
        record = MemoryRecord(
            layer=MemoryLayer.ACTIVE,
            text=self._sanitize(text),
            source=source,
            session_id=session_id,
            tags=tags or [],
        )
        self._append_jsonl(self.active_dir / f"{session_id}.jsonl", record)
        return record

    def record_passive(self, text: str, source: str, session_id: str | None = None, tags: list[str] | None = None) -> MemoryRecord:
        record = MemoryRecord(
            layer=MemoryLayer.PASSIVE,
            text=self._sanitize(text),
            source=source,
            session_id=session_id,
            tags=tags or [],
            confidence=0.45,
        )
        self._append_jsonl(self.passive_path, record)
        return record

    def add_long_term(
        self,
        text: str,
        *,
        source: str = "manual",
        target: str = "memory",
        tags: list[str] | None = None,
        confidence: float = 0.8,
    ) -> MemoryRecord:
        record = MemoryRecord(
            layer=MemoryLayer.LONG_TERM,
            text=self._sanitize(text),
            source=source,
            tags=tags or [],
            confidence=confidence,
        )
        path = self.user_path if target == "user" else self.long_term_path
        existing = self._read_long_term(path)
        if record.text not in {item.text for item in existing}:
            with path.open("a", encoding="utf-8") as handle:
                if path.stat().st_size > 0:
                    handle.write(MEMORY_DELIMITER)
                handle.write(record.model_dump_json())
                handle.write("\n")
        return record

    def recent_active(self, session_id: str, limit: int = 8) -> list[MemoryRecord]:
        return self._read_jsonl(self.active_dir / f"{session_id}.jsonl")[-limit:]

    def recent_passive(self, limit: int = 20) -> list[MemoryRecord]:
        return self._read_jsonl(self.passive_path)[-limit:]

    def long_term(self) -> list[MemoryRecord]:
        return self._read_long_term(self.long_term_path) + self._read_long_term(self.user_path)

    def search(self, query: str, limit: int = 8) -> list[MemoryRecord]:
        terms = {term for term in re.split(r"\W+", query.lower()) if len(term) > 2}
        if not terms:
            return []
        records = self.long_term() + self.recent_passive(limit=50)
        scored: list[tuple[int, MemoryRecord]] = []
        for record in records:
            haystack = set(re.split(r"\W+", record.text.lower()))
            score = len(terms & haystack)
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].timestamp), reverse=True)
        return [record for _, record in scored[:limit]]

    def context_for(self, query: str, session_id: str | None = None, limit: int = 8) -> str:
        records = self.search(query, limit=limit)
        if session_id:
            records = self.recent_active(session_id, limit=4) + records
        if not records:
            return "No relevant Lab memory found."
        return "\n".join(f"- [{record.layer}] {record.text}" for record in records[:limit])

    def status(self) -> dict[str, int | str]:
        return {
            "root": str(self.root),
            "active_sessions": len(list(self.active_dir.glob("*.jsonl"))),
            "passive_observations": len(self._read_jsonl(self.passive_path)),
            "long_term_memories": len(self._read_long_term(self.long_term_path)),
            "user_memories": len(self._read_long_term(self.user_path)),
        }

    def reset(self) -> None:
        for path in self.active_dir.glob("*.jsonl"):
            path.unlink(missing_ok=True)
        self.passive_path.unlink(missing_ok=True)
        self.long_term_path.unlink(missing_ok=True)
        self.user_path.unlink(missing_ok=True)
        self._ensure()

    @staticmethod
    def _append_jsonl(path: Path, record: MemoryRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[MemoryRecord]:
        if not path.exists():
            return []
        records = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(MemoryRecord.model_validate_json(line))
        return records

    @staticmethod
    def _read_long_term(path: Path) -> list[MemoryRecord]:
        if not path.exists():
            return []
        records = []
        for chunk in path.read_text(encoding="utf-8").split(MEMORY_DELIMITER):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                records.append(MemoryRecord.model_validate_json(chunk))
            except Exception:
                records.append(
                    MemoryRecord(
                        layer=MemoryLayer.LONG_TERM,
                        text=chunk,
                        source="legacy",
                        confidence=0.5,
                    )
                )
        return records

    @staticmethod
    def _sanitize(text: str) -> str:
        text = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2066-\u2069]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            raise ValueError("memory text cannot be blank")
        suspicious = ("ignore previous", "system prompt", "developer message", "tool call")
        if any(token in text.lower() for token in suspicious):
            raise ValueError("memory text looks like prompt injection, refusing to store it")
        return text[:2000]


def records_to_markdown(records: list[MemoryRecord]) -> str:
    if not records:
        return "No memory records found."
    lines = []
    for record in records:
        lines.append(
            f"- `{record.layer}` `{record.source}` `{record.confidence:.2f}` "
            f"{record.timestamp.isoformat()}: {record.text}"
        )
    return "\n".join(lines)
