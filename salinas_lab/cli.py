from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from salinas_lab import __version__
from salinas_lab.audit import AuditLogger, summarize_audit
from salinas_lab.chat import RoundTableChat
from salinas_lab.doctor import Doctor
from salinas_lab.dreaming import DreamingEngine
from salinas_lab.graph import ResearchDepth, ResearchRequest, SourceChannel
from salinas_lab.graph.pipeline import ResearchPipeline
from salinas_lab.memory import MemoryStore, SelfLearningLoop, records_to_markdown
from salinas_lab.security import redact
from salinas_lab.ui import CommandCenter, LabTui
from salinas_lab.ui.assets import LAB_SIGN

app = typer.Typer(
    help="OpenLogos Lab command center.",
    invoke_without_command=True,
    no_args_is_help=False,
)
console = Console()
memory_app = typer.Typer(help="Inspect and curate Lab memory.")
app.add_typer(memory_app, name="memory")


@app.callback()
def main(
    ctx: typer.Context,
    output_dir: Path = typer.Option(Path("outputs"), help="Directory for session output folders."),
    depth: ResearchDepth = typer.Option(ResearchDepth.STANDARD, help="Research depth."),
    audience: str = typer.Option("builder-founder", help="Target audience for the report."),
    demo: bool = typer.Option(False, "--demo", help="Run deterministic demo responses."),
) -> None:
    """Open the interactive Lab command center when no subcommand is supplied."""
    if ctx.invoked_subcommand is not None:
        return

    load_dotenv()
    if demo:
        import os

        os.environ["OPENLOGOS_DEMO"] = "true"
    CommandCenter(output_dir=output_dir, depth=depth, audience=audience, console=console).run()


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Idea or question to send to the Lab."),
    depth: ResearchDepth = typer.Option(ResearchDepth.STANDARD, help="Research depth."),
    audience: str = typer.Option("builder-founder", help="Target audience for the report."),
    output_dir: Path = typer.Option(Path("outputs"), help="Directory for session output folders."),
    tui: bool = typer.Option(True, "--tui/--no-tui", help="Show the animated Lab TUI."),
    demo: bool = typer.Option(False, "--demo", help="Run deterministic demo responses."),
) -> None:
    """Run a manual research request."""
    load_dotenv()
    if demo:
        import os

        os.environ["OPENLOGOS_DEMO"] = "true"
    request = ResearchRequest(
        prompt=prompt,
        depth=depth,
        audience=audience,
        source_channel=SourceChannel.CLI,
    )
    if tui:
        state = LabTui(request, output_dir=output_dir).run()
    else:
        state = ResearchPipeline(output_dir=output_dir).run(request)
    console.print(f"[green]Report written:[/green] {state.report.path if state.report else 'unknown'}")
    if state.report and not tui:
        console.print(state.report.markdown)


@app.command()
def chat(
    prompt: str = typer.Argument(..., help="Message for the Lab board room."),
    demo: bool = typer.Option(False, "--demo", help="Run deterministic demo responses."),
) -> None:
    """Chat with the department-head round table without running research mode."""
    load_dotenv()
    if demo:
        import os

        os.environ["OPENLOGOS_DEMO"] = "true"
    console.print(RoundTableChat().respond(prompt))


@app.command()
def dream(
    once: bool = typer.Option(True, help="Run one dreaming cycle."),
    output_dir: Path = typer.Option(Path("outputs"), help="Directory for session output folders."),
    tui: bool = typer.Option(True, "--tui/--no-tui", help="Show the animated Lab TUI."),
) -> None:
    """Let the Lab pick a topic from configured sources and research it."""
    if not once:
        raise typer.BadParameter("Only --once is implemented in the first milestone.")
    request = DreamingEngine().create_request()
    if tui:
        state = LabTui(request, output_dir=output_dir).run()
    else:
        state = ResearchPipeline(output_dir=output_dir).run(request)
    console.print(f"[cyan]Dream topic:[/cyan] {request.prompt}")
    console.print(f"[green]Report written:[/green] {state.report.path if state.report else 'unknown'}")


@app.command()
def audit(session_folder: Path = typer.Argument(..., help="Path to a session output folder.")) -> None:
    """Print a readable audit summary for a session folder."""
    audit_path = session_folder / "audit.jsonl"
    events = AuditLogger(audit_path).read()
    console.print(redact(summarize_audit(events)))


@app.command()
def doctor(live: bool = typer.Option(False, "--live", help="Run live LM Studio model checks.")) -> None:
    """Check configuration, paths, and optionally live model health."""
    table = Table(title="OpenLogos Lab Doctor", border_style="bright_blue", expand=True)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for check in Doctor().run(live=live):
        color = {"ok": "green", "warn": "yellow", "fail": "red"}.get(check.status, "white")
        table.add_row(check.name, f"[{color}]{check.status}[/]", redact(check.detail))
    console.print(table)


@app.command()
def version() -> None:
    """Print the OpenLogos Lab version."""
    console.print(f"OpenLogos Lab {__version__}")


@memory_app.command("status")
def memory_status() -> None:
    """Show active, passive, and long-term memory counts."""
    status = MemoryStore().status()
    console.print(Panel("\n".join(f"{key}: {value}" for key, value in status.items()), title="Memory Status"))


@memory_app.command("search")
def memory_search(query: str = typer.Argument(..., help="Search query.")) -> None:
    """Search long-term and recent passive memory."""
    records = MemoryStore().search(query)
    console.print(Panel(records_to_markdown(records), title=f"Memory Search: {query}"))


@memory_app.command("add")
def memory_add(
    text: str = typer.Argument(..., help="Memory text to store."),
    target: str = typer.Option("memory", help="memory or user"),
) -> None:
    """Add a curated long-term memory."""
    record = MemoryStore().add_long_term(text, source="manual-cli", target=target, confidence=0.95)
    console.print(f"[green]Stored memory:[/green] {record.memory_id}")


@memory_app.command("reflect")
def memory_reflect(limit: int = typer.Option(12, help="Recent passive observations to review.")) -> None:
    """Run the self-learning reflection loop over recent passive observations."""
    learned = SelfLearningLoop().reflect(limit=limit)
    if not learned:
        console.print("[yellow]No durable memories promoted.[/yellow]")
        return
    console.print(Panel("\n".join(f"- {item}" for item in learned), title="Promoted Memories"))


def _intake_panel() -> Panel:
    text = Text(LAB_SIGN, style="bright_white")
    text.append("\nOPENLOGOS LAB FRONT DESK\n", style="bold bright_blue")
    text.append(
        "Please describe the idea, question, hallucinated business opportunity, or "
        "other safely containerized thought specimen.\n",
        style="bright_white",
    )
    text.append(
        "The Lab will wake the departments, record the audit trail, and return a report.",
        style="yellow",
    )
    return Panel(text, title="Idea Specimen Intake", border_style="bright_cyan")


if __name__ == "__main__":
    app()
