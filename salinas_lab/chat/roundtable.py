from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from salinas_lab.audit import slugify
from salinas_lab.memory import MemoryStore, SelfLearningLoop
from salinas_lab.models import ModelClient, ModelClientError, ModelRouter, ModelTier
from salinas_lab.security import redact


@dataclass(frozen=True)
class RoundTableSeat:
    name: str
    title: str
    model_tier: ModelTier
    color: str
    mandate: str
    voice: str
    keywords: tuple[str, ...]


ROUND_TABLE = (
    RoundTableSeat(
        name="Dr. Logos",
        title="Research Director",
        model_tier=ModelTier.ORCHESTRATOR,
        color="bright_blue",
        mandate="Keep the board-room discussion focused and strategically useful.",
        voice="Strategic, founder-facing, crisp. Sounds like the person holding the clipboard and the detonator key.",
        keywords=("strategy", "plan", "direction", "decision", "should", "priority", "roadmap"),
    ),
    RoundTableSeat(
        name="Scout",
        title="Opportunity Discovery",
        model_tier=ModelTier.SMALL,
        color="bright_cyan",
        mandate="Spot use cases, business angles, and strange opportunities.",
        voice="Opportunity gremlin with a market radar. Energetic, concrete, and allergic to vague potential.",
        keywords=("idea", "market", "user", "customer", "opportunity", "use case", "app", "business"),
    ),
    RoundTableSeat(
        name="Nemo",
        title="Scientific Inquiry",
        model_tier=ModelTier.TECHNICAL,
        color="bright_white",
        mandate="Explain mechanisms, technical feasibility, and fragile assumptions.",
        voice="Technical scientist. Precise, skeptical, and fond of naming the variable that will ruin the experiment.",
        keywords=("technical", "science", "mechanism", "build", "model", "data", "experiment", "feasible"),
    ),
    RoundTableSeat(
        name="Prospect",
        title="Product Applications",
        model_tier=ModelTier.SYNTHESIS,
        color="bright_green",
        mandate="Translate the idea into product, market, and customer implications.",
        voice="Product operator. Practical, commercial, and focused on packaging discoveries into something people use.",
        keywords=("product", "pricing", "launch", "startup", "workflow", "feature", "mvp", "sell"),
    ),
    RoundTableSeat(
        name="Control",
        title="Risk and Ethics",
        model_tier=ModelTier.TECHNICAL,
        color="orange3",
        mandate="Flag risks, constraints, and what the Lab should not casually detonate.",
        voice="Containment officer. Dry, direct, and professionally suspicious of optimism near machinery.",
        keywords=("risk", "ethics", "legal", "security", "privacy", "danger", "failure", "safe"),
    ),
)


