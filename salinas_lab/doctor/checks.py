from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from salinas_lab.models import ModelHealthChecker, ModelRouter, ModelTier


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


class Doctor:
    def __init__(self) -> None:
        load_dotenv()

    def run(self, *, live: bool = False) -> list[DoctorCheck]:
        checks = [
            self._env_check(),
            self._path_check("outputs", Path(os.getenv("SALINAS_OUTPUT_DIR", "outputs"))),
            self._path_check("memory", Path(os.getenv("SALINAS_MEMORY_DIR", "memory"))),
            self._model_config_check(),
        ]
        if live:
            checks.extend(self._live_model_checks())
        return checks

    @staticmethod
    def _env_check() -> DoctorCheck:
        base = os.getenv("LM_STUDIO_BASE_URL", "")
        key = os.getenv("LM_STUDIO_API_KEY", "")
        if not base:
            return DoctorCheck("environment", "fail", "LM_STUDIO_BASE_URL is not set")
        if not key:
            return DoctorCheck("environment", "warn", "LM_STUDIO_API_KEY is not set")
        return DoctorCheck("environment", "ok", f"LM Studio URL configured: {base}")

    @staticmethod
    def _path_check(name: str, path: Path) -> DoctorCheck:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except Exception as exc:
            return DoctorCheck(name, "fail", f"{path}: {exc}")
        return DoctorCheck(name, "ok", str(path))

    @staticmethod
    def _model_config_check() -> DoctorCheck:
        router = ModelRouter()
        configured = ", ".join(f"{tier.value}={router.model_for(tier)}" for tier in ModelTier)
        return DoctorCheck("model config", "ok", configured)

    @staticmethod
    def _live_model_checks() -> list[DoctorCheck]:
        checks = []
        for health in ModelHealthChecker().check_all():
            status = "ok" if health.status == "ready" else "warn"
            detail = f"{health.model}: {health.status}"
            if health.latency_seconds is not None:
                detail += f" ({health.latency_seconds:.1f}s)"
            if health.detail:
                detail += f" - {health.detail}"
            checks.append(DoctorCheck(f"model {health.tier}", status, detail))
        return checks
