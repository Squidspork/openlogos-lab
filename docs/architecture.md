# Architecture

OpenLogos Lab is a local-first multi-agent research system.

## Flow

```text
Founder Console
  -> Chat Mode: selected department heads respond in parallel
  -> Research Mode: full department pipeline writes a report
  -> Memory: active, passive, and long-term context
  -> Outputs: transcripts, reports, audit logs, evidence
```

## Core Modules

- `salinas_lab/chat/`: board-room round table.
- `salinas_lab/departments/`: modular research departments.
- `salinas_lab/graph/`: request/state schemas and research pipeline.
- `salinas_lab/models/`: LM Studio client, routing, and health checks.
- `salinas_lab/memory/`: active, passive, and long-term memory.
- `salinas_lab/audit/`: output folders and append-only logs.
- `salinas_lab/ui/`: terminal UI and Founder Console.

## Design Constraints

- No cloud dependency by default.
- No fake local fallback in normal mode.
- Deterministic demo/test modes are explicit.
- Secrets should never be committed or displayed.
