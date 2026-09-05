"""Git history walker for detecting Terraform security drift."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from terradrift.analyzer import run_checkov
from terradrift.drift import detect_drift
from terradrift.models import DriftEvent, Finding

Scanner = Callable[[Path, str], list[Finding]]


@dataclass(slots=True)
class RepoResult:
    """Findings and drift events produced while walking one repository."""

    repo: str
    commits_walked: int
    findings: list[Finding] = field(default_factory=list)
    drift_events: list[DriftEvent] = field(default_factory=list)
    error: str = ""

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    def as_dict(self) -> dict[str, object]:
        return {
            "repo": self.repo,
            "commits_walked": self.commits_walked,
            "total_findings": self.total_findings,
            "findings": [finding.model_dump(mode="json") for finding in self.findings],
            "drift_events": [event.model_dump(mode="json") for event in self.drift_events],
            "error": self.error,
        }


def clone_repo(source: str, destination: Path, depth: int = 100) -> bool:
    """Clone a GitHub owner/name, URL, or local repository path."""
    if "://" in source or source.startswith(("/", ".")):
        url = source
    else:
        url = f"https://github.com/{source}.git"
    command = ["git", "clone", "--quiet", "--no-tags", "--depth", str(depth), url, str(destination)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def get_commit_log(repo_dir: Path, max_commits: int) -> list[tuple[str, datetime]]:
    """Return up to ``max_commits`` non-merge commits in oldest-first order."""
    result = subprocess.run(
        ["git", "log", f"--max-count={max_commits}", "--format=%H|%aI", "--no-merges"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    commits: list[tuple[str, datetime]] = []
    for line in result.stdout.splitlines():
        sha, separator, raw_date = line.partition("|")
        if not separator:
            continue
        try:
            committed_at = datetime.fromisoformat(raw_date)
        except ValueError:
            committed_at = datetime.now(UTC)
        commits.append((sha, committed_at))
    commits.reverse()
    return commits


def _checkout(repo_dir: Path, sha: str) -> bool:
    result = subprocess.run(
        ["git", "checkout", "--quiet", "--force", sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _has_terraform(repo_dir: Path) -> bool:
    return any(".terraform" not in path.parts for path in repo_dir.rglob("*.tf"))


def _scan(scanner: Scanner, directory: Path, sha: str) -> list[Finding]:
    return scanner(directory, sha)


def walk_repo(
    repo: str,
    *,
    source: str | None = None,
    clone_base: Path,
    max_commits: int = 50,
    scanner: Scanner = run_checkov,
) -> RepoResult:
    """Clone and scan a repository's commits from oldest to newest."""
    destination = clone_base / repo.replace("/", "__").replace(":", "_")
    clone_base.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(destination, ignore_errors=True)
    if not clone_repo(source or repo, destination, depth=max(max_commits, 2)):
        return RepoResult(repo=repo, commits_walked=0, error="clone_failed")

    try:
        commits = get_commit_log(destination, max_commits)
        if not commits:
            return RepoResult(repo=repo, commits_walked=0, error="no_commits")

        all_findings: list[Finding] = []
        all_events: list[DriftEvent] = []
        previous_findings: list[Finding] = []
        previous_sha = ""
        previous_at = commits[0][1]
        fixed_history: set[tuple[str, str, str]] = set()
        walked = 0

        for sha, committed_at in commits:
            if not _checkout(destination, sha):
                continue
            walked += 1
            current = _scan(scanner, destination, sha[:8]) if _has_terraform(destination) else []
            all_findings.extend(current)
            if not previous_sha:
                all_events.extend(
                    DriftEvent(
                        repo=repo,
                        rule_id=finding.rule_id,
                        resource_address=finding.resource_address,
                        event="INTRODUCED",
                        from_sha="00000000",
                        to_sha=sha[:8],
                        days_alive=0.0,
                    )
                    for finding in current
                )
            else:
                events = detect_drift(
                    repo,
                    previous_findings,
                    previous_sha,
                    previous_at,
                    current,
                    sha[:8],
                    committed_at,
                    history_fixed=fixed_history,
                )
                all_events.extend(events)
                fixed_keys = {
                    (event.rule_id, event.resource_address)
                    for event in events
                    if event.event == "FIXED"
                }
                fixed_history.update(
                    (finding.rule_id, finding.file_path, finding.resource_address)
                    for finding in previous_findings
                    if (finding.rule_id, finding.resource_address) in fixed_keys
                )
            previous_findings = current
            previous_sha = sha[:8]
            previous_at = committed_at

        return RepoResult(repo, walked, all_findings, all_events)
    finally:
        shutil.rmtree(destination, ignore_errors=True)


def load_manifest(path: Path, limit: int | None = None) -> list[str]:
    """Load repository names from a crawler CSV manifest."""
    with path.open(encoding="utf-8", newline="") as stream:
        repos = [row["full_name"].strip() for row in csv.DictReader(stream) if row.get("full_name")]
    return repos if limit is None else repos[:limit]


def save_results(results: list[RepoResult], output: Path) -> None:
    """Write machine-readable history results."""
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "repos_walked": len(results),
        "total_findings": sum(result.total_findings for result in results),
        "total_drift_events": sum(len(result.drift_events) for result in results),
        "results": [result.as_dict() for result in results],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Command-line entry point retained for ``corpus/walker.py`` users."""
    import argparse

    parser = argparse.ArgumentParser(description="Walk Terraform histories and detect drift.")
    parser.add_argument("--repo", help="Single GitHub owner/name")
    parser.add_argument("--source", help="Optional URL or local source for --repo")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-commits", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("corpus/results.json"))
    parser.add_argument("--clone-dir", type=Path, default=Path("corpus/clones"))
    args = parser.parse_args()

    if args.repo:
        repo_sources = [(args.repo, args.source)]
    elif args.manifest:
        repo_sources = [(repo, None) for repo in load_manifest(args.manifest, args.limit)]
    else:
        parser.error("provide --repo or --manifest")

    started = time.monotonic()
    results = [
        walk_repo(
            repo,
            source=source,
            clone_base=args.clone_dir,
            max_commits=args.max_commits,
        )
        for repo, source in repo_sources
    ]
    save_results(results, args.output)
    print(f"Walked {len(results)} repositories in {time.monotonic() - started:.1f}s")
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
