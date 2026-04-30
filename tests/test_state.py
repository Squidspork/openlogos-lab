from salinas_lab.graph import DepartmentFinding, DepartmentName, LabState, ResearchRequest


def test_research_request_strips_prompt() -> None:
    request = ResearchRequest(prompt="  ideas for science labs  ")

    assert request.prompt == "ideas for science labs"
    assert request.session_id


def test_lab_state_adds_department_finding() -> None:
    state = LabState(request=ResearchRequest(prompt="test idea"))
    finding = DepartmentFinding(
        department=DepartmentName.OPPORTUNITY_DISCOVERY,
        actor="Opportunity Scout",
        summary="Useful idea.",
        findings=["Build a small prototype."],
    )

    state.add_finding(finding)

    assert DepartmentName.OPPORTUNITY_DISCOVERY in state.department_findings
    assert state.department_findings[DepartmentName.OPPORTUNITY_DISCOVERY].actor == "Opportunity Scout"
