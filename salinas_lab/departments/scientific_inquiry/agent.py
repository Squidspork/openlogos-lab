from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph.state import DepartmentName
from salinas_lab.models import ModelTier


def build_agent() -> DepartmentAgent:
    return DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.SCIENTIFIC_INQUIRY,
            actor="Scientific Researcher",
            model_tier=ModelTier.TECHNICAL,
            mission="Analyze mechanisms, prior art, technical feasibility, and unknowns.",
            questions=(
                "How might the idea work in practice?",
                "What prior art or known science is relevant?",
                "Which assumptions are technically fragile?",
                "What evidence would strengthen or weaken the hypothesis?",
            ),
        )
    )
