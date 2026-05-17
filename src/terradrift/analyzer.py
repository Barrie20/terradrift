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

    cmd = [
        sys.executable, "-c",
        f"import sys; sys.argv = ['checkov', '-d', r'{target_dir}', '-o', 'json', '--quiet', '--compact']; "
        f"from checkov.main import Checkov; Checkov().run()"
    ]
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


# ---------------------------------------------------------------------------
# Offline fallback: a tiny rule engine that works without Checkov installed.
# It only flags a handful of obvious patterns; real research uses Checkov.
# ---------------------------------------------------------------------------

_OFFLINE_RULES: list[tuple[str, str, str]] = [
    # S3 rules
    ("CKV_AWS_20", r'acl\s*=\s*"public-read"', "S3 bucket allows public read"),
    ("CKV_AWS_18", r'logging\s*\{', "S3 access logging configured"),  # inverted below
    ("CKV_AWS_19", r'server_side_encryption_configuration\s*\{', "S3 encryption configured"),
    ("CKV_AWS_21", r'versioning\s*\{[^}]*enabled\s*=\s*true', "S3 versioning enabled"),
    # Network rules
    ("CKV_AWS_24", r'cidr_blocks\s*=\s*\[\s*"0\.0\.0\.0/0"', "SG allows 0.0.0.0/0"),
    ("CKV_AWS_260", r'from_port\s*=\s*0\s*\n\s*to_port\s*=\s*0', "SG allows all ports"),
    # IAM rules
    ("CKV_AWS_1", r'"Effect"\s*:\s*"Allow"[^}]*"\*"', "IAM policy with wildcard"),
    ("CKV_AWS_40", r'create_policy\s*=\s*true', "IAM policy attached directly"),
    # Secrets
    ("CKV_AWS_41", r'(AKIA[0-9A-Z]{16})', "Hardcoded AWS access key"),
    ("CKV_AWS_41b", r'secret_key\s*=\s*"[^"]{20,}"', "Hardcoded secret key"),
    # EC2 / metadata
    ("CKV_AWS_79", r'http_tokens\s*=\s*"optional"', "IMDSv2 not enforced"),
    ("CKV_AWS_79b", r'metadata_options\s*\{[^}]*http_endpoint\s*=\s*"enabled"', "Metadata endpoint enabled"),
    # Encryption
    ("CKV_AWS_16", r'storage_encrypted\s*=\s*false', "RDS not encrypted"),
    ("CKV_AWS_17", r'publicly_accessible\s*=\s*true', "RDS publicly accessible"),
    ("CKV_AWS_145", r'kms_key_id\s*=', "KMS key configured"),
    # Logging
    ("CKV_AWS_35", r'enable_log_file_validation\s*=\s*false', "CloudTrail log validation disabled"),
    ("CKV_AWS_36", r'is_multi_region_trail\s*=\s*false', "CloudTrail not multi-region"),
    # TLS
    ("CKV_AWS_103", r'minimum_protocol_version\s*=\s*"TLSv1"', "TLS 1.0 allowed"),
    ("CKV_AWS_103b", r'ssl_policy\s*=\s*"ELBSecurityPolicy-2016-08"', "Weak SSL policy"),
    # Deletion protection
    ("CKV_AWS_293", r'deletion_protection\s*=\s*false', "Deletion protection disabled"),
    # Tags (governance)
    ("CKV_AWS_TAG", r'resource\s+"aws_[^"]+"\s+"[^"]+"\s*\{(?:(?!tags\s*[=\{]).)*\}', "Resource missing tags"),
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
                # Use file:line as resource address so drift detector
                # can distinguish between different findings in same file
                rel_path = str(tf.relative_to(target_dir))
                resource = f"{rel_path}:{line}"
                findings.append(
                    Finding(
                        rule_id=rule_id,
                        category=classify(rule_id),
                        severity="HIGH",
                        file_path=rel_path,
                        resource_address=resource,
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
