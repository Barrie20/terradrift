# Corpus — The Dataset

> This folder holds the list of repos we mine and (eventually) the results.

## Files

| File | What it is | How to create it |
|---|---|---|
| `crawl.py` | The crawler script | Already here — run it |
| `repos.csv` | List of repos found | Created by running `crawl.py` |
| `manifest.parquet` | Full metadata (future) | Created in v0.3 |

## Quick start

```bash
# 1. Install the one dependency
pip install httpx

# 2. Set your GitHub token (free, takes 2 min)
export GITHUB_TOKEN=ghp_your_token_here

# 3. Run the crawler (start small — 100 repos)
python corpus/crawl.py --limit 100 --output corpus/repos.csv

# 4. Check the output
head corpus/repos.csv
wc -l corpus/repos.csv    # should show 101 (header + 100 repos)
```

## How to get a GitHub token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Name it "terradrift-crawler"
4. Check only the **`public_repo`** scope
5. Click "Generate token"
6. Copy it immediately (you won't see it again)
7. In your terminal: `export GITHUB_TOKEN=ghp_xxxxxxxxxxxx`

## What the crawler does

```
You run crawl.py
    ↓
It asks GitHub: "show me repos with .tf files, ≥10 stars, active in 2024+"
    ↓
GitHub returns pages of results (100 per page)
    ↓
crawl.py saves them to repos.csv
    ↓
You now have a list of repos to scan in the next step
```

## Rate limits

- **With token:** 30 search requests/minute (enough for 3,000 repos)
- **Without token:** 10 requests/minute (enough for 1,000 repos, just slower)
- The script automatically waits when rate-limited. Just let it run.
