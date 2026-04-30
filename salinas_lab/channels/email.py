from salinas_lab.channels.base import IncomingMessage, normalize_message
from salinas_lab.graph import ResearchRequest, SourceChannel


def request_from_email(subject: str, body: str, sender: str) -> ResearchRequest:
    prompt = f"{subject}\n\n{body}".strip()
    return normalize_message(
        IncomingMessage(text=prompt, sender_id=sender, source_channel=SourceChannel.EMAIL)
    )
