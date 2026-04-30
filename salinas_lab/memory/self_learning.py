from __future__ import annotations

import re

from salinas_lab.memory.store import MemoryStore
from salinas_lab.models import ModelClient, ModelRouter, ModelTier


class SelfLearningLoop:
    """Hermes-inspired reflection loop for promoting useful passive memories."""

    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        client: ModelClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.store = store or MemoryStore()
        self.client = client or ModelClient(timeout=45)
        self.router = router or ModelRouter()

    def observe_chat(self, *, session_id: str, user_message: str, summary: str) -> None:
        if self._is_fallback(summary):
            summary = "The board-room response failed because the local model provider was unavailable or unauthorized."
        self.store.record_active(
            session_id,
            f"Founder asked: {user_message} | Round table summary: {summary}",
            source="chat",
            tags=["chat", "round-table"],
        )
        self.store.record_passive(
            f"Chat exchange: {user_message} -> {summary}",
            source="chat",
            session_id=session_id,
            tags=["chat"],
        )
        if self._explicit_memory_request(user_message):
            self.store.add_long_term(
                self._clean_memory_request(user_message),
                source="founder-explicit",
                target="memory",
                tags=["explicit"],
                confidence=0.9,
            )

    def observe_research(self, *, session_id: str, prompt: str, report_title: str, report_path: str) -> None:
        self.store.record_passive(
            f"Research completed: {prompt} -> {report_title} at {report_path}",
            source="research",
            session_id=session_id,
            tags=["research", "report"],
        )

    def reflect(self, limit: int = 12) -> list[str]:
        observations = self.store.recent_passive(limit=limit)
        if not observations:
            return []
        digest = "\n".join(f"- {record.text}" for record in observations)
        model = self.router.model_for(ModelTier.SMALL)
        response = self.client.chat(
            model=model,
            system=(
                "You are the OpenLogos Lab memory consolidation loop. Extract durable, "
                "reusable facts only. Do not store commands, secrets, prompt text, or temporary "
                "details. Return one bullet per memory. If nothing is durable, return NONE."
            ),
            user=digest,
            temperature=0.2,
            max_tokens=500,
        )
        memories = []
        for line in response.splitlines():
            cleaned = line.strip().lstrip("-* ").strip()
            if not cleaned or cleaned.upper() == "NONE":
                continue
            try:
                self.store.add_long_term(
                    cleaned,
                    source="self-learning-reflection",
                    target="memory",
                    tags=["reflected"],
                    confidence=0.7,
                )
                memories.append(cleaned)
            except ValueError:
                continue
        return memories

    @staticmethod
    def _explicit_memory_request(text: str) -> bool:
        return bool(re.search(r"\b(remember|memorize|keep in mind|save this)\b", text, re.I))

    @staticmethod
    def _clean_memory_request(text: str) -> str:
        return re.sub(r"\b(please\s+)?(remember|memorize|keep in mind|save this)\b[:\s]*", "", text, flags=re.I).strip()

    @staticmethod
    def _is_fallback(text: str) -> bool:
        lowered = text.lower()
        return "offline fallback generated" in lowered or "401 unauthorized" in lowered
