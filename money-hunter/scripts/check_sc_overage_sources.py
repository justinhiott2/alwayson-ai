#!/usr/bin/env python3
"""Check availability of curated official South Carolina overage and court sources.
This is a link-health check only; it does not crawl claimant data or court dockets.
"""
from __future__ import annotations
import datetime as dt
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path("money-hunter/data/excess-proceeds")
REGISTRY = BASE / "south-carolina-county-sources.json"
OUT = BASE / "south-carolina-source-status.json"
UA = "MoneyHunterAI-SC-official-source-health/1.0"

def main():
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    targets = []
    for county in data["counties"]:
        for key in ("tax_office_url", "sale_announcement_url", "sale_information_url",
                    "faq_url", "overage_information_url", "public_overage_register_url",
                    "overage_claim_form_url"):
            url = county.get(key)
            if url and all(x["url"] != url for x in targets):
                targets.append({"county": county["county"], "kind": key, "url": url})
    for item in (data["legal_baseline"], data["court_index"]):
        if item.get("url"):
            targets.append({"county": "Statewide", "kind": "official_reference", "url": item["url"]})
        if item.get("guide_url"):
            targets.append({"county": "Statewide", "kind": "official_user_guide", "url": item["guide_url"]})
    results = []
    for target in targets:
        status, code, detail = "unreachable", None, ""
        try:
            req = urllib.request.Request(target["url"], headers={"User-Agent": UA, "Range": "bytes=0-1023"})
            with urllib.request.urlopen(req, timeout=25) as response:
                code = response.status
                status = "reachable" if 200 <= code < 400 else "restricted"
        except urllib.error.HTTPError as e:
            code = e.code
            status = "reachable" if 200 <= code < 400 else ("restricted" if code in (401,403,405,429) else "unreachable")
            detail = "Host refused or rate-limited automated link check; open manually."
        except Exception as e:
            detail = type(e).__name__ + ": " + str(e)[:180]
        results.append({**target, "status": status, "http_status": code, "detail": detail})
    payload = {
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "check_type": "official_source_link_health_only_not_docket_search",
        "county_count": len(data["counties"]),
        "source_count": len(results),
        "reachable": sum(x["status"] == "reachable" for x in results),
        "restricted": sum(x["status"] == "restricted" for x in results),
        "unreachable": sum(x["status"] == "unreachable" for x in results),
        "docket_checking": "manual_case_lookup_required_no_supported_public_api",
        "important": data["limits"],
        "sources": results,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(results)} official SC source links; wrote {OUT}")
    print(f"Reachable: {payload['reachable']}; restricted: {payload['restricted']}; unreachable: {payload['unreachable']}")

if __name__ == "__main__":
    main()
