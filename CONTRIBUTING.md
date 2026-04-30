# Contributing

Thanks for improving OpenLogos Lab.

## Development

```bash
python -m pip install -e ".[dev]"
SALINAS_OFFLINE=true pytest
ruff check .
mypy salinas_lab
```

## Guidelines

- Keep departments modular and self-contained.
- Do not commit `.env`, model tokens, transcripts, memory, or generated outputs.
- Prefer small, focused changes with tests.
- Use deterministic `OPENLOGOS_DEMO=true` or `SALINAS_OFFLINE=true` paths for tests.
