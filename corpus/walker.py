"""History Walker — clones repos and scans every commit for drift.

This is the core research engine. It takes a repo from repos.csv, clones it,
walks through its git history commit by commit, runs the scanner at each
commit, and detects drift events (INTRODUCED / FIXED / REGRESSED).

Real-world analogy:
    Imagine you're a health inspector with a time machine. Instead of checking
    a restaurant today, you go back in time and check it every month for the
    past 3 years. You can see: when did the violation first appear? How long
    until they fixed it? Did it come back?

Usage:
    # Scan one repo (quick test)
    python corpus/walker.py --repo terraform-aws-modules/terraform-aws-vpc

    # Scan first 5 repos from your manifest
    python corpus/walker.py --manifest corpus/repos.csv --limit 5

    # Scan all 1000 repos (full research run — takes hours)
    python corpus/walker.py --manifest corpus/repos.csv

Requirements:
    - git installed
    - pip install httpx duckdb
    - export PYTHONPATH=src
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

# Add src to path so we can import terradrift modules
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from terradrift.analyzer import run_checkov
from terradrift.drift import detect_drift
from terradrift.models import DriftEvent, Finding
from terradrift.taxonomy import classify


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "corpus" / "repos.csv"
DEFAULT_OUTPUT = ROOT / "corpus" / "results.json"
CLONE_DIR = ROOT / "corpus" / "clones"  # temporary, gitignored

# Max commits to walk per repo (keeps runtime reasonable)
MAX_COMMITS_PER_REPO = 50


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def clone_repo(full_name: str, dest: Path) -> bool:
    """Clone a GitHub repo to a local directory.

    Real-world analogy: downloading a restaurant's full inspection history
    from the city database.
    """
    url = f"https://github.com/{full_name}.git"
    try:
        result = subprocess.run(
            ["git", "clone", "--quiet", "--no-tags", "--depth", "100", url, str(dest)],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            print(f"  Clone failed: {result.stderr[:200]}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  Clone timed out (300s)")
        return False
    except OSError as e:
        print(f"  Clone OS error: {e}")
        return False


def get_commit_log(repo_dir: Path, max_commits: int = MAX_COMMITS_PER_REPO) -> list[dict]:
    """Get the commit history (SHA + date) for a repo.

    Returns newest-first, but we'll reverse it to walk oldest→newest.

    Real-world analogy: getting the list of all inspection dates for a
    restaurant, from the first day it opened to today.
    """
    result = subprocess.run(
        [
            "git", "log",
            f"--max-count={max_commits}",
            "--format=%H|%aI",  # SHA|ISO-date
            "--no-merges",      # skip merge commits (they don't change code)
        ],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 1)
        if len(parts) == 2:
            commits.append({"sha": parts[0], "date": parts[1]})

    # Reverse so we walk oldest → newest (natural time order)
    commits.reverse()
    return commits


def checkout_commit(repo_dir: Path, sha: str) -> bool:
    """Checkout a specific commit (detached HEAD).

    Real-world analogy: setting the time machine to a specific date.
    """
    result = subprocess.run(
        ["git", "checkout", "--quiet", "--force", sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def find_tf_dirs(repo_dir: Path) -> list[Path]:
    """Find directories containing .tf files.

    Real-world analogy: finding which rooms in the restaurant have
    food-handling equipment (those are the ones we need to inspect).
    """
    tf_dirs: set[Path] = set()
    for tf_file in repo_dir.rglob("*.tf"):
        # Skip .terraform directories (downloaded providers, not user code)
        if ".terraform" in tf_file.parts:
            continue
        tf_dirs.add(tf_file.parent)
    return sorted(tf_dirs)


# ---------------------------------------------------------------------------
# Core walk logic
# ---------------------------------------------------------------------------


@dataclass
class RepoResult:
    """Results from walking one repo's history."""

    repo: str
    commits_walked: int
    total_findings: int
    drift_events: list[dict]
    error: str = ""


