# Module 1: AI answers (daily and weekly tracking)

What the assistants say for the prompts in `prompts.json`, whether the brand is named, and which sources they cite. Google AI Overviews are tracked on the shorter `serp_queries`, because Overviews answer searches, not conversations.

## Daily slice: the assistants in `cadence.daily_assistants`

For each prompt and each daily assistant:

```
aeo_answer {"input": {"prompt": "<text>", "assistant": "chatgpt", "location": "<market.aeo_location>"},
            "max_cost": "<this assistant's price>",
            "idempotency_key": "<slug>-aeo-<YYYY-MM-DD>-chatgpt-<prompt id>"}
```

- **Gemini refuses `location`**: leave it out of Gemini calls.
- On the full server, send the whole panel for one assistant in one `batch_run` (`capability: "aeo.answer"`, `inputs`, `max_cost`, `max_total_cost` = prompts x price, `idempotency_key` = `<slug>-aeo-<date>-<assistant>`). If it comes back `done: false`, call it again with the same key to keep waiting; nothing bills twice.
- Check every call's status. A failed or refused call is a hole in the data, not a "not mentioned". Report the number of holes.
- The result has `answer`, `model` (the model that actually answered, often a small search model such as Perplexity `sonar` or ChatGPT `gpt-4o-mini`: say so in the report), `sources` (`url`, `title`) and `source_domains`.

## Weekly slice

1. The same calls for the assistants in `cadence.weekly_assistants` (Claude and Gemini by default).
2. **Google top 10 and AI Overview sources**, one call per query in `serp_queries`:

   ```
   seo_serp {"input": {"keyword": "<query>", "location": "<market.serp_location>", "language": "<market.language>"}, "max_cost": "<price>"}
   ```

   About $0.004 a query. `results` is the top 10 (`position`, `url`, `domain`, `title`, `snippet`), `ai_overview_present` says whether Google showed an Overview, and `ai_overview_sources` lists the URLs it cited. Module 2 reuses these results, so do not buy them twice in a week.

   **Full server only: the Overview's text.** To see which brands the Overview names, use the raw endpoint instead: `run` with `provider: "dataforseo"`, `endpoint: "/v3/serp/google/organic/live/advanced"`, `input: {"keyword": "<query>", "location_name": "<market.serp_location>", "language_code": "<market.language>", "depth": 10, "load_async_ai_overview": true}`, `max_cost: "0.05"`. If the call is refused for missing `match_type` and `match_value`, add `"match_type": "domain", "match_value": "<brand domain>"` (without `stop_crawl_on_match` they change nothing). In `result.data.tasks[0].result[0].items`, the `ai_overview` item has `markdown` (the text) and `references` (`domain`, `url`, `title`); `organic` items are the top 10; `people_also_ask` and `related_searches` suggest prompts for the next panel version.
3. **Where the brand's domains already appear**: `aeo_mentions` with `domain` for each of `brand.domains`, on `platform: "google"` (AI Mode, with `location`) and `platform: "chatgpt"` (held for the United States in English: leave location and language out, and say so). About $0.20 a search. A `no_match` is billed at the base price and is a finding (nothing cites the domain yet), not a failure.

## What to record per answer

One row per (date, assistant, prompt):

| field | how |
|---|---|
| `id` | `<date>\|<assistant>\|<prompt id>` |
| `date`, `assistant`, `model`, `prompt_id`, `group`, `panel_version` | from the call and the panel |
| `brand_named` | any of `brand.aliases`, case-insensitive, whole word |
| `brand_rank` | order of the brand's first mention among all tracked brands named (1 = first), null if absent |
| `competitors` | `{name: rank}` for every competitor alias found |
| `brand_cited` | a source URL on one of `brand.domains` |
| `sources` | every cited URL, normalised: lowercase host, no `www.`, no query string (assistants add `utm_source`), no fragment, no trailing slash |
| `run_id`, `charged` | from the receipt |
| `answer` | the full text |

Aliases marked `ambiguous` count only when the sentence is about the category (it names the problem or the platform the product plugs into). Gemini's sources come back as Google grounding redirect URLs with no readable domain: count Gemini in mention rates, leave it out of citation rates, and say so.

For Overviews, one row per (date, query): `ai_overview_present`, `sources`, `brand_cited`, and with the full-server text, `brand_named` and `competitors`.

## Metrics

Per assistant, over the last 7 days, on every group except `brand`:

- **Mention rate**: answers naming the brand / answers received.
- **Citation rate**: answers citing a brand domain / answers received (not Gemini).
- **Share of voice**: brand mentions / all tracked brand mentions.
- **Average rank when named.**
- **Owner per group**: the competitor named most in `alternative`, in each vertical, in `trust`.

Daily output, one line per assistant: `chatgpt: named 3/48 (6%), cited 1/48, SoV 4%, 7-day 5% (+1)`. The weekly report adds the movers (prompts where the brand appeared or vanished, quoted) and the citation graph: every source URL across answers and Overviews with its count, the assistants and the prompts, typed as comparison page, listicle, review site, Reddit, X, video, press, directory or vendor page. The listicles and threads at the top of that graph feed modules 2 and 3.

## Cheaper daily runs

On the full server, `discover` "chatgpt search scraper", "perplexity search scraper" or "gemini search scraper": raw Apify actors that read the consumer apps for a fraction of a cent a prompt. They break more often and answer differently from the API, so never mix the two in one trend line; switching starts a new series.