class RoundTableChat:
    """Board-room chat that does not activate the full research/report pipeline."""

    def __init__(
        self,
        *,
        client: ModelClient | None = None,
        router: ModelRouter | None = None,
        memory_store: MemoryStore | None = None,
        session_id: str = "board-room",
        transcript_root: Path | str = "outputs/boardroom",
    ) -> None:
        self.client = client or ModelClient(timeout=120)
        self.router = router or ModelRouter()
        self.memory_store = memory_store or MemoryStore()
        self.learning = SelfLearningLoop(store=self.memory_store, client=self.client, router=self.router)
        self.session_id = session_id
        self.transcript_dir = self._create_transcript_dir(transcript_root)
        self.transcript_path = self.transcript_dir / "transcript.md"
        self.history: list[tuple[str, str]] = []
        self.last_user_message: str | None = None
        self.last_summary: str | None = None
        self.last_rows: list[tuple[RoundTableSeat, str, str]] = []

    @property
    def seats(self) -> tuple[RoundTableSeat, ...]:
        return ROUND_TABLE

    def respond(self, user_message: str) -> Group:
        context = self._history_context()
        memory_context = self.memory_store.context_for(user_message, session_id=self.session_id)
        seats = self.route_seats(user_message)
        rows = self._department_responses(user_message, context, memory_context, seats)

        try:
            director_summary = self._director_summary(user_message, rows)
        except ModelClientError as exc:
            director_summary = (
                "Director's chair unavailable. OpenLogos Lab attempted to reach "
                f"`{self.router.model_for(ModelTier.ORCHESTRATOR)}` through LM Studio, "
                f"but LM Studio returned: {exc}"
            )
        self._record_turn(user_message, rows, director_summary)
        return self._render(user_message, rows, director_summary)

    def respond_live(self, user_message: str, console) -> Group:
        context = self._history_context()
        memory_context = self.memory_store.context_for(user_message, session_id=self.session_id)
        seats = self.route_seats(user_message)
        started_at: dict[str, float] = {}
        status: dict[str, tuple[RoundTableSeat, str, str, str, float | None]] = {
            seat.name: (
                seat,
                self.router.model_for(seat.model_tier),
                "waking",
                "Lights warming. Chair spinning into position.",
                None,
            )
            for seat in seats
        }

        def render_live(summary: str | None = None) -> Group:
            rows = [
                (seat, model, self._with_timing(message, elapsed))
                for seat, model, _, message, elapsed in status.values()
            ]
            if summary:
                return self._render(user_message, rows, summary)
            panels = [
                Panel(user_message, title="Founder", border_style="yellow"),
                Text("Board Room Round Table | Live", style="bold bright_blue", justify="center"),
            ]
            for seat, model, state, message, elapsed in status.values():
                marker = {"waking": "WAKING", "working": "WORKING", "complete": "COMPLETE", "error": "ERROR"}[state]
                timing = f"\n\n_Time: {elapsed:.1f}s_" if elapsed is not None else ""
                panels.append(
                    Panel(
                        Markdown(f"**{marker}**\n\n{message}{timing}"),
                        title=f"{seat.name} | {seat.title}",
                        subtitle=model,
                        border_style=seat.color,
                        expand=True,
                    )
                )
            panels.append(
                Panel(
                    "Director waits for department comments before closing the meeting.",
                    title="Director's Chair",
                    border_style="bright_cyan",
                )
            )
            return Group(*panels)  # type: ignore[arg-type]

        rows: list[tuple[RoundTableSeat, str, str]] = []
        with Live(render_live(), console=console, refresh_per_second=8, transient=False) as live:
            with ThreadPoolExecutor(max_workers=self._max_workers(seats)) as executor:
                futures = {}
                for seat in seats:
                    model = self.router.model_for(seat.model_tier)
                    started_at[seat.name] = time.time()
                    status[seat.name] = (
                        seat,
                        model,
                        "working",
                        "Reviewing notes, consulting gauges, tapping clipboard.",
                        0.0,
                    )
                    futures[executor.submit(self._seat_response, seat, user_message, context, memory_context)] = seat
                live.update(render_live())
                for future in as_completed(futures):
                    seat = futures[future]
                    model = self.router.model_for(seat.model_tier)
                    try:
                        result = future.result()
                        rows.append(result)
                        elapsed = time.time() - started_at.get(seat.name, time.time())
                        status[seat.name] = (seat, model, "complete", result[2], elapsed)
                    except ModelClientError as exc:
                        message = (
                            f"{seat.name} is unavailable. OpenLogos Lab attempted `{model}` "
                            f"through LM Studio, but the model call failed: {exc}"
                        )
                        result = (seat, model, message)
                        rows.append(result)
                        elapsed = time.time() - started_at.get(seat.name, time.time())
                        status[seat.name] = (seat, model, "error", message, elapsed)
                    except Exception as exc:
                        message = f"{seat.name} reports an unexpected board-room fault: {exc.__class__.__name__}."
                        result = (seat, model, message)
                        rows.append(result)
                        elapsed = time.time() - started_at.get(seat.name, time.time())
                        status[seat.name] = (seat, model, "error", message, elapsed)
                    live.update(render_live())

            rows_by_name = {seat.name: (seat, model, response) for seat, model, response in rows}
            ordered_rows = [rows_by_name[seat.name] for seat in seats]
            try:
                director_summary = self._director_summary(user_message, ordered_rows)
            except ModelClientError as exc:
                director_summary = (
                    "Director's chair unavailable. OpenLogos Lab attempted to reach "
                    f"`{self.router.model_for(ModelTier.ORCHESTRATOR)}` through LM Studio, "
                    f"but LM Studio returned: {exc}"
                )
            self._record_turn(user_message, ordered_rows, director_summary)
            final = self._render(user_message, ordered_rows, director_summary)
            live.update(final)
            return final

    def _director_summary(
        self, user_message: str, rows: list[tuple[RoundTableSeat, str, str]]
    ) -> str:
        available = [
            f"{seat.title}: {response[:600]}"
            for seat, _, response in rows
            if not self._is_unavailable(response)
        ]
        unavailable = [
            f"{seat.title}: {response[:300]}"
            for seat, _, response in rows
            if self._is_unavailable(response)
        ]
        digest = "\n".join(available) or "No department comments were available."
        failures = "\n".join(unavailable) or "None."
        model = self.router.model_for(ModelTier.ORCHESTRATOR)
        return self.client.chat(
            model=model,
            system=(
                "You are the Research Director closing a board-room discussion. Summarize the "
                "available department heads into a short founder-facing response. Do not treat "
                "unavailable departments as evidence. Mention whether the idea should stay in chat "
                "mode or be escalated to research mode. Use this format:\n"
                "Decision: ...\nWhy it matters: ...\nNext action: ..."
            ),
            user=(
                f"Founder said: {user_message}\n\n"
                f"Available department comments:\n{digest}\n\n"
                f"Unavailable departments:\n{failures}"
            ),
            temperature=0.35,
            max_tokens=1200,
        ).strip()

    def _department_responses(
        self,
        user_message: str,
        context: str,
        memory_context: str,
        seats: tuple[RoundTableSeat, ...],
    ) -> list[tuple[RoundTableSeat, str, str]]:
        responses: dict[str, tuple[RoundTableSeat, str, str]] = {}
        with ThreadPoolExecutor(max_workers=self._max_workers(seats)) as executor:
            futures = {
                executor.submit(self._seat_response, seat, user_message, context, memory_context): seat
                for seat in seats
            }
            for future in as_completed(futures):
                seat = futures[future]
                try:
                    responses[seat.name] = future.result()
                except ModelClientError as exc:
                    model = self.router.model_for(seat.model_tier)
                    responses[seat.name] = (
                        seat,
                        model,
                        (
                            f"{seat.name} is unavailable. OpenLogos Lab attempted `{model}` "
                            f"through LM Studio, but the model call failed: {exc}"
                        ),
                    )
                except Exception as exc:
                    model = self.router.model_for(seat.model_tier)
                    responses[seat.name] = (
                        seat,
                        model,
                        f"{seat.name} reports an unexpected board-room fault: {exc.__class__.__name__}.",
                    )
        return [responses[seat.name] for seat in seats]

    def _seat_response(
        self,
        seat: RoundTableSeat,
        user_message: str,
        context: str,
        memory_context: str,
    ) -> tuple[RoundTableSeat, str, str]:
        model = self.router.model_for(seat.model_tier)
        response = self.client.chat(
            model=model,
            system=(
                "You are in the OpenLogos Lab board room. The user is the founder "
                "and leader of the firm. Answer as one department head in a concise round-table "
                "discussion. Do not write a full research report. Do not claim the full Lab "
                "pipeline has run. Give practical, high-level advice and ask useful questions "
                "when needed. Keep the tone like comedic serious science, but be genuinely useful. "
                "Use exactly this shape with concise bullets:\n"
                "Observation: ...\nConcern: ...\nNext move: ...\n"
                "Keep it under 140 words.\n\n"
                f"Your seat: {seat.name}, {seat.title}.\n"
                f"Mandate: {seat.mandate}\nVoice: {seat.voice}"
            ),
            user=(
                f"Relevant Lab memory:\n{memory_context}\n\n"
                f"Conversation so far:\n{context}\n\n"
                f"Founder says:\n{user_message}"
            ),
            temperature=0.45,
            max_tokens=700,
        )
        return seat, model, self._clean_response(response)

    def route_seats(self, user_message: str) -> tuple[RoundTableSeat, ...]:
        lowered = user_message.lower()
        if any(token in lowered for token in ("everyone", "all departments", "whole board", "round table")):
            return ROUND_TABLE
        selected = [ROUND_TABLE[0]]
        for seat in ROUND_TABLE[1:]:
            if any(keyword in lowered for keyword in seat.keywords):
                selected.append(seat)
        if len(selected) == 1:
            selected.extend([ROUND_TABLE[1], ROUND_TABLE[-1]])
        return tuple(dict.fromkeys(selected))

    def _render(
        self,
        user_message: str,
        rows: list[tuple[RoundTableSeat, str, str]],
        director_summary: str,
    ) -> Group:
        panels = [
            Panel(user_message, title="Founder", border_style="yellow"),
            Panel(
                Markdown(self._founder_brief(director_summary)),
                title="Founder Brief",
                border_style="bright_green",
            ),
            Text("Board Room Round Table", style="bold bright_blue", justify="center"),
        ]
        for seat, model, response in rows:
            panels.append(
                Panel(
                    Markdown(response),
                    title=f"{seat.name} | {seat.title}",
                    subtitle=model,
                    border_style=seat.color,
                    expand=True,
                )
            )
        panels.append(
            Panel(
                Markdown(self._clean_response(director_summary)),
                title="Director's Chair",
                border_style="bright_cyan",
            )
        )
        return Group(*panels)  # type: ignore[arg-type]

    def _record_turn(
        self,
        user_message: str,
        rows: list[tuple[RoundTableSeat, str, str]],
        director_summary: str,
    ) -> None:
        self.history.append(("Founder", user_message))
        self.history.append(("Round Table", director_summary))
        self.history = self.history[-12:]
        self.last_user_message = user_message
        self.last_summary = director_summary
        self.last_rows = rows
        self.learning.observe_chat(
            session_id=self.session_id,
            user_message=user_message,
            summary=director_summary,
        )
        self._append_transcript(user_message, rows, director_summary)

    def _append_transcript(
        self,
        user_message: str,
        rows: list[tuple[RoundTableSeat, str, str]],
        director_summary: str,
    ) -> None:
        lines = [
            f"\n## {datetime.now(UTC).isoformat()}",
            "",
            f"### Founder\n\n{user_message}",
            "",
        ]
        for seat, model, response in rows:
            lines.append(f"### {seat.name} | {seat.title}\n\n_Model: `{model}`_\n\n{redact(response)}\n")
        lines.append(f"### Director's Chair\n\n{redact(director_summary)}\n")
        with self.transcript_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    def _history_context(self) -> str:
        if not self.history:
            return "No prior board-room discussion."
        return "\n".join(f"{speaker}: {message}" for speaker, message in self.history)

    @staticmethod
    def _clean_response(response: str) -> str:
        response = response.strip()
        response = re.sub(r"\n{3,}", "\n\n", response)
        if response.lower().startswith("offline fallback generated"):
            return (
                "Offline test-mode response. In normal mode, OpenLogos Lab does not fabricate "
                "local fallback answers."
            )
        return response or "No comment arrived from this department."

    @staticmethod
    def _with_timing(message: str, elapsed: float | None) -> str:
        if elapsed is None:
            return message
        return f"{message}\n\n_Time: {elapsed:.1f}s_"

    @staticmethod
    def _is_unavailable(response: str) -> bool:
        lowered = response.lower()
        return "is unavailable" in lowered or "model call failed" in lowered or "unexpected board-room fault" in lowered

    @staticmethod
    def _founder_brief(summary: str) -> str:
        if all(label in summary for label in ("Decision:", "Why it matters:", "Next action:")):
            return summary
        cleaned = summary.strip() or "No Director brief available."
        first_sentence = cleaned.split(".")[0].strip()
        return (
            f"Decision: Continue board-room discussion unless you explicitly escalate.\n\n"
            f"Why it matters: {first_sentence or 'The board has not produced a clear conclusion yet.'}.\n\n"
            "Next action: Ask a narrower question or use `/research this` to wake the full lab."
        )

    @staticmethod
    def _create_transcript_dir(root: Path | str) -> Path:
        base = Path(root)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        path = base / f"{stamp}_{slugify('board-room')}"
        path.mkdir(parents=True, exist_ok=True)
        path.joinpath("transcript.md").write_text("# OpenLogos Lab Board Room Transcript\n", encoding="utf-8")
        return path

    @staticmethod
    def _max_workers(seats: tuple[RoundTableSeat, ...]) -> int:
        configured = int(os.getenv("SALINAS_CHAT_MAX_WORKERS", "8"))
        return max(1, min(len(seats), configured))
