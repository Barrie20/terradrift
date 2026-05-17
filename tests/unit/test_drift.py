from datetime import datetime, timedelta, timezone

from terradrift.drift import detect_drift
from terradrift.models import Finding
from terradrift.taxonomy import Category


def _f(rule: str, resource: str = "aws_s3_bucket.x", sha: str = "sha") -> Finding:
    return Finding(
        rule_id=rule,
        category=Category.PUBLIC_EXPOSURE,
        severity="HIGH",
        file_path="main.tf",
        resource_address=resource,
        line_start=1,
        line_end=1,
        commit_sha=sha,
        detected_at=datetime.now(timezone.utc),
        message="x",
    )


def test_introduced_event() -> None:
    older = []
    newer = [_f("CKV_AWS_20")]
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=3)
    events = detect_drift("o/r", older, "a", t0, newer, "b", t1)
    assert len(events) == 1
    assert events[0].event == "INTRODUCED"


def test_fixed_event_records_days_alive() -> None:
    older = [_f("CKV_AWS_20")]
    newer = []
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=10)
    events = detect_drift("o/r", older, "a", t0, newer, "b", t1)
    assert len(events) == 1
    assert events[0].event == "FIXED"
    assert events[0].days_alive == 10.0


def test_regression_uses_history() -> None:
    older: list[Finding] = []
    newer = [_f("CKV_AWS_20")]
    history = {("CKV_AWS_20", "main.tf", "aws_s3_bucket.x")}
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=1)
    events = detect_drift("o/r", older, "a", t0, newer, "b", t1, history_fixed=history)
    assert len(events) == 1
    assert events[0].event == "REGRESSED"
