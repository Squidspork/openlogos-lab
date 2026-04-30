from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from salinas_lab.graph.state import AuditEvent, LabState, ResearchRequest, SessionPaths


def slugify(value: str, max_length: int = 72) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return (value or "research-request")[:max_length].strip("-")


class SessionStore:
    def __init__(self, output_dir: Path | str = "outputs") -> None:
        self.output_dir = Path(output_dir)

    def create(self, request: ResearchRequest) -> SessionPaths:
        slug = slugify(request.prompt)
        root = self.output_dir / f"{request.created_at:%Y%m%d-%H%M%S}_{request.session_id}_{slug}"
        departments = root / "departments"
        evidence = root / "evidence"
        departments.mkdir(parents=True, exist_ok=False)
        evidence.mkdir(parents=True, exist_ok=False)

        paths = SessionPaths(
            root=root,
            departments=departments,
            evidence=evidence,
            report=root / "report.md",
            audit=root / "audit.jsonl",
            request=root / "request.json",
            metadata=root / "metadata.json",
        )
        paths.request.write_text(request.model_dump_json(indent=2), encoding="utf-8")
        paths.metadata.write_text(
            json.dumps(
                {
                    "session_id": request.session_id,
                    "mode": request.mode,
                    "source_channel": request.source_channel,
                    "slug": slug,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        (evidence / "sources.json").write_text("[]\n", encoding="utf-8")
        (evidence / "notes.md").write_text("# Evidence Notes\n\n", encoding="utf-8")
        return paths

    @staticmethod
    def write_department_note(state: LabState, department: str, markdown: str) -> Path:
        if state.paths is None:
            raise ValueError("state paths have not been initialized")
        path = state.paths.departments / f"{department}.md"
        path.write_text(markdown, encoding="utf-8")
        return path

    @staticmethod
    def write_report(state: LabState, markdown: str) -> Path:
        if state.paths is None:
            raise ValueError("state paths have not been initialized")
        state.paths.report.write_text(markdown, encoding="utf-8")
        return state.paths.report

    @staticmethod
    def write_evidence(state: LabState) -> None:
        if state.paths is None:
            raise ValueError("state paths have not been initialized")
        items = [item.model_dump(mode="json") for item in state.evidence]
        state.paths.evidence.joinpath("sources.json").write_text(
            json.dumps(items, indent=2), encoding="utf-8"
        )


class AuditLogger:
    def __init__(self, audit_path: Path) -> None:
        self.audit_path = audit_path

    def append(self, event: AuditEvent) -> str:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")
        return event.event_id

    def read(self) -> list[AuditEvent]:
        if not self.audit_path.exists():
            return []
        events: list[AuditEvent] = []
        for line in self.audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(AuditEvent.model_validate_json(line))
        return events


def summarize_audit(events: Iterable[AuditEvent]) -> str:
    lines = ["# Audit Summary", ""]
    for event in events:
        department = f" [{event.department}]" if event.department else ""
        lines.append(f"- {event.timestamp.isoformat()} {event.actor}{department}: {event.action}")
    return "\n".join(lines) + "\n"
