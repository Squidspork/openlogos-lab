from salinas_lab.audit import AuditLogger, SessionStore, slugify
from salinas_lab.graph import AuditEvent, ResearchRequest, SourceChannel


def test_slugify_keeps_output_folder_readable() -> None:
    assert slugify("Ideas for Apps!!!") == "ideas-for-apps"


def test_audit_log_is_append_only_jsonl(tmp_path) -> None:
    request = ResearchRequest(prompt="audit test")
    paths = SessionStore(tmp_path).create(request)
    logger = AuditLogger(paths.audit)

    first = logger.append(
        AuditEvent(
            session_id=request.session_id,
            actor="Gateway",
            action="received",
            source_channel=SourceChannel.CLI,
        )
    )
    second = logger.append(
        AuditEvent(
            session_id=request.session_id,
            actor="Director",
            action="decomposed",
            source_channel=SourceChannel.CLI,
        )
    )

    events = logger.read()

    assert [event.event_id for event in events] == [first, second]
    assert paths.audit.read_text(encoding="utf-8").count("\n") == 2
