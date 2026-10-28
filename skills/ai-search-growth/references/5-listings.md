# Module 5: Marketplaces and directories

Which listings the competitors have, what the best listings look like, and what each marketplace needs from the brand. A human submits; this module ranks the targets and prepares the material.

## 1. Where competitors are listed

`seo_backlinks` for each competitor domain (`domain`, `limit` 100, about $0.10 each). From the referring domains keep app marketplaces, software and AI directories, review sites and launch platforms (for example `appsource.microsoft.com`, `marketplace.microsoft.com`, `workspace.google.com`, `apps.shopify.com`, `appexchange.salesforce.com`, `slack.com/apps`, `chromewebstore.google.com`, `producthunt.com`, `g2.com`, `capterra.com`, `alternativeto.net`, `theresanaiforthat.com`, `futurepedia.io`). Count how many competitors each one lists: a directory that lists four competitors and not the brand is a priority. Add what step 1 finds to `listings` in the config.

## 2. Read the marketplace search pages

For each of `listings.marketplaces`, `web_scrape` its search URLs for the category's words (about $0.006 a page). Tested formats:

- Microsoft marketplace: `https://appsource.microsoft.com/en-us/marketplace/apps?search=<words>&page=1` (now served by marketplace.microsoft.com). 15 listings a page with name, publisher, product type (add-in or SaaS), tagline, rating and count, price.
- Google Workspace Marketplace: `https://workspace.google.com/marketplace/search/<words>`. Name, developer, description, and the rating glued to the install count: `4.6616K+` reads as rating 4.6 and 616K+ installs, `4.926` as rating 4.9 and 26 installs. Split it with care and say when it is ambiguous.

Other marketplaces: scrape the search URL the same way and read what it returns; if a page comes back empty or blocked, say so and move on. Record per listing: name, publisher, type, tagline, rating, ratings or installs, price, rank in the search. Note which competitors are present and what the top five promise.

## 3. Directories

For each of `listings.directories`, `web_scrape` the search URL. On There's An AI For That (`https://theresanaiforthat.com/s/<words>/`) the first block is "Featured": paid placements, not ranking; skip it. Record whether the brand and the competitors are listed and where. On the full server, `discover` "<directory> scraper" finds raw actors that return the same as structured rows.

## 4. What each listing needs

For every target, a checklist row: account needed, review process and typical delay, required assets (logo sizes, screenshots, video, privacy policy URL, terms, support URL, a data processing agreement), category to choose, and the technical gate. Gates set the timeline, for example:

- **Google Workspace Marketplace**: OAuth app verification, and for apps that read or manage Gmail (restricted scopes) an independent security assessment, renewed yearly. Weeks, and a cost.
- **Microsoft marketplace**: a Partner Center account and publisher verification; the offer type (add-in or SaaS) decides the rest; Microsoft 365 app compliance is optional and shows on the listing.
- **Store-style marketplaces** (Shopify, Salesforce, Slack, Atlassian): a security or app review before listing.

Confirm each requirement on the marketplace's own documentation at the time of the run (`web_scrape` the current docs page and quote it). These rules change; date the checklist.

## Output

- **Listings table**: target, type (marketplace, directory, review site, launch site), competitors present, priority (high when three or more competitors are listed, or it appears in module 2), gate, lead time, owner, status.
- **Listing copy drafts** per marketplace: name, short and long description within that marketplace's limits, category, keywords, screenshot captions, written from what the top listings promise and what the brand does differently.
- **Order of work**: the slowest gate first, the free directories meanwhile.
