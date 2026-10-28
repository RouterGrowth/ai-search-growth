#!/usr/bin/env python3
"""Track whether AI assistants name your product, on a schedule.

  python runner/track.py daily      # the panel on cadence.daily_assistants
  python runner/track.py weekly     # cadence.weekly_assistants + Google results + AI mentions + weekly report
  python runner/track.py baseline   # everything once: day zero
  python runner/track.py report     # rebuild reports from data/ without any call

Options: --date YYYY-MM-DD, --dry-run (quote only), --limit N (first N prompts, for a test).
Needs ROUTERGROWTH_API_KEY. Reads config.json and prompts.json at the repo root; writes data/ and reports/.
Standard library only, Python 3.10+.
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze  # noqa: E402
import rg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
IN_ACTIONS = bool(os.environ.get("GITHUB_ACTIONS"))


def say(msg: str, level: str = "notice"):
    print(f"::{level}::{msg}" if IN_ACTIONS else f"[{level}] {msg}", flush=True)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def load_dir(folder: Path) -> list[dict]:
    rows = []
    for f in sorted(folder.glob("*.jsonl")):
        rows += load_jsonl(f)
    return rows


def merge_write(path: Path, rows: list[dict]):
    """Write rows into a jsonl file, replacing rows with the same id (a rerun the same day)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    keep = {r["id"]: r for r in load_jsonl(path)}
    keep.update({r["id"]: r for r in rows})
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep.values()))


def placeholder(config: dict) -> bool:
    b = config.get("brand", {})
    return "<" in json.dumps([b.get("name"), b.get("domains"), b.get("slug")])


def price_of(inspect: dict, platform: str | None = None) -> float | None:
    """The workspace's price for one call: the platform's base on aeo.answer, otherwise max_cost_for_all."""
    if platform:
        for offer in inspect.get("offers") or []:
            by = (offer.get("pricing") or {}).get("by_platform") or {}
            if offer.get("executable") and platform in by:
                return float(by[platform]["base"])
        return None
    amount = ((inspect.get("waterfall") or {}).get("max_cost_for_all") or {}).get("amount")
    return float(amount) if amount else None


