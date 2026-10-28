"""Turn assistant answers and search results into rows, metrics and reports.

Pure functions over plain dicts, so they can be tested offline and reused by
anything built on top (a dashboard, a Slack digest, another channel).
"""

import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from urllib.parse import urlsplit

UNPROMPTED = {"problem", "category", "alternative", "vertical", "trust"}
REDIRECT_HOSTS = {"vertexaisearch.cloud.google.com"}  # Gemini's grounding redirects: the source title holds the domain
DOMAIN = re.compile(r"(?:[a-z0-9-]+\.)+[a-z]{2,}")
COMMUNITY = {"reddit.com": "Reddit", "x.com": "X", "twitter.com": "X", "youtube.com": "video",
             "linkedin.com": "LinkedIn", "quora.com": "Quora", "medium.com": "blog platform"}

LINK_LINE = re.compile(r"^[ \t]*\[[^\]\n]*\]\([^)\s]*\)[ \t]*$", re.M)
LINK = re.compile(r"\[([^\]\n]*)\]\([^)\s]*\)")
BARE_URL = re.compile(r"https?://\S+")
SPLIT_ITEM = re.compile(r"[ \t]+-[ \t]*\n+\s*")
BOLD = re.compile(r"\*\*([^*\n]{2,60}?)\*\*")
# Words that open or close a bolded heading rather than a product name ("Best free options", "MCP servers").
NOT_NAME_FIRST = {"a", "accuracy", "all", "an", "best", "bottom", "budget", "caution", "cheapest", "choosing", "cons",
                  "considerations", "cost", "coverage", "data", "example", "for", "free", "freshness", "how", "if",
                  "important", "key", "lean", "main", "most", "note", "option", "our", "overview", "paid", "practical",
                  "pricing", "pros", "quick", "recommended", "similarities", "step", "summary", "the", "tip", "top",
                  "use", "verdict", "warning", "what", "when", "why", "with", "yes", "no"}
NOT_NAME_LAST = {"apis", "approach", "considerations", "guide", "options", "picks", "platforms", "recommendations",
                 "servers", "setup", "stack", "tier", "tools", "workflow"}


# --- normalising -----------------------------------------------------------

def normalize_url(url: str) -> str:
    """Host without www, path without trailing slash; scheme, query (utm_source=openai) and fragment dropped."""
    if not url:
        return ""
    parts = urlsplit(url if "://" in url else "https://" + url)
    host = (parts.hostname or "").lower().removeprefix("www.")
    return host + parts.path.rstrip("/")


def domain_of(url: str) -> str:
    return normalize_url(url).split("/", 1)[0]


def on_domain(url: str, domains: list[str]) -> bool:
    d = domain_of(url)
    return any(x and (d == x.lower().removeprefix("www.") or d.endswith("." + x.lower().removeprefix("www."))) for x in domains)


def source_urls(sources: list[dict]) -> list[str]:
    """Normalised source URLs. Gemini cites Google grounding redirects whose title is the real domain: that domain
    is kept, and a redirect without one is dropped rather than counted as a citation of Google."""
    out = []
    for s in sources or []:
        url = s.get("url") or ""
        if domain_of(url) in REDIRECT_HOSTS:
            title = (s.get("title") or "").strip().lower().removeprefix("www.")
            if DOMAIN.fullmatch(title):
                out.append(title)
        elif url:
            out.append(normalize_url(url))
    return out


# --- mentions --------------------------------------------------------------

def prose(text: str) -> str:
    """The answer as a reader sees it. ChatGPT puts unrelated page titles on lines of their own as citation links,
    so those lines go; inline links keep their text; bare URLs go; and list items that stripped citations split
    over two lines ("**Clay** - \\n\\nWaterfalls across...") are joined again."""
    text = LINK_LINE.sub("", text or "")
    text = LINK.sub(r"\1", text)
    text = BARE_URL.sub("", text)
    return SPLIT_ITEM.sub(" - ", text)


def _sentences(text: str):
    """(start offset, sentence) pairs, split on sentence ends and line breaks."""
    start = 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        yield start, text[start:m.start()]
        start = m.end()
    yield start, text[start:]


