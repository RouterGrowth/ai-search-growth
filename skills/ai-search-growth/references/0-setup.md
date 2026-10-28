# Module 0: Setup

Builds the two files the program runs on, from the brand's domain and the user's answers. About ten minutes and under $1. Run it again when the product, the market or the competitor set changes; the panel then gets a new version, never an edit.

Two checkpoints with the user, not one per step: after step 3 (the brand draft and the competitor list together) and at step 7 (what to track and the budget).

## 1. Ask

- The product's domain (and any second domain that hosts its comparison pages or blog).
- The market: country and language. One config per market.
- The buyers: industries, roles or company types (the "verticals"), if the product targets some.
- Competitors the user already knows. Optional; step 3 finds the rest.
- How often to track, on which assistants, how many prompts and how much to spend (step 7 proposes numbers).

## 2. Read the product

`web_scrape` the homepage, then the pricing, industries or use-case pages it links to (about $0.006 a page, 3 to 5 pages). Draft:

- `brand.name`, `brand.aliases` (how people write it, the company name if different), `brand.domains`
- `brand.one_liner`: what it does, for whom, how, in one or two sentences
- `brand.claims`: what the product says about itself that a buyer would ask an assistant about (integrations, data hosting, compliance, price model). These feed the `trust` prompts.
- `verticals`: from the industries pages, or the user's answer

Keep the draft for the first checkpoint, after step 3.

## 3. Find the competitors the assistants already name

`aeo_answer` on Perplexity (the cheapest, about $0.02) for three prompts in the market: two category prompts ("What is the best <category> for <vertical> in <country>?") and one problem prompt in the buyer's words. Category prompts surface the vendors of the category; the problem prompt surfaces the closest rivals, the ones that solve the same pain another way, which category prompts miss. Collect every product named. Add the user's list, and drop names that are not real competitors (a general assistant like ChatGPT itself, a different category, the providers the product is built on). Keep 5 to 10. For each: `name`, `aliases`, `domain` (the domain the answer cites; leave it `""` when no source shows it rather than guessing). Mark `ambiguous` the aliases that are common words or other products' names ("Copilot", "Spark", "Clay", "Apollo"): module 1 counts them only in context.

**Checkpoint 1.** Show the brand draft from step 2 and the competitor list together, and let the user correct both before writing prompts.

## 4. Write the prompt panel

30 to 50 prompts, phrased the way a buyer talks to an assistant, in the market's spelling. Groups and a typical split for 50:

| group | share | what it asks |
|---|---|---|
| `problem` | about 25% | the pain, no product named ("I spend hours every week chasing unpaid invoices") |
| `category` | about 20% | the product type ("best invoicing software for freelancers") |
| `alternative` | about 20% | competitor-anchored ("QuickBooks alternatives", "A vs B") |
| `vertical` | about 25% | the buyer's trade, at least two per vertical |
| `trust` | about 5 to 10% | the objections, from `brand.claims` ("which invoicing tools are HMRC compliant") |
| `brand` | 2 or 3 prompts | names the brand; kept out of every unprompted rate |

Rules: one question per prompt; no prompt that only the brand could answer; every major competitor appears in at least one `alternative` prompt; no two prompts that differ by one word. Optional: `aeo_keywords` with up to 100 of the panel's key phrases in one call (`keywords`, `location`) gives AI search volume. It is measured per short phrase, not per question, and a new category reads 0 on most phrases: use it to weight the groups toward what people ask, not to drop the prompts that carry the product's positioning.

## 5. Search queries, watches, outlets

- `serp_queries`: 15 to 25 short Google phrasings of the same intents ("quickbooks alternative", "invoicing software for contractors"). Check the candidates' volume in one `aeo_keywords` call (the list from step 4 can carry them). `seo_keywords` ideas drift to other meanings of a word ("clay alternative" returns clay bars and cat litter), so use it on unambiguous seeds only.
- `watches.reddit`, `watches.x`, `watches.news`: 3 to 6 phrases each, the way people write them in posts, not in search.
- `press.outlets`: `news_search` on two or three "<vertical> <problem>" queries in the market; trade titles that appear twice or more, with their domain. Leave out vendor blogs (competitors publish a lot of "news"), press-release wires and sites off the topic. In a niche this gives few titles: say so, and ask the user for the ones they know.
- `listings.marketplaces` and `listings.directories`: where the product installs (an app marketplace for each platform it plugs into, an MCP registry for an MCP server) and the AI or software directories that matter in the category, with a search URL each. A search URL you have not opened is a guess: say so in `brand.notes`, and module 5 checks it.
- `product_hunt.match`: words that identify the category in a launch's tagline or topics.

