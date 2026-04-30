from __future__ import annotations

from datetime import UTC, datetime

from salinas_lab.models import ModelClient, ModelRouter, ModelTier


class TopicPicker:
    def __init__(
        self,
        *,
        client: ModelClient | None = None,
        router: ModelRouter | None = None,
    ) -> None:
        self.client = client or ModelClient(timeout=30)
        self.router = router or ModelRouter()

    def pick(self, source_summaries: list[str]) -> str:
        if not source_summaries:
            return f"Autonomous research topic for {datetime.now(UTC):%Y-%m-%d}: local AI workflows"
        model = self.router.model_for(ModelTier.SMALL)
        return self.client.chat(
            model=model,
            system=(
                "You are the OpenLogos Lab Dreaming Engine. Select one strange, useful, "
                "research-worthy topic from source notes. Return one concise research prompt."
            ),
            user="\n\n".join(source_summaries),
            temperature=0.7,
            max_tokens=300,
        ).splitlines()[0]
