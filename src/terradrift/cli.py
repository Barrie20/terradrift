"""TerraDrift command-line interface.

Examples
--------
    terradrift scan ./my-tf-module
    terradrift scan ./my-tf-module --output report.csv
    terradrift reproduce --subset mini
    terradrift version
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from terradrift import __version__
from terradrift.analyzer import run_checkov

console = Console()


@click.group(help="TerraDrift — empirical study of IaC security drift.")
def main() -> None:
    """Top-level CLI."""


@main.command()
def version() -> None:
    """Print version."""
    click.echo(f"terradrift {__version__}")


@main.command()
@click.argument("target", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="CSV output path")
@click.option("--commit", default="HEAD", help="Commit SHA label for findings")
def scan(target: Path, output: Path | None, commit: str) -> None:
    """Scan a Terraform directory and print / write a misconfig report.

    Real-world example:
        terradrift scan ./sample/aws-s3-public

    will scan the included sample module and surface a public-read S3 bucket
    plus a hard-coded AWS key.
    """
    findings = run_checkov(target, commit_sha=commit)

    table = Table(title=f"TerraDrift scan: {target}")
    table.add_column("Rule")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("File")
    table.add_column("Line", justify="right")
    table.add_column("Message")

    for f in findings:
        table.add_row(
            f.rule_id,
            f.category.value,
            f.severity,
            f.file_path,
            str(f.line_start),
            f.message,
        )

    console.print(table)
    console.print(f"[bold]{len(findings)}[/bold] findings.")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(
                ["rule_id", "category", "severity", "file_path",
                 "resource", "line_start", "line_end", "commit_sha", "message"]
            )
            for f in findings:
                w.writerow([f.rule_id, f.category.value, f.severity, f.file_path,
                            f.resource_address, f.line_start, f.line_end,
                            f.commit_sha, f.message])
        console.print(f"Wrote: [green]{output}[/green]")

    sys.exit(0 if not findings else 1)


@main.command()
@click.option("--subset", type=click.Choice(["mini", "full"]), default="mini")
def reproduce(subset: str) -> None:
    """Reproduce paper results.

    `mini` runs a 200-module subset on a laptop in ~15 minutes.
    `full` runs the full corpus and is intended for AWS Batch (~6h).
    """
    if subset == "mini":
        console.print("[yellow]Mini reproduction is a stub in v0.1; "
                      "wire crawler in v0.2.[/yellow]")
    else:
        console.print("[yellow]Full reproduction requires AWS credentials; "
                      "see infra/terraform/.[/yellow]")


if __name__ == "__main__":
    main()
