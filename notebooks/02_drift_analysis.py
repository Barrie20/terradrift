"""TerraDrift — Drift Analysis & Paper Figures.

This script reads corpus/results.json and generates:
1. Summary statistics (for the paper abstract)
2. Bar chart: INTRODUCED vs FIXED vs REGRESSED
3. Fix rate calculation
4. Top misconfiguration categories
5. Per-repo breakdown

Run:
    python notebooks/02_drift_analysis.py

Output:
    - Prints summary stats to terminal
    - Saves figures to notebooks/figures/
    - Saves summary CSV to notebooks/summary.csv

No external dependencies beyond Python stdlib + the data file.
(matplotlib is optional — if not installed, prints text-only results)
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "corpus" / "results.json"
FIGURES_DIR = ROOT / "notebooks" / "figures"


def load_results(path: Path) -> dict:
    """Load the results JSON from the walker."""
    if not path.exists():
        print(f"ERROR: {path} not found.")
        print("Run the walker first:")
        print("  python corpus/walker.py --manifest corpus/repos.csv --limit 20 --max-commits 50")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def analyze(data: dict) -> None:
    """Print summary statistics and generate figures."""

    results = data.get("results", [])
    if not results:
        print("No results found in the data file.")
        return

    # Collect all drift events
    all_events = []
    for repo_result in results:
        for event in repo_result.get("drift_events", []):
            event["repo"] = repo_result["repo"]
            all_events.append(event)

    # Count event types
    event_counts = Counter(e["event"] for e in all_events)
    introduced = event_counts.get("INTRODUCED", 0)
    fixed = event_counts.get("FIXED", 0)
    regressed = event_counts.get("REGRESSED", 0)
    total = introduced + fixed + regressed

    # Fix rate
    fix_rate = (fixed / introduced * 100) if introduced > 0 else 0

    # Per-repo stats
    repos_walked = len(results)
    repos_with_errors = sum(1 for r in results if r.get("error"))
    repos_successful = repos_walked - repos_with_errors
    total_commits = sum(r.get("commits_walked", 0) for r in results)
    total_findings = sum(r.get("total_findings", 0) for r in results)

    # Top rules
    rule_counts = Counter(e["rule_id"] for e in all_events if e["event"] == "INTRODUCED")
    top_rules = rule_counts.most_common(10)

    # Per-repo drift density
    repo_drift = []
    for r in results:
        events = r.get("drift_events", [])
        if r.get("commits_walked", 0) > 0:
            repo_drift.append({
                "repo": r["repo"],
                "commits": r["commits_walked"],
                "findings": r["total_findings"],
                "introduced": sum(1 for e in events if e["event"] == "INTRODUCED"),
                "fixed": sum(1 for e in events if e["event"] == "FIXED"),
                "regressed": sum(1 for e in events if e["event"] == "REGRESSED"),
            })

    # Sort by most drift events
    repo_drift.sort(key=lambda x: x["introduced"], reverse=True)

    # =========================================================================
    # PRINT RESULTS
    # =========================================================================

    print()
    print("=" * 70)
    print("  TERRADRIFT — DRIFT ANALYSIS RESULTS")
    print("=" * 70)
    print()
    print("  DATASET OVERVIEW")
    print(f"    Repos walked:        {repos_successful} (of {repos_walked} attempted)")
    print(f"    Total commits:       {total_commits:,}")
    print(f"    Total findings:      {total_findings:,}")
    print(f"    Total drift events:  {total:,}")
    print()
    print("  DRIFT EVENT BREAKDOWN")
    print(f"    INTRODUCED:          {introduced:,}  (new misconfigs appeared)")
    print(f"    FIXED:               {fixed:,}  (misconfigs resolved)")
    print(f"    REGRESSED:           {regressed:,}  (fixed misconfigs came back)")
    print()
    print("  KEY METRICS")
    print(f"    Fix rate:            {fix_rate:.1f}%  ({fixed} fixed / {introduced} introduced)")
    print(f"    Unfixed rate:        {100 - fix_rate:.1f}%  (NEVER resolved)")
    print(f"    Regression rate:     {regressed / max(fixed, 1) * 100:.1f}%  (of fixed, came back)")
    print()

    print("  TOP 10 MOST COMMON INTRODUCED MISCONFIGURATIONS")
    print(f"    {'Rule ID':<15} {'Count':<8} {'Category'}")
    print(f"    {'-'*15} {'-'*8} {'-'*30}")
    # Map rule IDs to friendly names
    rule_names = {
        "CKV_AWS_20": "S3 public read",
        "CKV_AWS_18": "S3 no logging",
        "CKV_AWS_19": "S3 no encryption",
        "CKV_AWS_24": "SG open 0.0.0.0/0",
        "CKV_AWS_41": "Hardcoded AWS key",
        "CKV_AWS_79": "IMDSv2 not enforced",
        "CKV_AWS_16": "RDS not encrypted",
        "CKV_AWS_17": "RDS publicly accessible",
        "CKV_AWS_260": "SG all ports open",
        "CKV_AWS_1": "IAM wildcard policy",
        "CKV_AWS_103": "TLS 1.0 allowed",
        "CKV_AWS_293": "No deletion protection",
        "CKV_AWS_41b": "Hardcoded secret key",
    }
    for rule_id, count in top_rules:
        name = rule_names.get(rule_id, rule_id)
        print(f"    {rule_id:<15} {count:<8} {name}")
    print()

    print("  TOP 10 REPOS BY DRIFT (most misconfigs introduced)")
    print(f"    {'Repo':<45} {'Intro':<7} {'Fixed':<7} {'Regr':<6}")
    print(f"    {'-'*45} {'-'*7} {'-'*7} {'-'*6}")
    for r in repo_drift[:10]:
        name = r["repo"][:44]
        print(f"    {name:<45} {r['introduced']:<7} {r['fixed']:<7} {r['regressed']:<6}")
    print()

    # =========================================================================
    # PAPER-READY ABSTRACT NUMBERS
    # =========================================================================

    print("  " + "=" * 66)
    print("  PAPER ABSTRACT (copy-paste ready)")
    print("  " + "=" * 66)
    print(f"""
  We mine {repos_successful} public Terraform modules spanning {total_commits:,}
  commits. We detect {total:,} drift events: {introduced:,} misconfigurations
  introduced, {fixed:,} fixed, and {regressed:,} regressed. The fix rate is
  {fix_rate:.1f}% — meaning {100 - fix_rate:.1f}% of security misconfigurations
  in public Terraform modules are never resolved.
