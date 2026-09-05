# TerraDrift 10-Repository Pilot

Run date: 2026-09-05

## Scope

- 10 public Terraform repositories
- 3 recent non-merge commits per repository
- 30 commits scanned successfully
- Resource-aware offline scanner (Checkov was not required)
- Results persisted to DuckDB and exported as JSON, CSV, and SVG

## Aggregate results

| Metric | Value |
|---|---:|
| Repositories completed | 10 |
| Repository errors | 0 |
| Commits scanned | 30 |
| Finding snapshots | 1,034 |
| Introduced events | 354 |
| Fixed events | 24 |
| Regressed events | 0 |
| Total drift events | 378 |

## Per-repository results

| Repository | Commits | Finding snapshots | Introduced | Fixed | Regressed |
|---|---:|---:|---:|---:|---:|
| terraform-aws-modules/terraform-aws-vpc | 3 | 128 | 44 | 2 | 0 |
| terraform-aws-modules/terraform-aws-eks | 3 | 114 | 38 | 0 | 0 |
| terraform-aws-modules/terraform-aws-rds | 3 | 24 | 8 | 0 | 0 |
| terraform-aws-modules/terraform-aws-s3-bucket | 3 | 108 | 36 | 0 | 0 |
| cloudposse/terraform-aws-vpc | 3 | 18 | 6 | 0 | 0 |
| cloudposse/terraform-aws-ec2-instance | 3 | 21 | 7 | 0 | 0 |
| nozaq/terraform-aws-secure-baseline | 3 | 203 | 69 | 2 | 0 |
| bridgecrewio/terragoat | 3 | 105 | 35 | 0 | 0 |
| antonbabenko/terraform-best-practices | 3 | 15 | 5 | 0 | 0 |
| futurice/terraform-examples | 3 | 298 | 106 | 20 | 0 |

## Interpretation

The pipeline completed without repository failures and detected both introduced
and fixed security states. No regressions appeared in this narrow three-commit
window. The result validates the end-to-end workflow, but it is not yet enough
to estimate real-world regression frequency.

A finding snapshot is one finding observed at one commit, so the 1,034 count is
not a count of unique vulnerabilities. The offline scanner is intentionally a
small fallback and does not provide Checkov-equivalent rule coverage. A larger
study should scan more commits, pin the scanner version, review a sample of
findings manually, and report confidence intervals.

## Reproduce

```bash
make pilot
```

Generated aggregate artifacts:

- `summary.json`
- `drift-events.csv`
- `drift-events.svg`

The detailed `results.json` and `terradrift.duckdb` files are generated locally
and excluded from Git because they can grow quickly.