def walk_repo(full_name: str, clone_base: Path = CLONE_DIR, max_commits: int = MAX_COMMITS_PER_REPO) -> RepoResult:
    """Walk a single repo's history and detect drift.

    This is the main function. For each repo it:
    1. Clones it
    2. Gets the commit log
    3. For each commit: checkout → find .tf dirs → scan → compare with previous
    4. Records drift events
    5. Cleans up

    Real-world analogy: the full inspection of one restaurant across time.
    """
    print(f"\n{'='*60}")
    print(f"  Walking: {full_name}")
    print(f"{'='*60}")

    # Clone to a temp directory
    clone_base.mkdir(parents=True, exist_ok=True)
    repo_dir = clone_base / full_name.replace("/", "__")

    # Clean up any previous clone
    if repo_dir.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)

    # Step 1: Clone
    print(f"  Cloning...")
    if not clone_repo(full_name, repo_dir):
        return RepoResult(repo=full_name, commits_walked=0, total_findings=0,
                          drift_events=[], error="clone_failed")

    # Step 2: Get commit log
    commits = get_commit_log(repo_dir, max_commits=max_commits)
    if not commits:
        shutil.rmtree(repo_dir, ignore_errors=True)
        return RepoResult(repo=full_name, commits_walked=0, total_findings=0,
                          drift_events=[], error="no_commits")

    print(f"  Found {len(commits)} commits to walk")

    # Step 3: Walk each commit
    previous_findings: list[Finding] = []
    previous_sha = ""
    previous_date = datetime.now(timezone.utc)
    all_drift_events: list[DriftEvent] = []
    total_findings = 0
    history_fixed: set[tuple[str, str, str]] = set()
    is_first_commit = True

    for i, commit in enumerate(commits):
        sha = commit["sha"]
        try:
            commit_date = datetime.fromisoformat(commit["date"])
        except ValueError:
            commit_date = datetime.now(timezone.utc)

        # Checkout this commit
        if not checkout_commit(repo_dir, sha):
            continue

        # Find Terraform directories
        tf_dirs = find_tf_dirs(repo_dir)

        # Scan all .tf directories at this commit
        current_findings: list[Finding] = []
        for tf_dir in tf_dirs:
            findings = run_checkov(tf_dir, commit_sha=sha[:8])
            current_findings.extend(findings)

        total_findings += len(current_findings)

        # Detect drift
        if is_first_commit:
            # First commit: all findings are INTRODUCED (they didn't exist before)
            for f in current_findings:
                all_drift_events.append(
                    DriftEvent(
                        repo=full_name,
                        rule_id=f.rule_id,
                        resource_address=f.resource_address,
                        event="INTRODUCED",
                        from_sha="000000",
                        to_sha=sha[:8],
                        days_alive=0.0,
                    )
                )
            is_first_commit = False
        elif previous_sha:
            events = detect_drift(
                repo=full_name,
                older=previous_findings,
                older_sha=previous_sha,
                older_at=previous_date,
                newer=current_findings,
                newer_sha=sha[:8],
                newer_at=commit_date,
                history_fixed=history_fixed,
            )
            all_drift_events.extend(events)

            # Track fixed findings for regression detection
            for e in events:
                if e.event == "FIXED":
                    history_fixed.add((e.rule_id, "", e.resource_address))

        # Progress indicator
        status = f"  [{i+1}/{len(commits)}] {sha[:8]} | {len(current_findings)} findings"
        if all_drift_events:
            introduced = sum(1 for e in all_drift_events if e.event == "INTRODUCED")
            fixed = sum(1 for e in all_drift_events if e.event == "FIXED")
            regressed = sum(1 for e in all_drift_events if e.event == "REGRESSED")
            status += f" | drift: +{introduced} -{fixed} ↺{regressed}"
        print(status)

        # Save state for next iteration
        previous_findings = current_findings
        previous_sha = sha[:8]
        previous_date = commit_date

    # Step 4: Clean up
    shutil.rmtree(repo_dir, ignore_errors=True)

    # Summary
    introduced = sum(1 for e in all_drift_events if e.event == "INTRODUCED")
    fixed = sum(1 for e in all_drift_events if e.event == "FIXED")
    regressed = sum(1 for e in all_drift_events if e.event == "REGRESSED")

    print(f"\n  Summary for {full_name}:")
    print(f"    Commits walked: {len(commits)}")
    print(f"    Total findings: {total_findings}")
    print(f"    Drift events:   {len(all_drift_events)}")
    print(f"      INTRODUCED:   {introduced}")
    print(f"      FIXED:        {fixed}")
    print(f"      REGRESSED:    {regressed}")

    return RepoResult(
        repo=full_name,
        commits_walked=len(commits),
        total_findings=total_findings,
        drift_events=[
            {
                "repo": e.repo,
                "rule_id": e.rule_id,
                "resource": e.resource_address,
                "event": e.event,
                "from_sha": e.from_sha,
                "to_sha": e.to_sha,
                "days_alive": e.days_alive,
            }
            for e in all_drift_events
        ],
    )


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> list[str]:
    """Load repo names from the CSV manifest."""
    repos = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("full_name", "").strip()
            if name:
                repos.append(name)
    return repos


