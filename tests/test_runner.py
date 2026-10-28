"""Offline tests for the runner: mention detection, rows, metrics, reports, and the report mode end to end."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runner"))
import analyze  # noqa: E402
import track  # noqa: E402

EM_DASH = chr(0x2014)

CONFIG = {
    "brand": {"name": "Acme", "slug": "acme", "aliases": ["Acme", "Acme Invoices"], "domains": ["acme.io"]},
    "competitors": [
        {"name": "QuickBooks", "aliases": ["QuickBooks"], "domain": "quickbooks.intuit.com", "ambiguous": []},
        {"name": "Wave", "aliases": ["Wave"], "domain": "waveapps.com", "ambiguous": ["Wave"]},
    ],
    "category_terms": ["invoice", "invoicing"],
    "market": {"aeo_location": "US", "serp_location": "United States", "language": "en"},
}
PROMPTS = {"version": "v1", "prompts": [
    {"id": "p01", "group": "problem", "text": "How do I stop chasing unpaid invoices?"},
    {"id": "p02", "group": "alternative", "text": "QuickBooks alternatives?"},
    {"id": "p03", "group": "brand", "text": "Is Acme any good?"},
]}


def run(answer, sources=(), status="succeeded", charged="0.05"):
    return {"run_id": "run_x", "status": status, "billing": {"charged": charged},
            "result": {"answer": answer, "model": "m", "sources": [{"url": u} for u in sources]}}


class Mentions(unittest.TestCase):
    def test_rank_follows_first_mention(self):
        self.assertEqual(analyze.mentions("Try QuickBooks or Acme for invoicing.", CONFIG), {"QuickBooks": 1, "Acme": 2})

    def test_whole_words_only(self):
        self.assertEqual(analyze.mentions("Acmeology is not a product.", CONFIG), {})

    def test_ambiguous_alias_needs_a_category_sentence(self):
        self.assertEqual(analyze.mentions("Catch the next wave of growth. Wave is great.", CONFIG), {})
        self.assertEqual(analyze.mentions("Wave handles invoicing for free.", CONFIG), {"Wave": 1})

    def test_ambiguous_alias_as_a_bolded_name(self):
        # Claude splits list items where it strips citations: "**Wave** - \n\nFree for freelancers"
        self.assertEqual(analyze.mentions("6. **Wave** - \n\nFree for freelancers.\n\n7. **QuickBooks** - \n\nThe default.", CONFIG),
                         {"Wave": 1, "QuickBooks": 2})
        self.assertEqual(analyze.mentions("**2. Wave Pro**: free for freelancers.", CONFIG), {"Wave": 1})
        self.assertEqual(analyze.mentions("Ride the **wave** of growth.", CONFIG), {})

    def test_citation_links_are_not_mentions(self):
        # ChatGPT prints an unrelated page title as a link on its own line before each item
        text = ("[QuickBooks Online review](https://example.com/qb?utm_source=openai)\n**Acme**  \n"
                "Acme sends reminders. ([acme.io](https://acme.io/?utm_source=openai))")
        self.assertEqual(analyze.mentions(text, CONFIG), {"Acme": 1})
        self.assertEqual(analyze.mentions("See https://quickbooks.intuit.com/x for Acme invoicing.", CONFIG), {"Acme": 1})
        self.assertEqual(analyze.mentions("Use [QuickBooks](https://quickbooks.intuit.com) for invoices.", CONFIG), {"QuickBooks": 1})

    def test_url_normalising(self):
        self.assertEqual(analyze.normalize_url("https://www.Acme.io/blog/?utm_source=openai#x"), "acme.io/blog")
        self.assertTrue(analyze.on_domain("https://app.acme.io/x", ["acme.io"]))
        self.assertFalse(analyze.on_domain("https://notacme.io/x", ["acme.io"]))
        self.assertFalse(analyze.on_domain("https://acme.io/x", [""]))  # a competitor without a known domain

    def test_gemini_sources_read_the_title(self):
        redirect = "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUZIYQ"
        self.assertEqual(analyze.source_urls([{"url": redirect, "title": "www.Acme.io"}, {"url": redirect, "title": "A blog post"},
                                              {"url": "https://g2.com/x?utm_source=openai"}]), ["acme.io", "g2.com/x"])


class Selection(unittest.TestCase):
    PANEL = [{"id": f"p{i:02d}", "group": g, "text": "x"} for i, g in
             enumerate(["problem", "problem", "category", "alternative", "vertical", "brand"], 1)]

    def ids(self, spec):
        return [p["id"] for p in track.select_prompts(self.PANEL, spec)]

    def test_prompts_by_id_group_and_range(self):
        self.assertEqual(self.ids("all"), ["p01", "p02", "p03", "p04", "p05", "p06"])
        self.assertEqual(self.ids(None), self.ids("all"))
        self.assertEqual(self.ids("p05,problem"), ["p01", "p02", "p05"])  # panel order kept
        self.assertEqual(self.ids(["p02-p04"]), ["p02", "p03", "p04"])
        for bad in ("p99", "pricing", "p40-p50"):
            with self.assertRaises(ValueError):
                self.ids(bad)

    def test_assistants_and_models(self):
        self.assertEqual(track.parse_assistants("chatgpt, Claude:claude-sonnet-5-5,chatgpt"),
                         ["chatgpt", "claude:claude-sonnet-5-5"])
        with self.assertRaises(ValueError):
            track.parse_assistants("copilot")

    def test_plan_uses_the_cadence_and_the_overrides(self):
        config = {**CONFIG, "serp_queries": ["q"], "cadence": {
            "daily_assistants": ["chatgpt"], "weekly_assistants": ["claude"],
            "daily_prompts": ["p01-p02"], "weekly_prompts": "all"}}
        daily = track.plan("daily", config, self.PANEL)
        self.assertEqual(([p["id"] for p in daily["prompts"]], daily["assistants"], daily["serp_queries"]),
                         (["p01", "p02"], ["chatgpt"], []))
        base = track.plan("baseline", config, self.PANEL)
        self.assertEqual((len(base["prompts"]), base["assistants"]), (6, ["chatgpt", "claude"]))
        one = track.plan("weekly", config, self.PANEL, 1, "category,vertical", "gemini")
        self.assertEqual(([p["id"] for p in one["prompts"]], one["assistants"]), (["p03"], ["gemini"]))

    def test_price_covers_the_default_limit(self):
        mentions = {"waterfall": {"max_cost_for_all": {"amount": "0.202"}}, "offers": [
            {"executable": True, "pricing": {"base": "0.2", "per_result": "0.002", "default_limit": 10}}]}
        self.assertEqual(track.price_of(mentions), 0.22)
        serp = {"waterfall": {"max_cost_for_all": {"amount": "0.007"}}, "offers": [
            {"executable": True, "pricing": {"base": "0.004", "per_result": "0", "default_limit": 10}},
            {"executable": True, "pricing": {"by_platform": {"*": {"base": "0.007"}}}}]}
        self.assertEqual(track.price_of(serp), 0.007)


class Untracked(unittest.TestCase):
    def test_bolded_names_not_tracked(self):
        texts = {"chatgpt": "**1. FreshBooks** - fast.\n**QuickBooks** - default.\n**Best free options**",
                 "claude:claude-sonnet-5-5": "Try **FreshBooks (free tier)** or **Acme Invoices**.",
                 "gemini": "**Zoho Invoice** and **Coverage**:"}
        answers = [analyze.answer_row("2026-10-28", a, PROMPTS["prompts"][0], "v1", run(t), CONFIG) for a, t in texts.items()]
        self.assertEqual(analyze.untracked_names(answers, CONFIG), [("FreshBooks", 2, ["chatgpt", "claude"])])


class Rows(unittest.TestCase):
    def test_answer_row(self):
        r = analyze.answer_row("2026-10-28", "chatgpt", PROMPTS["prompts"][1], "v1",
                               run("Acme beats QuickBooks for invoices.", ["https://acme.io/vs?utm_source=openai"]), CONFIG)
        self.assertTrue(r["brand_named"])
        self.assertEqual(r["brand_rank"], 1)
        self.assertEqual(r["competitors"], {"QuickBooks": 2})
        self.assertTrue(r["brand_cited"])
        self.assertEqual(r["sources"], ["acme.io/vs"])

    def test_failed_run_is_a_hole(self):
        r = analyze.answer_row("2026-10-28", "claude", PROMPTS["prompts"][0], "v1",
                               {"status": "failed", "error": {"code": "provider_error"}}, CONFIG)
        self.assertEqual(r["error"], "provider_error")
        self.assertNotIn("brand_named", r)


class Metrics(unittest.TestCase):
    def rows(self):
        p = PROMPTS["prompts"]
        return [
            analyze.answer_row("2026-10-28", "chatgpt", p[0], "v1", run("Use Acme for invoicing.", ["https://acme.io"]), CONFIG),
            analyze.answer_row("2026-10-28", "chatgpt", p[1], "v1", run("QuickBooks is the default for invoicing."), CONFIG),
            analyze.answer_row("2026-10-28", "chatgpt", p[2], "v1", run("Acme is fine."), CONFIG),  # brand group: ignored
            analyze.answer_row("2026-10-28", "gemini", p[0], "v1", run("Acme.", ["https://vertexaisearch.cloud.google.com/x"]), CONFIG),
            analyze.answer_row("2026-10-28", "gemini", p[1], "v1", {"status": "failed"}, CONFIG),
            analyze.answer_row("2026-10-28", "gemini", p[0], "v1", {"run_id": "run_g", "status": "succeeded", "result": {
                "answer": "Acme for invoicing.", "sources": [{"url": "https://vertexaisearch.cloud.google.com/y", "title": "acme.io"}]}},
                CONFIG) | {"date": "2026-10-27"},
        ]

    def test_scoreboard(self):
        s = analyze.scoreboard(self.rows(), "Acme")
        self.assertEqual(s["chatgpt"]["answered"], 2)
        self.assertEqual(s["chatgpt"]["named"], 1)
        self.assertEqual(s["chatgpt"]["mention_rate"], 0.5)
        self.assertEqual(s["chatgpt"]["citation_rate"], 0.5)
        self.assertEqual(s["chatgpt"]["share_of_voice"], 0.5)
        self.assertEqual(s["gemini"]["cited"], 1)  # the redirect titled acme.io counts, the untitled one does not
        self.assertEqual(s["gemini"]["citation_rate"], 0.5)
        self.assertEqual(s["gemini"]["holes"], 1)

    def test_movers(self):
        now, before = self.rows(), [dict(r, date="2026-10-20", brand_named=False) for r in self.rows()]
        moved = analyze.movers(now, before)
        self.assertIn(("chatgpt", "p01"), moved["appeared"])
        self.assertEqual(moved["vanished"], [])

    def test_reports_render(self):
        serp = analyze.serp_row("2026-10-28", "best invoicing app", {"status": "succeeded", "result": {
            "results": [{"position": 3, "url": "https://acme.io/"}], "ai_overview_present": True,
            "ai_overview_sources": ["https://www.reddit.com/r/smallbusiness/comments/1"]}}, CONFIG)
        self.assertEqual(serp["brand_position"], 3)
        text = analyze.weekly_report("2026-10-28", self.rows(), [serp], [], CONFIG, PROMPTS, 1.23)
        self.assertIn("| chatgpt | 2 | 0 | 1 | 50%", text)
        self.assertIn("reddit.com/r/smallbusiness/comments/1 | 1 | google ai overview | Reddit", text)
        self.assertNotIn(EM_DASH, text)


class ReportMode(unittest.TestCase):
    def test_report_mode_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "config.json").write_text(json.dumps(CONFIG))
            (root / "prompts.json").write_text(json.dumps(PROMPTS))
            (root / "data" / "answers").mkdir(parents=True)
            rows = Metrics().rows()
            (root / "data" / "answers" / "2026-10-28.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            out = subprocess.run([sys.executable, str(ROOT / "runner" / "track.py"), "report", "--date", "2026-10-28",
                                  "--root", d], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("Acme: AI search scoreboard", (root / "reports" / "latest.md").read_text())
            self.assertTrue((root / "data" / "summary.csv").read_text().startswith("date,assistant"))

    def test_template_config_calls_nothing(self):
        out = subprocess.run([sys.executable, str(ROOT / "runner" / "track.py"), "daily", "--root", str(ROOT)],
                             capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(out.returncode, 0)
        self.assertIn("template placeholders", out.stdout)


class Skill(unittest.TestCase):
    def test_frontmatter_and_house_rules(self):
        text = (ROOT / "skills" / "ai-search-growth" / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: ai-search-growth\n"))
        for f in list((ROOT / "skills").rglob("*.md")) + [ROOT / "README.md"]:
            self.assertNotIn(EM_DASH, f.read_text(), f)


if __name__ == "__main__":
    unittest.main()
