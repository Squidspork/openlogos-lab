from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph.state import DepartmentName
from salinas_lab.models import ModelTier


def build_agent() -> DepartmentAgent:
    return DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.OPPORTUNITY_DISCOVERY,
            actor="Opportunity Scout",
            model_tier=ModelTier.SMALL,
            mission="Extrapolate use cases, beneficiaries, and adjacent opportunities.",
            questions=(
                "What could this idea become?",
                "Who would care about it?",
                "Which use cases are obvious, strange, or commercially interesting?",
                "What adjacent topics should be researched next?",
            ),
        )
    )
