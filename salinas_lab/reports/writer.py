from __future__ import annotations

from salinas_lab.graph.state import DepartmentName, LabState, ReportArtifact
from salinas_lab.models import ModelClient, ModelClientError, ModelRouter, ModelTier


class ReportWriter:
    def __init__(
        self,
        *,
        client: ModelClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.client = client or ModelClient()
        self.router = router or ModelRouter()

    @property
    def model(self) -> str:
        return self.router.model_for(ModelTier.SYNTHESIS)

    def run(self, state: LabState) -> ReportArtifact:
        department_digest = "\n\n".join(
            f"## {finding.actor}\n"
            f"Summary: {finding.summary}\n"
            f"Findings: {finding.findings}\n"
            f"Assumptions: {finding.assumptions}\n"
            f"Risks: {finding.risks}\n"
            f"Recommendations: {finding.recommendations}"
            for key, finding in state.department_findings.items()
            if key != DepartmentName.PUBLICATIONS
        )
        try:
            response = self.client.chat(
                model=self.model,
                system=(
                    "You are the Department of Publications and Findings at OpenLogos Lab. "
                    "Write a research-paper-style Markdown report with scientific seriousness, "
                    "accountable uncertainty, and light institutional humor. Include these sections: "
                    "Title, Abstract, Original Question, Executive Summary, Research Questions, "
                    "Use-Case Landscape, Technical and Scientific Analysis, Business and Product "
                    "Analysis, Proposed Experiments and Test Subjects, Risk and Ethics Review, "
                    "Recommendations, Open Questions, Sources and Evidence Log, Appendix."
                ),
                user=(
                    f"Original request: {state.request.prompt}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Department findings:\n{department_digest}"
                ),
                temperature=0.4,
                max_tokens=5000,
            )
        except ModelClientError as exc:
            response = self._fallback_report(state, department_digest, str(exc))
        markdown = self._ensure_report_shape(state, response)
        return ReportArtifact(
            title=self._title_from_markdown(markdown),
            abstract=self._abstract_from_markdown(markdown),
            markdown=markdown,
        )

    @staticmethod
    def _fallback_report(state: LabState, department_digest: str, reason: str) -> str:
        return (
            f"# OpenLogos Lab Findings: {state.request.prompt[:80]}\n\n"
            "## Abstract\n\n"
            "The Publications model was unavailable, so this report was assembled from the "
            "department records already produced by the pipeline.\n\n"
            "## Original Question\n\n"
            f"{state.request.prompt}\n\n"
            "## Executive Summary\n\n"
            "Some departments may be marked unavailable. Review their individual files and "
            "`audit.jsonl` before treating this as a complete research result.\n\n"
            "## Department Findings\n\n"
            f"{department_digest or 'No department findings were produced.'}\n\n"
            "## Publication Model Status\n\n"
            f"{reason}\n\n"
            "## Recommendations\n\n"
            "- Run `openlogos-lab doctor --live` to check configured models.\n"
            "- Retry the request after replacing or restarting unavailable models.\n"
            "- Treat this fallback report as an operational record, not a final research paper.\n"
        )

    @staticmethod
    def _ensure_report_shape(state: LabState, markdown: str) -> str:
        if "# " in markdown[:50] and "## Abstract" in markdown:
            return markdown
        return (
            f"# OpenLogos Lab Findings: {state.request.prompt[:80]}\n\n"
            "## Abstract\n\n"
            "This report contains the Lab's initial findings. The subject was reviewed by "
            "multiple departments and returned with only minor conceptual bruising.\n\n"
            "## Original Question\n\n"
            f"{state.request.prompt}\n\n"
            "## Department Findings\n\n"
            + markdown
            + "\n\n## Accountability Note\n\n"
            "Review `audit.jsonl` and the `departments/` folder for the underlying actions and "
            "department notes.\n"
        )

    @staticmethod
    def _title_from_markdown(markdown: str) -> str:
        for line in markdown.splitlines():
            if line.startswith("# "):
                return line.removeprefix("# ").strip()
        return "OpenLogos Lab Findings"

    @staticmethod
    def _abstract_from_markdown(markdown: str) -> str:
        lines = markdown.splitlines()
        for index, line in enumerate(lines):
            if line.strip().lower() == "## abstract":
                content: list[str] = []
                for next_line in lines[index + 1 :]:
                    if next_line.startswith("## "):
                        break
                    if next_line.strip():
                        content.append(next_line.strip())
                return " ".join(content)[:1000]
        return markdown[:1000]
