from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.align import Align
from rich.console import Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from salinas_lab.graph import DepartmentName, LabState, ResearchRequest
from salinas_lab.graph.pipeline import ResearchPipeline
from salinas_lab.ui.assets import (
    BUILDING_WINDOWS,
    DEPARTMENT_COLORS,
    DEPARTMENT_ICONS,
    DEPARTMENT_LABELS,
    FACILITY_ART,
    LAB_SIGN,
    status_bubble,
)


@dataclass
class DepartmentDisplay:
    status: str = "sleeping"
    message: str = "Awaiting questionable science."
    model: str | None = None
    completed: bool = False


@dataclass
class LabDisplayState:
    request: ResearchRequest
    started_at: float = field(default_factory=time.time)
    session_folder: str = "warming up"
    final_report: str = ""
    events: list[str] = field(default_factory=list)
    departments: dict[DepartmentName, DepartmentDisplay] = field(
        default_factory=lambda: {name: DepartmentDisplay() for name in DepartmentName}
    )
    done: bool = False
    error: str | None = None


class LabTui:
    def __init__(self, request: ResearchRequest, *, output_dir: Path | str = "outputs") -> None:
        self.request = request
        self.output_dir = output_dir
        self.state = LabDisplayState(request=request)
        self.events: queue.Queue[dict[str, Any]] = queue.Queue()
        self.result: LabState | None = None

    def run(self) -> LabState:
        worker = threading.Thread(target=self._run_pipeline, daemon=True)
        worker.start()
        with Live(self._render(), refresh_per_second=8, screen=False) as live:
            while worker.is_alive() or not self.events.empty():
                self._drain_events()
                live.update(self._render())
                time.sleep(0.12)
            worker.join()
            self._drain_events()
            live.update(self._render())
        if self.state.error:
            raise RuntimeError(self.state.error)
        if self.result is None:
            raise RuntimeError("Lab run ended without a result.")
        return self.result

    def _run_pipeline(self) -> None:
        try:
            self.result = ResearchPipeline(
                output_dir=self.output_dir,
                progress_callback=self.events.put,
            ).run(self.request)
        except Exception as exc:
            self.events.put({"event": "failed", "message": str(exc)})

    def _drain_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._apply_event(event)

    def _apply_event(self, event: dict[str, Any]) -> None:
        kind = event.get("event", "event")
        department = event.get("department")
        message = str(event.get("message", ""))
        actor = str(event.get("actor", "Lab"))
        model = event.get("model")

        if kind == "session_created":
            self.state.session_folder = message.removeprefix("Session folder: ")
        elif kind == "department_started" and department:
            display = self.state.departments[DepartmentName(department)]
            display.status = "awake"
            display.message = message
            display.model = str(model) if model else display.model
        elif kind == "department_completed" and department:
            display = self.state.departments[DepartmentName(department)]
            display.status = "complete"
            display.message = message[:180]
            display.model = str(model) if model else display.model
            display.completed = True
        elif kind == "completed":
            self.state.done = True
            self.state.final_report = message
        elif kind == "failed":
            self.state.error = message

        if message:
            self.state.events.append(f"{actor}: {message}")
            self.state.events = self.state.events[-8:]

    def _render(self) -> Group:
        return Group(
            self._header(),
            self._building_panel(),
            self._department_table(),
            self._event_panel(),
        )

    def _header(self) -> Panel:
        elapsed = int(time.time() - self.state.started_at)
        title = "OPENLOGOS LAB - APPLIED CURIOSITY CONTAINMENT FACILITY"
        subtitle = (
            f"Specimen: {self.request.prompt[:90]} | "
            f"Session: {self.request.session_id} | Runtime: {elapsed}s"
        )
        sign = Text(LAB_SIGN, style="bright_white")
        sign.append("\n")
        sign.append(title, style="bold bright_blue")
        sign.append("\n")
        sign.append("Progress Through Questionable Confidence and Excellent Documentation.", style="yellow")
        sign.append("\n")
        sign.append(subtitle, style="bright_black")
        return Panel(sign, border_style="bright_blue")

    def _building_panel(self) -> Panel:
        status_lines = []
        for department in DepartmentName:
            display = self.state.departments[department]
            color = DEPARTMENT_COLORS[department]
            lamp = "ON " if display.status == "awake" else "OK " if display.completed else "..."
            status_lines.append(
                f"[{color}]{DEPARTMENT_ICONS[department]}:{lamp}[/]"
            )
        building = FACILITY_ART
        legend = "  ".join(
            f"[{DEPARTMENT_COLORS[name]}]{DEPARTMENT_ICONS[name]}[/]" for name in DepartmentName
        )
        return Panel(
            Align.center(
                Text.from_markup(
                    f"[bright_white]{building}[/]\n"
                    f"{'  '.join(status_lines)}\n\n"
                    f"[bright_black]Legend:[/] {legend}"
                )
            ),
            title="Facility Status | OpenLogos Lab",
            border_style="yellow",
        )

    def _department_table(self) -> Table:
        table = Table(title="Department Wake Board", border_style="bright_blue", expand=True)
        table.add_column("Wing", style="bold")
        table.add_column("Status")
        table.add_column("Model")
        table.add_column("Work Bubble")
        for department in DepartmentName:
            display = self.state.departments[department]
            color = DEPARTMENT_COLORS[department]
            status = {
                "sleeping": "[bright_black]sleeping[/]",
                "awake": f"[{color}]awake[/] {self._pulse()}",
                "complete": "[bright_green]complete[/]",
            }[display.status]
            table.add_row(
                f"[{color}]{DEPARTMENT_ICONS[department]} {DEPARTMENT_LABELS[department]}[/]",
                status,
                display.model or "[bright_black]not assigned[/]",
                status_bubble(display.message),
            )
        return table

    def _event_panel(self) -> Panel:
        lines = self.state.events or ["Lab quiet. This is normal. Probably."]
        if self.state.done and self.state.final_report:
            lines.append(f"Final report: {self.state.final_report}")
        if self.state.error:
            lines.append(f"ERROR: {self.state.error}")
        return Panel(
            "\n".join(f"- {line}" for line in lines),
            title=f"Accountability Feed | Output: {self.state.session_folder}",
            border_style="bright_cyan",
        )

    @staticmethod
    def _department_for_window(floor: int, bay: int) -> DepartmentName | None:
        for department, coords in BUILDING_WINDOWS.items():
            if coords == (floor, bay):
                return department
        return None

    @staticmethod
    def _pulse() -> str:
        frames = ("o..", ".o.", "..o", ".o.")
        return frames[int(time.time() * 4) % len(frames)]
