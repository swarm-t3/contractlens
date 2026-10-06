#!/usr/bin/env python3
"""Send one plain-text email from the brand alias and log it (no secrets logged).
Usage: send.py <to> <subject> <bodyfile>"""
import os, smtplib, sys, json, datetime
from email.message import EmailMessage
from email.utils import make_msgid
env = {}
for line in open(os.path.expanduser("~/.config/swarm/secrets.env")):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1); env[k] = v.strip().strip('"').strip("'")
user = env["BRAND_GMAIL_ADDRESS"]; pw = env["BRAND_GMAIL_APP_PASSWORD"].replace(" ", "")
alias = user.replace("@", "+contractlens@")
to, subject, body = sys.argv[1], sys.argv[2], open(sys.argv[3]).read()
m = EmailMessage(); m["From"] = f"ContractLens <{alias}>"; m["To"] = to; m["Subject"] = subject
m["Reply-To"] = alias; m["Message-ID"] = make_msgid(domain="gmail.com"); m.set_content(body)
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(user, pw); s.send_message(m)
log = os.path.join(os.path.dirname(__file__), "sent.jsonl")
with open(log, "a") as f:
    f.write(json.dumps({"t": datetime.datetime.utcnow().isoformat() + "Z", "to": to, "subject": subject, "body_file": os.path.basename(sys.argv[3])}) + "\n")
print("sent", to)
