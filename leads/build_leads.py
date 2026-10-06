#!/usr/bin/env python3
"""Lead list of small, active Base tokens whose websites publish a contact email.
Sources: CoinGecko coin list (Base addresses), DexScreener token API (market data + websites), project homepages.
Output: leads/base_tokens.json"""
import json, re, time, urllib.request, concurrent.futures as cf
UA = {"User-Agent": "Mozilla/5.0 (compatible; contractlens-research/1.0)"}
def get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")
base = json.load(open("/tmp/cg_base.json"))
by_addr = {c["platforms"]["base"].lower(): c for c in base if c["platforms"]["base"].startswith("0x")}
addrs = list(by_addr)
best = {}
for i in range(0, len(addrs), 30):
    try:
        pairs = json.loads(get("https://api.dexscreener.com/tokens/v1/base/" + ",".join(addrs[i:i+30])))
    except Exception as e:
        time.sleep(5); continue
    for p in pairs:
        a = p["baseToken"]["address"].lower()
        if a not in by_addr: continue
        liq = (p.get("liquidity") or {}).get("usd") or 0
        if a not in best or liq > best[a]["liq"]:
            best[a] = {"liq": liq, "vol": (p.get("volume") or {}).get("h24") or 0, "mcap": p.get("marketCap") or p.get("fdv") or 0,
                       "websites": [w["url"] for w in (p.get("info") or {}).get("websites", [])]}
    time.sleep(0.4)
print("dex", len(best), flush=True)
pick = [(a, b) for a, b in best.items() if 50_000 <= b["mcap"] <= 150_000_000 and b["vol"] >= 5_000 and b["websites"]]
pick.sort(key=lambda x: -x[1]["vol"])
print("picked", len(pick), flush=True)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD = re.compile(r"ag-grid|example|sentry|wixpress|\.png|\.jpg|\.svg|\.webp|\.gif|domain\.com|email\.com|yourname|u003e|@2x|privacy@|abuse@|legal@|dmca|noreply|no-reply", re.I)
def scrape(item):
    a, b = item
    emails = set()
    h = b["websites"][0]
    for path in ("", "contact", "about", "team", "contact-us"):
        try:
            html = get(h.rstrip("/") + ("/" + path if path else ""), timeout=12)
        except Exception:
            continue
        emails |= {e.lower().rstrip(".") for e in EMAIL.findall(html) if not BAD.search(e)}
        if emails: break
    c = by_addr[a]
    return {"id": c["id"], "name": c["name"], "symbol": c["symbol"], "mcap": b["mcap"], "vol": b["vol"], "liq": b["liq"],
            "base": a, "homepage": h, "emails": sorted(emails)}
with cf.ThreadPoolExecutor(8) as ex:
    out = list(ex.map(scrape, pick[:250]))
json.dump(out, open("base_tokens.json", "w"), indent=1)
print("done", len(out), "with email", sum(1 for o in out if o["emails"]), flush=True)
