#!/usr/bin/env python3
"""
Campagne email avec tracking intégré — Searching Murphy
Pattern: lit un CSV, envoie via SMTP, maintient tracking.json
"""

import smtplib
import csv
import json
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

# ── Config ─────────────────────────────────────────────
SENDER_EMAIL = "searching.murphy@gmail.com"
SENDER_NAME = "Thomas Leroyer — Searching Murphy"
APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # Gmail App Password
INTERVAL = 3  # secondes entre chaque envoi

DATA_DIR = Path(".")  # override per campaign
LOG_FILE = DATA_DIR / "campagne_log.json"
TRACKING_FILE = DATA_DIR / "tracking.json"

# ── Charger templates ──────────────────────────────────
def load_template(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ── Tracking state ─────────────────────────────────────
def load_tracking():
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sent": [], "bounced": [], "stop": [], "positive": [],
            "negative": [], "no_response": []}

def save_tracking(tracking):
    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)

# ── Send one email ─────────────────────────────────────
def send_email(to_email, to_name, subject, html_body):
    """Returns (success: bool, error: str|None)"""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr((SENDER_NAME, SENDER_EMAIL))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["BCC"] = SENDER_EMAIL

        # Plain text fallback — customize per campaign
        plain = f"Bonjour {to_name},\n\n"
        plain += "Message en version texte.\n\n"
        plain += "Si tu ne veux plus recevoir mes nouvelles, réponds STOP.\n\nThomas"

        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())

        return True, None

    except smtplib.SMTPRecipientsRefused as e:
        return False, f"BOUNCE: {e}"
    except smtplib.SMTPResponseException as e:
        return False, f"SMTP error {e.smtp_code}: {e.smtp_error}"
    except Exception as e:
        return False, str(e)

# ── Run campaign from CSV ──────────────────────────────
def run_campaign(csv_path, template_html, subject, prenom_col="prenom",
                 email_col="email", placeholder="{prenom_addresse}"):
    tracking = load_tracking()

    with open(csv_path, "r", encoding="utf-8") as f:
        contacts = list(csv.DictReader(f))

    total = len(contacts)
    sent_count = 0
    fail_count = 0

    for i, c in enumerate(contacts, 1):
        email = c[email_col].strip()
        prenom = c.get(prenom_col, "").strip()

        if email in tracking["sent"] or email in tracking["bounced"]:
            print(f"  [{i}/{total}] ⏭️  {email} — déjà traité")
            continue

        greeting = f" {prenom}" if prenom else ""
        html = template_html.replace(placeholder, greeting)

        success, error = send_email(email, prenom or email, subject, html)

        if success:
            tracking["sent"].append(email)
            tracking["no_response"].append(email)
            sent_count += 1
            print(f"  [{i}/{total}] ✅ {email}")
        else:
            fail_count += 1
            print(f"  [{i}/{total}] ❌ {email} — {error}")
            if "BOUNCE" in str(error):
                tracking["bounced"].append(email)

        save_tracking(tracking)
        if i < total:
            time.sleep(INTERVAL)

    print(f"\n✅ {sent_count} envoyés, {fail_count} échecs")
    return sent_count, fail_count
