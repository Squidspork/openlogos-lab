from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

from salinas_lab.graph import ResearchDepth, ResearchRequest, SourceChannel
from salinas_lab.graph.pipeline import ResearchPipeline

app = FastAPI(title="OpenLogos Lab Gateway", version="0.1.0")


class ResearchRunRequest(BaseModel):
    prompt: str
    depth: ResearchDepth = ResearchDepth.STANDARD
    audience: str = "builder-founder"
    source_channel: SourceChannel = SourceChannel.API


class ResearchRunResponse(BaseModel):
    session_id: str
    status: str
    output_folder: str
    report_path: str | None
    report_markdown: str | None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "salinas-research-lab"}


@app.post("/research/run", response_model=ResearchRunResponse)
def run_research(payload: ResearchRunRequest) -> ResearchRunResponse:
    request = ResearchRequest(
        prompt=payload.prompt,
        depth=payload.depth,
        audience=payload.audience,
        source_channel=payload.source_channel,
    )
    state = ResearchPipeline(output_dir=Path("outputs")).run(request)
    return ResearchRunResponse(
        session_id=state.request.session_id,
        status=state.status,
        output_folder=str(state.paths.root) if state.paths else "",
        report_path=str(state.report.path) if state.report and state.report.path else None,
        report_markdown=state.report.markdown if state.report else None,
    )
