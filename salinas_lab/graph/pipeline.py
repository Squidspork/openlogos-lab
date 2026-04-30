from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from salinas_lab.audit import AuditLogger, SessionStore
from salinas_lab.departments.base import DepartmentAgent, finding_to_markdown
from salinas_lab.departments.director.agent import build_agent as build_director
from salinas_lab.departments.human_testing.agent import build_agent as build_human_testing
from salinas_lab.departments.opportunity_discovery.agent import build_agent as build_opportunity
from salinas_lab.departments.product_applications.agent import build_agent as build_product
from salinas_lab.departments.risk_ethics.agent import build_agent as build_risk
from salinas_lab.departments.scientific_inquiry.agent import build_agent as build_science
from salinas_lab.graph.state import AuditEvent, DepartmentName, LabState, ResearchRequest
from salinas_lab.memory import MemoryStore, SelfLearningLoop
from salinas_lab.reports import ReportWriter

DepartmentFactory = Callable[[], DepartmentAgent]
ProgressCallback = Callable[[dict[str, Any]], None]


class ResearchPipeline:
    def __init__(
        self,
        *,
        output_dir: Path | str | None = None,
        departments: list[DepartmentFactory] | None = None,
        report_writer: ReportWriter | None = None,
        progress_callback: ProgressCallback | None = None,
        memory_store: MemoryStore | None = None,
    ) -> None:
        load_dotenv()
        resolved_output_dir: Path | str = (
            output_dir if output_dir is not None else os.getenv("SALINAS_OUTPUT_DIR", "outputs")
        )
        self.store = SessionStore(resolved_output_dir)
        self.departments = departments or [
            build_director,
            build_opportunity,
            build_science,
            build_product,
            build_human_testing,
            build_risk,
        ]
        self.report_writer = report_writer or ReportWriter()
        self.progress_callback = progress_callback
        self.memory_store = memory_store or MemoryStore()
        self.learning = SelfLearningLoop(store=self.memory_store)

    def run(self, request: ResearchRequest) -> LabState:
        paths = self.store.create(request)
        logger = AuditLogger(paths.audit)
        state = LabState(request=request, paths=paths, status="running")
        memory_context = self.memory_store.context_for(request.prompt, session_id=request.session_id)
        state.messages.append({"role": "memory", "content": memory_context})
        self.memory_store.record_active(
            request.session_id,
            f"Research request started: {request.prompt}",
            source="research",
            tags=["research", "request"],
        )
        self._emit("session_created", actor="Gateway", message=f"Session folder: {paths.root}")
        self._audit(
            state,
            logger,
            actor="Gateway",
            department=None,
            action="research_request_received",
            input_summary=request.prompt,
            output_summary=f"Created session folder {paths.root}; memory context loaded.",
        )

        for factory in self.departments:
            agent = factory()
            self._run_department(state, logger, agent)

        self._run_accountability_gate(state, logger)
        self._emit(
            "department_started",
            actor="Department of Publications and Findings",
            department=DepartmentName.PUBLICATIONS,
            message="Publications is assembling the final specimen paperwork.",
            model=self.report_writer.model,
        )
        report = self.report_writer.run(state)
        report.path = self.store.write_report(state, report.markdown)
        state.report = report
        state.status = "completed"
        self.store.write_evidence(state)
        self._audit(
            state,
            logger,
            actor="Department of Publications and Findings",
            department=DepartmentName.PUBLICATIONS,
            action="final_report_written",
            input_summary=f"{len(state.department_findings)} department findings",
            output_summary=str(report.path),
            model=self.report_writer.model,
        )
        self._emit(
            "department_completed",
            actor="Department of Publications and Findings",
            department=DepartmentName.PUBLICATIONS,
            message=f"Report sealed and labeled: {report.path}",
            model=self.report_writer.model,
        )
        self._emit("completed", actor="Gateway", message=str(report.path))
        self.learning.observe_research(
            session_id=request.session_id,
            prompt=request.prompt,
            report_title=report.title,
            report_path=str(report.path),
        )
        return state

    def _run_department(self, state: LabState, logger: AuditLogger, agent: DepartmentAgent) -> None:
        self._emit(
            "department_started",
            actor=agent.spec.actor,
            department=agent.spec.department,
            message="Lights on. Specimen accepted for departmental examination.",
            model=agent.model,
        )
        self._audit(
            state,
            logger,
            actor=agent.spec.actor,
            department=agent.spec.department,
            action="department_started",
            input_summary=state.request.prompt,
            output_summary="Department accepted specimen.",
            model=agent.model,
        )
        finding = agent.run(state)
        state.add_finding(finding)
        self.store.write_department_note(state, finding.department, finding_to_markdown(finding))
        self._emit(
            "department_completed",
            actor=agent.spec.actor,
            department=agent.spec.department,
            message=finding.summary,
            model=agent.model,
        )
        self._audit(
            state,
            logger,
            actor=agent.spec.actor,
            department=agent.spec.department,
            action="department_completed",
            input_summary=state.request.prompt,
            output_summary=finding.summary,
            model=agent.model,
        )

    def _run_accountability_gate(self, state: LabState, logger: AuditLogger) -> None:
        self._emit(
            "department_started",
            actor="Feasibility and Accountability Gate",
            department=DepartmentName.RISK_ETHICS,
            message="The Lab is checking its own homework. Please stand behind the yellow line.",
        )
        contradictions = []
        if not state.department_findings:
            contradictions.append("No department findings were produced.")
        if not state.evidence:
            contradictions.append("No evidence records were attached.")
        if contradictions:
            state.risks.extend(contradictions)
        self._audit(
            state,
            logger,
            actor="Feasibility and Accountability Gate",
            department=DepartmentName.RISK_ETHICS,
            action="accountability_gate_checked",
            input_summary=f"{len(state.department_findings)} findings, {len(state.evidence)} evidence items",
            output_summary="; ".join(contradictions) or "No blocking accountability issues detected.",
        )
        self._emit(
            "department_completed",
            actor="Feasibility and Accountability Gate",
            department=DepartmentName.RISK_ETHICS,
            message="; ".join(contradictions) or "No blocking accountability issues detected.",
        )

    def _audit(
        self,
        state: LabState,
        logger: AuditLogger,
        *,
        actor: str,
        department: DepartmentName | None,
        action: str,
        input_summary: str = "",
        output_summary: str = "",
        model: str | None = None,
    ) -> None:
        event = AuditEvent(
            session_id=state.request.session_id,
            actor=actor,
            department=department,
            action=action,
            input_summary=input_summary[:1000],
            output_summary=output_summary[:1000],
            source_channel=state.request.source_channel,
            model=model,
        )
        state.audit_events.append(logger.append(event))

    def _emit(self, event: str, **payload: Any) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback({"event": event, **payload})
