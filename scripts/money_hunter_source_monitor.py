#!/usr/bin/env python3
"""Money Hunter official-source monitor.

This bot checks whether selected official public pages respond. It does NOT
search claimant databases, establish ownership, identify money owed, or qualify
real-estate/contract deals.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT = Path("money-hunter/reports/latest.json")
SOURCES = [
    ("South Carolina Unclaimed Property", "https://southcarolina.findyourunclaimedproperty.com/"),
    ("MissingMoney nationwide search", "https://www.missingmoney.com/"),
    ("SC state surplus real estate", "https://admin.sc.gov/services/real-estate"),
    ("SC procurement opportunities", "https://procurement.sc.gov/doing-biz"),
    ("USA.gov unclaimed money guide", "https://www.usa.gov/unclaimed-money"),
]

def check(label, url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "MoneyHunterSourceMonitor/1.0 (+public-page-status-check)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return {
                "label": label,
                "url": url,
                "status": "reachable",
                "http_status": response.status,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as exc:
        code = getattr(exc, "code", None)
        return {
            "label": label,
            "url": url,
            "status": "check_failed",
            "http_status": code,
            "note": str(exc)[:240],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

def main():
    if not REPORT.exists():
        raise SystemExit(f"Missing report file: {REPORT}")
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    checks = [check(label, url) for label, url in SOURCES]
    now = datetime.now(timezone.utc)
    reachable = sum(item["status"] == "reachable" for item in checks)
    data["source_monitor"] = {
        "checked_at": now.isoformat(),
        "scope": "HTTP reachability only; not a database search or verification of a personal claim/deal",
        "reachable": reachable,
        "total": len(checks),
        "checks": checks,
    }
    data["monitor_updated_at"] = now.isoformat()
    base_summary = data.get("summary", "").split(" Automated source monitor:", 1)[0]
    data["summary"] = (
        base_summary
        + f" Automated source monitor: {reachable}/{len(checks)} official public pages responded "
          "to an HTTP check. This does not mean records were searched or claims/deals were verified."
    )
    REPORT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated {REPORT}: {reachable}/{len(checks)} official pages reachable.")

if __name__ == "__main__":
    main()
