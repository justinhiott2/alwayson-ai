#!/usr/bin/env python3
"""Free-first maintenance checks for the Money Hunter static PWA.

This bot diagnoses common repository/app problems. It never edits production
source files, handles claimant data, submits claims, or changes payment settings.
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "money-hunter"
REPORT = APP / "reports" / "maintenance.json"
REQUIRED = [
    "money-hunter/index.html",
    "money-hunter/manifest.webmanifest",
    "money-hunter/sw.js",
    "money-hunter/bot.js",
    "money-hunter/reports/latest.json",
    "money-hunter/reports/claim-finder.json",
    "money-hunter/claim-finder.html",
]
class MarkupCheck(HTMLParser):
    def error(self, message): raise ValueError(message)

def check():
    findings=[]
    def add(level, code, message, path=""):
        findings.append({"level":level,"code":code,"message":message,"path":path})
    for rel in REQUIRED:
        if not (ROOT/rel).is_file():
            add("error","missing_required_file",f"Required app file is missing: {rel}",rel)
    for p in ROOT.rglob("*.json"):
        if ".git" in p.parts or "node_modules" in p.parts: continue
        try: json.loads(p.read_text(encoding="utf-8"))
        except Exception as e: add("error","invalid_json",f"JSON cannot be parsed: {e}",str(p.relative_to(ROOT)))
    for p in APP.glob("*.html"):
        try:
            parser=MarkupCheck(); parser.feed(p.read_text(encoding="utf-8")); parser.close()
        except Exception as e: add("warning","html_parse_warning",f"HTML parser reported: {e}",str(p.relative_to(ROOT)))
    pyfiles=list((ROOT/"scripts").glob("*.py")) if (ROOT/"scripts").exists() else []
    for p in pyfiles:
        try: compile(p.read_text(encoding="utf-8"),str(p),"exec")
        except Exception as e: add("error","python_syntax_error",str(e),str(p.relative_to(ROOT)))
    node = subprocess.run(["node","--version"],capture_output=True,text=True) if os.system("command -v node >/dev/null 2>&1")==0 else None
    if node:
        for p in list(APP.glob("*.js"))+list((APP/"scripts").glob("*.js")) if (APP/"scripts").exists() else list(APP.glob("*.js")):
            r=subprocess.run(["node","--check",str(p)],capture_output=True,text=True)
            if r.returncode: add("error","javascript_syntax_error",(r.stderr or r.stdout).strip()[:1500],str(p.relative_to(ROOT)))
    # Catch accidental private credentials committed into source (not a full secret scanner).
    patterns=[("private_key",re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
              ("likely_api_secret",re.compile(r"(?i)(?:sk_live_|sk_test_|ghp_|github_pat_)[A-Za-z0-9_]{16,}"))]
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or "node_modules" in p.parts or p.suffix.lower() not in {".html",".js",".json",".py",".yml",".yaml",".md"}: continue
        try: content=p.read_text(encoding="utf-8")
        except Exception: continue
        for code,pat in patterns:
            if pat.search(content): add("error","possible_secret_exposed",f"Possible {code} detected. Rotate it if genuine and remove it from repository history.",str(p.relative_to(ROOT)))
    errors=sum(x["level"]=="error" for x in findings)
    warnings=sum(x["level"]=="warning" for x in findings)
    result={"bot":"Money Hunter App Repair & Upgrade Bot","checked_at":datetime.now(timezone.utc).isoformat(),"status":"needs_attention" if errors else ("warnings" if warnings else "healthy"),"summary":{"checks_run":len(REQUIRED)+len(list(ROOT.rglob("*.json")))+len(list(APP.glob("*.html")))+len(pyfiles),"errors":errors,"warnings":warnings},"findings":findings,"scope":"Repository/static-app diagnostics only. No personal claimant records or payment accounts are accessed.","auto_repair_policy":"No production source edits are made automatically. Failures are reported for reviewed repair."}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))
    return 1 if errors else 0

if __name__=="__main__": sys.exit(check())
