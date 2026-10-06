#!/usr/bin/env python3
"""Render a scan JSON (from scanner.py) into a static, shareable HTML report under docs/reports/.

Usage: make_report.py <scan.json> [notes.md]
notes.md (optional) is a hand-written triage section rendered as preformatted paragraphs.
"""
import datetime
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPLORERS = {"1": "https://etherscan.io/address/", "8453": "https://basescan.org/address/",
             "42161": "https://arbiscan.io/address/", "10": "https://optimistic.etherscan.io/address/",
             "137": "https://polygonscan.com/address/", "56": "https://bscscan.com/address/"}
RISKY = re.compile(r"mint|pause|blacklist|block|freeze|setfee|settax|fee|tax|upgrade|withdraw|rescue|sweep|setrouter|setpair|exclude|limit|maxtx|maxwallet|trading|enable", re.I)


def esc(x):
    return html.escape(str(x))


def link(chain, a):
    base = EXPLORERS.get(str(chain))
    return f'<a href="{base}{esc(a)}">{esc(a)}</a>' if base else esc(a)


def verdict(r):
    ctl = r.get("control") or {}
    kinds = [v.get("kind", "") for k, v in ctl.items() if isinstance(v, dict)]
    risky_fns = [f["function"] for f in r.get("privilegedFunctions", []) if RISKY.search(f["function"].split("(")[0])]
    high = (r.get("summary", {}).get("findingsByImpact", {}) or {}).get("High", 0)
    points = []
    if not r.get("proxy") and not r.get("privilegedFunctions"):
        points.append(("ok", "No admin functions and not upgradeable: nobody can mint, pause, blacklist or change this contract."))
    if r.get("proxy"):
        points.append(("warn", "Upgradeable: the code can be replaced by the proxy admin."))
    if any(k.startswith("EOA") for k in kinds):
        points.append(("bad", "Admin rights sit with a single private key (EOA). One leaked or malicious key is enough to use them."))
    if any(k.startswith("Safe") for k in kinds):
        points.append(("ok", "Admin rights sit with a Safe multisig: " + ", ".join(k for k in kinds if k.startswith("Safe")) + "."))
    if any(k == "renounced" for k in kinds):
        points.append(("ok", "Ownership is renounced: owner-only functions can no longer be called."))
    if risky_fns:
        points.append(("warn", f"{len(risky_fns)} admin functions touch supply, fees, transfers or upgrades: " + ", ".join(risky_fns[:8]) + ("..." if len(risky_fns) > 8 else "")))
    if high:
        points.append(("warn", f"{high} High-impact static-analysis finding(s) need a human look (Slither has false positives)."))
    if not points:
        points.append(("ok", "No owner, no proxy and no High findings detected."))
    return points


def render(r, notes=""):
    chain, addr = r["chainId"], r["address"]
    title = f'{r.get("analysedContract") or r.get("contractName")} on {r["chain"]}'
    f_by = r.get("summary", {}).get("findingsByImpact", {})
    rows = "".join(
        f'<tr><td class="{esc(f["impact"])}">{esc(f["impact"])}</td><td>{esc(f["confidence"])}</td><td><code>{esc(f["check"])}</code></td><td><pre>{esc(f["description"])}</pre></td></tr>'
        for f in r.get("findings", []) if f["impact"] in ("High", "Medium", "Low"))
    priv = "".join(f'<li><code>{esc(p["function"])}</code> <small>{esc(", ".join(p["modifiers"]))}</small></li>' for p in r.get("privilegedFunctions", []))
    ctl = r.get("control") or {}
    ctl_html = "".join(f'<li>{esc(k)}: <b>{esc(v.get("kind"))}</b> {link(chain, v.get("address"))}</li>' for k, v in ctl.items() if isinstance(v, dict))
    if ctl.get("note"):
        ctl_html += f"<li>{esc(ctl['note'])}</li>"
    proxy = r.get("proxy")
    proxy_html = (f'<p>Proxy type {esc(proxy.get("type"))}. Current implementation {link(chain, proxy.get("implementation"))} ({esc(proxy.get("implementationName"))}).</p>' if proxy else "<p>Not a proxy.</p>")
    v = "".join(f'<li class="{c}">{esc(t)}</li>' for c, t in verdict(r))
    notes_html = ""
    if notes.strip():
        notes_html = "<h2>Reviewer notes</h2>" + "".join(f"<p>{esc(p.strip())}</p>" for p in notes.split("\n\n") if p.strip())
    date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ContractLens report: {esc(title)}</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;max-width:900px;margin:30px auto;padding:0 16px;color:#111}}
code{{background:#f3f3f3;padding:1px 4px;border-radius:3px}} pre{{white-space:pre-wrap;margin:0;font-size:12px}}
table{{border-collapse:collapse;width:100%}} td{{border-top:1px solid #eee;padding:6px;vertical-align:top}}
.High,.bad{{color:#b00}} .Medium,.warn{{color:#b60}} .ok{{color:#070}} small{{color:#666}}</style>
<p><a href="../">ContractLens</a> · independent automated report</p>
<h1>{esc(title)}</h1>
<p>{link(chain, addr)} · chain {esc(chain)} · compiler {esc(r.get("compiler"))} · Sourcify {esc(r.get("sourcifyMatch"))} · generated {date}</p>
<h2>Summary</h2><ul>{v}</ul>
<p>Findings by impact: {esc(json.dumps(f_by))}</p>
<h2>Who holds the keys</h2><ul>{ctl_html or "<li>No owner() or proxy admin found.</li>"}</ul>
<h2>Upgradeability</h2>{proxy_html}
<h2>Privileged functions ({len(r.get("privilegedFunctions", []))})</h2><ul>{priv or "<li>None detected.</li>"}</ul>
{notes_html}
<h2>Static analysis (High, Medium, Low)</h2>
<table><tr><td>Impact</td><td>Confidence</td><td>Check</td><td>Detail</td></tr>{rows or "<tr><td colspan=4>None.</td></tr>"}</table>
<p><small>Generated by ContractLens from the Sourcify-verified source and live on-chain reads. This is automated static analysis plus reviewer notes, not a full manual audit. Findings can be false positives. Re-run any time: <a href="../">swarm-t3.github.io/contractlens</a>.</small></p>
</html>"""


if __name__ == "__main__":
    r = json.load(open(sys.argv[1]))
    notes = open(sys.argv[2]).read() if len(sys.argv) > 2 else ""
    os.makedirs(os.path.join(ROOT, "docs", "reports"), exist_ok=True)
    name = f'{r["chainId"]}-{r["address"].lower()}.html'
    with open(os.path.join(ROOT, "docs", "reports", name), "w") as f:
        f.write(render(r, notes))
    print(f"https://swarm-t3.github.io/contractlens/reports/{name}")
