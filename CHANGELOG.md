# Changelog

## 0.2.0

- Choose the prompts and the assistants: `cadence.daily_prompts` and `cadence.weekly_prompts` (`"all"`, or ids, groups and ranges such as `p01-p10`), `assistant:model` to pin a model (`claude:claude-sonnet-5-5`, its own series), and `--prompts` / `--assistants` for one run, also as fields of Run workflow.
- Fixed: the weekly AI-mention searches were refused (`cost_limit_exceeded`): the runner capped them at the one-row price instead of the quote for the default 10 rows.
- Fixed: `--limit` no longer skips the budget guard.
- Mentions read the prose: citation-only link lines (ChatGPT prints unrelated page titles there) and URLs no longer count; an ambiguous alias also counts as a bolded name in a list; list items split by stripped citations (Claude) are joined.
- Gemini citations count, at domain level, from each grounding redirect's title.
- Reports list "Named but not tracked": bolded names from two assistants or three answers that are missing from `competitors[]`.
- Setup: AGENTS.md and CLAUDE.md point any agent opening the repo to the skill; the README separates the OAuth setup from the API key; the skill maps every tool to the full server, finds competitors with a problem prompt too, and asks for two checkpoints instead of one per step.

## 0.1.0

- Template repository: `config.json` and `prompts.json`, a standard-library Python runner (`runner/track.py`) for daily, weekly and baseline runs on RouterGrowth, a GitHub Actions schedule that commits every answer, source and receipt, and reports (`reports/latest.md`, weekly reports, `data/summary.csv`).
- The `ai-search-growth` agent skill: setup from a domain, AI answer tracking, pages that rank and get cited, Reddit and X threads, trade press, marketplace and directory listings, Product Hunt launch research. Drafts only.
- Budget guard at the workspace's live prices, idempotent reruns, holes counted instead of read as "not named", offline tests including the runner against a stand-in API.
