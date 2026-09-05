import os
import subprocess
from pathlib import Path

from terradrift.analyzer import _offline_fallback_scan
from terradrift.history import walk_repo


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True, text=True)


def _commit(repo: Path, content: str, message: str, day: int) -> None:
    (repo / "main.tf").write_text(content, encoding="utf-8")
    _git(repo, "add", "main.tf")
    environment = os.environ.copy()
    timestamp = f"2026-01-{day:02d}T12:00:00+00:00"
    environment.update({"GIT_AUTHOR_DATE": timestamp, "GIT_COMMITTER_DATE": timestamp})
    _git(repo, "commit", "-m", message, env=environment)


def test_local_history_detects_introduced_fixed_and_regressed(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _git(source, "init", "-b", "main")
    _git(source, "config", "user.name", "TerraDrift Test")
    _git(source, "config", "user.email", "test@example.com")

    insecure = """
resource "aws_s3_bucket" "demo" {
  bucket = "demo"
  acl = "public-read"
}
"""
    secure = """
resource "aws_s3_bucket" "demo" {
  bucket = "demo"
  acl = "private"
  logging { target_bucket = "logs" }
  server_side_encryption_configuration {}
  versioning { enabled = true }
  tags = { Name = "demo" }
}
"""
    _commit(source, insecure, "introduce insecure bucket", 1)
    _commit(source, secure, "secure bucket", 2)
    _commit(source, insecure, "regress bucket", 3)

    result = walk_repo(
        "local/example",
        source=str(source),
        clone_base=tmp_path / "clones",
        max_commits=10,
        scanner=_offline_fallback_scan,
    )

    event_types = {event.event for event in result.drift_events}
    assert result.error == ""
    assert result.commits_walked == 3
    assert event_types == {"INTRODUCED", "FIXED", "REGRESSED"}
    assert any(
        event.event == "REGRESSED" and event.resource_address == "aws_s3_bucket.demo"
        for event in result.drift_events
    )
