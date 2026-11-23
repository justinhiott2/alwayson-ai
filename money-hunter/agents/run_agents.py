#!/usr/bin/env python3
"""Free, scheduled public-source agents for Money Hunter.
No secrets, paid APIs, private-record access, identity verification, or legal authority.
Each agent reports evidence and next actions; it never claims ownership or submits claims.
"""
import json, datetime, urllib.request, urllib.parse, urllib.error, pathlib, re, time

ROOT = pathlib.Path("money-hunter/agents/reports")
ROOT.mkdir(parents=True, exist_ok=True)
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
UA = "MoneyHunterFreeAgents/1.0 (public information discovery; contact: repository owner)"
RESULTS = []

def record(agent, kind, title, url, summary, status="lead", evidence=None, next_action=None):
    RESULTS.append({
        "agent": agent, "type": kind, "title": title, "url": url,
        "summary": summary, "status": status, "evidence": evidence or {},
        "next_action": next_action or "Open the official source and independently verify eligibility, ownership, deadlines and terms."
    })

def get_json(url, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        "User-Agent": UA, "Accept": "application/json",
        "Content-Type": "application/json"
    })
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read(5_000_000).decode("utf-8", "replace"))

def source_link_agent():
    agent = "Money Discovery"
    sources = [
      ("USA.gov unclaimed money guide","https://www.usa.gov/unclaimed-money","Official guide to federal and state unclaimed money."),
      ("NAUPA state directory","https://unclaimed.org/search/","Directory of official state unclaimed-property programs."),
      ("MissingMoney","https://www.missingmoney.com/","Participating-state unclaimed-property search; coverage varies."),
      ("US Department of Labor wage search","https://webapps.dol.gov/WOW/","Search tool for wages held by the Department of Labor."),
      ("PBGC missing pensions","https://www.pbgc.gov/workers-retirees/find-unclaimed-retirement-benefits","Pension benefit search."),
      ("FDIC unclaimed funds","https://closedbanks.fdic.gov/funds/","Unclaimed deposits from failed banks."),
      ("NCUA liquidations","https://ncua.gov/support-services/conservatorships-liquidations","Credit union liquidation and asset information."),
      ("Treasury savings bonds","https://www.treasurydirect.gov/savings-bonds/","Official savings bond information and search guidance."),
      ("SEC distributions","https://www.sec.gov/enforce/investor-alerts-and-bulletins/investor-alert-unclaimed-funds","Investor distributions and unclaimed funds guidance."),
      ("VA life insurance","https://insurance.va.gov/","VA insurance information."),
      ("US Courts unclaimed funds","https://ucf.uscourts.gov/","Bankruptcy court unclaimed funds search.")
    ]
    for title,url,summary in sources:
        status="source_link"
        try:
            req=urllib.request.Request(url,headers={"User-Agent":UA},method="HEAD")
            with urllib.request.urlopen(req,timeout=15) as r:
                status="reachable" if r.status < 400 else "restricted"
            evidence={"http_status":r.status}
        except urllib.error.HTTPError as e:
            status="restricted" if e.code in (401,403,405,429) else "unreachable"
            evidence={"http_status":e.code,"note":"Automated request blocked or failed; manual official-site check may still work."}
        except Exception as e:
            evidence={"error":type(e).__name__}
            status="check_manually"
        record(agent,"official_source",title,url,summary,status,evidence,
               "Search the portal manually using your legal name and prior addresses; do not send sensitive identifiers to this app.")
        time.sleep(.15)

def federal_register_agent():
    agent="Land & Public Notice"
    searches=[
      ("Surplus real property","surplus real property disposal"),
      ("Public land sale notices","public land sale"),
      ("Tax and property notices","tax sale property notice"),
      ("Government property disposition","government property disposal")
    ]
    for label,term in searches:
        url="https://www.federalregister.gov/api/v1/documents.json?"+urllib.parse.urlencode({
            "per_page":10,"order":"newest","conditions[term]":term,
            "fields[]":["title","publication_date","html_url","type","agencies"]
        },doseq=True)
        try:
            data=get_json(url)
            for d in data.get("results",[]):
                record(agent,"federal_notice",d.get("title","Federal Register notice"),d.get("html_url",""),
                    "Federal Register result for: "+term,"unverified_notice",
                    {"publication_date":d.get("publication_date"),"document_type":d.get("type"),"agencies":d.get("agencies",[])},
                    "Read the notice. Confirm whether it is an active sale or opportunity and verify deadlines and eligibility with the issuing agency.")
        except Exception as e:
            record(agent,"source_error",label,url,"Public API request did not complete.","error",{"error":type(e).__name__})
        time.sleep(.2)

