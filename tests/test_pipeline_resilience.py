from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph import DepartmentName, LabState, ResearchRequest
from salinas_lab.models import ModelClientError, ModelTier
from salinas_lab.reports import ReportWriter


class FailingClient:
    def chat(self, **kwargs):
        raise ModelClientError("test model timeout")


def test_department_model_failure_becomes_unavailable_finding() -> None:
    agent = DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.DIRECTOR,
            actor="Research Director",
            model_tier=ModelTier.ORCHESTRATOR,
            mission="Test mission",
            questions=("What failed?",),
        ),
        client=FailingClient(),
    )
    state = LabState(request=ResearchRequest(prompt="test"))

    finding = agent.run(state)

    assert finding.confidence == 0
    assert "unavailable" in finding.summary
    assert finding.risks


def test_report_model_failure_becomes_fallback_report() -> None:
    state = LabState(request=ResearchRequest(prompt="test report"))
    writer = ReportWriter(client=FailingClient())

    report = writer.run(state)

    assert "Publication Model Status" in report.markdown
    assert "test model timeout" in report.markdown
