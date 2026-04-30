from salinas_lab.graph import DepartmentFinding, DepartmentName, LabState, ResearchRequest
from salinas_lab.reports import ReportWriter


class FakeClient:
    def chat(self, **kwargs):
        return "# Lab Report\n\n## Abstract\n\nA useful abstract.\n"


def test_report_writer_returns_artifact() -> None:
    state = LabState(request=ResearchRequest(prompt="test report"))
    state.add_finding(
        DepartmentFinding(
            department=DepartmentName.SCIENTIFIC_INQUIRY,
            actor="Scientific Researcher",
            summary="Feasible with caveats.",
            findings=["Prototype first."],
        )
    )

    report = ReportWriter(client=FakeClient()).run(state)

    assert report.title == "Lab Report"
    assert "A useful abstract" in report.abstract
