"""Resource-aware Terraform scanner used when Checkov is unavailable.

This is intentionally a small fallback, not a replacement for Checkov. It
recognizes complete HCL blocks so matches are attached to stable Terraform
resource addresses instead of whichever line happened to contain a token.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from terradrift.models import Finding
from terradrift.taxonomy import classify


@dataclass(frozen=True, slots=True)
class HCLBlock:
    """A top-level HCL block with its labels and source location."""

    kind: str
    labels: tuple[str, ...]
    text: str
    start: int
    end: int

    @property
    def resource_address(self) -> str:
        if self.kind == "resource" and len(self.labels) == 2:
            return f"{self.labels[0]}.{self.labels[1]}"
        suffix = ".".join(self.labels)
        return f"{self.kind}.{suffix}" if suffix else self.kind


_HEADER = re.compile(
    r'^\s*(resource|data|provider|module)\s+"([^"]+)"(?:\s+"([^"]+)")?\s*\{',
    re.MULTILINE,
)


# Explicitly insecure settings. The optional resource-type tuple prevents a
# token in an unrelated block from being reported as a cloud finding.
_BLOCK_RULES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "CKV_AWS_20",
        r'acl\s*=\s*"public-read(?:-write)?"',
        "S3 bucket allows public access",
        ("aws_s3_bucket",),
    ),
    (
        "CKV_AWS_24",
        r'cidr_blocks\s*=\s*\[[^]]*"0\.0\.0\.0/0"',
        "Security group allows 0.0.0.0/0",
        ("aws_security_group", "aws_security_group_rule"),
    ),
    (
        "CKV_AWS_260",
        r"from_port\s*=\s*0\s*(?:\n|\r\n).*?to_port\s*=\s*0",
        "Security group allows all ports",
        ("aws_security_group", "aws_security_group_rule"),
    ),
    (
        "CKV_AWS_1",
        r'"Effect"\s*:\s*"Allow"[\s\S]*?"(?:Action|Resource)"\s*:\s*(?:"\*"|\[[^]]*"\*")',
        "IAM policy grants wildcard access",
        ("aws_iam_policy", "aws_iam_role_policy"),
    ),
    ("CKV_AWS_40", r"create_policy\s*=\s*true", "IAM policy attached directly", ("aws_iam_role",)),
    (
        "CKV_AWS_79",
        r'http_tokens\s*=\s*"optional"',
        "IMDSv2 is not enforced",
        ("aws_instance", "aws_launch_template"),
    ),
    (
        "CKV_AWS_16",
        r"storage_encrypted\s*=\s*false",
        "Database storage is not encrypted",
        ("aws_db_instance", "aws_rds_cluster"),
    ),
    (
        "CKV_AWS_17",
        r"publicly_accessible\s*=\s*true",
        "Database is publicly accessible",
        ("aws_db_instance", "aws_rds_cluster"),
    ),
    (
        "CKV_AWS_35",
        r"enable_log_file_validation\s*=\s*false",
        "CloudTrail log validation is disabled",
        ("aws_cloudtrail",),
    ),
    (
        "CKV_AWS_36",
        r"is_multi_region_trail\s*=\s*false",
        "CloudTrail is not multi-region",
        ("aws_cloudtrail",),
    ),
    (
        "CKV_AWS_103",
        r'minimum_protocol_version\s*=\s*"(?:TLSv1|SSLv3)"',
        "Obsolete TLS protocol is allowed",
        ("aws_cloudfront_distribution",),
    ),
    (
        "CKV_AWS_103b",
        r'ssl_policy\s*=\s*"ELBSecurityPolicy-2016-08"',
        "Weak load-balancer TLS policy is enabled",
        ("aws_lb_listener", "aws_elb"),
    ),
    (
        "CKV_AWS_293",
        r"deletion_protection\s*=\s*false",
        "Deletion protection is disabled",
        ("aws_db_instance", "aws_rds_cluster", "aws_lb"),
    ),
)

_SECRET_RULES: tuple[tuple[str, str, str], ...] = (
    ("CKV_AWS_41", r"AKIA[0-9A-Z]{16}", "Hardcoded AWS access key"),
    (
        "CKV_AWS_41",
        r'(?:secret_key|secret_access_key)\s*=\s*"[^"]{20,}"',
        "Hardcoded AWS secret key",
    ),
)


def _block_end(text: str, opening_brace: int) -> int:
    """Return the index after the matching brace, ignoring strings/comments."""
    depth = 0
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    index = opening_brace
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "#" or (char == "/" and next_char == "/"):
            line_comment = True
            if char == "/":
                index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return len(text)


def parse_hcl_blocks(text: str) -> list[HCLBlock]:
    """Extract complete top-level resource-like blocks from Terraform text."""
    blocks: list[HCLBlock] = []
    occupied_until = 0
    for match in _HEADER.finditer(text):
        if match.start() < occupied_until:
            continue
        opening_brace = match.end() - 1
        end = _block_end(text, opening_brace)
        labels = tuple(label for label in match.groups()[1:] if label is not None)
        blocks.append(
            HCLBlock(match.group(1), labels, text[match.start() : end], match.start(), end)
        )
        occupied_until = end
    return blocks


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _finding(
    *,
    rule_id: str,
    message: str,
    file_path: str,
    resource: str,
    line: int,
    commit_sha: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=classify(rule_id),
        severity="HIGH",
        file_path=file_path,
        resource_address=resource,
        line_start=line,
        line_end=line,
        commit_sha=commit_sha,
        detected_at=datetime.now(UTC),
        message=message,
    )


def _linked_s3_features(blocks: list[HCLBlock]) -> dict[str, set[str]]:
    """Map S3 bucket labels to security features configured in separate resources."""
    links: dict[str, set[str]] = {}
    feature_types = {
        "aws_s3_bucket_logging": "logging",
        "aws_s3_bucket_versioning": "versioning",
        "aws_s3_bucket_server_side_encryption_configuration": "encryption",
    }
    for block in blocks:
        if block.kind != "resource" or not block.labels:
            continue
        feature = feature_types.get(block.labels[0])
        if feature is None:
            continue
        target = re.search(r"bucket\s*=\s*aws_s3_bucket\.([A-Za-z0-9_-]+)\.", block.text)
        if target:
            links.setdefault(target.group(1), set()).add(feature)
    return links


def _scan_block(
    block: HCLBlock,
    *,
    whole_text: str,
    file_path: str,
    commit_sha: str,
    s3_links: dict[str, set[str]],
) -> Iterator[Finding]:
    resource_type = block.labels[0] if block.kind == "resource" and block.labels else ""
    for rule_id, pattern, message, resource_types in _BLOCK_RULES:
        if resource_type not in resource_types:
            continue
        for match in re.finditer(pattern, block.text, re.IGNORECASE):
            yield _finding(
                rule_id=rule_id,
                message=message,
                file_path=file_path,
                resource=block.resource_address,
                line=_line_number(whole_text, block.start + match.start()),
                commit_sha=commit_sha,
            )

    if resource_type == "aws_s3_bucket" and len(block.labels) == 2:
        linked = s3_links.get(block.labels[1], set())
        required = (
            ("CKV_AWS_18", "logging", r"\blogging\s*\{", "S3 access logging is missing"),
            (
                "CKV_AWS_19",
                "encryption",
                r"\bserver_side_encryption_configuration\s*\{",
                "S3 server-side encryption is missing",
            ),
            (
                "CKV_AWS_21",
                "versioning",
                r"\bversioning\s*\{[\s\S]*?enabled\s*=\s*true",
                "S3 versioning is missing or disabled",
            ),
        )
        for rule_id, feature, pattern, message in required:
            if feature not in linked and re.search(pattern, block.text, re.IGNORECASE) is None:
                yield _finding(
                    rule_id=rule_id,
                    message=message,
                    file_path=file_path,
                    resource=block.resource_address,
                    line=_line_number(whole_text, block.start),
                    commit_sha=commit_sha,
                )

    if resource_type.startswith("aws_") and re.search(r"\btags\s*(?:=|\{)", block.text) is None:
        yield _finding(
            rule_id="CKV_AWS_TAG",
            message="AWS resource is missing tags",
            file_path=file_path,
            resource=block.resource_address,
            line=_line_number(whole_text, block.start),
            commit_sha=commit_sha,
        )


def scan_directory(target_dir: Path, commit_sha: str) -> list[Finding]:
    """Scan all Terraform files under a directory using resource-aware rules."""
    findings: list[Finding] = []
    for tf_file in sorted(target_dir.rglob("*.tf")):
        if ".terraform" in tf_file.parts:
            continue
        try:
            text = tf_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative_path = str(tf_file.relative_to(target_dir))
        blocks = parse_hcl_blocks(text)
        links = _linked_s3_features(blocks)
        for block in blocks:
            findings.extend(
                _scan_block(
                    block,
                    whole_text=text,
                    file_path=relative_path,
                    commit_sha=commit_sha,
                    s3_links=links,
                )
            )
        for rule_id, pattern, message in _SECRET_RULES:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                containing = next(
                    (block for block in blocks if block.start <= match.start() < block.end), None
                )
                resource = (
                    containing.resource_address if containing else f"{relative_path}:credentials"
                )
                findings.append(
                    _finding(
                        rule_id=rule_id,
                        message=message,
                        file_path=relative_path,
                        resource=resource,
                        line=_line_number(text, match.start()),
                        commit_sha=commit_sha,
                    )
                )

    unique: dict[tuple[str, str, str], Finding] = {}
    for finding in findings:
        key = (finding.rule_id, finding.file_path, finding.resource_address)
        unique.setdefault(key, finding)
    return sorted(unique.values(), key=lambda item: (item.file_path, item.line_start, item.rule_id))
