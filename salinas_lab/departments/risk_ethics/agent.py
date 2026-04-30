from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph.state import DepartmentName
from salinas_lab.models import ModelTier


def build_agent() -> DepartmentAgent:
    return DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.RISK_ETHICS,
            actor="Risk, Ethics, and Unintended Consequences Reviewer",
            model_tier=ModelTier.TECHNICAL,
            mission="Identify feasibility, ethical, legal, security, and operational failure modes.",
            questions=(
                "What could go wrong technically or socially?",
                "What should be constrained before deployment?",
                "Where could the report overstate evidence?",
                "What follow-up checks are mandatory?",
            ),
        )
    )
