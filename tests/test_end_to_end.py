"""The runner end to end against a local stand-in for the RouterGrowth API, serving the response shapes the
real API returns (run receipts with billing and result, a done:false run to poll, a billed no_match)."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICES = {"chatgpt": "0.08", "perplexity": "0.02", "claude": "0.138", "gemini": "0.102"}


class FakeAPI(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *a):
        pass

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # polling a run that was still going
        self._send(200, {"run_id": self.path.split("/")[3].split("?")[0], "status": "succeeded", "done": True,
                         "billing": {"charged": "0.05"}, "result": {"answer": "Acme leads for invoicing.", "model": "m",
                                                                   "sources": [{"url": "https://acme.io/"}]}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeAPI.calls.append({"path": self.path, "body": body, "key": self.headers.get("Idempotency-Key")})
        if self.path == "/v1/inspect":
            cap = body["capability"]
            if cap == "aeo.answer":
                return self._send(200, {"offers": [{"executable": True, "pricing": {"by_platform": {
                    a: {"base": p, "per_result": "0"} for a, p in PRICES.items()}}}]})
            return self._send(200, {"waterfall": {"max_cost_for_all": {"amount": "0.007" if cap == "seo.serp" else "0.202"}}})
        cap, inp = body["capability"], body["input"]
        if cap == "aeo.answer":
            if inp["assistant"] == "claude" and "chasing" in inp["prompt"]:
                return self._send(202, {"run_id": "run_slow", "status": "running", "done": False})
            if inp["assistant"] == "gemini" and "QuickBooks" in inp["prompt"]:
                return self._send(502, {"run_id": "run_fail", "status": "failed", "done": True,
                                        "error": {"code": "provider_error", "message": "x"}})
            answer = "QuickBooks is common, Acme is newer." if "QuickBooks" in inp["prompt"] else "Try Acme for invoicing."
            return self._send(200, {"run_id": "run_" + inp["assistant"], "status": "succeeded", "done": True,
                                    "billing": {"charged": "0.01"},
                                    "result": {"answer": answer, "model": "m",
                                               "sources": [{"url": "https://www.reddit.com/r/smallbusiness/comments/1/?utm_source=openai"}]}})
        if cap == "seo.serp":
            return self._send(200, {"run_id": "run_serp", "status": "succeeded", "done": True, "billing": {"charged": "0.004"},
                                    "result": {"results": [{"position": 4, "url": "https://acme.io/pricing", "title": "Acme"}],
                                               "ai_overview_present": True, "ai_overview_sources": ["https://zapier.com/blog/best/"]}})
        if cap == "aeo.mentions":
            return self._send(404, {"run_id": "run_m", "status": "no_match", "done": True, "billing": {"charged": "0.2"},
                                    "error": {"code": "no_match", "message": "the empty result is the finding"}})
        self._send(400, {"error": {"code": "invalid_request"}})


CONFIG = {
    "brand": {"name": "Acme", "slug": "acme", "aliases": ["Acme"], "domains": ["acme.io"]},
    "competitors": [{"name": "QuickBooks", "aliases": ["QuickBooks"], "domain": "quickbooks.intuit.com"}],
    "category_terms": ["invoice", "invoicing"],
    "market": {"aeo_location": "GB", "serp_location": "United Kingdom", "language": "en"},
    "cadence": {"daily_assistants": ["chatgpt", "perplexity"], "weekly_assistants": ["claude", "gemini"]},
    "budgets": {"daily_usd": 1, "weekly_usd": 2, "baseline_usd": 3},
    "serp_queries": ["best invoicing app"],
}
PROMPTS = {"version": "v1", "prompts": [
    {"id": "p01", "group": "problem", "text": "How do I stop chasing unpaid invoices?"},
    {"id": "p02", "group": "alternative", "text": "What are the best QuickBooks alternatives?"},
]}


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeAPI)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def track(self, root, *args, config=CONFIG):
        (root / "config.json").write_text(json.dumps(config))
        (root / "prompts.json").write_text(json.dumps(PROMPTS))
        env = {**os.environ, "ROUTERGROWTH_API_KEY": "rg_test_x", "ROUTERGROWTH_API_URL": self.url}
        env.pop("GITHUB_ACTIONS", None)
        return subprocess.run([sys.executable, str(ROOT / "runner" / "track.py"), *args, "--root", str(root),
                               "--date", "2026-10-26"], capture_output=True, text=True, env=env, timeout=60)

    def test_weekly(self):
        FakeAPI.calls = []
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = self.track(root, "weekly")
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            runs = [c for c in FakeAPI.calls if c["path"] == "/v1/run"]
            gemini = [c["body"]["input"] for c in runs if c["body"]["input"].get("assistant") == "gemini"]
            self.assertTrue(gemini and all("location" not in i for i in gemini))  # Gemini refuses a location
            claude = [c["body"]["input"] for c in runs if c["body"]["input"].get("assistant") == "claude"]
            self.assertTrue(all(i["location"] == "GB" for i in claude))
            self.assertIn("acme-aeo-2026-10-26-claude-p01", [c["key"] for c in runs])
            self.assertEqual({c["body"]["routing"]["max_cost"] for c in runs if c["body"]["capability"] == "aeo.answer"},
                             {"0.138000", "0.102000"})
            rows = [json.loads(x) for x in (root / "data/answers/2026-10-26.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 4)
            polled = next(r for r in rows if r["id"] == "2026-10-26|claude|p01")
            self.assertTrue(polled["brand_named"] and polled["brand_cited"])  # came back through GET /v1/runs
            hole = next(r for r in rows if r["id"] == "2026-10-26|gemini|p02")
            self.assertEqual(hole["error"], "provider_error")
            mention = json.loads((root / "data/mentions/2026-10-26.jsonl").read_text().splitlines()[0])
            self.assertEqual((mention["status"], mention["total"]), ("no_match", 0))
            receipt = json.loads((root / "data/runs/2026-10-26-weekly.json").read_text())
            self.assertEqual(receipt["answer_holes"], 1)
            report = (root / "reports/weekly/2026-10-26.md").read_text()
            self.assertIn("| best invoicing app | yes | no | 4 |", report)
            self.assertIn("zapier.com/blog/best | 1 | google ai overview", report)
            self.assertTrue((root / "reports/latest.md").exists())

    def test_rerun_same_day_replays_by_id(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.track(root, "daily")
            self.track(root, "daily")
            rows = (root / "data/answers/2026-10-26.jsonl").read_text().splitlines()
            self.assertEqual(len(rows), 4)

    def test_budget_stops_before_any_run(self):
        FakeAPI.calls = []
        with tempfile.TemporaryDirectory() as d:
            out = self.track(Path(d), "weekly", config={**CONFIG, "budgets": {"weekly_usd": 0.1}})
            self.assertEqual(out.returncode, 1)
            self.assertIn("above budgets.weekly_usd", out.stdout)
            self.assertFalse([c for c in FakeAPI.calls if c["path"] == "/v1/run"])


if __name__ == "__main__":
    unittest.main()
