# AI search growth

**Does ChatGPT recommend your product? Track it every day, see who it names instead, and get the pages, threads and press that change the answer.**

An open-source template: your buyers' questions sent on a schedule to ChatGPT, Perplexity, Claude, Gemini and Google AI Overviews, every answer and every cited source committed to this repo, a scoreboard updated each morning and a weekly report. An agent skill in the same repo builds the prompt panel from your domain and runs the work that moves the numbers: comparison pages, Reddit and X threads, trade press, marketplace listings, a Product Hunt plan.

Runs on [RouterGrowth](https://www.routergrowth.com): one API key for the assistants, Google results and AI mention data, paid per call.

## What you get

- `reports/latest.md`: per assistant, how often you are named on unprompted buyer questions, how often your domain is cited, your share of voice against competitors, and the change on the week before.
- `reports/weekly/<date>.md`: the movers (questions where you appeared or vanished), who owns each kind of question, Google top 10 and AI Overview citations, where your domain already shows in AI answers, and the citation graph: the pages and threads the assistants read.
- `data/`: every answer, source and receipt as jsonl, plus `summary.csv` to chart. The history is the git log.

## Start

1. **Use this template** (top of the page) to create your own repository. Make it private if you do not want your tracking public.
2. **Add your key.** Create a key at [routergrowth.com](https://www.routergrowth.com) (new workspaces get free credit), then in your repo: Settings > Secrets and variables > Actions > New repository secret, name `ROUTERGROWTH_API_KEY`.
3. **Describe your product.** Fill `config.json` and `prompts.json`, or let your agent do it. In Claude Code, open the repo and connect RouterGrowth (`claude mcp add --transport http routergrowth https://api.routergrowth.com/mcp/claude`, then `/mcp` to sign in), then say:

   > set up ai-search-growth for acme.com

   The skill in `skills/ai-search-growth` reads your site, finds the competitors the assistants already name, writes 30 to 50 buyer prompts in your market's words, and agrees a budget with you. Under $1.
4. **Run the baseline.** Actions > track > Run workflow > `baseline`. Day zero on all four assistants and Google.
5. **Done.** `daily` runs at 06:00 UTC, `weekly` on Mondays at 06:30 UTC, and each run commits its results.

Try it cheaply first: Run workflow with `limit` 2 sends only the first two prompts. Locally: `ROUTERGROWTH_API_KEY=... python runner/track.py daily --dry-run` prints the quote without calling anything.

## What it costs

At RouterGrowth prices in late October 2026 (the runner reads your workspace's live prices and refuses a run quoted above the budget you set in `config.json`):

| Run | What | About |
|---|---|---|
| Daily | 50 prompts on ChatGPT and Perplexity | $3.50 to $5 |
| Weekly | 50 prompts on Claude and Gemini, 20 Google results pages with AI Overviews, AI mention searches | $10 to $15 |
| Baseline | everything once | about $18 |

About $150 to $200 a month for 50 prompts. Twenty prompts, or every other day, cost proportionally less.

## Move the numbers

The tracking says where you stand; the skill does the rest with your agent. Each module drafts, nothing is posted or sent for you:

| Say | Module |
|---|---|
| "which pages rank on Google and get cited by ChatGPT for our category" | pages that win both, read and turned into page briefs |
| "which Reddit and X threads should we answer" | threads the answers pull from, watched weekly, reply briefs with disclosure |
| "build a press list for our verticals" | trade journalists from their own articles, verified emails, pitch drafts |
| "where should we be listed" | marketplaces and directories that list competitors, with what each needs |
| "plan our Product Hunt launch" | the score to beat per weekday, the category's winners, assets and timeline |

Install the skill on its own in any agent with `npx skills add RouterGrowth/ai-search-growth`. More GTM skills: [RouterGrowth/skills](https://github.com/RouterGrowth/skills).

## How it works

```
config.json + prompts.json
        │
runner/track.py ──► POST /v1/run aeo.answer (one per prompt and assistant)
        │           POST /v1/run seo.serp, aeo.mentions (weekly)
        ▼
data/answers/<date>.jsonl ──► runner/analyze.py ──► reports/latest.md, reports/weekly/<date>.md, data/summary.csv
```

- **Named** means one of your aliases appears as a whole word; an ambiguous alias ("Spark", "Wave") counts only in a sentence that also names a `category_terms` word. **Rank** is the order of first mention among the tracked brands.
- **Cited** means a source URL on one of your domains. Gemini cites Google redirect links, so it counts for mentions, not citations.
- Rates are computed on the unprompted questions only: the `brand` group names you and would inflate them. Answers vary run to run, so the reports use rolling 7 days.
- A failed call is a hole, counted and reported, never a "not named". A rerun on the same day replays the calls already made (idempotency keys) and replaces that day's rows.
- Standard library Python, no dependencies. `python -m unittest discover -s tests` runs offline.

## Build on it

- **Another assistant or cadence**: `config.json` > `cadence`.
- **Another market or product**: another copy of the template, or another config and panel pair (`--root`).
- **New prompts**: add a `v2` panel with new ids rather than editing `v1`, so the trend stays comparable.
- **A dashboard**: `data/summary.csv` and the jsonl files are the whole state; see `data/README.md` for the fields.
- **Another channel or report**: `runner/analyze.py` is pure functions over plain rows; add a module to the skill as `skills/ai-search-growth/references/7-<name>.md`.

Pull requests welcome.

## License

MIT, Altria LLC (RouterGrowth).
