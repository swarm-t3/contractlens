#!/usr/bin/env python3
"""Send the informational report email for each draft in leads/drafts/ once. No offer in the first email.
Usage: send_drafts.py [--dry] [max]"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEND = os.path.join(os.path.dirname(HERE), "outreach", "send.py")
sent_path = os.path.join(HERE, "sent_ids.json")
sent = set(json.load(open(sent_path))) if os.path.exists(sent_path) else set()
dry = "--dry" in sys.argv
nums = [a for a in sys.argv[1:] if a.isdigit()]
limit = int(nums[0]) if nums else 10
leads = {L["id"]: L for L in json.load(open(os.path.join(HERE, "base_tokens.json")))}

n = 0
for fn in sorted(os.listdir(os.path.join(HERE, "drafts"))):
    lid = fn[:-5]
    if lid in sent or n >= limit:
        continue
    d = json.load(open(os.path.join(HERE, "drafts", fn)))
    home = leads.get(lid, {}).get("homepage", "your website")
    facts = "\n".join(f"- {f}" for f in d["facts"])
    flag = [v for v in d["verdict"] if "single private key" in v or "Upgradeable" in v]
    flag_txt = f"\nThe item holder tools are most likely to flag: {flag[0]}\n" if flag else ""
    body = f"""Hi {d['name']} team,

We run ContractLens, an independent scanner that answers the question holders ask most about a token: who can mint, pause or change it?

We ran it on {d['symbol']} on Base ({d['address']}) and published the result here:
{d['report']}

What it shows:
{facts}
{flag_txt}
You don't need to do anything. If something is out of date (for example, ownership has since moved to a multisig), reply and we'll re-run it. If you'd rather the page weren't public, reply "remove" and we'll take it down.

ContractLens
https://swarm-t3.github.io/contractlens/

You're getting this one email because {d['to']} is listed on {home}. Reply "no" and we won't write again.
"""
    subject = f"{d['symbol']} contract check: who holds the admin keys (public report)"
    if dry:
        print("TO:", d["to"], "\nSUBJECT:", subject, "\n", body, "\n" + "=" * 60)
    else:
        bf = os.path.join(HERE, "drafts", lid + ".txt")
        open(bf, "w").write(body)
        r = subprocess.run(["python3", SEND, d["to"], subject, bf], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip()[-200:])
        if r.returncode == 0:
            sent.add(lid)
            json.dump(sorted(sent), open(sent_path, "w"), indent=1)
    n += 1
