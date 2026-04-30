# OpenLogos Lab

OpenLogos Lab converts raw ideas and questions into structured research reports. It is
designed as a modular scientific institution: each department owns its prompts, schemas, tools,
and report fragments, while the core pipeline keeps every action accountable through append-only
logs.

> Progress Through Questionable Confidence and Excellent Documentation.

## Features

- Founder Console with chat and research modes.
- Live board-room panels with parallel department responses.
- Modular research pipeline with labeled output folders.
- LM Studio model routing and health checks.
- Active, passive, and long-term local memory.
- Deterministic demo mode for trying the UI without models.
- Append-only audit logs and redacted diagnostics.

## What Happens To A Request

1. A request enters through the CLI, API, Telegram, email, or a future app adapter.
2. The gateway normalizes it into a `ResearchRequest` and assigns a session ID.
3. The Research Director decomposes the request into research questions.
4. Modular departments investigate the idea from different angles.
5. A feasibility and accountability gate checks risks, contradictions, and weak assumptions.
6. Publications turns the findings into a Markdown research report.
7. Outputs, evidence, department notes, metadata, and audit logs are written to one session folder.

## Local Model Setup

The app reads LM Studio configuration from environment variables. Do not hardcode tokens.

```bash
cp .env.example .env
```

Expected LM Studio defaults:

```text
LM_STUDIO_BASE_URL=http://localhost:1234/v1
SALINAS_MODEL_SMALL=google/gemma-4-e4b
SALINAS_MODEL_TECHNICAL=nvidia/nemotron-3-nano-omni
SALINAS_MODEL_ORCHESTRATOR=qwen3.6-27b-mlx
SALINAS_MODEL_SYNTHESIS=qwen/qwen3.6-35b-a3b
SALINAS_CHAT_MAX_WORKERS=8
```

## Run

```bash
pip install -e ".[dev]"
openlogos-lab
openlogos-lab run "ideas for apps around local-first AI memory"
```

Try the UI without LM Studio:

```bash
openlogos-lab --demo
```

Check your environment:

```bash
openlogos-lab doctor
openlogos-lab doctor --live
```

Running bare `openlogos-lab` opens the Founder Console. It has two modes:

- **Chat mode:** a board-room round table with department heads. This does not activate the full
  research pipeline.
- **Research mode:** wakes the full facility, writes an audit trail, creates a labeled output
  folder, and produces a report.

Press **Shift+Tab** in the Founder Console to cycle between Chat and Research modes. Chat mode
shows live board-room panels: selected departments wake up, work in parallel, and update as their
LM Studio responses arrive. The Director summarizes after the selected departments finish.

Useful chat commands:

```text
/chat              switch to chat mode
/research          switch to research mode
/research this     send the last chat topic into the full research pipeline
/brief             show the latest Director summary
/departments       show board-room seats and routing hints
/models            show LM Studio model mapping
/health            run model health checks
/transcript        show the current board-room transcript path
/memory            search memory for the latest topic
/memory status     show memory counts
/memory search     search memory
/memory reset      clear Lab memory
/remember <text>   store a long-term memory
/remember this     store the latest Director brief
/clear             clear board-room context and start a new transcript
/quit              leave the facility
```

Board-room transcripts are saved under `outputs/boardroom/`.

By default, `run` opens the thematic Lab TUI directly: a terminal facility board where departments
wake up, display high-level work bubbles, and log progress as the report is assembled. Use plain
mode for scripts:

```bash
openlogos-lab run "ideas for apps around local-first AI memory" --no-tui
```

One-shot board-room chat:

```bash
openlogos-lab chat "Should we turn this into a product studio?"
```

## Memory

The Lab has three local memory layers:

- **Active memory:** per-session working notes.
- **Passive memory:** append-only observations from chat and research.
- **Long-term memory:** curated durable facts, stored locally and searched before chat/research.

Hermes-style self-learning is available as an explicit reflection step:

```bash
openlogos-lab memory status
openlogos-lab memory search "local-first AI"
openlogos-lab memory add "The founder prefers modular lab departments."
openlogos-lab memory reflect
```

If you say “remember ...” in chat mode, the Lab promotes that statement to long-term memory after
sanitizing it.

The run creates:

```text
outputs/<session-id>_<slug>/
  request.json
  metadata.json
  report.md
  audit.jsonl
  departments/
    director.md
    opportunity_discovery.md
    scientific_inquiry.md
    product_applications.md
    human_testing.md
    risk_ethics.md
  evidence/
    sources.json
    notes.md
```

## Dreaming Mode

The Dreaming Engine monitors configured sources, selects promising topics, and submits them to
the same research pipeline as manual requests.

```bash
openlogos-lab dream --once
```

The first implementation uses simple RSS/URL ingestion and deterministic fallbacks so the system
can be tested without network or model access.

## Development

```bash
make dev
make check
```

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [Departments](docs/departments.md)
- [Demo Mode](docs/demo.md)
