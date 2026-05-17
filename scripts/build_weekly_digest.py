"""Build a weekly digest from /journal/papers/*.md.

Real-world analogy: like a Sunday-night newsletter that summarizes everything
you read this week, so committee reviewers can see *consistent* learning.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "journal" / "papers"
REPORTS = ROOT / "reports"


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    iso_year, iso_week, _ = today.isocalendar()
    out = REPORTS / f"{iso_year}-W{iso_week:02d}.md"

    week_start = today - dt.timedelta(days=7)
    notes = []
    if JOURNAL.exists():
        for md in sorted(JOURNAL.glob("*.md")):
            try:
                d = dt.date.fromisoformat(md.stem)
            except ValueError:
                continue
            if week_start <= d <= today:
                notes.append(md)

    lines = [
        f"# Weekly digest — {iso_year}-W{iso_week:02d}",
        "",
        f"Generated on {today.isoformat()}.",
        "",
        f"Papers read this week: **{len(notes)}**",
        "",
    ]
    for md in notes:
        title = md.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        lines.append(f"- `{md.stem}` — {title}")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
