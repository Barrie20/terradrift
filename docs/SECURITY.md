# Security Policy

## Supported versions

The latest tagged release is supported. Older versions receive critical fixes
on a best-effort basis until the next minor release.

## Reporting a vulnerability

Email: security@your-domain.dev (placeholder — update before publication).
Please **do not** open public issues for security vulnerabilities.

We aim to:
- Acknowledge within 72 hours
- Provide a remediation plan within 14 days
- Publish a CVE-pinned advisory upon fix

## Supply-chain security

| Control | Tool |
|---|---|
| SBOM | Anchore SBOM action (SPDX-JSON) |
| Image signing | Cosign / Sigstore (keyless OIDC) |
| Build provenance | SLSA Level 3 (slsa-github-generator) |
| Static analysis | Semgrep, CodeQL, ruff, mypy |
| IaC scanning | Checkov, Trivy, tfsec |
| Dependency scanning | pip-audit, OSV-Scanner |
| Secret scanning | gitleaks (pre-commit + CI) |

## Hardening checklist (image)

- ✅ Distroless base
- ✅ Non-root (UID 65532)
- ✅ Read-only root filesystem
- ✅ No shell, no package manager
- ✅ Minimal env, no secrets baked in
