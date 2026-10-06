#!/usr/bin/env python3
"""Build a lead list of small Base tokens whose websites publish a contact email.
Sources: CoinGecko public API (markets + coin links) and the project's own homepage. Output: leads/base_tokens.json"""
import json, re, time, urllib.request, sys
UA = {"User-Agent": "Mozilla/5.0 (compatible; contractlens-research/1.0)"}
def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")
base = json.load(open("/tmp/cg_base.json"))
ids = [c["id"] for c in base]
markets = []
for i in range(0, len(ids), 250):
    chunk = ",".join(ids[i:i+250])
    for attempt in range(4):
        try:
            markets += json.loads(get(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={chunk}&per_page=250"))
            break
        except Exception as e:
            time.sleep(20)
    time.sleep(6)
print("markets", len(markets), flush=True)
addr = {c["id"]: c["platforms"]["base"] for c in base}
pick = [m for m in markets if (m.get("market_cap") or 0) >= 200_000 and (m.get("market_cap") or 0) <= 30_000_000 and (m.get("total_volume") or 0) >= 20_000]
pick.sort(key=lambda m: -(m.get("total_volume") or 0))
print("picked", len(pick), flush=True)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD = re.compile(r"example|sentry|wixpress|\.png|\.jpg|\.svg|\.webp|domain\.com|email\.com|yourname|u003e|@2x", re.I)
out = []
for m in pick[:160]:
    try:
        info = json.loads(get(f"https://api.coingecko.com/api/v3/coins/{m['id']}?localization=false&tickers=false&market_data=false&community_data=false&developer_data=false"))
    except Exception:
        time.sleep(30); continue
    home = [h for h in (info.get("links", {}).get("homepage") or []) if h][:1]
    emails = set()
    for h in home:
        for path in ("", "contact", "about"):
            try:
                html = get(h.rstrip("/") + ("/" + path if path else ""), timeout=12)
            except Exception:
                continue
            for e in EMAIL.findall(html):
                if not BAD.search(e):
                    emails.add(e.lower())
            if emails:
                break
    out.append({"id": m["id"], "name": m["name"], "symbol": m["symbol"], "mcap": m.get("market_cap"), "vol": m.get("total_volume"),
                "base": addr.get(m["id"]), "homepage": home[0] if home else None, "emails": sorted(emails)})
    print(m["name"], home[:1], sorted(emails)[:2], flush=True)
    time.sleep(4)
json.dump(out, open("/home/mac-home-lab/Projects/swarm-work/r01-a3/leads/base_tokens.json", "w"), indent=1)
print("done", len(out), sum(1 for o in out if o["emails"]))
