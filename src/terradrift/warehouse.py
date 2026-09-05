"""DuckDB persistence and dependency-free summary chart generation."""

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path

import duckdb

from terradrift.models import DriftEvent, Finding

_SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    repo VARCHAR NOT NULL,
    rule_id VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    severity VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    resource_address VARCHAR NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    commit_sha VARCHAR NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    message VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS drift_events (
    repo VARCHAR NOT NULL,
    rule_id VARCHAR NOT NULL,
    resource_address VARCHAR NOT NULL,
    event VARCHAR NOT NULL,
    from_sha VARCHAR NOT NULL,
    to_sha VARCHAR NOT NULL,
    days_alive DOUBLE NOT NULL
);
"""


def initialize_database(path: Path) -> None:
    """Create the warehouse and its tables if they do not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as connection:
        connection.execute(_SCHEMA)


def replace_repository_data(
    path: Path,
    repo: str,
    findings: Iterable[Finding],
    events: Iterable[DriftEvent],
) -> None:
    """Atomically replace one repository's rows in the warehouse."""
    initialize_database(path)
    finding_rows = [
        (
            repo,
            finding.rule_id,
            finding.category.value,
            finding.severity,
            finding.file_path,
            finding.resource_address,
            finding.line_start,
            finding.line_end,
            finding.commit_sha,
            finding.detected_at,
            finding.message,
        )
        for finding in findings
    ]
    event_rows = [
        (
            event.repo,
            event.rule_id,
            event.resource_address,
            event.event,
            event.from_sha,
            event.to_sha,
            event.days_alive,
        )
        for event in events
    ]
    with duckdb.connect(str(path)) as connection:
        connection.begin()
        try:
            connection.execute("DELETE FROM findings WHERE repo = ?", [repo])
            connection.execute("DELETE FROM drift_events WHERE repo = ?", [repo])
            if finding_rows:
                connection.executemany(
                    "INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    finding_rows,
                )
            if event_rows:
                connection.executemany(
                    "INSERT INTO drift_events VALUES (?, ?, ?, ?, ?, ?, ?)", event_rows
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def event_counts(path: Path) -> dict[str, int]:
    """Return drift event totals, including zero-valued event types."""
    counts = {"INTRODUCED": 0, "FIXED": 0, "REGRESSED": 0}
    if not path.exists():
        return counts
    with duckdb.connect(str(path), read_only=True) as connection:
        rows = connection.execute(
            "SELECT event, COUNT(*) FROM drift_events GROUP BY event ORDER BY event"
        ).fetchall()
    counts.update({str(event): int(count) for event, count in rows})
    return counts


def warehouse_summary(path: Path) -> dict[str, object]:
    """Compute compact aggregate metrics from a warehouse."""
    if not path.exists():
        return {"repositories": 0, "findings": 0, "drift_events": event_counts(path)}
    with duckdb.connect(str(path), read_only=True) as connection:
        repository_row = connection.execute("SELECT COUNT(DISTINCT repo) FROM findings").fetchone()
        finding_row = connection.execute("SELECT COUNT(*) FROM findings").fetchone()
    repositories = int(repository_row[0]) if repository_row else 0
    findings = int(finding_row[0]) if finding_row else 0
    return {
        "repositories": repositories,
        "findings": findings,
        "drift_events": event_counts(path),
    }


def write_summary_files(path: Path, output_dir: Path) -> dict[str, Path]:
    """Write JSON, CSV, and an SVG bar chart from warehouse aggregates."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = warehouse_summary(path)
    counts = summary["drift_events"]
    if not isinstance(counts, dict):
        raise TypeError("drift_events summary must be a dictionary")

    json_path = output_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    csv_path = output_dir / "drift-events.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["event", "count"])
        writer.writerows((event, counts[event]) for event in ("INTRODUCED", "FIXED", "REGRESSED"))

    chart_path = output_dir / "drift-events.svg"
    chart_path.write_text(_svg_chart(counts), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "chart": chart_path}


def _svg_chart(counts: Mapping[str, int]) -> str:
    left, top, chart_height = 90, 70, 260
    events = ("INTRODUCED", "FIXED", "REGRESSED")
    colors = ("#d97706", "#059669", "#dc2626")
    maximum = max((int(counts.get(event, 0)) for event in events), default=0) or 1
    bars: list[str] = []
    for index, (event, color) in enumerate(zip(events, colors, strict=True)):
        value = int(counts.get(event, 0))
        bar_height = int(chart_height * value / maximum)
        x = left + 65 + index * 190
        y = top + chart_height - bar_height
        bars.extend(
            [
                (f'<rect x="{x}" y="{y}" width="90" height="{bar_height}" fill="{color}" rx="5"/>'),
                (
                    f'<text x="{x + 45}" y="{y - 10}" text-anchor="middle" '
                    f'class="value">{value}</text>'
                ),
                (
                    f'<text x="{x + 45}" y="{top + chart_height + 30}" '
                    f'text-anchor="middle" class="label">'
                    f"{html.escape(event.title())}</text>"
                ),
            ]
        )
    return "\n".join(
        [
            (
                '<svg xmlns="http://www.w3.org/2000/svg" width="720" '
                'height="420" viewBox="0 0 720 420">'
            ),
            (
                "<style>text{font-family:system-ui,sans-serif;fill:#172033}"
                ".title{font-size:24px;font-weight:700}.label{font-size:15px}"
                ".value{font-size:18px;font-weight:700}</style>"
            ),
            '<rect width="720" height="420" fill="#f8fafc" rx="12"/>',
            (
                '<text x="360" y="38" text-anchor="middle" class="title">'
                "TerraDrift Security Events</text>"
            ),
            (
                f'<line x1="{left}" y1="{top + chart_height}" x2="680" '
                f'y2="{top + chart_height}" stroke="#64748b"/>'
            ),
            *bars,
            "</svg>",
        ]
    )


def count_events(events: Iterable[Mapping[str, object]]) -> dict[str, int]:
    """Count serialized event dictionaries for console summaries."""
    raw = Counter(str(event.get("event", "UNKNOWN")) for event in events)
    return {event: raw[event] for event in ("INTRODUCED", "FIXED", "REGRESSED")}
