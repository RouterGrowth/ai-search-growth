# Module 3: The Reddit and X threads AI search pulls from

Assistants and Google both lean on community threads. This module finds the threads that already feed the answers, the ones climbing, and where an honest reply from someone at the company would be welcome. It never posts.

## 1. Threads the assistants already cite

From the module 1 store, every cited URL on `reddit.com`, `x.com` or `twitter.com` (note `youtube.com`, `quora.com` and `linkedin.com` too), with the prompts, the assistants and the count. Add the Reddit and X rows from the Google top 10s (`domain` `www.reddit.com`) and from `ai_overview_sources`. This is the priority list: those threads already move answers.

## 2. Threads ranking in Google for the money queries

For 10 money queries, `seo_serp` with the query plus the word "reddit" ("best crm for agencies reddit"). Do not use a `site:reddit.com` operator: it is not honoured and costs more. Keep every reddit.com row: URL, subreddit, position, title. A thread in the top 10 for two or more queries is a hub.

## 3. What the platforms surface themselves

```
social_search {"input": {"platform": "reddit", "query": "<phrase>", "limit": 10}, "max_cost": "<price>"}
social_search {"input": {"platform": "x", "query": "<phrase>", "limit": 20}, "max_cost": "<price>"}
```

Priced per post returned (Reddit about $0.003, X under $0.001). Reddit rows: `url`, `text` (title), `body`, `community`, `author`, `created_at`; engagement counts are null. Expect off-topic rows; filter by reading. Merge with steps 1 and 2 on URL.

## 4. Read the hubs

For the top 10 threads, cited ones first:

```
social_comments {"input": {"url": "<thread url>", "limit": 30}, "max_cost": "<price>"}
```

Reddit costs about $0.08 a thread plus about $0.008 a comment, so 10 threads at 30 comments is about $3: quote it and get a yes. Reddit returns the comments, not the post: take the post's title and body from the `social_search` row when the thread came from a search. On X, pass the status URL. Record: products recommended and how often, objections, questions nobody answered, whether the brand or competitors are named, the newest comment date (a thread with replies this month is alive). Quote verbatim with the comment URL. Never look up a commenter.

## 5. Watches for what is new

One watch per phrase in `watches.reddit` and `watches.x`:

```
create_social_search_watch {"input": {"platform": "reddit", "query": "<phrase>", "limit": 10}, "max_cost": "<price>"}
```

Keep the `watch_id`s in the store. The weekly run calls `refresh_social_search_watch` (`watch_id`, `max_cost`) for each, which returns only the posts that are new since the last refresh. A new post asking exactly the brand's question is the best reply opportunity there is.

## 6. Subreddit roster

Reddit blocks automated reads of its rules pages. For each subreddit that appears twice or more, ask the user to open `https://www.reddit.com/r/<name>/about/rules/` and paste the rules. Record vendor tolerance (self-promotion rule, flair, disclosure) and classify: open, conditional, closed, unknown.

## Output

- **Thread table**: URL, platform, subreddit, cited by (assistants, count), Google rank and query, last activity, products recommended, open questions.
- **Recommendation table**: product, threads recommending it, the typical reason.
- **Reply briefs** for the 5 to 10 best threads: what was asked, what the existing answers miss, the honest point the brand can add, and a disclosure line ("I work on <brand>, so weigh this accordingly"). A human writes and posts from their own account, within the community's rules.
- **New this week** from the watches.

Never post, vote or DM; no sock puppets; one reply per thread; a reply that does not answer better than the existing ones is not worth posting.
