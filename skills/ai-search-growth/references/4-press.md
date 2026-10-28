# Module 4: Trade press in the target verticals

A press list built from what journalists actually wrote, with a verified email and an angle each. Coverage in trade titles also becomes a source the assistants cite. The skill drafts pitches; a human sends them.

## 1. Outlets

Start from `press.outlets` (name, vertical, domain). Add any trade outlet that appears in step 2 for two or more queries, with the domain taken from its article URLs. Leave national and consumer titles out unless the user asks.

## 2. Who covers the topic

`news_search` per vertical and angle, in the market (`location` = `market.serp_location`, `limit` 20):

- the problem in the trade: "<vertical> <the problem the product solves>"
- the technology in the trade: "<vertical> AI", "<vertical> software", "<vertical> automation"
- each competitor's name: who already writes about the category

About $0.004 to $0.013 a search. Rows: `title`, `source`, `snippet`, `url`, publication time. Keep articles from the last 12 months on a target outlet or another trade outlet in the market.

## 3. Bylines

News rows carry no author. `web_scrape` each kept article (about $0.006) and read the byline, the author's role if printed, and the date. Record journalist, outlet, outlet domain, article title, URL, date and a one-line beat. A journalist with two or more relevant articles, or one about a competitor, is a target. Note freelancers: their email is not on the outlet's domain.

## 4. Emails

For staff journalists:

```
contact_find {"input": {"first_name": "<first>", "last_name": "<last>", "company_domain": "<outlet domain>"}, "max_cost": "<max_cost_for_all>"}
```

Charged only when an email is found (up to about $0.10 at `max_cost_for_all`); a miss is free. A catch-all or unverified result is not send-ready: say so, or check it with `contact_verify`. Many outlets publish a news desk or editor address on their contact page: `web_scrape` it as the fallback. Never guess an address.

## 5. Angles

Per vertical, an angle the readers care about, built on facts:

- **Data from module 1**: "We asked ChatGPT, Perplexity, Claude and Gemini the questions <vertical> professionals ask about <problem>. Here is what they recommend, and what they get wrong." Original data on how AI answers a trade's questions is a story; the product is a footnote.
- **The trade's pain, quantified**, from published research (cite it), and its seasonal peaks.
- **Trust**: the questions a firm in the vertical should ask any vendor in the category (data, compliance, control), drawn from `brand.claims`.

## 6. Pitches

One draft per target: subject line, three to five sentences, a reference to their own article (title and date), the angle, what can be offered (data, a spokesperson, a customer willing to talk), no attachment on first contact, plain text. Written for a human to send from their own mailbox; each one marked `draft`.

## 7. Watch

One `create_news_search_watch` per phrase in `watches.news`; the weekly run refreshes each with `refresh_news_search_watch`. New articles from target journalists go to the top of the weekly report with a one-line reactive angle.

## Output

The press list (`<slug>-press` table or `data/press.csv`): journalist, outlet, vertical, email, email status, fallback desk address, articles (URL, date), angle, pitch draft, status (`draft`, `sent`, `replied`, set by the human). Plus the outlet roster and the total charged.
