from __future__ import annotations

from dataclasses import dataclass

from salinas_lab.graph import ResearchRequest, SourceChannel


@dataclass(frozen=True)
class IncomingMessage:
    text: str
    sender_id: str
    source_channel: SourceChannel
    thread_id: str | None = None


def normalize_message(message: IncomingMessage) -> ResearchRequest:
    return ResearchRequest(
        prompt=message.text,
        source_channel=message.source_channel,
        tags=[message.sender_id, message.thread_id or ""],
    )
