from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from salinas_lab.chat import RoundTableChat
from salinas_lab.graph import ResearchDepth, ResearchRequest, SourceChannel
from salinas_lab.memory import records_to_markdown
from salinas_lab.models import ModelHealthChecker
from salinas_lab.ui.assets import COMMAND_CENTER_ART, LAB_SIGN
from salinas_lab.ui.tui import LabTui


class InteractionMode(StrEnum):
    CHAT = "chat"
    RESEARCH = "research"


@dataclass
class CommandCenter:
    output_dir: Path
    depth: ResearchDepth
    audience: str
    console: Console

    def run(self) -> None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings

        mode = InteractionMode.CHAT
        bindings = KeyBindings()
        chat = RoundTableChat(transcript_root=self.output_dir / "boardroom")

        @bindings.add("s-tab")
        def _(event) -> None:
            nonlocal mode
            mode = self._next_mode(mode)
            event.app.invalidate()

        session: PromptSession[str] = PromptSession(key_bindings=bindings)
        self.console.print(self._intro_panel())
        self.console.print(
            "[bright_black]Shift+Tab cycles modes. /chat, /research, /help, /quit also work.[/bright_black]\n"
        )

        while True:
            try:
                current_mode = mode

                def toolbar() -> object:
                    return self._toolbar(current_mode)

                user_text = session.prompt(
                    self._prompt_message(current_mode),
                    bottom_toolbar=toolbar,
                ).strip()
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]The board room adjourns. Nobody admits liability.[/yellow]")
                return

            if not user_text:
                continue
            command = user_text.lower()
            if command in {"/quit", "/exit", "quit", "exit"}:
                self.console.print("[yellow]Session ended. The specimen drawer has been locked.[/yellow]")
                return
            if command == "/help":
                self.console.print(self._help_panel())
                continue
            if command == "/departments":
                self.console.print(self._departments_panel(chat))
                continue
            if command == "/transcript":
                self.console.print(Panel(str(chat.transcript_path), title="Board-Room Transcript"))
                continue
            if command == "/models":
                self.console.print(self._models_panel())
                continue
            if command == "/health":
                self.console.print("[cyan]Running model health checks through LM Studio...[/cyan]")
                self.console.print(self._health_panel())
                continue
            if command == "/brief":
                self.console.print(
                    Panel(chat.last_summary or "No board-room brief has been generated yet.", title="Latest Founder Brief")
                )
                continue
            if command.startswith("/memory"):
                self._handle_memory_command(chat, user_text)
                continue
            if command.startswith("/remember"):
                memory_text = user_text.removeprefix("/remember").strip()
                if memory_text == "this":
                    memory_text = chat.last_summary or ""
                if not memory_text:
                    self.console.print("[yellow]Nothing to remember yet.[/yellow]")
                    continue
                record = chat.memory_store.add_long_term(memory_text, source="founder-command", confidence=0.95)
                self.console.print(f"[green]Stored memory:[/green] {record.memory_id}")
                continue
            if command.startswith("/research"):
                research_text = user_text.removeprefix("/research").strip()
                if research_text == "this" or not research_text:
                    research_text = chat.last_user_message or ""
                if not research_text:
                    self.console.print("[yellow]No prior specimen to research.[/yellow]")
                    continue
                if research_text == chat.last_user_message and chat.last_summary:
                    research_text = self._research_context_from_chat(chat)
                self._run_research(research_text)
                mode = InteractionMode.CHAT
                continue
            if command == "/clear":
                chat = RoundTableChat(transcript_root=self.output_dir / "boardroom")
                self.console.print("[cyan]Board-room context cleared. New transcript opened.[/cyan]")
                continue
            if command == "/chat":
                mode = InteractionMode.CHAT
                continue
            if command == "/research":
                mode = InteractionMode.RESEARCH
                continue

            if mode == InteractionMode.CHAT:
                chat.respond_live(user_text, self.console)
                continue

            self._run_research(user_text)
            mode = InteractionMode.CHAT

    @staticmethod
    def _next_mode(mode: InteractionMode) -> InteractionMode:
        return InteractionMode.RESEARCH if mode == InteractionMode.CHAT else InteractionMode.CHAT

    def _run_research(self, prompt: str) -> None:
        request = ResearchRequest(
            prompt=prompt,
            depth=self.depth,
            audience=self.audience,
            source_channel=SourceChannel.CLI,
        )
        state = LabTui(request, output_dir=self.output_dir).run()
        self.console.print(f"[green]Report written:[/green] {state.report.path if state.report else 'unknown'}")

    @staticmethod
    def _prompt_message(mode: InteractionMode):
        from prompt_toolkit.formatted_text import HTML

        color = "ansicyan" if mode == InteractionMode.CHAT else "ansiyellow"
        label = "BOARD ROOM CHAT" if mode == InteractionMode.CHAT else "RESEARCH MODE"
        return HTML(f"<b><{color}>{label}</{color}></b> <ansibrightblack>›</ansibrightblack> ")

    @staticmethod
    def _toolbar(mode: InteractionMode):
        from prompt_toolkit.formatted_text import HTML

        other = "research" if mode == InteractionMode.CHAT else "chat"
        return HTML(
            f" <b>Mode:</b> {mode.value} | Shift+Tab: switch to {other} | "
            "/chat /research this /brief /memory /help /quit "
        )

    @staticmethod
    def _intro_panel() -> Panel:
        text = Text(LAB_SIGN, style="bright_white")
        text.append(COMMAND_CENTER_ART, style="bright_cyan")
        text.append("\nOPENLOGOS LAB COMMAND CENTER\n", style="bold bright_blue")
        text.append(
            "You are seated at the founder's end of the board-room table. "
            "Chat mode consults department heads. Research mode wakes the full facility.",
            style="bright_white",
        )
        return Panel(text, title="Founder Console | OpenLogos Lab", border_style="bright_cyan")

    @staticmethod
    def _help_panel() -> Panel:
        return Panel(
            "\n".join(
                [
                    "Chat mode: round-table conversation with department heads.",
                    "Research mode: full pipeline, audit log, labeled output folder, final report.",
                    "Memory: chat and research both read relevant Lab memory and write passive observations.",
                    "Self-learning: use `openlogos-lab memory reflect` to promote durable observations.",
                    "Shift+Tab: cycle modes.",
                    "/chat: switch to chat mode.",
                    "/research: switch to research mode.",
                    "/research this: send the last chat topic into research mode.",
                    "/brief: show the latest Director summary.",
                    "/departments: show the board-room seats and routing hints.",
                    "/models: show LM Studio model mapping.",
                    "/health: run model health checks.",
                    "/transcript: show current transcript path.",
                    "/memory: search memory for the latest topic.",
                    "/memory status: show memory counts.",
                    "/memory search <query>: search memory.",
                    "/memory reset: clear Lab memory.",
                    "/remember <text|this>: store a long-term memory.",
                    "/clear: clear board-room context and start a new transcript.",
                    "/quit: leave the facility.",
                ]
            ),
            title="Controls",
            border_style="yellow",
        )

    @staticmethod
    def _departments_panel(chat: RoundTableChat) -> Panel:
        lines = []
        for seat in chat.seats:
            lines.append(
                f"- {seat.name} ({seat.title}): {seat.mandate} "
                f"[keywords: {', '.join(seat.keywords[:5])}]"
            )
        return Panel("\n".join(lines), title="Department Heads", border_style="bright_blue")

    def _handle_memory_command(self, chat: RoundTableChat, user_text: str) -> None:
        parts = user_text.split(maxsplit=2)
        if len(parts) == 1:
            records = chat.memory_store.search(chat.last_user_message or "", limit=8)
            self.console.print(Panel(records_to_markdown(records), title="Relevant Memory"))
            return
        action = parts[1].lower()
        if action == "status":
            status = chat.memory_store.status()
            self.console.print(Panel("\n".join(f"{k}: {v}" for k, v in status.items()), title="Memory Status"))
            return
        if action == "search":
            query = parts[2] if len(parts) > 2 else chat.last_user_message or ""
            records = chat.memory_store.search(query, limit=8)
            self.console.print(Panel(records_to_markdown(records), title=f"Memory Search: {query}"))
            return
        if action == "reset":
            chat.memory_store.reset()
            self.console.print("[yellow]Lab memory reset.[/yellow]")
            return
        self.console.print("[yellow]Unknown memory command. Try /memory status, /memory search <query>, or /memory reset.[/yellow]")

    @staticmethod
    def _research_context_from_chat(chat: RoundTableChat) -> str:
        lines = [
            chat.last_user_message or "",
            "",
            "Context from the OpenLogos Lab board-room discussion:",
            "",
            f"Founder Brief:\n{chat.last_summary or 'No brief available.'}",
            "",
            "Department comments:",
        ]
        for seat, model, response in chat.last_rows:
            lines.append(f"- {seat.name} ({seat.title}, {model}): {response}")
        return "\n".join(lines)

    @staticmethod
    def _models_panel() -> Table:
        checker = ModelHealthChecker()
        loaded = set(checker.loaded_models())
        table = Table(title="LM Studio Model Mapping", border_style="bright_blue", expand=True)
        table.add_column("Tier")
        table.add_column("Model")
        table.add_column("Loaded")
        for tier, model in checker.configured_models():
            table.add_row(tier, model, "yes" if not loaded or model in loaded else "no")
        return table

    @staticmethod
    def _health_panel() -> Table:
        checker = ModelHealthChecker()
        table = Table(title="LM Studio Health", border_style="bright_green", expand=True)
        table.add_column("Tier")
        table.add_column("Model")
        table.add_column("Status")
        table.add_column("Latency")
        table.add_column("Detail")
        for result in checker.check_all():
            latency = f"{result.latency_seconds:.1f}s" if result.latency_seconds is not None else "-"
            table.add_row(result.tier, result.model, result.status, latency, result.detail[:80])
        return table
