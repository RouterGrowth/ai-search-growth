# Module 6: Product Hunt launch research

What it takes to be the #1 product of the day, which day to pick, what the category's winners did, and what to prepare. The skill researches and drafts. It never asks anyone for upvotes: Product Hunt's rules forbid it and penalise launches that do. Ask people to look at the launch and leave honest feedback.

## The daily leaderboard

```
web_scrape {"input": {"url": "https://www.producthunt.com/leaderboard/daily/<YYYY>/<M>/<D>"}, "max_cost": "<price>"}
```

About $0.006 a day. The page comes back as clean markdown: the day's top launches in order, each with name, tagline, description, `Score`, `Comments`, the Product Hunt page, the external URL, launch tags (topics) and categories. Weekly and monthly boards follow the same pattern (`/leaderboard/weekly/<YYYY>/<week>`, `/leaderboard/monthly/<YYYY>/<M>`).

On the full server, the raw actor `/logiover/product-hunt-daily-launches-scraper` (provider `apify`, `mode: "daily"` or `"dateRange"` with `dateFrom` and `dateTo`, `sortBy: "VOTES"`, `max_cost` at least "2.00", Apify's minimum hold, settling at a few cents a day) adds `launchDayVotes`, `dailyRank` and the `makers` with their usernames and headlines. Its `topic` mode returned unrelated all-time launches in testing: filter by topics after the call instead.

## 1. The bar to beat

The last 4 to 8 weeks of daily boards (28 to 56 pages, about $0.20 to $0.40). Per weekday: the median and range of the #1, #2 and #3 scores and comment counts. Weekends need fewer votes and bring less traffic; Tuesday to Thursday are the most contested. Recommend a day with the score and comment target it needs, and say how many days the numbers rest on.

## 2. The category's winners

From the same pages, keep launches whose tags, categories or tagline match `product_hunt.match`. Add each competitor's own Product Hunt page (`web_scrape` `https://www.producthunt.com/products/<slug>`) for its past launches. Record for each: launch date, rank, score, comments, tagline, topics, what the first gallery image promised. The top five taglines and first comments are the template: quote them, do not copy them.

## 3. Hunters and makers (optional)

On the full server the actor's `makers` field lists who launched in the category; the user may want to reach some as peers or hunters. Look a person up (`social_profile`, `person_enrich`) only when the user asks. A hunter is optional; one with a following in the category helps.

## 4. Supporters

The best supporters are the brand's own: the waitlist, customers, the team's networks, partners. Draft three messages: a heads-up a week before, a launch-day note with the link, a thank-you. None of them asks for an upvote.

## 5. Launch day

Scrape the day's board every two hours: the brand's rank, score and comments against the top three. Report the gap and the hour; nothing else is automated.

## Output

- **Day pick**: the recommended day, score and comment targets, and the weekday table behind them.
- **Category teardown**: the top 10 relevant launches with their numbers, taglines and what they did well.
- **Asset checklist**: tagline (60 characters), description, the maker's first comment, gallery (the first image carries the promise), a short video, a launch offer if any, the topics to pick.
- **Timeline**: 4 to 6 weeks out (day, hunter, assets), 1 week out (heads-up), launch day (board every two hours, every comment answered within the hour), day after (thank-you, publish the result).
- **Message drafts**: heads-up, launch day, thank-you.
