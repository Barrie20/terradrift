# Threat model — STRIDE

> Plain-English version: this is the "what could go wrong?" doc. We list every
> bad thing that could happen to TerraDrift and what we do about it.

## Assets

| Asset | Why it matters |
|---|---|
| Corpus parquet | Months of mining work; tampering invalidates results |
| Findings DB | Used for paper figures; integrity = scientific integrity |
| Public API | Exposed; abuse = cost + liability |
| Container images | Used by reviewers; tampering = supply chain attack |
| CI runner | Pushes signed artifacts; takeover = signing-key theft |

## STRIDE

| Threat | Asset | Mitigation |
|---|---|---|
| **S**poofing | Public API | mTLS via cert-manager, OIDC for write paths |
| **T**ampering | Corpus parquet | S3 object lock + SHA-256 in manifest, signed w/ Cosign |
| **R**epudiation | Crawl logs | OTEL traces shipped to Loki w/ append-only retention |
| **I**nformation disclosure | PII in repo metadata | `scrubber.py` strips emails / keys before publish |
| **D**oS | Public API | Envoy rate limit + AWS WAF |
| **E**oP | CI runner | OIDC short-lived creds, no long-lived secrets, GH OIDC → AWS |

## Trust boundaries

```
[GitHub public]  --untrusted-->  [Crawler]  --trusted-->  [S3 corpus]
[Reviewer laptop]  --untrusted-->  [Public API]  --trusted-->  [DuckDB]
```

## Out-of-scope

- Private Terraform code (we never crawl private repos).
- Customer data (none collected).
