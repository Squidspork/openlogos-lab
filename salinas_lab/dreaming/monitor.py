from __future__ import annotations

import re

import httpx

from salinas_lab.dreaming.sources import DEFAULT_SOURCES, DreamSource
from salinas_lab.dreaming.topic_picker import TopicPicker
from salinas_lab.graph import ResearchMode, ResearchRequest, SourceChannel


class DreamingEngine:
    def __init__(
        self,
        *,
        sources: list[DreamSource] | None = None,
        topic_picker: TopicPicker | None = None,
    ) -> None:
        self.sources = sources or DEFAULT_SOURCES
        self.topic_picker = topic_picker or TopicPicker()

    def create_request(self) -> ResearchRequest:
        summaries = self.collect_source_summaries()
        topic = self.topic_picker.pick(summaries)
        return ResearchRequest(
            prompt=topic,
            mode=ResearchMode.DREAM,
            source_channel=SourceChannel.DREAM,
            tags=["dreaming"],
        )

    def collect_source_summaries(self) -> list[str]:
        summaries: list[str] = []
        for source in self.sources:
            try:
                response = httpx.get(str(source.url), timeout=10)
                response.raise_for_status()
                text = re.sub(r"<[^>]+>", " ", response.text)
                text = re.sub(r"\s+", " ", text).strip()
                summaries.append(f"{source.name} ({source.topic_hint}): {text[:2500]}")
            except Exception as exc:
                summaries.append(f"{source.name} unavailable: {exc}")
        return summaries
