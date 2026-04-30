from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph.state import DepartmentName
from salinas_lab.models import ModelTier


def build_agent() -> DepartmentAgent:
    return DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.PRODUCT_APPLICATIONS,
            actor="Product Applications Analyst",
            model_tier=ModelTier.SYNTHESIS,
            mission="Translate findings into products, businesses, workflows, and market paths.",
            questions=(
                "What concrete products or services could be built?",
                "What business models fit?",
                "Who are the early adopters?",
                "What makes the idea defensible or easy to copy?",
            ),
        )
    )
