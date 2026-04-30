from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph.state import DepartmentName
from salinas_lab.models import ModelTier


def build_agent() -> DepartmentAgent:
    return DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.HUMAN_TESTING,
            actor="Human Testing and Simulation Lead",
            model_tier=ModelTier.SMALL,
            mission="Design ethical validation plans, test subject personas, and success metrics.",
            questions=(
                "Which test subject personas should represent the target users?",
                "What small experiments should validate demand or feasibility?",
                "What metrics prove progress?",
                "What should not be tested on humans without extra review?",
            ),
        )
    )
