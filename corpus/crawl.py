"""GitHub Terraform Repository Crawler.

This script searches GitHub for public repositories containing Terraform files
and saves them to a CSV manifest. This is the "delivery truck" that brings
raw materials (repos) to our analysis factory.

Real-world analogy:
    Imagine you want to study restaurant hygiene across a city. First you need
    a list of all restaurants. This script is the Yellow Pages — it finds all
    the "restaurants" (Terraform repos) so we can inspect them later.

Usage:
    python corpus/crawl.py --stars 10 --limit 1000 --output corpus/repos.csv

Requirements:
    - A GitHub personal access token in the GITHUB_TOKEN environment variable
    - pip install httpx

How to get a GitHub token (free, takes 2 minutes):
    1. Go to https://github.com/settings/tokens
    2. Click "Generate new token (classic)"
    3. Check the "public_repo" scope only
    4. Copy the token
    5. In Git Bash: export GITHUB_TOKEN=ghp_your_token_here
"""

from __future__ import annotations

import csv
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
SEARCH_ENDPOINT = f"{GITHUB_API}/search/repositories"

# We search for repos that are Terraform-related (topic or language),
# have at least N stars, and were pushed to within the last 24 months.
# Strategy: search by topic "terraform" + language "HCL" for best results.
SEARCH_QUERY_TEMPLATE = "topic:terraform language:HCL stars:>={stars} pushed:>={since}"


@dataclass
class RepoInfo:
    """One row in our manifest — metadata about a single Terraform repo."""

    full_name: str  # e.g. "hashicorp/terraform-aws-vpc"
    html_url: str
    description: str
    stars: int
    forks: int
    language: str
    created_at: str
    pushed_at: str
    default_branch: str
    topics: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def get_token() -> str:
    """Get GitHub token from environment.

    Real-world analogy: like showing your library card before you can
    borrow books. GitHub limits anonymous requests to 10/minute but
    authenticated requests get 30/minute for search.
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print(
            "WARNING: No GITHUB_TOKEN set. You'll be rate-limited to ~10 requests/min.\n"
            "To fix: export GITHUB_TOKEN=ghp_your_token_here\n"
            "Get one at: https://github.com/settings/tokens"
        )
    return token


def search_repos(
    min_stars: int = 10,
    limit: int = 1000,
    since_year: int = 2024,
) -> list[RepoInfo]:
    """Search GitHub for Terraform repositories.

    How it works:
        GitHub's search API returns 100 results per page, max 1000 results
        per query. We paginate through all pages until we hit our limit.

    Real-world analogy:
        Like flipping through pages of search results on Google. Each page
        has 100 results. We keep flipping until we have enough.
    """
    token = get_token()
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    since = f"{since_year}-01-01"
    query = SEARCH_QUERY_TEMPLATE.format(stars=min_stars, since=since)

    repos: list[RepoInfo] = []
    page = 1
    per_page = 100  # GitHub max

    print(f"Searching GitHub for Terraform repos (stars≥{min_stars}, pushed≥{since})...")
    print(f"Target: {limit} repos\n")

    while len(repos) < limit:
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        }

        try:
            resp = httpx.get(
                SEARCH_ENDPOINT,
                params=params,
                headers=headers,
                timeout=30.0,
            )
        except httpx.RequestError as e:
            print(f"  Network error: {e}. Retrying in 10s...")
            time.sleep(10)
            continue

        if resp.status_code == 403:
            # Rate limited — wait and retry
            reset_time = int(resp.headers.get("X-RateLimit-Reset", "0"))
            wait = max(reset_time - int(time.time()), 10)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            print(f"  Error {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        items = data.get("items", [])

        if not items:
            print(f"  No more results at page {page}.")
            break

        for item in items:
            if len(repos) >= limit:
                break
            repos.append(
                RepoInfo(
                    full_name=item.get("full_name", ""),
                    html_url=item.get("html_url", ""),
                    description=(item.get("description") or "")[:200],
                    stars=item.get("stargazers_count", 0),
                    forks=item.get("forks_count", 0),
                    language=item.get("language") or "",
                    created_at=item.get("created_at", ""),
                    pushed_at=item.get("pushed_at", ""),
                    default_branch=item.get("default_branch", "main"),
                    topics=item.get("topics", []),
                )
            )

        print(f"  Page {page}: got {len(items)} repos (total: {len(repos)}/{limit})")
        page += 1

        # Be polite — don't hammer the API
        time.sleep(2)

    print(f"\nDone. Found {len(repos)} repos.")
    return repos


def save_to_csv(repos: list[RepoInfo], output_path: Path) -> None:
    """Save the repo manifest to CSV.

    Real-world analogy: writing down all the restaurant addresses in a
    spreadsheet so the health inspector knows where to go tomorrow.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "full_name", "html_url", "description", "stars", "forks",
            "language", "created_at", "pushed_at", "default_branch", "topics",
        ])
        for r in repos:
            writer.writerow([
                r.full_name,
                r.html_url,
                r.description,
                r.stars,
                r.forks,
                r.language,
                r.created_at,
                r.pushed_at,
                r.default_branch,
                ";".join(r.topics),
            ])

    print(f"Saved to: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point. Parse args and run the crawler."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Crawl GitHub for public Terraform repositories.",
        epilog="Example: python corpus/crawl.py --stars 10 --limit 100",
    )
    parser.add_argument(
        "--stars", type=int, default=10,
        help="Minimum star count (default: 10)",
    )
    parser.add_argument(
        "--limit", type=int, default=1000,
        help="Max repos to collect (default: 1000, max: 1000 per GitHub API)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("corpus/repos.csv"),
        help="Output CSV path (default: corpus/repos.csv)",
    )
    parser.add_argument(
        "--since", type=int, default=2024,
        help="Only repos pushed after this year (default: 2024)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  TerraDrift Crawler v0.2")
    print("=" * 60)
    print(f"  Min stars:  {args.stars}")
    print(f"  Limit:      {args.limit}")
    print(f"  Since:      {args.since}")
    print(f"  Output:     {args.output}")
    print(f"  Time:       {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    print()

    repos = search_repos(
        min_stars=args.stars,
        limit=args.limit,
        since_year=args.since,
    )

    if repos:
        save_to_csv(repos, args.output)
    else:
        print("No repos found. Check your GITHUB_TOKEN and network connection.")
        sys.exit(1)


if __name__ == "__main__":
    main()
