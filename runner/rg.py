"""Minimal RouterGrowth REST client (standard library only).

POST /v1/run executes a capability and waits up to wait_seconds; a run still
going answers done:false and is polled at GET /v1/runs/{id}?wait=. Retries
reuse the Idempotency-Key, so a retried call is never billed twice.
"""

import json
import re
import time
import urllib.error
import urllib.request

RETRY_CODES = {"rate_limited", "provider_rate_limited", "provider_error", "provider_timeout", "internal_error"}
STOP_CODES = {"insufficient_balance", "budget_exceeded", "cost_limit_exceeded", "invalid_api_key", "forbidden"}


class Client:
    def __init__(self, key: str, base: str = "https://api.routergrowth.com", timeout: int = 150):
        self.key, self.base, self.timeout = key, base.rstrip("/"), timeout

    def _request(self, method: str, path: str, body: dict | None = None, headers: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self.key}", "Content-Type": "application/json",
            "User-Agent": "ai-search-growth-runner/0.1", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read() or b"{}")
            except ValueError:
                payload = {}
            payload.setdefault("error", {"code": f"http_{e.code}", "message": str(e)})
            return payload
        except (urllib.error.URLError, TimeoutError) as e:
            return {"error": {"code": "network_error", "message": str(e)}}

    def inspect(self, capability: str) -> dict:
        return self._request("POST", "/v1/inspect", {"capability": capability})

    def wallet(self) -> dict:
        return self._request("GET", "/v1/wallet")

    def run(self, capability: str, input: dict, max_cost: str, idempotency_key: str, attempts: int = 4) -> dict:
        body = {"capability": capability, "input": input, "routing": {"max_cost": max_cost}, "wait_seconds": 60}
        idempotency_key = re.sub(r"[^A-Za-z0-9._-]+", "-", idempotency_key)[:200]  # header-safe, also for non-ASCII queries
        out: dict = {}
        for attempt in range(attempts):
            out = self._request("POST", "/v1/run", body, {"Idempotency-Key": idempotency_key})
            code = (out.get("error") or {}).get("code")
            # A run that exists has finished (a replay returns the same run): retry only requests that never became one.
            if (code in RETRY_CODES or code == "network_error") and not out.get("run_id"):
                time.sleep(2 ** attempt * 3)
                continue
            break
        polls = 0
        while out.get("run_id") and out.get("done") is False and polls < 6:
            out = self._request("GET", f"/v1/runs/{out['run_id']}?wait=60")
            polls += 1
        return out


def error_code(run: dict) -> str | None:
    return (run.get("error") or {}).get("code")


def charged(run: dict) -> float:
    try:
        return float((run.get("billing") or {}).get("charged") or 0)
    except (TypeError, ValueError):
        return 0.0
