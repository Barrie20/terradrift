"""Update README.md and benchmarks/results.md with the latest nightly metrics.

Real-world analogy: like the scoreboard at a stadium that gets refreshed each
night. The scoreboard does not lie — but neither does it pretend to be more
than what was measured.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_MD = ROOT / "benchmarks" / "results.md"
RESULTS_JSON = ROOT / "benchmarks" / "latest.json"
README = ROOT / "README.md"


def main() -> None:
    if not RESULTS_JSON.exists():
        print(f"No latest.json yet at {RESULTS_JSON} — skipping.")
        return

    data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")

    table = (
        "| Metric | Value |\n"
        "|---|---|\n"
        f"| Modules scanned | {data.get('modules_scanned', 'n/a')} |\n"
        f"| Median scan time / module | {data.get('median_scan_ms', 'n/a')} ms |\n"
        f"| Total misconfigs detected | {data.get('total_findings', 'n/a')} |\n"
        f"| Last updated (UTC) | {when} |\n"
    )

    RESULTS_MD.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD.write_text(
        f"# Benchmarks — latest run\n\n{table}\n", encoding="utf-8"
    )

    if README.exists():
        readme = README.read_text(encoding="utf-8")
        new = re.sub(
            r"<!-- BEGIN: AUTO-GENERATED RESULTS -->.*?<!-- END: AUTO-GENERATED RESULTS -->",
            f"<!-- BEGIN: AUTO-GENERATED RESULTS -->\n{table}\n<!-- END: AUTO-GENERATED RESULTS -->",
            readme,
            flags=re.DOTALL,
        )
        if new != readme:
            README.write_text(new, encoding="utf-8")
            print("README updated.")


if __name__ == "__main__":
    main()
