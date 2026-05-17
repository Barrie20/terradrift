"""Drift detector — compares Findings between two commits.

Real-world analogy: it's a "spot the difference" puzzle between yesterday's
and today's photo of the cloud infrastructure. We label each difference as
INTRODUCED (new mistake), FIXED (mistake resolved), or REGRESSED (a fixed
mistake came back).
"""

from __future__ import annotations

from datetime import datetime

from terradrift.models import DriftEvent, Finding


def _key(f: Finding) -> tuple[str, str, str]:
    """Stable identity for a finding across commits."""
    return (f.rule_id, f.file_path, f.resource_address)


def detect_drift(
    repo: str,
    older: list[Finding],
    older_sha: str,
    older_at: datetime,
    newer: list[Finding],
    newer_sha: str,
    newer_at: datetime,
    history_fixed: set[tuple[str, str, str]] | None = None,
) -> list[DriftEvent]:
    """Compute drift events between two commits.

    Parameters
    ----------
    history_fixed : set
        Keys of findings that were fixed at any earlier commit. Used to detect
        REGRESSED events.
    """
    history_fixed = history_fixed or set()
    older_keys = {_key(f) for f in older}
    newer_keys = {_key(f) for f in newer}

    introduced = newer_keys - older_keys
    fixed = older_keys - newer_keys

    days = max((newer_at - older_at).total_seconds() / 86400.0, 0.0)

    events: list[DriftEvent] = []

    for k in introduced:
        event_kind = "REGRESSED" if k in history_fixed else "INTRODUCED"
        events.append(
            DriftEvent(
                repo=repo,
                rule_id=k[0],
                resource_address=k[2],
                event=event_kind,  # type: ignore[arg-type]
                from_sha=older_sha,
                to_sha=newer_sha,
                days_alive=0.0,
            )
        )

    for k in fixed:
        events.append(
            DriftEvent(
                repo=repo,
                rule_id=k[0],
                resource_address=k[2],
                event="FIXED",
                from_sha=older_sha,
                to_sha=newer_sha,
                days_alive=days,
            )
        )

    return events
