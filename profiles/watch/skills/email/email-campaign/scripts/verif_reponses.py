#!/usr/bin/env python3
"""
Vérification post-campagne par IMAP — Classification automatique des réponses.
Catégories: STOP (opt-out), POSITIF, NÉGATIF, sans réponse.
Met à jour tracking.json.
"""

import imaplib
import email as em
import json
import re
from email.header import decode_header
from pathlib import Path
from datetime import datetime, timedelta

# ── Config ─────────────────────────────────────────────
IMAP_HOST = "imap.gmail.com"
EMAIL_ADDRESS = "searching.murphy@gmail.com"
APP_PASSWORD = "xxxx xxxx xxxx xxxx"

TRACKING_FILE = Path("tracking.json")

# ── Keywords ───────────────────────────────────────────
STOP_KEYWORDS = [
    "ne plus être contacté", "ne plus me contacter", "ne pas me contacter",
    "pas intéressé", "pas interesse", "supprimer mon", "retirez-moi",
    "ne me contactez plus", "arrêtez", "désabonner", "desabonner",
    "stop", "unsubscribe",
]

POSITIVE_KEYWORDS = [
    "intéressé", "interesse", "rdv", "appelez-moi", "rappelle",
    "bravo", "félicitations", "super", "beau site", "joli",
    "cool", "nice", "on en parle", "contacte-moi",
]

NEGATIVE_KEYWORDS = ["pas maintenant", "pas pour moi", "laisse tomber"]

# ── Helpers ────────────────────────────────────────────
def decode_str(s):
    if s is None:
        return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or "utf-8", errors="ignore")
        else:
            result += part
    return result

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode("utf-8", errors="ignore")
    else:
        return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
    return ""

# ── English month abbrevs (IMAP SINCE expects these) ───
MONTHS = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
          7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

# ── Main ───────────────────────────────────────────────
def check_replies(days_back=7):
    if not TRACKING_FILE.exists():
        print("❌ tracking.json introuvable — lance la campagne d'abord")
        return

    with open(TRACKING_FILE, "r", encoding="utf-8") as f:
        tracking = json.load(f)

    d = datetime.now() - timedelta(days=days_back)
    since_str = f"{d.day}-{MONTHS[d.month]}-{d.year}"

    mail = imaplib.IMAP4_SSL(IMAP_HOST)
    mail.login(EMAIL_ADDRESS, APP_PASSWORD)
    mail.select("INBOX")

    status, data = mail.search(None, f'(SINCE "{since_str}")')
    if status != "OK":
        print("❌ Erreur IMAP")
        return

    msg_ids = data[0].split()
    print(f"📨 {len(msg_ids)} messages récents\n")

    new_stops, new_positive, new_negative = [], [], []

    for msg_id in msg_ids[-200:]:
        status, data = mail.fetch(msg_id, "(RFC822)")
        if status != "OK":
            continue
        msg = em.message_from_bytes(data[0][1])
        subject = decode_str(msg["Subject"]).lower()
        from_addr = decode_str(msg["From"]).lower()
        body = get_body(msg).lower()[:800]

        sender_email = ""
        match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', from_addr)
        if match:
            sender_email = match.group(0)

        if "searching.murphy" in sender_email:
            continue

        # Phase 1: campaign reply?
        is_reply = (
            "re:" in subject
            or "mise à jour" in subject
            or "candidature" in subject
            or "searching murphy" in body[:500]
        )
        if not is_reply:
            continue

        # Phase 2: classify
        if any(kw in body[:500] for kw in STOP_KEYWORDS):
            new_stops.append(sender_email)
            print(f"🛑 STOP: {sender_email}")
        elif any(kw in body[:500] for kw in POSITIVE_KEYWORDS):
            new_positive.append(sender_email)
            print(f"👍 POSITIF: {sender_email}")
        elif any(kw in body[:500] for kw in NEGATIVE_KEYWORDS):
            new_negative.append(sender_email)
            print(f"👎 NÉGATIF: {sender_email}")

    # Update tracking
    for e in new_stops:
        if e not in tracking["stop"]:
            tracking["stop"].append(e)
        if e in tracking["no_response"]:
            tracking["no_response"].remove(e)
    for e in new_positive:
        if e not in tracking["positive"]:
            tracking["positive"].append(e)
        if e in tracking["no_response"]:
            tracking["no_response"].remove(e)
    for e in new_negative:
        if e not in tracking["negative"]:
            tracking["negative"].append(e)
        if e in tracking["no_response"]:
            tracking["no_response"].remove(e)

    with open(TRACKING_FILE, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)

    mail.logout()

    print(f"\n📊 RÉSULTATS:")
    print(f"   🛑 STOP: {len(tracking['stop'])}")
    print(f"   👍 Positif: {len(tracking['positive'])}")
    print(f"   👎 Négatif: {len(tracking['negative'])}")
    print(f"   💥 Bounced: {len(tracking['bounced'])}")
    print(f"   ⏳ Sans réponse: {len(tracking['no_response'])}")
