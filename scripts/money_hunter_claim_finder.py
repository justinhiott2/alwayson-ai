#!/usr/bin/env python3
"""Money Hunter Claim Finder: official-source directory and public-page monitor.

This bot discovers no personal entitlement. It checks public official resource
pages for availability and publishes a structured directory for the PWA.
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("money-hunter/reports/claim-finder.json")
SOURCES = [
    {"category":"State unclaimed property","name":"South Carolina Unclaimed Property","priority":"South Carolina first","url":"https://southcarolina.findyourunclaimedproperty.com/","how":"Search your current and former legal names and prior states of residence."},
    {"category":"State unclaimed property","name":"NAUPA official state directory","priority":"Nationwide","url":"https://unclaimed.org/search/","how":"Open each state's official program; search every state where you lived, worked, or did business."},
    {"category":"State unclaimed property","name":"MissingMoney nationwide search","priority":"Nationwide","url":"https://www.missingmoney.com/","how":"Search participating state databases, then complete any claim on the official state portal."},
    {"category":"Federal money directory","name":"USA.gov unclaimed money guide","priority":"Nationwide","url":"https://www.usa.gov/unclaimed-money","how":"Use its category-by-category links; there is no single federal database."},
    {"category":"Federal unclaimed assets","name":"U.S. Treasury unclaimed assets guidance","priority":"Nationwide","url":"https://fiscal.treasury.gov/about-us/unclaimed-assets","how":"Identify the agency and payment type; contact the responsible agency."},
    {"category":"Unpaid wages","name":"U.S. Department of Labor back wages","priority":"Nationwide","url":"https://www.dol.gov/agencies/whd/wow","how":"Search the Wage and Hour Division Workers Owed Wages tool for employers and workers."},
    {"category":"Pensions and retirement","name":"Pension Benefit Guaranty Corporation missing participants","priority":"Nationwide","url":"https://www.pbgc.gov/workers-retirees/find-unclaimed-retirement-benefits","how":"Search for certain benefits from terminated private-sector defined-benefit plans."},
    {"category":"Bank and credit union failures","name":"FDIC unclaimed deposits","priority":"Nationwide","url":"https://closedbanks.fdic.gov/funds/","how":"Check whether a failed FDIC-insured bank held an unpaid insured deposit."},
    {"category":"Bank and credit union failures","name":"NCUA unclaimed deposits and shares","priority":"Nationwide","url":"https://ncua.gov/support-services/share-insurance-fund/unclaimed-deposits","how":"Check accounts at liquidated federally insured credit unions."},
    {"category":"Bankruptcy funds","name":"U.S. Courts Unclaimed Funds Locator","priority":"Nationwide","url":"https://ucf.uscourts.gov/","how":"Search court-held bankruptcy funds; court procedures and proof of entitlement apply."},
    {"category":"Mortgage and insurance refunds","name":"HUD/FHA refunds","priority":"Nationwide","url":"https://www.hud.gov/program_offices/housing/sfh/fharesourcecenter","how":"Use HUD's official FHA resources if you had an FHA-insured mortgage; confirm current refund lookup instructions."},
    {"category":"Veterans insurance","name":"VA unclaimed insurance funds","priority":"Nationwide","url":"https://insurance.va.gov/","how":"Relevant only to eligible current or former policyholders and beneficiaries."},
    {"category":"Tax refunds","name":"IRS refund status and missing refund help","priority":"Nationwide","url":"https://www.irs.gov/refunds","how":"Use only for a tax return/refund you filed or reasonably expect; the bot cannot see IRS private records."},
    {"category":"Investment enforcement distributions","name":"SEC claims and distributions","priority":"Nationwide","url":"https://www.sec.gov/enforcement-litigation/claims-and-distributions","how":"Check whether an SEC enforcement distribution relates to an investment you held."},
    {"category":"Railroad retirement","name":"U.S. Railroad Retirement Board","priority":"Nationwide","url":"https://www.rrb.gov/","how":"Relevant to qualifying railroad workers and eligible family members."},
    {"category":"SC county tax-sale and foreclosure surplus","name":"South Carolina county offices and court records","priority":"South Carolina first","url":"https://www.sccourts.org/","how":"Check county treasurer/tax collector and clerk of court records. A surplus listing alone does not prove you are entitled."},
    {"category":"SC public contract opportunities","name":"South Carolina procurement","priority":"South Carolina first","url":"https://procurement.sc.gov/doing-biz","how":"Potential earnings, not money already owed. Bid/contract rules and performance costs apply."},
]

def probe(source):
    req = urllib.request.Request(source["url"], headers={"User-Agent":"MoneyHunterClaimFinder/1.0"}, method="GET")
    result = dict(source)
    try:
        with urllib.request.urlopen(req, timeout=18) as response:
            result.update({"page_status":"reachable","http_status":response.status})
    except Exception as exc:
        result.update({"page_status":"check_failed","http_status":getattr(exc,"code",None),"check_note":str(exc)[:180]})
    return result

def main():
    now = datetime.now(timezone.utc).isoformat()
    results = [probe(s) for s in SOURCES]
    payload = {
        "schema_version": 1,
        "generated_at": now,
        "bot": "Money Hunter Claim Finder",
        "scope": "Official-source directory and public-page reachability checks only; no personal claimant database access or entitlement verification.",
        "totals": {
            "sources_listed": len(results),
            "pages_reachable": sum(x["page_status"] == "reachable" for x in results),
            "pages_check_failed": sum(x["page_status"] != "reachable" for x in results),
            "personal_claims_verified": 0,
            "claims_submitted": 0,
            "payments_received": 0
        },
        "important": [
            "Searching is generally free on official government sites.",
            "No government-wide database contains every type of unclaimed money.",
            "A possible name match is only a lead; verify address, ownership, dates, and agency requirements.",
            "Never pay an upfront fee to search an official state unclaimed-property database.",
            "The bot never submits claims, signs declarations, contacts agencies, or handles payments."
        ],
        "sources": results
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Published {len(results)} sources; {payload['totals']['pages_reachable']} pages reachable.")

if __name__ == "__main__":
    main()