def first_mention(text: str, aliases: list[str], ambiguous: list[str], category_terms: list[str]) -> int | None:
    """Offset of the first mention of any alias. An ambiguous alias ("Copilot", "Spark") counts only in a
    sentence that also names one of the category terms, or written as a bolded name in a list ("**Spark**",
    "**2. Spark MCP**"), with the capitals given in the config."""
    best = None
    terms = [t.lower() for t in category_terms]
    amb = {a.lower() for a in ambiguous}
    for alias in aliases:
        pattern = re.compile(r"(?<![\w-])" + re.escape(alias) + r"(?![\w-])", re.I)
        if alias.lower() in amb:
            bold = re.compile(r"\*\*\s*(?:\d+\.\s*)?" + re.escape(alias) + r"(?![\w-])(?:[ .][\w.+-]+){0,2}\s*\*\*")
            m = bold.search(text)
            if m and (best is None or m.start() < best):
                best = m.start()
            for offset, sentence in _sentences(text) if terms else ():
                if any(t in sentence.lower() for t in terms):
                    m = pattern.search(sentence)
                    if m and (best is None or offset + m.start() < best):
                        best = offset + m.start()
                        break
        else:
            m = pattern.search(text)
            if m and (best is None or m.start() < best):
                best = m.start()
    return best


def mentions(text: str, config: dict) -> dict[str, int]:
    """{brand or competitor name: rank of first mention}, 1 = named first. The brand is keyed as its name.
    Read on the prose: citation links and URLs do not count as mentions."""
    terms = config.get("category_terms", [])
    text = prose(text)
    found = {}
    brand = config["brand"]
    off = first_mention(text, brand.get("aliases") or [brand["name"]], brand.get("ambiguous", []), terms)
    if off is not None:
        found[brand["name"]] = off
    for c in config.get("competitors", []):
        off = first_mention(text, c.get("aliases") or [c["name"]], c.get("ambiguous", []), terms)
        if off is not None:
            found[c["name"]] = off
    return {name: rank for rank, (name, _) in enumerate(sorted(found.items(), key=lambda kv: kv[1]), 1)}


def bold_names(text: str) -> set[str]:
    """Product-like names an answer puts in bold ("**LeadMagic**", "**2. Hunter.io (free tier)**")."""
    names = set()
    for raw in BOLD.findall(prose(text)):
        name = re.sub(r"^\d+\.\s*", "", raw)
        name = re.sub(r"\s*\(.*$", "", name).strip(" -:.,")
        words = name.split()
        if (not words or len(words) > 3 or not (name[0].isupper() or name[0].isdigit()) or any(c in name for c in ",;/?!")
                or words[0].lower() in NOT_NAME_FIRST or words[-1].lower() in NOT_NAME_LAST):
            continue
        names.add(name)
    return names


