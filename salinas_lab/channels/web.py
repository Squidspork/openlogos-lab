from salinas_lab.channels.base import IncomingMessage, normalize_message
from salinas_lab.graph import ResearchRequest, SourceChannel


def request_from_web(prompt: str, user_id: str = "web-user") -> ResearchRequest:
    return normalize_message(
        IncomingMessage(text=prompt, sender_id=user_id, source_channel=SourceChannel.WEB)
    )
