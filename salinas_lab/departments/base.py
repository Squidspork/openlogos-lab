from __future__ import annotations

from dataclasses import dataclass

from salinas_lab.graph.state import DepartmentFinding, DepartmentName, EvidenceItem, LabState
from salinas_lab.models import ModelClient, ModelRouter, ModelTier


@dataclass(frozen=True)
class DepartmentSpec:
    department: DepartmentName
    actor: str
    model_tier: ModelTier
    mission: str
    questions: tuple[str, ...]


class DepartmentAgent:
    def __init__(
        self,
        spec: DepartmentSpec,
        *,
        client: ModelClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.spec = spec
        self.client = client or ModelClient()
        self.router = router or ModelRouter()

    @property
    def model(self) -> str:
        return self.router.model_for(self.spec.model_tier)

    def run(self, state: LabState) -> DepartmentFinding:
        response = self.client.chat(
            model=self.model,
            system=self._system_prompt(),
            user=self._user_prompt(state),
            temperature=0.35,
        )
        return self._finding_from_text(response)

    def _system_prompt(self) -> str:
        questions = "\n".join(f"- {question}" for question in self.spec.questions)
        return (
            "You are a department inside OpenLogos Lab. Work with scientific seriousness, "
            "dry institutional humor, and clear accountability. Separate findings from assumptions. "
            "Do not invent source URLs.\n\n"
            f"Department mission: {self.spec.mission}\n\n"
            f"Questions to answer:\n{questions}"
        )

    def _user_prompt(self, state: LabState) -> str:
        prior = "\n\n".join(
            f"{finding.department}: {finding.summary}"
            for finding in state.department_findings.values()
        )
        memory = "\n".join(
            message["content"]
            for message in state.messages
            if message.get("role") == "memory"
        )
        return (
            f"Research request: {state.request.prompt}\n"
            f"Audience: {state.request.audience}\n"
            f"Depth: {state.request.depth}\n\n"
            f"Relevant Lab memory:\n{memory or 'No relevant Lab memory found.'}\n\n"
            f"Prior department findings:\n{prior or 'None yet.'}\n\n"
            "Return concise Markdown with sections: Summary, Findings, Assumptions, Risks, "
            "Recommendations, Evidence Notes."
        )

    def _finding_from_text(self, text: str) -> DepartmentFinding:
        bullets = [
            line.strip("- ").strip()
            for line in text.splitlines()
            if line.strip().startswith(("-", "*"))
        ]
        findings = bullets[:8] or [text[:800]]
        return DepartmentFinding(
            department=self.spec.department,
            actor=self.spec.actor,
            summary=text.splitlines()[0][:500] if text.splitlines() else text[:500],
            findings=findings,
            assumptions=["Model-generated analysis requires source verification."],
            risks=[],
            recommendations=findings[-3:] if len(findings) >= 3 else findings,
            evidence=[
                EvidenceItem(
                    title=f"{self.spec.actor} generated analysis",
                    note=text[:1000],
                    confidence=0.45,
                )
            ],
            confidence=0.55,
            model=self.model,
        )


def finding_to_markdown(finding: DepartmentFinding) -> str:
    def section(title: str, items: list[str]) -> str:
        if not items:
            return f"## {title}\n\nNone recorded.\n"
        return f"## {title}\n\n" + "\n".join(f"- {item}" for item in items) + "\n"

    return "\n".join(
        [
            f"# {finding.actor}",
            "",
            f"**Department:** `{finding.department}`",
            f"**Model:** `{finding.model or 'unknown'}`",
            f"**Confidence:** `{finding.confidence:.2f}`",
            "",
            "## Summary",
            "",
            finding.summary,
            "",
            section("Findings", finding.findings),
            section("Assumptions", finding.assumptions),
            section("Risks", finding.risks),
            section("Recommendations", finding.recommendations),
        ]
    )
