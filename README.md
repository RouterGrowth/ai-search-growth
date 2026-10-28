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
2. **Describe your product with your agent.** Clone your copy and open it in Claude Code: the repo's `CLAUDE.md` points the agent to the skill in `skills/ai-search-growth`. In any other agent, install the skill with `npx skills add RouterGrowth/ai-search-growth` (or copy `skills/ai-search-growth` into the agent's skills folder, `.claude/skills/` for Claude Code). Connect RouterGrowth (`claude mcp add --transport http routergrowth https://api.routergrowth.com/mcp/claude`, then `/mcp` to sign in; the RouterGrowth plugin or the full server at `/mcp` works too). Sign-in is OAuth: no key needed for this step. Then say:

   > set up ai-search-growth for acme.com

   The skill reads your site, finds the competitors the assistants already name, writes 30 to 50 buyer prompts in your market's words, and agrees with you which prompts and assistants to track and the budget. Under $1, so the $1 credit of a new workspace covers it. You can also fill `config.json` and `prompts.json` by hand.
3. **Add your key for the schedule.** Create a key at [routergrowth.com](https://www.routergrowth.com), then in your repo: Settings > Secrets and variables > Actions > New repository secret, name `ROUTERGROWTH_API_KEY`. Top up before the baseline: about $18 for 50 prompts on all four assistants, less on a smaller selection.
4. **Run the baseline.** Actions > track > Run workflow > `baseline`. Day zero on the selected prompts and assistants, and Google.
5. **Done.** `daily` runs at 06:00 UTC, `weekly` on Mondays at 06:30 UTC, and each run commits its results.

Try it cheaply first: Run workflow with `limit` 2 sends only the first two prompts of the selection. Locally, after setup: `ROUTERGROWTH_API_KEY=... python runner/track.py daily --dry-run` prints the quote, read at your workspace's prices with the free `inspect`, without any paid call.

## Choose the prompts and the assistants

Every run sends a selection of the panel to a set of assistants. Set it once in `config.json` > `cadence`, or for one run:

| What | In `config.json` > `cadence` | For one run |
|---|---|---|
| Assistants | `daily_assistants`, `weekly_assistants`: `chatgpt`, `perplexity`, `claude`, `gemini` | `--assistants chatgpt,claude` |
| A model | `assistant:model`, e.g. `"claude:claude-sonnet-5-5"`, `"chatgpt:gpt-4.1"` | `--assistants claude:claude-sonnet-5-5` |
| Prompts | `daily_prompts`, `weekly_prompts`: `"all"`, or ids, groups and ranges, e.g. `["p01-p10", "category"]` | `--prompts p01-p10,category` |

On GitHub, Run workflow has the same `prompts` and `assistants` fields. The baseline takes both slices: every prompt either cadence tracks, on every assistant either uses. The budget guard applies to every selection, `--limit` included.

Without a model, each assistant answers with its provider's default search model (in late October 2026: gpt-4o-mini, sonar, claude-sonnet-4-5, gemini-2.5-flash). A pinned model is its own series in the reports, so switching models starts a new trend line rather than bending the old one. A model the provider refuses comes back as a hole, not billed: try it on one prompt first (`--prompts p01 --assistants chatgpt:gpt-4.1`).

## What it costs

At RouterGrowth prices in late October 2026 (the runner reads your workspace's live prices and refuses a run quoted above the budget you set in `config.json`):

| Run | What | About |
|---|---|---|
| Daily | 50 prompts on ChatGPT and Perplexity | $3.50 to $5 |
| Weekly | 50 prompts on Claude and Gemini, 20 Google results pages with AI Overviews, AI mention searches | $10 to $15 |
| Baseline | everything once | about $18 |

About $150 to $200 a month for 50 prompts. Twenty prompts, fewer assistants, or every other day cost proportionally less: per prompt, ChatGPT is quoted about $0.08, Perplexity $0.02, Claude $0.14 and Gemini $0.10, and most answers settle 20 to 40% below the quote.

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

- **Named** means one of your aliases appears as a whole word in the answer's prose (citation links and URLs do not count); an ambiguous alias ("Spark", "Wave") counts only in a sentence that also names a `category_terms` word, or as a bolded name in a list (`**Spark**`). **Rank** is the order of first mention among the tracked brands.
- **Cited** means a source on one of your domains. Gemini cites Google redirect links; the runner reads the domain from each source's title, so Gemini citations count at domain level.
- **Named but not tracked**: names the assistants put in bold that are not in `competitors[]`, from two assistants or three answers. The rivals your list missed.
- Rates are computed on the unprompted questions only: the `brand` group names you and would inflate them. Answers vary run to run, so the reports use rolling 7 days.
- A failed call is a hole, counted and reported, never a "not named". A rerun on the same day replays the calls already made (idempotency keys) and replaces that day's rows.
- Standard library Python, no dependencies. `python -m unittest discover -s tests` runs offline.

## Build on it

- **Other assistants, models, prompts or cadence**: `config.json` > `cadence` (see [Choose the prompts and the assistants](#choose-the-prompts-and-the-assistants)).
- **Another market or product**: another copy of the template, or another config and panel pair (`--root`).
- **New prompts**: add a `v2` panel with new ids rather than editing `v1`, so the trend stays comparable.
- **A dashboard**: `data/summary.csv` and the jsonl files are the whole state; see `data/README.md` for the fields.
- **Another channel or report**: `runner/analyze.py` is pure functions over plain rows; add a module to the skill as `skills/ai-search-growth/references/7-<name>.md`.

Pull requests welcome.

## License

MIT, Altria LLC (RouterGrowth).
