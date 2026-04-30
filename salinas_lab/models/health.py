from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from salinas_lab.models.client import ModelClient, ModelClientError
from salinas_lab.models.router import ModelRouter, ModelTier


@dataclass(frozen=True)
class ModelHealth:
    tier: str
    model: str
    status: str
    latency_seconds: float | None = None
    detail: str = ""


class ModelHealthChecker:
    def __init__(
        self,
        *,
        client: ModelClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.client = client or ModelClient(timeout=30)
        self.router = router or ModelRouter()

    def configured_models(self) -> list[tuple[str, str]]:
        seen: set[tuple[str, str]] = set()
        models: list[tuple[str, str]] = []
        for tier in (
            ModelTier.SMALL,
            ModelTier.TECHNICAL,
            ModelTier.ORCHESTRATOR,
            ModelTier.SYNTHESIS,
        ):
            item = (tier.value, self.router.model_for(tier))
            if item not in seen:
                seen.add(item)
                models.append(item)
        return models

    def loaded_models(self) -> list[str]:
        headers = {}
        if self.client.api_key:
            headers["Authorization"] = f"Bearer {self.client.api_key}"
        try:
            response = httpx.get(
                f"{self.client.base_url}/models",
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            return [item.get("id", "") for item in response.json().get("data", []) if item.get("id")]
        except Exception:
            return []

    def check_all(self) -> list[ModelHealth]:
        loaded = set(self.loaded_models())
        results: list[ModelHealth] = []
        for tier, model in self.configured_models():
            if loaded and model not in loaded:
                results.append(ModelHealth(tier=tier, model=model, status="not loaded"))
                continue
            started = time.time()
            try:
                response = self.client.chat(
                    model=model,
                    system="Reply with exactly: OK",
                    user="health check",
                    temperature=0,
                    max_tokens=60,
                )
            except ModelClientError as exc:
                results.append(
                    ModelHealth(
                        tier=tier,
                        model=model,
                        status="error",
                        latency_seconds=time.time() - started,
                        detail=str(exc),
                    )
                )
                continue
            status = "ready" if response.strip() else "empty"
            results.append(
                ModelHealth(
                    tier=tier,
                    model=model,
                    status=status,
                    latency_seconds=time.time() - started,
                    detail=response[:120],
                )
            )
        return results
