from datetime import UTC, datetime
from pathlib import Path

import duckdb

from terradrift.models import DriftEvent, Finding
from terradrift.taxonomy import Category
from terradrift.warehouse import event_counts, replace_repository_data, write_summary_files


def _finding(sha: str = "abc") -> Finding:
    return Finding(
        rule_id="CKV_AWS_20",
        category=Category.PUBLIC_EXPOSURE,
        severity="HIGH",
        file_path="main.tf",
        resource_address="aws_s3_bucket.public",
        line_start=1,
        line_end=2,
        commit_sha=sha,
        detected_at=datetime.now(UTC),
        message="public",
    )


def _event(kind: str = "INTRODUCED") -> DriftEvent:
    return DriftEvent(
        repo="owner/repo",
        rule_id="CKV_AWS_20",
        resource_address="aws_s3_bucket.public",
        event=kind,
        from_sha="one",
        to_sha="two",
        days_alive=1,
    )


def test_repository_data_is_replaced_atomically(tmp_path: Path) -> None:
    database = tmp_path / "results.duckdb"
    replace_repository_data(database, "owner/repo", [_finding("one")], [_event()])
    replace_repository_data(database, "owner/repo", [_finding("two")], [_event("FIXED")])

    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0] == 1
        assert connection.execute("SELECT commit_sha FROM findings").fetchone()[0] == "two"

    assert event_counts(database) == {"INTRODUCED": 0, "FIXED": 1, "REGRESSED": 0}


def test_summary_outputs_include_svg_and_csv(tmp_path: Path) -> None:
    database = tmp_path / "results.duckdb"
    replace_repository_data(database, "owner/repo", [_finding()], [_event("REGRESSED")])

    paths = write_summary_files(database, tmp_path / "summary")

    assert paths["json"].exists()
    assert "REGRESSED,1" in paths["csv"].read_text(encoding="utf-8")
    assert "TerraDrift Security Events" in paths["chart"].read_text(encoding="utf-8")