def contracts_agent():
    agent="Contract & Award Research"
    url="https://api.usaspending.gov/api/v2/search/spending_by_award/"
    queries=[
      ("South Carolina recent federal contract awards",{"award_type_codes":["A","B","C","D"],"place_of_performance_locations":[{"country":"USA","state":"SC"}]}),
      ("Nationwide recent federal contract awards",{"award_type_codes":["A","B","C","D"]})
    ]
    for label,filters in queries:
        body={"filters":filters,"fields":["Award ID","Recipient Name","Award Amount","Description","Start Date","End Date","Awarding Agency","Place of Performance State Code"],"page":1,"limit":10,"sort":"Award Amount","order":"desc"}
        try:
            data=get_json(url,"POST",body)
            for row in data.get("results",[]):
                record(agent,"federal_award",str(row.get("Recipient Name") or "Federal award")+" — "+str(row.get("Description") or "Award record"),
                    "https://www.usaspending.gov/search", "Award-history lead from USAspending; an award is not an open bid or assignable contract.","award_record",
                    {"award_id":row.get("Award ID"),"amount":row.get("Award Amount"),"start":row.get("Start Date"),"end":row.get("End Date"),"agency":row.get("Awarding Agency"),"state":row.get("Place of Performance State Code")},
                    "Use the award record to identify agencies and incumbents. Find the actual solicitation or subcontract route; do not represent an awarded contract as available for transfer.")
        except Exception as e:
            record(agent,"source_error",label,url,"USAspending public API request failed.","error",{"error":type(e).__name__})
        time.sleep(.2)
    sam="https://sam.gov/content/opportunities"
    record(agent,"procurement_portal","SAM.gov contract opportunities",sam,
        "Official federal opportunity portal. Automated API searching requires an approved API key; this free agent supplies the portal link, not fabricated live bid results.",
        "manual_search",{"api_key_required_for_api":True},
        "Search active opportunities by South Carolina location, NAICS code and set-aside; review solicitation and eligibility.")

def state_land_agent():
    agent="State & County Land Discovery"
    portals=[
      ("South Carolina State Surplus Property","https://admin.sc.gov/office-state-surplus-property","Official state surplus property program."),
      ("South Carolina Treasurer","https://treasurer.sc.gov/","State financial and unclaimed-property information; not a land-sale list."),
      ("South Carolina county tax sale directory search","https://www.google.com/search?q=site%3Asc.gov+county+tax+sale+real+property+South+Carolina","Searches public county-government pages for tax-sale notices."),
      ("Federal real property disposal information","https://disposal.gsa.gov/","Federal property disposal information.")
    ]
    for title,url,summary in portals:
        record(agent,"land_source",title,url,summary,"source_link",{},
          "Confirm the parcel is actually offered for sale. Obtain parcel ID, title search, tax status, access, zoning, utilities and redemption information before any bid or payment.")

def ownership_agent():
    record("Ownership & Evidence","process_template","Ownership evidence workflow","https://www.usa.gov/","Checklist only: identify the issuing authority, official record, claimant relationship, required proof, filing method and written confirmation.","preparation_only",
      {"automated_ownership_determination":False},
      "The agent cannot establish title or beneficial ownership. Obtain the deed, agency determination, court order or other legally recognized evidence from the competent authority.")
    record("Ownership & Evidence","process_template","Contract assignment permission workflow","https://www.sba.gov/business-guide/manage-your-business","Check contract language, consent, licensing, notice, disclosure, liability and payment trigger before any transfer.","preparation_only",
      {"automated_assignment_authority":False},
      "Get written consent where required and legal review before signing or assigning.")

def claims_agent():
    record("Claims & Documents","document_workflow","Claim packet preparation checklist","https://www.usa.gov/unclaimed-money","Prepare a packet checklist from the agency's own instructions; keep sensitive identity documents off this public app.","preparation_only",
      {"can_sign_or_submit":False},
      "You must review, sign and submit through the official agency channel. Never pay a finder fee to claim your own property unless the official rules expressly allow it.")

def revenue_agent():
    record("Revenue & Accounting","ledger_workflow","Revenue ledger initialized","./revenue-ledger.json","Only money actually received and documented should count as revenue. Leads, asking prices and award amounts are not earnings.","tracking_only",
      {"verified_receipts_recorded":0,"currency":"USD"},
      "Add receipts only after funds clear; retain invoice, payer, date, amount, fees and proof of deposit.")

def main():
    agents=[source_link_agent,federal_register_agent,contracts_agent,state_land_agent,ownership_agent,claims_agent,revenue_agent]
    for fn in agents:
        try: fn()
        except Exception as e:
            record(fn.__name__,"agent_error",fn.__name__,"","Agent stopped unexpectedly.","error",{"error":type(e).__name__})
    report={
      "generated_at":NOW,
      "mode":"free_public_source_autonomous_scan",
      "important":"This run searches public APIs where available and refreshes official source links. It does not perform personal claimant searches, prove ownership, submit claims, bid, sign contracts, or confirm income.",
      "agents":[fn.__name__ for fn in agents],
      "counts":{"total":len(RESULTS),"errors":sum(1 for x in RESULTS if x["status"]=="error")},
      "results":RESULTS
    }
    (ROOT/"latest.json").write_text(json.dumps(report,indent=2)+"\n")
    # append immutable dated report for audit trail
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    (ROOT/(stamp+".json")).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["counts"]))
if __name__=="__main__": main()
