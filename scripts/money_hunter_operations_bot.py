#!/usr/bin/env python3
"""Money Hunter Operations Bot: safe production health checks; never charges or changes live billing."""
from __future__ import annotations
import json, os, pathlib, sys, urllib.request, urllib.error
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "money-hunter" / "reports" / "operations.json"
APP_URL = os.getenv("MONEY_HUNTER_APP_URL", "https://justinhiott2.github.io/alwayson-ai/money-hunter/")
HEALTH_URL = os.getenv("MONEY_HUNTER_BILLING_HEALTH_URL", "https://unjulxbkxnscwkxlmtbd.supabase.co/functions/v1/billing-health")
UA = "MoneyHunterOperationsBot/1.0 (safe health checks)"

def get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read(1_000_000).decode("utf-8", "replace")
        return response.status, body, response.headers.get("content-type", "")

def check(name, ok, detail, critical=True):
    return {"name": name, "status": "passed" if ok else ("blocked" if critical else "attention"), "detail": detail}

def main():
    checks = []
    app_html = ""
    try:
        code, app_html, _ = get(APP_URL)
        checks.append(check("Published Money Hunter page", 200 <= code < 400, f"HTTP {code}: {APP_URL}"))
    except Exception as exc:
        checks.append(check("Published Money Hunter page", False, f"{type(exc).__name__}: {str(exc)[:220]}"))

    for name, url in [
        ("Cloud account integration script", APP_URL + "cloud.js"),
        ("Research report feed", APP_URL + "agents/latest.json"),
    ]:
        try:
            code, body, _ = get(url)
            ok = 200 <= code < 400
            checks.append(check(name, ok, f"HTTP {code}; {len(body)} bytes"))
        except Exception as exc:
            checks.append(check(name, False, f"{type(exc).__name__}: {str(exc)[:220]}"))

    health = {}
    try:
        code, body, _ = get(HEALTH_URL)
        health = json.loads(body)
        checks.append(check("Supabase billing health endpoint", code == 200 and health.get("backend") == "online",
                            f"HTTP {code}; backend={health.get('backend', 'unknown')}"))
        checks.append(check("PayPal credentials configured", bool(health.get("credentials_configured")),
                            "Configured" if health.get("credentials_configured") else "Missing PayPal client ID/secret in server secrets"))
        checks.append(check("PayPal webhook configured", bool(health.get("webhook_configured")),
                            "Configured" if health.get("webhook_configured") else "PayPal webhook ID is missing"))
        checks.append(check("PayPal subscription plan configured", bool(health.get("subscription_plan_configured")),
                            "Configured" if health.get("subscription_plan_configured") else "Subscription product/plan has not been provisioned"))
        checks.append(check("Database ready", bool(health.get("database_ready")),
                            "Ready" if health.get("database_ready") else "Billing database/server configuration is not ready"))
        env = health.get("environment", "unknown")
        sandbox_ready = bool(health.get("sandbox_test_ready"))
        checks.append(check("Sandbox checkout prerequisites", sandbox_ready,
                            f"environment={env}; sandbox_test_ready={sandbox_ready}"))
        live_enabled = bool(health.get("live_checkout_enabled"))
        checks.append(check("Live charges remain safely gated", not live_enabled,
                            "Live checkout is disabled pending verified end-to-end tests" if not live_enabled else "Live checkout reports enabled; bot will not change this setting",
                            critical=False))
    except Exception as exc:
        checks.append(check("Supabase billing health endpoint", False, f"{type(exc).__name__}: {str(exc)[:220]}"))

    blocked = [c for c in checks if c["status"] == "blocked"]
    attention = [c for c in checks if c["status"] == "attention"]
    report = {
        "bot": "Money Hunter Operations Bot",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if blocked else ("attention" if attention else "healthy"),
        "summary": {"checks": len(checks), "passed": sum(c["status"] == "passed" for c in checks),
                    "blocked": len(blocked), "attention": len(attention)},
        "checks": checks,
        "billing": {k: health.get(k) for k in [
            "provider", "environment", "credentials_configured", "webhook_configured",
            "setup_token_configured", "database_ready", "subscription_plan_configured",
            "sandbox_test_ready", "live_checkout_enabled", "live_checkout_locked", "next_step"
        ] if k in health},
        "remaining_manual_gates": [
            "A human must complete PayPal sandbox payer approval; an unattended bot cannot approve a real payer's subscription.",
            "Verify PayPal subscription-created/activated and payment webhook delivery against the sandbox event log.",
            "Verify cancellation in the PayPal sandbox and confirm the membership status updates in Supabase.",
            "Only after all tests pass may the owner explicitly authorize live checkout. This bot never enables live charges."
        ],
        "safety": "Read-only production checks and synthetic browser tests only. No live payment, subscription, claim, bid, contract, or customer-data action is performed."
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if blocked else 0

if __name__ == "__main__":
    sys.exit(main())
