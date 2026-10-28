# data

Written by `runner/track.py`, one file per day, committed by the `track` workflow. Rows are merged by `id`, so a rerun on the same day replaces that day's rows instead of duplicating them.

| Path | One row per | Fields |
|---|---|---|
| `answers/<date>.jsonl` | date, assistant, prompt | `id`, `date`, `assistant` (`claude`, or `claude:claude-sonnet-5-5` when a model is pinned), `model` (the one that answered), `prompt_id`, `group`, `panel_version`, `status`, `brand_named`, `brand_rank`, `competitors` (`{name: rank}`), `brand_cited`, `sources` (normalised URLs; for Gemini, the domain from each redirect's title), `answer`, `run_id`, `charged`; failed calls carry `error` instead of the answer fields |
| `serp/<date>.jsonl` | date, query | `ai_overview_present`, `ai_overview_sources`, `brand_in_overview`, `brand_position`, `results` (top 10: `position`, `url`, `title`), `run_id`, `charged` |
| `mentions/<date>.jsonl` | date, domain, platform | `status` (`no_match` means nothing cites the domain yet), `total`, `questions`, `run_id`, `charged` |
| `runs/<date>-<mode>.json` | run of the workflow | `quote`, `charged`, `calls`, `answer_holes`, `stopped`, `run_ids` |
| `summary.csv` | date, assistant | the daily series on unprompted prompts, ready to chart |
