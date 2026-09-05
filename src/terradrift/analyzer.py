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
from terradrift.offline import scan_directory
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
    """Check if Checkov CLI is available and working."""
    if shutil.which("checkov") is None:
        return False
    # Quick smoke test — some Python versions break Checkov
    proc = subprocess.run(
        ["checkov", "--version"], capture_output=True, text=True, check=False, timeout=10
    )
    return proc.returncode == 0


def run_checkov(target_dir: Path, commit_sha: str = "HEAD") -> list[Finding]:
    """Run Checkov on a directory and return Finding objects.

    Uses Checkov CLI if available and working, otherwise falls back to
    the built-in offline scanner (which covers 20+ common rules).
    """
    if _checkov_available():
        return _run_checkov_cli(target_dir, commit_sha)
    return _offline_fallback_scan(target_dir, commit_sha)


def _run_checkov_cli(target_dir: Path, commit_sha: str) -> list[Finding]:
    """Run Checkov via CLI subprocess."""
    proc = _run(
        ["checkov", "-d", str(target_dir), "-o", "json", "--quiet"],
    )
    return _parse_checkov_json(proc.stdout, commit_sha)


def _run_checkov_library(target_dir: Path, commit_sha: str) -> list[Finding]:
    """Run Checkov as a Python library (when CLI is not on PATH)."""
    import sys

    command = (
        f"import sys; sys.argv = ['checkov', '-d', r'{target_dir}', "
        "'-o', 'json', '--quiet', '--compact']; "
        "from checkov.main import Checkov; Checkov().run()"
    )
    cmd = [sys.executable, "-c", command]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
    return _parse_checkov_json(proc.stdout, commit_sha)


def _parse_checkov_json(stdout: str, commit_sha: str) -> list[Finding]:
    """Parse Checkov JSON output into Finding objects."""
    if not stdout.strip():
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        results = [r for d in data for r in d.get("results", {}).get("failed_checks", [])]
    else:
        results = data.get("results", {}).get("failed_checks", [])

    findings: list[Finding] = []
    for r in results:
        rule_id = r.get("check_id", "UNKNOWN")
        sev = SEVERITY_NORMALIZE.get(str(r.get("severity") or "MEDIUM").upper(), "MEDIUM")
        resource = str(r.get("resource") or "")
        file_path = str(r.get("file_path") or "")
        line_range = r.get("file_line_range") or [0, 0]
        findings.append(
            Finding(
                rule_id=rule_id,
                category=classify(rule_id),
                severity=sev,  # type: ignore[arg-type]
                file_path=file_path,
                resource_address=resource if resource else f"{file_path}:{line_range[0]}",
                line_start=int(line_range[0] or 0),
                line_end=int(line_range[1] or 0),
                commit_sha=commit_sha,
                detected_at=datetime.now(UTC),
                message=str(r.get("check_name") or ""),
            )
        )
    return findings


def _offline_fallback_scan(target_dir: Path, commit_sha: str) -> list[Finding]:
    """Run the built-in resource-aware scanner."""
    return scan_directory(target_dir, commit_sha)
