# Sample: aws-s3-public (intentionally insecure)

This module is **intentionally broken** so `make demo` has something to flag.

| Mistake | Real-world consequence |
|---|---|
| Hardcoded AWS keys | 2019 Uber breach (57M users) |
| `acl = "public-read"` on S3 | 2017 Verizon leak (14M records) |
| `0.0.0.0/0` on SSH | Standard cryptojacking entry point |

Do not deploy this. Run:
```
make demo
```