## 6. Save

Write `config.json` and `prompts.json` (fields below). Without a file system, store them in workspace tables: `<slug>-panel` (one row per prompt, `key: "field:id"`) and `<slug>-config` (one row, `id: "config"`, the config as fields). Without either, give the user both JSON blocks to keep and paste back.

## 7. Agree the cadence and the budget

**Checkpoint 2.** Quote from the live prices: the daily slice (tracked prompts x daily assistants), the weekly slice, and the month. Propose ChatGPT and Perplexity daily, Claude and Gemini weekly. For a small budget, track fewer prompts daily (`cadence.daily_prompts`, for example the `category` and `alternative` groups, or 10 to 20 ids spread across the groups) and keep the whole panel weekly, drop an assistant, or run every other day. Pin a model only when the user asks for one (`"claude:claude-sonnet-5-5"`). Set `budgets.daily_usd`, `budgets.weekly_usd` and `budgets.baseline_usd` to the quote plus about 20%, with the user's yes. Then offer the `baseline` run, and say what it costs: a new workspace's $1 credit covers setup, not the baseline.

## config.json

| key | type | used by |
|---|---|---|
| `brand.name`, `brand.slug` | string | everywhere; `slug` names tables and idempotency keys (lowercase, hyphens) |
| `brand.aliases` | string[] | module 1 mention detection |
| `brand.ambiguous` | string[] | aliases of the brand that are common words; counted only in context, like a competitor's |
| `brand.domains` | string[] | citation detection, modules 1 and 2 |
| `brand.one_liner`, `brand.claims` | string, string[] | prompts, briefs, pitches, listing copy |
| `brand.notes` | string | anything a later run must know (where comparison pages live) |
| `competitors[]` | `{name, aliases[], domain, ambiguous[]}` | modules 1 to 6; `domain` is `""` when no source shows it |
| `market` | `{country, aeo_location, serp_location, language}` | `aeo_location` is the two-letter code for `aeo_answer`; `serp_location` the country name for search tools |
| `verticals` | string[] | prompts, press angles |
| `category_terms` | string[] | words that mark a sentence as about the category ("invoice", "Outlook"); an `ambiguous` alias counts only in such a sentence, or as a bolded name in a list |
| `cadence` | `{daily_assistants[], weekly_assistants[], weekly_day, daily_prompts, weekly_prompts}` | module 1. Assistants: `chatgpt`, `perplexity`, `claude`, `gemini`, optionally `assistant:model`. Prompts: `"all"`, or ids, groups and ranges (`["p01-p10", "category"]`) |
| `budgets` | `{daily_usd, weekly_usd, baseline_usd, one_off_ask_above_usd}` | budget rules; the runner refuses a run quoted above its mode's budget |
| `serp_queries` | string[] | modules 1 and 2 |
| `watches` | `{reddit[], x[], news[]}` | modules 3 and 4 |
| `press.outlets[]` | `{name, vertical, domain}` | module 4 |
| `listings` | `{marketplaces[], directories[]}`, each `{name, search_urls[]}` | module 5 |
| `product_hunt` | `{match[], launch_date}` | module 6 |
| `tables` | `{answers, threads, press, listings}` | storage names, default `<slug>-<name>` |
| `runner` | `{concurrency}` | the repo's runner: calls in flight at once (default 4) |

## prompts.json

`{"version": "v1", "created": "<date>", "market": "<country>", "prompts": [{"id": "p01", "group": "problem", "text": "..."}]}`. IDs are never reused. A new version keeps the old IDs it carries over and numbers new prompts after the last one.
