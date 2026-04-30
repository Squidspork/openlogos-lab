from typer.testing import CliRunner

from salinas_lab.cli import app


def test_cli_run_creates_report_folder(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SALINAS_OFFLINE", "true")
    monkeypatch.setenv("SALINAS_MEMORY_DIR", str(tmp_path / "memory"))
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["run", "ideas for apps around lab notebooks", "--output-dir", str(tmp_path), "--no-tui"],
    )

    assert result.exit_code == 0
    reports = list(tmp_path.glob("*/report.md"))
    audits = list(tmp_path.glob("*/audit.jsonl"))
    department_notes = list(tmp_path.glob("*/departments/*.md"))
    assert reports
    assert audits
    assert department_notes
