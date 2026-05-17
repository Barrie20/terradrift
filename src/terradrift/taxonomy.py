"""17-category misconfiguration taxonomy.

Real-world analogy: think of these as the 17 most common ways to leave your
front door unlocked. Each Checkov rule maps to exactly one category so we can
talk about misconfigs at a higher level than rule IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Category(str, Enum):
    """High-level categories of IaC security misconfigurations."""

    PUBLIC_EXPOSURE = "public_exposure"  # e.g., S3 bucket public read
    MISSING_ENCRYPTION = "missing_encryption"  # e.g., RDS unencrypted
    WEAK_AUTHENTICATION = "weak_auth"  # e.g., IAM password policy
    OVERPRIVILEGED_IAM = "overprivileged_iam"  # e.g., wildcard policy
    MISSING_LOGGING = "missing_logging"  # e.g., no CloudTrail
    MISSING_BACKUP = "missing_backup"  # e.g., RDS no snapshot
    OPEN_NETWORK = "open_network"  # e.g., 0.0.0.0/0 SSH
    HARDCODED_SECRET = "hardcoded_secret"  # e.g., key in tfvars
    OUTDATED_VERSION = "outdated_version"  # e.g., old TLS, old K8s
    MISSING_MFA = "missing_mfa"  # e.g., root no MFA
    INSECURE_DEFAULTS = "insecure_defaults"  # e.g., default VPC use
    MISSING_TAGS = "missing_tags"  # governance, not security
    INSECURE_TLS = "insecure_tls"  # e.g., TLS 1.0 allowed
    MISSING_VERSIONING = "missing_versioning"  # e.g., S3 no versioning
    DISABLED_DELETION_PROTECTION = "no_deletion_protection"
    EXPOSED_METADATA = "exposed_metadata"  # e.g., IMDSv1 still allowed
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class CategoryInfo:
    category: Category
    description: str
    real_world_example: str


CATEGORY_INFO: dict[Category, CategoryInfo] = {
    Category.PUBLIC_EXPOSURE: CategoryInfo(
        Category.PUBLIC_EXPOSURE,
        "Resource is reachable from the public internet without need.",
        "2017 Verizon S3 leak — 14M records exposed via public bucket.",
    ),
    Category.MISSING_ENCRYPTION: CategoryInfo(
        Category.MISSING_ENCRYPTION,
        "Data at rest or in transit is not encrypted.",
        "2019 First American Financial — 885M records leaked, no encryption.",
    ),
    Category.WEAK_AUTHENTICATION: CategoryInfo(
        Category.WEAK_AUTHENTICATION,
        "Password / token policy is weaker than industry minimum.",
        "2012 LinkedIn — 6.5M unsalted SHA-1 hashes leaked.",
    ),
    Category.OVERPRIVILEGED_IAM: CategoryInfo(
        Category.OVERPRIVILEGED_IAM,
        "Identity has more permissions than its task requires.",
        "2019 Capital One — over-permissive WAF role led to 100M records.",
    ),
    Category.MISSING_LOGGING: CategoryInfo(
        Category.MISSING_LOGGING,
        "No audit log on a security-relevant component.",
        "2020 Twitter — slow detection due to gaps in admin-tool logging.",
    ),
    Category.MISSING_BACKUP: CategoryInfo(
        Category.MISSING_BACKUP,
        "No automated backups / snapshots configured.",
        "2017 GitLab incident — 6h of data lost when backups were untested.",
    ),
    Category.OPEN_NETWORK: CategoryInfo(
        Category.OPEN_NETWORK,
        "Security group / firewall rule allows 0.0.0.0/0 on sensitive ports.",
        "Common cause of cryptojacking on exposed EC2 SSH (port 22).",
    ),
    Category.HARDCODED_SECRET: CategoryInfo(
        Category.HARDCODED_SECRET,
        "Secret value committed to the repository.",
        "2019 Uber — AWS keys in private GitHub repo led to 57M user breach.",
    ),
    Category.OUTDATED_VERSION: CategoryInfo(
        Category.OUTDATED_VERSION,
        "Component pinned to a version with known CVEs.",
        "2017 Equifax — Apache Struts CVE-2017-5638, 147M records.",
    ),
    Category.MISSING_MFA: CategoryInfo(
        Category.MISSING_MFA,
        "Privileged account does not require multi-factor authentication.",
        "2022 Uber — contractor MFA bypass led to internal access.",
    ),
    Category.INSECURE_DEFAULTS: CategoryInfo(
        Category.INSECURE_DEFAULTS,
        "Resource left with insecure default settings.",
        "Default VPC re-use leaks subnet reachability across accounts.",
    ),
    Category.MISSING_TAGS: CategoryInfo(
        Category.MISSING_TAGS,
        "Governance / cost-allocation tags missing.",
        "Untagged resources cause $1M+ unaccounted cloud spend annually.",
    ),
    Category.INSECURE_TLS: CategoryInfo(
        Category.INSECURE_TLS,
        "TLS configuration permits weak ciphers / old protocols.",
        "POODLE (CVE-2014-3566) — SSL 3.0 still being permitted.",
    ),
    Category.MISSING_VERSIONING: CategoryInfo(
        Category.MISSING_VERSIONING,
        "Object/blob storage versioning disabled.",
        "Ransomware can overwrite objects when versioning is off.",
    ),
    Category.DISABLED_DELETION_PROTECTION: CategoryInfo(
        Category.DISABLED_DELETION_PROTECTION,
        "Resource can be deleted by a single API call.",
        "2017 GitLab — accidental rm -rf on the wrong DB host.",
    ),
    Category.EXPOSED_METADATA: CategoryInfo(
        Category.EXPOSED_METADATA,
        "Instance metadata service v1 still enabled (SSRF risk).",
        "2019 Capital One — IMDSv1 + SSRF chained for credential theft.",
    ),
    Category.OTHER: CategoryInfo(
        Category.OTHER,
        "Misconfig that does not fit the 16 categories above.",
        "Catch-all for emerging Checkov rules.",
    ),
}


# Mapping of Checkov rule IDs → category. Extendable; covers the most common rules.
CHECKOV_RULE_TO_CATEGORY: dict[str, Category] = {
    # S3
    "CKV_AWS_18": Category.MISSING_LOGGING,
    "CKV_AWS_19": Category.MISSING_ENCRYPTION,
    "CKV_AWS_20": Category.PUBLIC_EXPOSURE,
    "CKV_AWS_21": Category.MISSING_VERSIONING,
    "CKV_AWS_53": Category.PUBLIC_EXPOSURE,
    "CKV_AWS_54": Category.PUBLIC_EXPOSURE,
    "CKV_AWS_55": Category.PUBLIC_EXPOSURE,
    "CKV_AWS_56": Category.PUBLIC_EXPOSURE,
    # IAM
    "CKV_AWS_1": Category.OVERPRIVILEGED_IAM,
    "CKV_AWS_40": Category.OVERPRIVILEGED_IAM,
    "CKV_AWS_41": Category.HARDCODED_SECRET,
    # RDS
    "CKV_AWS_16": Category.MISSING_ENCRYPTION,
    "CKV_AWS_17": Category.PUBLIC_EXPOSURE,
    "CKV_AWS_133": Category.MISSING_BACKUP,
    "CKV_AWS_293": Category.DISABLED_DELETION_PROTECTION,
    # Networking
    "CKV_AWS_24": Category.OPEN_NETWORK,
    "CKV_AWS_25": Category.OPEN_NETWORK,
    "CKV_AWS_260": Category.OPEN_NETWORK,
    # EC2
    "CKV_AWS_79": Category.EXPOSED_METADATA,
    "CKV_AWS_135": Category.MISSING_ENCRYPTION,
    # CloudTrail
    "CKV_AWS_35": Category.MISSING_LOGGING,
    "CKV_AWS_36": Category.MISSING_LOGGING,
    # KMS
    "CKV_AWS_7": Category.WEAK_AUTHENTICATION,
    # TLS
    "CKV_AWS_103": Category.INSECURE_TLS,
}


def classify(rule_id: str) -> Category:
    """Map a Checkov rule ID to a high-level category.

    Real-world analogy: like turning 200 specific symptoms into 17 disease groups
    so doctors (and reviewers) can reason at the right level.
    """
    return CHECKOV_RULE_TO_CATEGORY.get(rule_id, Category.OTHER)
