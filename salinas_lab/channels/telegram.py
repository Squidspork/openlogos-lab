from salinas_lab.channels.base import IncomingMessage, normalize_message
from salinas_lab.graph import ResearchRequest, SourceChannel


def request_from_telegram(text: str, chat_id: str) -> ResearchRequest:
    return normalize_message(
        IncomingMessage(text=text, sender_id=chat_id, source_channel=SourceChannel.TELEGRAM)
    )
