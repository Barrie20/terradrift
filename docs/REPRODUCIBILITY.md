# Reproducibility

> Goal: any reviewer can rebuild every figure in the paper from this repo.

## Two flows

| Flow | When | Time | Cost |
|---|---|---|---|
| `make reproduce-mini` | reviewer audit | ~15 min | $0 (laptop) |
| `make reproduce` | full paper rebuild | ~6 h | ~$15 on AWS Batch Spot |

## Pinning

- Python: `>=3.12,<3.13`
- Checkov: pinned in `requirements/lock.txt`
- Trivy: pinned via Docker tag in `infra/`
- Terraform sample: pinned via `required_version`

## Random seeds

- Statistical tests use `seed=42` (set in `notebooks/utils.py`).
- Sampling for the mini subset is deterministic via `corpus/sample_mini.csv`.

## Environment

- Verified on: Ubuntu 24.04, macOS 14, Windows 11 + WSL2.
- Container: `ghcr.io/barrie20/terradrift:vX.Y.Z` (signed).

## Hash manifest

Every parquet file in the published artifact has a SHA-256 in
`corpus/manifest.parquet`. The manifest itself is signed with Cosign.
