#!/usr/bin/env python3
"""Scan official Davidson County motion-response docket PDFs for excess-proceeds motions.
Records case-level docket mentions only; never stores party names or claimant contact data.
A motion listing is not an order, proof of parcel match, or proof of payment.
"""
from __future__ import annotations
import datetime as dt
import json
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from pypdf import PdfReader

INDEX_URL = "https://chanceryclerkandmaster.nashville.gov/cases/motion-dockets/"
REGISTER = Path("money-hunter/data/excess-proceeds/davidson-county.json")
OUT = Path("money-hunter/data/excess-proceeds/davidson-docket-status.json")
UA = "MoneyHunterAI-public-motion-docket-monitor/1.0"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href", "")
            label = " ".join(dict(attrs).get("class", []))
            if href:
                self.items.append(href)

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=35) as response:
        return response.read()

def pdf_links(page: bytes):
    parser = Links()
    parser.feed(page.decode("utf-8", "replace"))
    found = []
    for href in parser.items:
        low = href.lower()
        if ".pdf" not in low or "docket" not in low:
            continue
        if href.startswith("/"):
            href = "https://chanceryclerkandmaster.nashville.gov" + href
        elif href.startswith("//"):
            href = "https:" + href
        if href.startswith("https://chanceryclerkandmaster.nashville.gov/"):
            if href not in found:
                found.append(href)
    return found

def docket_date(url: str):
    m = re.search(r"/(\d{1,2})[._-](\d{1,2})[._-](\d{2,4})[^/]*\.pdf", url, re.I)
    if not m:
        return None
    month, day, year = map(int, m.groups())
    if year < 100:
        year += 2000
    try:
        return dt.date(year, month, day).isoformat()
    except ValueError:
        return None

def extract_events(pdf_bytes: bytes, url: str, case_numbers: set[str]):
    reader = PdfReader(BytesIO(pdf_bytes))
    text = " ".join((p.extract_text() or "") for p in reader.pages)
    text = re.sub(r"\s+", " ", text)
    docket_day = docket_date(url)
    events = []
    for case in sorted(case_numbers):
        for match in re.finditer(re.escape(case), text, re.I):
            start = max(0, match.start() - 450)
            end = min(len(text), match.end() + 1100)
            context = text[start:end]
            phrase = None
            for candidate in ("Motion to Claim Excess Sale Proceeds",
                              "Motion to Claim Excess Proceeds",
                              "Claim for Excess Proceeds",
                              "Motion to Claim Excess Sale"):
                if re.search(re.escape(candidate), context, re.I):
                    phrase = candidate
                    break
            if not phrase:
                continue
            before_phrase = context[:context.lower().find(phrase.lower())]
            dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", before_phrase)
            filed = dates[-1] if dates else None
            events.append({
                "case_number": case,
                "docket_date": docket_day,
                "motion_filed_date": filed,
                "event_type": "excess_proceeds_motion_listed",
                "event_label": phrase,
                "source_pdf_url": url,
                "parcel_specific": False,
                "result_status": "motion_listed_outcome_not_verified",
            })
            break
    return events, len(reader.pages)

def main():
    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    case_numbers = {r["case_number"] for r in register.get("records", []) if r.get("case_number")}
    checked_at = dt.datetime.now(dt.timezone.utc).isoformat()
    errors = []
    try:
        page = fetch(INDEX_URL)
        urls = pdf_links(page)
    except Exception as e:
        urls = []
        errors.append(type(e).__name__ + ": " + str(e)[:180])
    events, checked = [], []
    for url in urls:
        try:
            raw = fetch(url)
            matches, pages = extract_events(raw, url, case_numbers)
            checked.append({"url": url, "docket_date": docket_date(url), "pages": pages, "matched_case_events": len(matches)})
            events.extend(matches)
        except Exception as e:
            errors.append(url + " — " + type(e).__name__ + ": " + str(e)[:140])
    unique = {}
    for event in events:
        key = (event["case_number"], event["source_pdf_url"], event["event_label"])
        unique[key] = event
    payload = {
        "checked_at": checked_at,
        "source_index_url": INDEX_URL,
        "check_type": "official_published_motion_docket_pdf_scan_case_level_only",
        "pdfs_checked": len(checked),
        "pdfs": checked,
        "event_count": len(unique),
        "events": list(unique.values()),
        "errors": errors,
        "important": "A motion appearing on a published response docket only establishes that a motion was listed for a case. It does not establish the motion was heard, granted, denied, withdrawn, parcel-specific, or paid. The tax-sale case may cover many parcels. Verify the signed order and custodian balance directly.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(checked)} official docket PDFs; found {len(unique)} case-level excess-proceeds motion entries; errors: {len(errors)}")

if __name__ == "__main__":
    main()
