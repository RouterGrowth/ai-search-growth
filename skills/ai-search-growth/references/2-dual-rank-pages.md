# Module 2: Pages that rank in Google and get cited by AI

The pages worth copying (and the pages worth getting onto) are the ones that win both surfaces: Google's top 10 and the assistants' citations. This module finds them, reads them, and turns the pattern into page briefs.

## 1. The query set

Start from `serp_queries`. Expand once with `seo_keywords` on 3 to 5 seeds (`keyword`, `location` = `market.serp_location`, `limit` 20): keep the comparison, alternative, category and vertical queries with volume; drop navigational ones. Aim for 20 to 30.

## 2. Google top 10 and AI Overview sources

Reuse this week's `seo_serp` results from module 1 where they exist; run `seo_serp` for the rest. Each gives the top 10 and `ai_overview_sources`.

## 3. Assistant citations

From the module 1 store, the last 7 days: every cited URL for the prompts that share the query's intent (same competitor, same vertical, same category). If module 1 has not run yet, run `aeo_answer` on ChatGPT and Perplexity for the queries rewritten as questions.

## 4. The overlap table

Normalise URLs (lowercase host, no `www.`, no query string or fragment, no trailing slash). For each URL:

| column | meaning |
|---|---|
| `google_rank` | best position in the top 10 across queries, or none |
| `queries` | the queries it ranks for |
| `ai_overview` | times cited in an Overview |
| `assistants` | which assistants cite it, how often |
| `class` | **dual** (top 10 and cited by an assistant or an Overview), **google-only**, **ai-only** |
| `owner` | the brand, a competitor (which), or a third party |
| `type` | listicle, vs page, alternatives page, review, guide, Reddit thread, video, vendor product page |
| `brand_listed` | whether the page names the brand (step 5) |

Sort dual first, then by how many queries and assistants each covers.

## 5. Read the dual winners

`web_scrape` the top 10 to 15 dual pages (about $0.006 a page). For each, record what makes it citable:

- page type and H1; how many products it lists, in what order, and where the brand would fit
- a comparison table (its columns), pricing shown, a dated "updated" line, an author with credentials
- an FAQ block, headings phrased as questions, a short direct answer near the top
- rough length, original data or testing claims, screenshots
- whether it names the brand and the competitors that matter in the market

Quote structure, never copy text.

## 6. The brand's own pages

For each of `brand.domains`, `seo_ranked_keywords` (`domain`, `location`, `limit` 100); the rows come sorted by volume, so keep positions 20 or better yourself. When the comparison pages live on another domain than the product (`brand.notes`), check both and report which one the assistants cite.

## Output

1. **Overlap table**, top 30 rows.
2. **Page briefs**, one per gap, most valuable first. A gap is a query cluster where dual winners exist and the brand has no page in the top 20. Each brief: target queries, the page type the winners use, the sections they all have, comparison columns, competitors to cover honestly, proof to add (data, screenshots, customer quotes), FAQ questions from People Also Ask, internal links, which domain should host it.
3. **Inclusion targets**: third-party dual pages that do not list the brand, with the author or editor named on the page. A human asks for inclusion; module 4's contact method applies.
4. **Refresh list**: the brand's pages ranking 11 to 20, and what the winners have that they lack.
