from salinas_lab.departments.base import DepartmentAgent, DepartmentSpec
from salinas_lab.graph.state import DepartmentName
from salinas_lab.models import ModelTier


def build_agent() -> DepartmentAgent:
    return DepartmentAgent(
        DepartmentSpec(
            department=DepartmentName.DIRECTOR,
            actor="Research Director",
            model_tier=ModelTier.ORCHESTRATOR,
            mission="Decompose the specimen idea into research questions and coordinate the lab.",
            questions=(
                "What is the core research subject?",
                "Which questions must the lab answer before recommending action?",
                "What would count as useful evidence?",
                "Which departments should be especially suspicious?",
            ),
        )
    )
