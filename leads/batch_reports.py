#!/usr/bin/env python3
"""For each lead with a published contact email: scan the Base contract, publish a report page, and draft
an informational email (no offer) summarising what holders' tools will see. Drafts go to leads/drafts/.

Usage: batch_reports.py [max]
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = os.path.expanduser("~/.local/share/uv/tools/slither-analyzer/bin/python")
sys.path.insert(0, os.path.join(ROOT, "server"))
from make_report import render, verdict  # noqa: E402

RISKY = re.compile(r"mint|pause|blacklist|block|freeze|fee|tax|upgrade|withdraw|rescue|sweep|exclude|limit|max|trading|enable", re.I)
leads = json.load(open(os.path.join(HERE, "base_tokens.json")))
done_path = os.path.join(HERE, "scanned.json")
done = json.load(open(done_path)) if os.path.exists(done_path) else {}
os.makedirs(os.path.join(HERE, "drafts"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "docs", "reports"), exist_ok=True)
limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
n = 0
for L in leads:
    if not L["emails"] or not L.get("base") or L["id"] in done:
        continue
    if n >= limit:
        break
    n += 1
    out = subprocess.run([PY, os.path.join(ROOT, "server", "scanner.py"), "8453", L["base"]], capture_output=True, text=True, cwd="/tmp", timeout=200)
    try:
        r = json.loads(out.stdout)
    except Exception:
        r = {"ok": False, "error": "no output"}
    done[L["id"]] = {"ok": r.get("ok"), "error": r.get("error")}
    json.dump(done, open(done_path, "w"), indent=1)
    if not r.get("ok"):
        print("skip", L["name"], r.get("error", "")[:80], flush=True)
        continue
    os.makedirs(os.path.join(HERE, "scans"), exist_ok=True)
    json.dump(r, open(os.path.join(HERE, "scans", f'{L["id"]}.json'), "w"))
    name = f'8453-{r["address"].lower()}.html'
    with open(os.path.join(ROOT, "docs", "reports", name), "w") as f:
        f.write(render(r))
    url = f"https://swarm-t3.github.io/contractlens/reports/{name}"
    ctl = r.get("control") or {}
    facts = []
    for k, v in ctl.items():
        if isinstance(v, dict):
            facts.append(f"{'Owner' if k == 'owner' else 'Proxy admin'}: {v.get('kind')} ({v.get('address')})")
    if r.get("proxy"):
        facts.append(f"The token is an upgradeable proxy ({r['proxy'].get('type')}); the implementation can be swapped by the admin.")
    risky = [p["function"] for p in r.get("privilegedFunctions", []) if RISKY.search(p["function"].split("(")[0])]
    if risky:
        facts.append("Owner-only functions holders will ask about: " + ", ".join(risky[:6]) + ("..." if len(risky) > 6 else ""))
    fb = r.get("summary", {}).get("findingsByImpact", {})
    facts.append(f"Static analysis (Slither): {fb.get('High', 0)} High, {fb.get('Medium', 0)} Medium, {fb.get('Low', 0)} Low; many of these are usually library false positives.")
    v = verdict(r)
    L.update({"report": url, "facts": facts, "verdict": v})
    draft = {"to": L["emails"][0], "name": L["name"], "symbol": L["symbol"].upper(), "address": r["address"], "report": url, "facts": facts,
             "verdict": [t for _, t in v]}
    json.dump(draft, open(os.path.join(HERE, "drafts", f"{L['id']}.json"), "w"), indent=1)
    print("ok", L["name"], url, flush=True)
json.dump(leads, open(os.path.join(HERE, "base_tokens.json"), "w"), indent=1)
