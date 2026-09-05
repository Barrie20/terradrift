from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from terradrift.cli import main
from terradrift.models import Finding
from terradrift.taxonomy import Category


def _finding() -> Finding:
    return Finding(
        rule_id="CKV_AWS_20",
        category=Category.PUBLIC_EXPOSURE,
        severity="HIGH",
        file_path="main.tf",
        resource_address="aws_s3_bucket.public",
        line_start=2,
        line_end=2,
        commit_sha="HEAD",
        detected_at=datetime.now(UTC),
        message="public bucket",
    )


def test_version_command() -> None:
    result = CliRunner().invoke(main, ["version"])

    assert result.exit_code == 0
    assert "terradrift 0.1.0" in result.output


def test_scan_clean_directory_exits_zero(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("terradrift.cli.run_checkov", lambda target, commit_sha: [])

    result = CliRunner().invoke(main, ["scan", str(tmp_path)])

    assert result.exit_code == 0
    assert "0 findings" in result.output


def test_scan_findings_write_csv_and_exit_one(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("terradrift.cli.run_checkov", lambda target, commit_sha: [_finding()])
    output = tmp_path / "nested" / "report.csv"

    result = CliRunner().invoke(main, ["scan", str(tmp_path), "--output", str(output)])

    assert result.exit_code == 1
    assert output.exists()
    assert "CKV_AWS_20" in output.read_text(encoding="utf-8")


def test_reproduce_command_invokes_pipeline(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(subset: str, **kwargs):
        captured.update({"subset": subset, **kwargs})
        return SimpleNamespace(
            results_json=tmp_path / "results.json",
            chart=tmp_path / "chart.svg",
        )

    monkeypatch.setattr("terradrift.cli.run_reproduction", fake_run)
    monkeypatch.setattr("terradrift.cli.describe_reproduction", lambda artifacts: "done")

    result = CliRunner().invoke(
        main,
        [
            "reproduce",
            "--subset",
            "mini",
            "--limit",
            "3",
            "--max-commits",
            "2",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert captured["subset"] == "mini"
    assert captured["limit"] == 3
    assert captured["max_commits"] == 2
    assert "done" in result.output


def test_full_reproduction_requires_manifest(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        main,
        ["reproduce", "--subset", "full", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "requires --manifest" in result.output
