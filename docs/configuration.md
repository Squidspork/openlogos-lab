# Configuration

Copy `.env.example` to `.env`.

```bash
cp .env.example .env
```

## Required

- `LM_STUDIO_BASE_URL`: OpenAI-compatible LM Studio endpoint.
- `LM_STUDIO_API_KEY`: LM Studio token, if auth is enabled.

## Model Routing

- `SALINAS_MODEL_SMALL`: lightweight/scout model.
- `SALINAS_MODEL_TECHNICAL`: technical/risk model.
- `SALINAS_MODEL_ORCHESTRATOR`: Director model.
- `SALINAS_MODEL_SYNTHESIS`: product/report synthesis model.
- `SALINAS_MODEL_EMBEDDING`: embedding model.

## Runtime

- `SALINAS_OUTPUT_DIR`: reports, transcripts, audit logs.
- `SALINAS_MEMORY_DIR`: active/passive/long-term memory.
- `SALINAS_CHAT_MAX_WORKERS`: max parallel board-room calls.
- `OPENLOGOS_DEMO=true`: deterministic demo responses.
- `SALINAS_OFFLINE=true`: test-only deterministic fallback.
