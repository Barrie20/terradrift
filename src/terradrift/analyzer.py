"""Static analyzer adapters.

Wraps Checkov / Trivy / tfsec, normalizes their output into Finding objects.

Real-world analogy: these are three different home inspectors checking the
same house. Each notices different problems; we merge their reports.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from terradrift.models import Finding
from terradrift.taxonomy import classify

SEVERITY_NORMALIZE = {
    "INFO": "LOW",
    "LOW": "LOW",
    "MEDIUM": "MEDIUM",
    "MODERATE": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "CRITICAL",
}


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a subprocess and capture output. Never raise on non-zero exit;
    Checkov returns 1 when findings are present."""
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def _checkov_available() -> bool:
    return shutil.which("checkov") is not None


def run_checkov(target_dir: Path, commit_sha: str = "HEAD") -> list[Finding]:
    """Run Checkov on a directory and return Finding objects.

    If Checkov is not installed, fall back to a deterministic offline parser
    so the demo and tests work without external tooling.
    """
    if not _checkov_available():
        return _offline_fallback_scan(target_dir, commit_sha)

    proc = _run(
        ["checkov", "-d", str(target_dir), "-o", "json", "--quiet"],
    )
    if not proc.stdout.strip():
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []

    # Checkov returns either a list (multi-framework) or dict (single).
    if isinstance(data, list):
        results = [r for d in data for r in d.get("results", {}).get("failed_checks", [])]
    else:
        results = data.get("results", {}).get("failed_checks", [])

    findings: list[Finding] = []
    for r in results:
        rule_id = r.get("check_id", "UNKNOWN")
        sev = SEVERITY_NORMALIZE.get(str(r.get("severity") or "MEDIUM").upper(), "MEDIUM")
        findings.append(
            Finding(
                rule_id=rule_id,
                category=classify(rule_id),
                severity=sev,  # type: ignore[arg-type]
                file_path=str(r.get("file_path") or ""),
                resource_address=str(r.get("resource") or ""),
                line_start=int((r.get("file_line_range") or [0, 0])[0] or 0),
                line_end=int((r.get("file_line_range") or [0, 0])[1] or 0),
                commit_sha=commit_sha,
                detected_at=datetime.now(UTC),
                message=str(r.get("check_name") or ""),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Offline fallback: a tiny rule engine that works without Checkov installed.
# It only flags a handful of obvious patterns; real research uses Checkov.
# ---------------------------------------------------------------------------

_OFFLINE_RULES: list[tuple[str, str, str]] = [
    # (rule_id, regex_pattern, message)
    ("CKV_AWS_20", r'acl\s*=\s*"public-read"', "S3 bucket allows public read"),
    ("CKV_AWS_18", r'aws_s3_bucket"\s+"', "S3 access logging not configured"),
    ("CKV_AWS_24", r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"', "SG allows 0.0.0.0/0"),
    ("CKV_AWS_41", r"(AKIA[0-9A-Z]{16})", "Hardcoded AWS access key"),
    ("CKV_AWS_19", r'aws_s3_bucket"\s+"', "S3 server-side encryption not set"),
]


def _offline_fallback_scan(target_dir: Path, commit_sha: str) -> list[Finding]:
    import re

    findings: list[Finding] = []
    for tf in target_dir.rglob("*.tf"):
        try:
            text = tf.read_text(errors="ignore")
        except OSError:
            continue
        for rule_id, pattern, msg in _OFFLINE_RULES:
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        category=classify(rule_id),
                        severity="HIGH",
                        file_path=str(tf.relative_to(target_dir)),
                        resource_address="(offline-mode)",
                        line_start=line,
                        line_end=line,
                        commit_sha=commit_sha,
                        detected_at=datetime.now(UTC),
                        message=msg,
                    )
                )
    # Deduplicate by (rule_id, file_path, line_start)
    seen: set[tuple[str, str, int]] = set()
    unique: list[Finding] = []
    for f in findings:
        key = (f.rule_id, f.file_path, f.line_start)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique
