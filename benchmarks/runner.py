"""Nightly micro-benchmark.

Real-world analogy: a daily lap-time at the track. We scan the bundled
sample, time it, and write a JSON file the README ingests.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from terradrift.analyzer import run_checkov

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample" / "aws-s3-public"
OUT = ROOT / "benchmarks" / "latest.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()

    times_ms: list[float] = []
    total_findings = 0

    for _ in range(args.repeats):
        t0 = time.perf_counter()
        findings = run_checkov(SAMPLE, commit_sha=args.commit)
        times_ms.append((time.perf_counter() - t0) * 1000.0)
        total_findings = len(findings)

    payload = {
        "commit": args.commit,
        "modules_scanned": 1,
        "repeats": args.repeats,
        "median_scan_ms": round(statistics.median(times_ms), 2),
        "min_scan_ms": round(min(times_ms), 2),
        "max_scan_ms": round(max(times_ms), 2),
        "total_findings": total_findings,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
