"""Reproducible local pipeline: history scan, DuckDB load, and summaries."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from terradrift.history import RepoResult, load_manifest, save_results, walk_repo
from terradrift.warehouse import replace_repository_data, warehouse_summary, write_summary_files

MINI_REPOSITORIES: tuple[str, ...] = (
    "terraform-aws-modules/terraform-aws-vpc",
    "terraform-aws-modules/terraform-aws-eks",
    "terraform-aws-modules/terraform-aws-rds",
    "terraform-aws-modules/terraform-aws-s3-bucket",
    "cloudposse/terraform-aws-vpc",
    "cloudposse/terraform-aws-ec2-instance",
    "nozaq/terraform-aws-secure-baseline",
    "bridgecrewio/terragoat",
    "antonbabenko/terraform-best-practices",
    "futurice/terraform-examples",
)


@dataclass(frozen=True, slots=True)
class ReproductionArtifacts:
    """Paths and results produced by one reproducibility run."""

    results: tuple[RepoResult, ...]
    output_dir: Path
    results_json: Path
    database: Path
    summary_json: Path
    chart: Path


def repository_set(
    subset: str,
    *,
    manifest: Path | None = None,
    limit: int | None = None,
) -> list[str]:
    """Resolve repository names for a mini or full run."""
    if manifest is not None:
        repos = load_manifest(manifest, limit)
    elif subset == "mini":
        repos = list(MINI_REPOSITORIES[:limit]) if limit is not None else list(MINI_REPOSITORIES)
    else:
        raise ValueError("the full subset requires --manifest")
    if not repos:
        raise ValueError("the selected repository set is empty")
    return repos


def run_reproduction(
    subset: str,
    *,
    output_dir: Path,
    manifest: Path | None = None,
    limit: int | None = None,
    max_commits: int = 10,
    repositories: Sequence[str] | None = None,
) -> ReproductionArtifacts:
    """Run the complete pipeline and return all generated artifacts."""
    repos = (
        list(repositories)
        if repositories is not None
        else repository_set(subset, manifest=manifest, limit=limit)
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    clone_dir = output_dir / "clones"
    database = output_dir / "terradrift.duckdb"
    results_json = output_dir / "results.json"
    if database.exists():
        database.unlink()
    shutil.rmtree(clone_dir, ignore_errors=True)

    results: list[RepoResult] = []
    for index, repo in enumerate(repos, 1):
        print(f"[{index}/{len(repos)}] Walking {repo}")
        result = walk_repo(repo, clone_base=clone_dir, max_commits=max_commits)
        results.append(result)
        replace_repository_data(database, repo, result.findings, result.drift_events)
        status = result.error or "ok"
        print(
            f"  {status}: {result.commits_walked} commits, "
            f"{result.total_findings} findings, {len(result.drift_events)} events"
        )

    save_results(results, results_json)
    summary_paths = write_summary_files(database, output_dir)
    shutil.rmtree(clone_dir, ignore_errors=True)
    return ReproductionArtifacts(
        results=tuple(results),
        output_dir=output_dir,
        results_json=results_json,
        database=database,
        summary_json=summary_paths["json"],
        chart=summary_paths["chart"],
    )


def describe_reproduction(artifacts: ReproductionArtifacts) -> str:
    """Return a concise human-readable completion message."""
    summary = warehouse_summary(artifacts.database)
    errors = sum(bool(result.error) for result in artifacts.results)
    return (
        f"Completed {len(artifacts.results)} repositories ({errors} errors); "
        f"stored {summary['findings']} findings in {artifacts.database}."
    )
