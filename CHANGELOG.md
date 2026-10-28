# Changelog

## 0.1.0

- Template repository: `config.json` and `prompts.json`, a standard-library Python runner (`runner/track.py`) for daily, weekly and baseline runs on RouterGrowth, a GitHub Actions schedule that commits every answer, source and receipt, and reports (`reports/latest.md`, weekly reports, `data/summary.csv`).
- The `ai-search-growth` agent skill: setup from a domain, AI answer tracking, pages that rank and get cited, Reddit and X threads, trade press, marketplace and directory listings, Product Hunt launch research. Drafts only.
- Budget guard at the workspace's live prices, idempotent reruns, holes counted instead of read as "not named", offline tests including the runner against a stand-in API.