def plan(mode: str, config: dict, prompts: list[dict], limit: int | None) -> dict:
    cadence = config.get("cadence", {})
    daily, weekly = cadence.get("daily_assistants", []), cadence.get("weekly_assistants", [])
    assistants = {"daily": daily, "weekly": weekly, "baseline": list(dict.fromkeys(daily + weekly))}[mode]
    with_search = mode in ("weekly", "baseline")
    return {"assistants": assistants, "prompts": prompts[:limit] if limit else prompts,
            "serp_queries": config.get("serp_queries", []) if with_search else [],
            "mention_targets": [(d, p) for d in config["brand"]["domains"] for p in ("google", "chatgpt")] if with_search else []}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["daily", "weekly", "baseline", "report"])
    ap.add_argument("--date", default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()

    root = Path(args.root)
    config = json.loads((root / "config.json").read_text())
    panel = json.loads((root / "prompts.json").read_text())
    if placeholder(config):
        say("config.json still holds the template placeholders. Fill it (or ask your agent to run the setup "
            "of the ai-search-growth skill), then run again. Nothing was called.", "warning")
        return 0
    data, reports, day = root / "data", root / "reports", args.date

    if args.mode != "report":
        key = os.environ.get("ROUTERGROWTH_API_KEY")
        if not key:
            say("ROUTERGROWTH_API_KEY is not set (repo Settings > Secrets and variables > Actions). Nothing was called.", "warning")
            return 0
        client = rg.Client(key, os.environ.get("ROUTERGROWTH_API_URL", "https://api.routergrowth.com"))
        p = plan(args.mode, config, panel["prompts"], args.limit)

        # Quote first, at this workspace's own prices, and stop above the budget.
        aeo = client.inspect("aeo.answer")
        if rg.error_code(aeo):
            say(f"inspect failed: {aeo['error']}", "error")
            return 1
        prices = {a: price_of(aeo, a) for a in p["assistants"]}
        missing = [a for a, v in prices.items() if v is None]
        if missing:
            say(f"no live price for {missing} on aeo.answer; check the assistant names in config.cadence", "error")
            return 1
        serp_price = price_of(client.inspect("seo.serp")) if p["serp_queries"] else 0.0
        ment_price = price_of(client.inspect("aeo.mentions")) if p["mention_targets"] else 0.0
        if serp_price is None or ment_price is None:
            say("no live price for seo.serp or aeo.mentions; try again later", "error")
            return 1
        quote = (len(p["prompts"]) * sum(prices.values()) + len(p["serp_queries"]) * (serp_price or 0)
                 + len(p["mention_targets"]) * (ment_price or 0))
        budget = (config.get("budgets") or {}).get(f"{args.mode}_usd")
        print(f"{args.mode} {day}: {len(p['prompts'])} prompts x {p['assistants']}, {len(p['serp_queries'])} searches, "
              f"{len(p['mention_targets'])} AI-mention searches. Quote ${quote:.2f} (settles at or below), budget {budget}.")
        if budget is not None and quote > float(budget) and not args.limit:
            say(f"quote ${quote:.2f} is above budgets.{args.mode}_usd ({budget}). Raise it in config.json or shrink the panel. Nothing was called.", "error")
            return 1
        if args.dry_run:
            return 0

        slug, location = config["brand"]["slug"], config["market"]
        stop = {"code": None}

        def call(capability, input, max_cost, idem):
            if stop["code"]:
                return {"status": "skipped", "error": {"code": "skipped_after_" + stop["code"]}}
            out = client.run(capability, input, f"{max_cost:.6f}", idem)
            if rg.error_code(out) in rg.STOP_CODES or out.get("status") == "blocked":
                stop["code"] = rg.error_code(out) or "blocked"
            return out

        jobs = []
        for a in p["assistants"]:
            for pr in p["prompts"]:
                inp = {"prompt": pr["text"], "assistant": a}
                if a != "gemini":  # Gemini refuses a location
                    inp["location"] = location["aeo_location"]
                jobs.append(("answer", a, pr, ("aeo.answer", inp, prices[a], f"{slug}-aeo-{day}-{a}-{pr['id']}")))
        for q in p["serp_queries"]:
            inp = {"keyword": q, "location": location["serp_location"], "language": location.get("language", "en")}
            jobs.append(("serp", None, q, ("seo.serp", inp, serp_price, f"{slug}-serp-{day}-{q}")))
        for d, platform in p["mention_targets"]:
            inp = {"domain": d, "platform": platform}
            if platform == "google":  # chatgpt mentions are held for the US in English: no location
                inp["location"] = location["serp_location"]
            jobs.append(("mention", platform, d, ("aeo.mentions", inp, ment_price, f"{slug}-mentions-{day}-{d}-{platform}")))

        workers = int((config.get("runner") or {}).get("concurrency", 4))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda j: call(*j[3]), jobs))

        ver = panel.get("version", "v1")
        answers = [analyze.answer_row(day, a, pr, ver, r, config) for (k, a, pr, _), r in zip(jobs, results) if k == "answer"]
        serps = [analyze.serp_row(day, q, r, config) for (k, _, q, _), r in zip(jobs, results) if k == "serp"]
        ments = [analyze.mention_row(day, d, pl, r) for (k, pl, d, _), r in zip(jobs, results) if k == "mention"]
        merge_write(data / "answers" / f"{day}.jsonl", answers)
        if serps:
            merge_write(data / "serp" / f"{day}.jsonl", serps)
        if ments:
            merge_write(data / "mentions" / f"{day}.jsonl", ments)

        total = sum(rg.charged(r) for r in results)
        holes = [r for r in answers if r["status"] != "succeeded"]
        receipt = {"date": day, "mode": args.mode, "quote": round(quote, 4), "charged": round(total, 4),
                   "calls": len(jobs), "answer_holes": len(holes), "stopped": stop["code"],
                   "run_ids": [r.get("run_id") for r in results if r.get("run_id")]}
        (data / "runs").mkdir(parents=True, exist_ok=True)
        (data / "runs" / f"{day}-{args.mode}.json").write_text(json.dumps(receipt, indent=1) + "\n")
        for a, m in analyze.scoreboard(answers, config["brand"]["name"]).items():
            print(f"{a}: named {m['named']}/{m['answered']} ({analyze._pct(m['mention_rate'])}), "
                  f"cited {'n/a' if m['cited'] is None else m['cited']}, holes {m['holes']}")
        print(f"charged ${total:.4f} over {len(receipt['run_ids'])} runs")
        if stop["code"]:
            say(f"stopped early: {stop['code']}. Top up or raise the spend guard, then rerun the same day: done calls replay free.", "error")
        if holes and len(holes) == len(answers):
            say("every answer failed; nothing to report", "error")
            return 1

    all_answers, all_serps = load_dir(data / "answers"), load_dir(data / "serp")
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "latest.md").write_text(analyze.latest_report(day, all_answers, all_serps, config, panel))
    write_summary(data / "summary.csv", all_answers, config)
    if args.mode in ("weekly", "baseline"):
        receipt_path = data / "runs" / f"{day}-{args.mode}.json"
        total = json.loads(receipt_path.read_text())["charged"] if receipt_path.exists() else 0.0
        name = f"baseline-{day}.md" if args.mode == "baseline" else f"weekly/{day}.md"
        (reports / name).parent.mkdir(parents=True, exist_ok=True)
        (reports / name).write_text(analyze.weekly_report(day, all_answers, all_serps, load_dir(data / "mentions"), config, panel,
                                                          total, "Baseline" if args.mode == "baseline" else "Weekly report"))
    return 0


def write_summary(path: Path, answers: list[dict], config: dict):
    """One line per date and assistant, unprompted prompts only: the series to chart."""
    by_day = {}
    for r in answers:
        by_day.setdefault(r["date"], []).append(r)
    lines = ["date,assistant,answered,holes,named,mention_rate,cited,citation_rate,share_of_voice,avg_rank"]
    for d in sorted(by_day):
        for a, m in analyze.scoreboard(by_day[d], config["brand"]["name"]).items():
            vals = [d, a, m["answered"], m["holes"], m["named"], m["mention_rate"], m["cited"], m["citation_rate"],
                    m["share_of_voice"], m["avg_rank"]]
            lines.append(",".join("" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v)) for v in vals))
    path.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