""")

    # =========================================================================
    # SAVE SUMMARY CSV
    # =========================================================================

    csv_path = ROOT / "notebooks" / "summary.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("repo,commits,findings,introduced,fixed,regressed\n")
        for r in repo_drift:
            f.write(f"{r['repo']},{r['commits']},{r['findings']},"
                    f"{r['introduced']},{r['fixed']},{r['regressed']}\n")
    print(f"  Summary CSV saved to: {csv_path}")

    # =========================================================================
    # GENERATE FIGURES (if matplotlib available)
    # =========================================================================

    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt

        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

        # Figure 1: Drift event breakdown (bar chart)
        fig, ax = plt.subplots(figsize=(8, 5))
        categories = ["INTRODUCED", "FIXED", "REGRESSED"]
        values = [introduced, fixed, regressed]
        colors = ["#e74c3c", "#2ecc71", "#f39c12"]
        bars = ax.bar(categories, values, color=colors, edgecolor="black", linewidth=0.5)
        ax.set_ylabel("Count", fontsize=12)
        ax.set_title("Drift Events in Public Terraform Modules", fontsize=14)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 20,
                    f"{val:,}", ha="center", fontsize=11, fontweight="bold")
        ax.set_ylim(0, max(values) * 1.15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "drift_events_bar.png", dpi=150)
        print(f"  Figure saved: {FIGURES_DIR / 'drift_events_bar.png'}")

        # Figure 2: Fix rate pie chart
        fig, ax = plt.subplots(figsize=(6, 6))
        sizes = [introduced - fixed, fixed]
        labels = [f"Never fixed\n({100 - fix_rate:.1f}%)", f"Fixed\n({fix_rate:.1f}%)"]
        colors = ["#e74c3c", "#2ecc71"]
        ax.pie(sizes, labels=labels, colors=colors, startangle=90,
               textprops={"fontsize": 13}, autopct="", shadow=False,
               wedgeprops={"edgecolor": "white", "linewidth": 2})
        ax.set_title("Misconfiguration Fix Rate", fontsize=14)
        plt.tight_layout()
        fig.savefig(FIGURES_DIR / "fix_rate_pie.png", dpi=150)
        print(f"  Figure saved: {FIGURES_DIR / 'fix_rate_pie.png'}")

        # Figure 3: Top rules bar chart
        if top_rules:
            fig, ax = plt.subplots(figsize=(10, 6))
            rules = [rule_names.get(r, r) for r, _ in top_rules[:8]]
            counts = [c for _, c in top_rules[:8]]
            ax.barh(rules[::-1], counts[::-1], color="#3498db", edgecolor="black", linewidth=0.5)
            ax.set_xlabel("Count", fontsize=12)
            ax.set_title("Most Common Introduced Misconfigurations", fontsize=14)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            plt.tight_layout()
            fig.savefig(FIGURES_DIR / "top_rules_bar.png", dpi=150)
            print(f"  Figure saved: {FIGURES_DIR / 'top_rules_bar.png'}")

        plt.close("all")
        print("\n  All figures generated successfully!")

    except ImportError:
        print("\n  [INFO] matplotlib not installed — text results only.")
        print("  To get charts: pip install matplotlib")

    print()
    print("=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    data = load_results(RESULTS)
    analyze(data)
