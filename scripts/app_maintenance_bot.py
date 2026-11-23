#!/usr/bin/env python3
"""Money Hunter static-app diagnostics and smoke tests; never submits claims or payments."""
from __future__ import annotations
import json, os, re, subprocess, sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/"money-hunter"
REPORT=APP/"reports"/"maintenance.json"
REQUIRED=["money-hunter/index.html","money-hunter/manifest.webmanifest","money-hunter/sw.js","money-hunter/bot.js","money-hunter/reports/latest.json","money-hunter/reports/claim-finder.json","money-hunter/claim-finder.html"]
REQUIRED_TABS={"home","search","bot","profile","matches","claims","pricing","revenue","settings"}

class MarkupCheck(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.tabs=[]; self.scripts=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get("id"): self.ids.append(attrs["id"])
        if attrs.get("data-tab"): self.tabs.append(attrs["data-tab"])
        if tag=="script" and attrs.get("src"): self.scripts.append(attrs["src"])

def inspect_markup(path:Path,content:str):
    findings=[]; parser=MarkupCheck(); rel=str(path.relative_to(ROOT))
    try: parser.feed(content); parser.close()
    except Exception as exc: return [{"level":"error","code":"html_parse_error","message":str(exc),"path":rel}]
    duplicates=sorted({x for x in parser.ids if parser.ids.count(x)>1})
    if duplicates: findings.append({"level":"error","code":"duplicate_html_ids","message":"Duplicate element IDs: "+", ".join(duplicates),"path":rel})
    missing=sorted(REQUIRED_TABS-set(parser.ids))
    if missing: findings.append({"level":"error","code":"missing_navigation_targets","message":"Missing tab sections: "+", ".join(missing),"path":rel})
    broken=sorted(set(parser.tabs)-set(parser.ids))
    if broken: findings.append({"level":"error","code":"broken_navigation_tabs","message":"Navigation points to missing sections: "+", ".join(broken),"path":rel})
    for src in parser.scripts:
        if src.startswith(("https://","http://","//")): continue
        target=(path.parent/src.split("?",1)[0].split("#",1)[0]).resolve()
        if not target.is_file(): findings.append({"level":"error","code":"missing_script_asset","message":f"Referenced script is missing: {src}","path":rel})
    return findings

def check():
    findings=[]
    def add(level,code,message,path=""): findings.append({"level":level,"code":code,"message":message,"path":path})
    for rel in REQUIRED:
        if not (ROOT/rel).is_file(): add("error","missing_required_file",f"Required app file is missing: {rel}",rel)
    # Ignore the obsolete tee artifact that previously captured stdout in the repo root.
    json_files=[p for p in ROOT.rglob("*.json") if ".git" not in p.parts and "node_modules" not in p.parts and p.name!="maintenance-output.json"]
    for p in json_files:
        try: json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc: add("error","invalid_json",f"JSON cannot be parsed: {exc}",str(p.relative_to(ROOT)))
    for p in APP.glob("*.html"): findings.extend(inspect_markup(p,p.read_text(encoding="utf-8")))
    try:
        manifest=json.loads((APP/"manifest.webmanifest").read_text(encoding="utf-8"))
        if manifest.get("name")!="Money Hunter AI" or manifest.get("display")!="standalone": add("error","invalid_pwa_manifest","PWA name or standalone display configuration is missing","money-hunter/manifest.webmanifest")
        for icon in manifest.get("icons",[]):
            if not (APP/icon.get("src","")).resolve().is_file(): add("error","missing_pwa_icon",f"Manifest icon is missing: {icon.get('src')}","money-hunter/manifest.webmanifest")
    except Exception as exc: add("error","invalid_pwa_manifest",str(exc),"money-hunter/manifest.webmanifest")
    index=(APP/"index.html").read_text(encoding="utf-8") if (APP/"index.html").exists() else ""
    if index and not re.search(r'<button[^>]*id=["\']premiumCheckout["\'][^>]*disabled',index,re.I):
        add("error","unsafe_checkout_state","Premium checkout must remain disabled until recurring billing is implemented and verified","money-hunter/index.html")
    if "Square" in index: add("warning","obsolete_payment_provider","Square reference remains in app source","money-hunter/index.html")
    pyfiles=list((ROOT/"scripts").glob("*.py")) if (ROOT/"scripts").exists() else []
    for p in pyfiles:
        try: compile(p.read_text(encoding="utf-8"),str(p),"exec")
        except Exception as exc: add("error","python_syntax_error",str(exc),str(p.relative_to(ROOT)))
    if os.system("command -v node >/dev/null 2>&1")==0:
        jsfiles=list(APP.glob("*.js"))+list((APP/"scripts").glob("*.js")) if (APP/"scripts").exists() else list(APP.glob("*.js"))
        for p in jsfiles:
            result=subprocess.run(["node","--check",str(p)],capture_output=True,text=True)
            if result.returncode: add("error","javascript_syntax_error",(result.stderr or result.stdout).strip()[:1500],str(p.relative_to(ROOT)))
    patterns=[("private_key",re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),("likely_api_secret",re.compile(r"(?i)(?:sk_live_|sk_test_|ghp_|github_pat_)[A-Za-z0-9_]{16,}"))]
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts or "node_modules" in p.parts or p.suffix.lower() not in {".html",".js",".json",".py",".yml",".yaml",".md"}: continue
        try: source=p.read_text(encoding="utf-8")
        except Exception: continue
        for code,pattern in patterns:
            if pattern.search(source): add("error","possible_secret_exposed",f"Possible {code} detected. Rotate it if genuine and remove it from repository history.",str(p.relative_to(ROOT)))
    errors=sum(x["level"]=="error" for x in findings); warnings=sum(x["level"]=="warning" for x in findings)
    result={"bot":"Money Hunter App Repair & Upgrade Bot","checked_at":datetime.now(timezone.utc).isoformat(),"status":"needs_attention" if errors else ("warnings" if warnings else "healthy"),"summary":{"checks_run":len(REQUIRED)+len(json_files)+len(list(APP.glob("*.html")))+len(pyfiles)+2,"errors":errors,"warnings":warnings},"findings":findings,"scope":"Repository/static-app diagnostics only. No personal claimant records or payment accounts are accessed.","auto_repair_policy":"Diagnostics and smoke tests run automatically. Production source changes require reviewed commits; claims and payments are never submitted automatically."}
    REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2)); return 1 if errors else 0

if __name__=="__main__": sys.exit(check())
