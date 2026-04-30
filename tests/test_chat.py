import time

import httpx

from salinas_lab.chat import RoundTableChat
from salinas_lab.chat.roundtable import ROUND_TABLE
from salinas_lab.models import ModelClient
from salinas_lab.ui.command_center import CommandCenter


class FakeClient:
    def chat(self, **kwargs):
        return f"response from {kwargs['model']}"


def test_roundtable_chat_returns_board_room_group(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SALINAS_OFFLINE", "true")
    monkeypatch.setenv("SALINAS_MEMORY_DIR", str(tmp_path / "memory"))
    chat = RoundTableChat(client=FakeClient(), transcript_root=tmp_path / "boardroom")

    rendered = chat.respond("Should this be research mode?")

    assert rendered.renderables
    assert chat.history
    assert chat.transcript_path.exists()


def test_roundtable_departments_run_in_parallel(tmp_path, monkeypatch) -> None:
    class SlowClient:
        def chat(self, **kwargs):
            if "closing a board-room discussion" not in kwargs["system"]:
                time.sleep(0.1)
            return f"response from {kwargs['model']}"

    monkeypatch.setenv("SALINAS_OFFLINE", "true")
    monkeypatch.setenv("SALINAS_MEMORY_DIR", str(tmp_path / "memory"))
    chat = RoundTableChat(client=SlowClient(), transcript_root=tmp_path / "boardroom")

    start = time.time()
    chat.respond("everyone parallel check")
    elapsed = time.time() - start

    assert elapsed < 0.35


def test_roundtable_routes_casual_chat_to_subset(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SALINAS_MEMORY_DIR", str(tmp_path / "memory"))
    chat = RoundTableChat(client=FakeClient(), transcript_root=tmp_path / "boardroom")

    casual = chat.route_seats("hello")
    full = chat.route_seats("everyone weigh in")

    assert len(casual) < len(full)
    assert full == chat.seats


def test_model_client_timeout_error_does_not_mask_name_error() -> None:
    client = ModelClient(timeout=12)

    message = client._safe_error(httpx.ReadTimeout("timed out"))

    assert "12s timeout" in message
    assert "NameError" not in message


def test_founder_brief_wraps_unstructured_summary() -> None:
    brief = RoundTableChat._founder_brief("The board thinks this should stay in chat.")

    assert "Decision:" in brief
    assert "Why it matters:" in brief
    assert "Next action:" in brief


def test_research_context_includes_latest_brief_and_rows(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SALINAS_MEMORY_DIR", str(tmp_path / "memory"))
    chat = RoundTableChat(client=FakeClient(), transcript_root=tmp_path / "boardroom")
    chat.last_user_message = "test idea"
    chat.last_summary = "Decision: research\nWhy it matters: useful\nNext action: proceed"
    chat.last_rows = [(ROUND_TABLE[0], "qwen3.6-27b-mlx", "Observation: useful")]

    context = CommandCenter._research_context_from_chat(chat)

    assert "Founder Brief" in context
    assert "Observation: useful" in context


def test_memory_reset_clears_records(tmp_path) -> None:
    from salinas_lab.memory import MemoryStore

    store = MemoryStore(tmp_path / "memory")
    store.add_long_term("durable test memory")
    store.record_passive("passive test", source="test")

    store.reset()

    assert store.status()["long_term_memories"] == 0
    assert store.status()["passive_observations"] == 0
