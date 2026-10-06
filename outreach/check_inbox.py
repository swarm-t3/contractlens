#!/usr/bin/env python3
"""List mail addressed to the +contractlens alias (replies, bounces). Read-only; never deletes or moves mail."""
import os, imaplib, email, email.header, json
env = {}
for line in open(os.path.expanduser("~/.config/swarm/secrets.env")):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1); env[k] = v.strip().strip('"').strip("'")
user = env["BRAND_GMAIL_ADDRESS"]; pw = env["BRAND_GMAIL_APP_PASSWORD"].replace(" ", "")
alias = user.replace("@", "+contractlens@")
M = imaplib.IMAP4_SSL("imap.gmail.com", 993); M.login(user, pw)
M.select('"[Gmail]/All Mail"', readonly=True)
typ, data = M.search(None, f'(OR TO "{alias}" X-GM-RAW "contractlens")')
def dec(s):
    return "".join(t.decode(c or "utf-8", "replace") if isinstance(t, bytes) else t for t, c in email.header.decode_header(s or ""))
out = []
for num in data[0].split()[-60:]:
    typ, msg = M.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])")
    h = email.message_from_bytes(msg[0][1])
    out.append({"date": h["Date"], "from": dec(h["From"]), "subject": dec(h["Subject"])})
for o in out: print(json.dumps(o))