def save_results(results: list[RepoResult], output: Path) -> None:
    """Save all results to a JSON file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos_walked": len(results),
        "total_drift_events": sum(len(r.drift_events) for r in results),
        "results": [
            {
                "repo": r.repo,
                "commits_walked": r.commits_walked,
                "total_findings": r.total_findings,
                "drift_events": r.drift_events,
                "error": r.error,
            }
            for r in results
        ],
    }
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\nResults saved to: {output}")
    print(f"File size: {output.stat().st_size / 1024:.1f} KB")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Walk Terraform repo histories and detect security drift.",
        epilog=(
            "Examples:\n"
            "  python corpus/walker.py --repo terraform-aws-modules/terraform-aws-vpc\n"
            "  python corpus/walker.py --manifest corpus/repos.csv --limit 5\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo", type=str, default=None,
        help="Single repo to walk (e.g. owner/name)",
    )
    parser.add_argument(
        "--manifest", type=Path, default=None,
        help="Path to repos.csv manifest",
    )
    parser.add_argument(
        "--limit", type=int, default=5,
        help="Max repos to walk from manifest (default: 5)",
    )
    parser.add_argument(
        "--max-commits", type=int, default=MAX_COMMITS_PER_REPO,
        help=f"Max commits per repo (default: {MAX_COMMITS_PER_REPO})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="Output JSON path (default: corpus/results.json)",
    )

    args = parser.parse_args()

    max_commits = args.max_commits

    print("=" * 60)
    print("  TerraDrift History Walker v0.3")
    print("=" * 60)
    print(f"  Max commits/repo: {args.max_commits}")
    print(f"  Output:           {args.output}")
    print(f"  Time:             {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Determine which repos to walk
    if args.repo:
        repo_list = [args.repo]
    elif args.manifest:
        repo_list = load_manifest(args.manifest)[:args.limit]
    else:
        # Default: use the standard manifest
        if DEFAULT_MANIFEST.exists():
            repo_list = load_manifest(DEFAULT_MANIFEST)[:args.limit]
        else:
            print("ERROR: No --repo or --manifest specified, and corpus/repos.csv not found.")
            print("Run the crawler first: python corpus/crawl.py --limit 100")
            sys.exit(1)

    print(f"\n  Repos to walk: {len(repo_list)}")
    for i, name in enumerate(repo_list[:10], 1):
        print(f"    {i}. {name}")
    if len(repo_list) > 10:
        print(f"    ... and {len(repo_list) - 10} more")

    # Walk each repo
    results: list[RepoResult] = []
    start_time = time.time()

    for i, repo_name in enumerate(repo_list, 1):
        print(f"\n[{i}/{len(repo_list)}] Starting: {repo_name}")
        result = walk_repo(repo_name, max_commits=max_commits)
        results.append(result)

    # Save results
    elapsed = time.time() - start_time
    save_results(results, args.output)

    # Final summary
    total_events = sum(len(r.drift_events) for r in results)
    total_introduced = sum(
        sum(1 for e in r.drift_events if e["event"] == "INTRODUCED")
        for r in results
    )
    total_fixed = sum(
        sum(1 for e in r.drift_events if e["event"] == "FIXED")
        for r in results
    )
    total_regressed = sum(
        sum(1 for e in r.drift_events if e["event"] == "REGRESSED")
        for r in results
    )

    print("\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)
    print(f"  Repos walked:     {len(results)}")
    print(f"  Repos with errors:{sum(1 for r in results if r.error)}")
    print(f"  Total commits:    {sum(r.commits_walked for r in results)}")
    print(f"  Total findings:   {sum(r.total_findings for r in results)}")
    print(f"  Total drift events: {total_events}")
    print(f"    INTRODUCED:     {total_introduced}")
    print(f"    FIXED:          {total_fixed}")
    print(f"    REGRESSED:      {total_regressed}")
    print(f"  Time elapsed:     {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print("=" * 60)

    if total_regressed > 0:
        pct = total_regressed / max(total_events, 1) * 100
        print(f"\n  🔬 KEY FINDING: {total_regressed} regressions detected ({pct:.1f}% of events)")
        print(f"     This means previously-fixed misconfigs came BACK.")
        print(f"     This is the novel finding for your paper.")


if __name__ == "__main__":
    main()
