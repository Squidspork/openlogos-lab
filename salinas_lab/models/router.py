from __future__ import annotations

import os
from enum import StrEnum


class ModelTier(StrEnum):
    SMALL = "small"
    TECHNICAL = "technical"
    ORCHESTRATOR = "orchestrator"
    SYNTHESIS = "synthesis"
    EMBEDDING = "embedding"


class ModelRouter:
    """Central model routing so departments depend on capability tiers, not hardcoded models."""

    def __init__(self) -> None:
        self.models = {
            ModelTier.SMALL: os.getenv("SALINAS_MODEL_SMALL", "google/gemma-4-e4b"),
            ModelTier.TECHNICAL: os.getenv(
                "SALINAS_MODEL_TECHNICAL", "nvidia/nemotron-3-nano-omni"
            ),
            ModelTier.ORCHESTRATOR: os.getenv("SALINAS_MODEL_ORCHESTRATOR", "qwen3.6-27b-mlx"),
            ModelTier.SYNTHESIS: os.getenv("SALINAS_MODEL_SYNTHESIS", "qwen/qwen3.6-35b-a3b"),
            ModelTier.EMBEDDING: os.getenv("SALINAS_MODEL_EMBEDDING", "bge-m3"),
        }

    def model_for(self, tier: ModelTier) -> str:
        return self.models[tier]
