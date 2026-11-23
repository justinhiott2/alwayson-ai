#!/usr/bin/env python3
"""Fetch and parse the official Davidson County Chancery Clerk excess-proceeds PDF.
Stores only case/parcel references and amounts; never claimant names or contact data.
"""
from __future__ import annotations
import datetime as dt
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from pypdf import PdfReader
from io import BytesIO

INDEX_URL = "https://chanceryclerkandmaster.nashville.gov/fees/property-tax-schedule/"
OUT = Path("money-hunter/data/excess-proceeds/davidson-county.json")
UA = "MoneyHunterAI-public-record-index/1.0 (automated official register parser)"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.hrefs.append(href)

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def discover_pdf(html: bytes) -> str:
    parser = Links()
    parser.feed(html.decode("utf-8", "replace"))
    candidates = []
    for href in parser.hrefs:
        low = href.lower()
        if ".pdf" in low and ("excess" in low or "proceed" in low):
            if href.startswith("/"):
                href = "https://chanceryclerkandmaster.nashville.gov" + href
            elif href.startswith("//"):
                href = "https:" + href
            if href.startswith("https://chanceryclerkandmaster.nashville.gov/"):
                candidates.append(href)
    if not candidates:
        raise RuntimeError("No official excess-proceeds PDF link found on the Clerk & Master's property-tax schedule page")
    # Page order is treated as newest-first; preserve the first matching official link.
    return candidates[0]

ROW = re.compile(
    r"^(?P<case>\d{2}-\d{4}-[IVX]+)\s+(?P<parcel>[A-Z0-9]+)\s+"
    r"(?P<middle>.+?)\s+(?P<amount>\$[\d,]+\.\d{2})\s+"
    r"(?P<held>\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(?P<activity>\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(?P<order>\d{1,2}/\d{1,2}/\d{4})\s*(?P<star>\*)?\s*$"
)

def parse_pdf(data: bytes):
    reader = PdfReader(BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    rows = []
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        m = ROW.match(line)
        if not m:
            continue
        g = m.groupdict()
        amount = float(g["amount"].replace("$", "").replace(",", ""))
        rows.append({
            "case_number": g["case"],
            "parcel_reference": g["parcel"],
            "amount_reported_usd": round(amount, 2),
            "funds_held_since": g["held"],
            "most_recent_financial_activity": g["activity"],
            "confirming_order_date": g["order"],
            "asterisk_flag": bool(g["star"]),
            "verification_status": "public_register_only_unverified",
        })
    if not rows:
        preview = "\n".join(text.splitlines()[:35])
        raise RuntimeError("PDF downloaded but no table rows matched expected format. Text preview:\n" + preview[:2500])
    # Remove duplicate rows while preserving order.
    unique = {}
    for row in rows:
        key = (row["case_number"], row["parcel_reference"])
        unique[key] = row
    return list(unique.values()), len(reader.pages)

def main():
    index = fetch(INDEX_URL)
    pdf_url = discover_pdf(index)
    pdf = fetch(pdf_url)
    rows, pages = parse_pdf(pdf)
    report_date = None
    m = re.search(r"(\d{1,2})[-_](\d{1,2})[-_](\d{2,4})", pdf_url)
    if m:
        month, day, year = map(int, m.groups())
        if year < 100:
            year += 2000
        report_date = f"{year:04d}-{month:02d}-{day:02d}"
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_name": "Davidson County Chancery Clerk & Master — official excess proceeds register",
        "source_index_url": INDEX_URL,
        "source_pdf_url": pdf_url,
        "report_date_from_filename": report_date,
        "parser": "pypdf line-table parser v1",
        "record_count": len(rows),
        "pdf_pages": pages,
        "important": "This is a transcription of a public register, not a docket search or proof funds remain available. An asterisk means a motion to claim or redeem may be pending or resolved and funds may not yet be disbursed. No claimant names or contact information are stored. Verify current docket, custodian balance, legal priority and disbursement directly before any action.",
        "records": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Parsed {len(rows)} public case/parcel rows from {pdf_url}")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