def untracked_names(answers: list[dict], config: dict, top: int = 10) -> list[tuple[str, int, list[str]]]:
    """Names the assistants put in bold that are neither the brand nor a tracked competitor, kept when two
    assistants or three answers give them: the candidates for competitors[]. (name, answers, assistants)."""
    known = [config["brand"]["name"], *config["brand"].get("aliases", [])]
    for c in config.get("competitors", []):
        known += [c["name"], *c.get("aliases", [])]
    known_re = [re.compile(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", re.I) for k in known if k]
    count, by = Counter(), defaultdict(set)
    for r in answers:
        if r.get("status") != "succeeded":
            continue
        for name in bold_names(r.get("answer") or ""):
            if not any(k.search(name) for k in known_re):
                count[name] += 1
                by[name].add(r["assistant"].partition(":")[0])
    keep = [(n, c, sorted(by[n])) for n, c in count.items() if len(by[n]) >= 2 or c >= 3]
    return sorted(keep, key=lambda x: (-len(x[2]), -x[1], x[0]))[:top]


# --- rows ------------------------------------------------------------------

def answer_row(day: str, assistant: str, prompt: dict, panel_version: str, run: dict, config: dict) -> dict:
    """One row per (date, assistant, prompt), whatever the run's outcome."""
    brand = config["brand"]
    row = {"id": f"{day}|{assistant}|{prompt['id']}", "date": day, "assistant": assistant,
           "prompt_id": prompt["id"], "group": prompt["group"], "panel_version": panel_version,
           "run_id": run.get("run_id"), "status": run.get("status") or "error",
           "charged": float((run.get("billing") or {}).get("charged") or 0)}
    result = run.get("result") if run.get("status") == "succeeded" else None
    if not result:
        row["error"] = (run.get("error") or {}).get("code") or row["status"]
        return row
    text = result.get("answer") or ""
    named = mentions(text, config)
    sources = source_urls(result.get("sources"))
    row.update({
        "model": result.get("model"),
        "brand_named": brand["name"] in named,
        "brand_rank": named.get(brand["name"]),
        "competitors": {k: v for k, v in named.items() if k != brand["name"]},
        "brand_cited": any(on_domain(s, brand["domains"]) for s in sources),
        "sources": sources,
        "answer": text,
    })
    return row


def serp_row(day: str, query: str, run: dict, config: dict) -> dict:
    row = {"id": f"{day}|{query}", "date": day, "query": query, "run_id": run.get("run_id"),
           "status": run.get("status") or "error", "charged": float((run.get("billing") or {}).get("charged") or 0)}
    result = run.get("result") if run.get("status") == "succeeded" else None
    if not result:
        row["error"] = (run.get("error") or {}).get("code") or row["status"]
        return row
    results = [{"position": r.get("position"), "url": normalize_url(r.get("url", "")), "title": r.get("title", "")}
               for r in result.get("results") or []]
    overview = [normalize_url(u) for u in result.get("ai_overview_sources") or []]
    brand_pos = next((r["position"] for r in results if on_domain(r["url"], config["brand"]["domains"])), None)
    row.update({"ai_overview_present": bool(result.get("ai_overview_present")), "ai_overview_sources": overview,
                "brand_in_overview": any(on_domain(u, config["brand"]["domains"]) for u in overview),
                "brand_position": brand_pos, "results": results})
    return row


def mention_row(day: str, domain: str, platform: str, run: dict) -> dict:
    result = run.get("result") or {}
    status = run.get("status") or "error"
    if (run.get("error") or {}).get("code") == "no_match":
        status = "no_match"
    items = result.get("mentions") or []
    return {"id": f"{day}|{domain}|{platform}", "date": day, "domain": domain, "platform": platform,
            "status": status, "total": result.get("total") or (0 if status == "no_match" else None),
            "questions": [m.get("question") for m in items if isinstance(m, dict) and m.get("question")][:10],
            "run_id": run.get("run_id"), "charged": float((run.get("billing") or {}).get("charged") or 0)}


# --- metrics ---------------------------------------------------------------

def window(rows: list[dict], end: str, days: int = 7) -> list[dict]:
    last = date.fromisoformat(end)
    first = (last - timedelta(days=days - 1)).isoformat()
    return [r for r in rows if first <= r["date"] <= end]


def scoreboard(rows: list[dict], brand: str) -> dict[str, dict]:
    """Per assistant, on unprompted prompts: answered, holes, mention rate, citation rate, share of voice, rank."""
    out = {}
    by_assistant = defaultdict(list)
    for r in rows:
        if r.get("group") in UNPROMPTED:
            by_assistant[r["assistant"]].append(r)
    for assistant, rs in sorted(by_assistant.items()):
        ok = [r for r in rs if r["status"] == "succeeded"]
        named = [r for r in ok if r.get("brand_named")]
        cited = [r for r in ok if r.get("brand_cited")]
        brand_mentions = len(named)
        all_mentions = brand_mentions + sum(len(r.get("competitors") or {}) for r in ok)
        ranks = [r["brand_rank"] for r in named if r.get("brand_rank")]
        out[assistant] = {
            "answered": len(ok), "holes": len(rs) - len(ok), "named": len(named),
            "mention_rate": len(named) / len(ok) if ok else None,
            "cited": len(cited),
            "citation_rate": len(cited) / len(ok) if ok else None,
            "share_of_voice": brand_mentions / all_mentions if all_mentions else None,
            "avg_rank": sum(ranks) / len(ranks) if ranks else None,
        }
    return out


def owners(rows: list[dict], brand: str) -> dict[str, list[tuple[str, int]]]:
    """Per prompt group, the names mentioned most often (brand included), top three."""
    counts = defaultdict(Counter)
    for r in rows:
        if r["status"] != "succeeded":
            continue
        for name in r.get("competitors") or {}:
            counts[r["group"]][name] += 1
        if r.get("brand_named"):
            counts[r["group"]][brand] += 1
    return {g: c.most_common(3) for g, c in sorted(counts.items())}


def movers(current: list[dict], previous: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """(assistant, prompt id) pairs where the brand appeared this window and never in the previous one, and the reverse."""
    def named_set(rows):
        seen, named = set(), set()
        for r in rows:
            if r["status"] == "succeeded":
                seen.add((r["assistant"], r["prompt_id"]))
                if r.get("brand_named"):
                    named.add((r["assistant"], r["prompt_id"]))
        return seen, named
    seen_now, now = named_set(current)
    seen_before, before = named_set(previous)
    return {"appeared": sorted((now - before) & seen_before), "vanished": sorted((before - now) & seen_now)}


def source_type(url: str, config: dict) -> str:
    if on_domain(url, config["brand"]["domains"]):
        return "brand"
    for c in config.get("competitors", []):
        if c.get("domain") and on_domain(url, [c["domain"]]):
            return "competitor: " + c["name"]
    for d, label in COMMUNITY.items():
        if on_domain(url, [d]):
            return label
    return "third party"


def citation_graph(answers: list[dict], serps: list[dict], config: dict, top: int = 20) -> dict:
    """Most cited URLs and domains across assistant answers and AI Overviews, with who cites them."""
    urls, domains = Counter(), Counter()
    cited_by = defaultdict(set)
    for r in answers:
        if r["status"] != "succeeded":
            continue
        for u in {s for s in r.get("sources") or [] if domain_of(s) not in REDIRECT_HOSTS}:  # rows from 0.1 kept redirects
            urls[u] += 1
            domains[domain_of(u)] += 1
            cited_by[u].add(r["assistant"])
    for r in serps:
        for u in set(r.get("ai_overview_sources") or []):
            urls[u] += 1
            domains[domain_of(u)] += 1
            cited_by[u].add("google ai overview")
    return {"urls": [(u, n, sorted(cited_by[u]), source_type(u, config)) for u, n in urls.most_common(top)],
            "domains": [(d, n, source_type(d, config)) for d, n in domains.most_common(top)]}


# --- reports ---------------------------------------------------------------

def _pct(x):
    return "n/a" if x is None else f"{x * 100:.0f}%"


def _delta(now, before):
    if now is None or before is None:
        return ""
    d = (now - before) * 100
    return f" ({'+' if d >= 0 else ''}{d:.0f})"


def scoreboard_table(now: dict, before: dict | None = None) -> str:
    before = before or {}
    lines = ["| Assistant | Answers | Holes | Named | Mention rate | Cited | Citation rate | Share of voice | Avg rank |",
             "|---|---|---|---|---|---|---|---|---|"]
    for a, m in now.items():
        b = before.get(a, {})
        cited = "n/a" if m["cited"] is None else m["cited"]
        rank = "n/a" if m["avg_rank"] is None else f"{m['avg_rank']:.1f}"
        lines.append(f"| {a} | {m['answered']} | {m['holes']} | {m['named']} | {_pct(m['mention_rate'])}{_delta(m['mention_rate'], b.get('mention_rate'))} | "
                     f"{cited} | {_pct(m['citation_rate'])}{_delta(m['citation_rate'], b.get('citation_rate'))} | "
                     f"{_pct(m['share_of_voice'])}{_delta(m['share_of_voice'], b.get('share_of_voice'))} | {rank} |")
    return "\n".join(lines)


def untracked_section(answers: list[dict], config: dict) -> list[str]:
    names = untracked_names(answers, config)
    if not names:
        return []
    return ["", "## Named but not tracked", "",
            "Bolded names in the answers that are not in `competitors[]`, given by two assistants or in three answers. "
            "Add the real competitors to config.json: they then count in share of voice.", ""] + \
           [f"- {n}: {c} answers ({', '.join(by)})" for n, c, by in names]


def latest_report(day: str, answers: list[dict], serps: list[dict], config: dict, prompts: dict) -> str:
    brand = config["brand"]["name"]
    last7 = window(answers, day)
    prev = window(answers, (date.fromisoformat(day) - timedelta(days=7)).isoformat())
    graph = citation_graph(last7, window(serps, day, 28), config, 10)
    out = [f"# {brand}: AI search scoreboard", "",
           f"Updated {day}. Rolling 7 days on the unprompted prompts (the `brand` group is left out). "
           "Change against the 7 days before in brackets. Answers vary between runs: read the trend, not one day.", "",
           scoreboard_table(scoreboard(last7, brand), scoreboard(prev, brand)), "",
           "## Who the assistants name, by prompt group", ""]
    for group, top in owners(last7, brand).items():
        out.append(f"- **{group}**: " + ", ".join(f"{n} ({c})" for n, c in top))
    out += untracked_section(last7, config)
    out += ["", "## Most cited domains (7 days, plus AI Overviews from the last 4 weeks)", "",
            "| Domain | Citations | Type |", "|---|---|---|"]
    out += [f"| {d} | {n} | {t} |" for d, n, t in graph["domains"]]
    out += ["", f"Panel {prompts.get('version')}, {len(prompts.get('prompts', []))} prompts. Data in `data/`, weekly reports in `reports/weekly/`."]
    return "\n".join(out) + "\n"


def weekly_report(day: str, answers: list[dict], serps: list[dict], mentions_rows: list[dict], config: dict,
                  prompts: dict, charged_total: float, title: str = "Weekly report") -> str:
    brand = config["brand"]["name"]
    texts = {p["id"]: p["text"] for p in prompts.get("prompts", [])}
    last7 = window(answers, day)
    prev = window(answers, (date.fromisoformat(day) - timedelta(days=7)).isoformat())
    week_serps = window(serps, day)
    graph = citation_graph(last7, week_serps, config)
    moved = movers(last7, prev)
    out = [f"# {brand}: {title}, {day}", "", "## Scoreboard (7 days, unprompted prompts)", "",
           scoreboard_table(scoreboard(last7, brand), scoreboard(prev, brand)), "", "## Movers", ""]
    for kind, label in (("appeared", "Named this week, not the week before"), ("vanished", "Named the week before, not this week")):
        out.append(f"**{label}**" + (":" if moved[kind] else ": none"))
        out += [f"- {a}: {pid} \"{texts.get(pid, '')}\"" for a, pid in moved[kind]]
        out.append("")
    out += ["## Who owns each prompt group", ""]
    out += [f"- **{g}**: " + ", ".join(f"{n} ({c})" for n, c in top) for g, top in owners(last7, brand).items()]
    out += untracked_section(last7, config)
    out += ["", "## Google results and AI Overviews", "",
            "| Query | AI Overview | Brand cited in it | Brand position |", "|---|---|---|---|"]
    for r in week_serps:
        if r["status"] == "succeeded":
            out.append(f"| {r['query']} | {'yes' if r['ai_overview_present'] else 'no'} | {'yes' if r['brand_in_overview'] else 'no'} | "
                       f"{r['brand_position'] or 'not in top 10'} |")
    if mentions_rows:
        out += ["", "## Where the brand's domains already appear in AI answers (aeo.mentions)", "",
                "| Domain | Platform | Answers found |", "|---|---|---|"]
        out += [f"| {m['domain']} | {m['platform']} | {m['total'] if m['total'] is not None else m['status']} |" for m in mentions_rows]
    out += ["", "## Citation graph", "", "| URL | Citations | Cited by | Type |", "|---|---|---|---|"]
    out += [f"| {u} | {n} | {', '.join(by)} | {t} |" for u, n, by, t in graph["urls"]]
    out += ["", "## Next actions", "",
            "Run the modules with an agent and the skill in `skills/ai-search-growth`: module 2 for the third-party pages above "
            "that do not list the brand, module 3 for the Reddit and X rows, module 4 for the press angle on this week's data.",
            "", f"Charged this run: ${charged_total:.2f}. Run IDs in `data/runs/`."]
    return "\n".join(out) + "\n"
