#!/usr/bin/env python3
"""
Campagne email avec Gmail API OAuth2 — import direct (pas de subprocess).
Ce pattern évite les erreurs ModuleNotFoundError dans les sous-processus détachés.

Utilisation :
  1. Adapter CSV_FILE, HTML_TEMPLATE, SUBJECT, INTERVAL
  2. python campagne.py
  3. tail -f campagne-log.txt

Prérequis : google_token.json et google_client_secret.json dans HERMES_HOME
"""

import csv
import sys
import time
from pathlib import Path

# ── Ajouter google-workspace scripts au path et importer directement ──
_gapi_dir = str(Path.home() / "AppData" / "Local" / "hermes" / "skills" / "productivity" / "google-workspace" / "scripts")
if _gapi_dir not in sys.path:
    sys.path.insert(0, _gapi_dir)
import google_api

# ── CONFIG ──────────────────────────────────────────────────
CSV_FILE = Path.home() / "Downloads" / "contacts.csv"
LOG_FILE = Path.home() / "campagne-log.txt"
INTERVAL = 120  # secondes entre envois

SUBJECT = "Votre sujet ici"

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<body style="font-family: system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #cbe8e8;">
  <div style="background: #0c9f93; padding: 30px; border-radius: 14px;">
    <p style="color: rgba(255,255,255,0.9); font-size: 16px; line-height: 1.6;">
      Bonjour <strong style="color: #fdc502;">{nom}</strong>,
    </p>
    <p style="color: rgba(255,255,255,0.9); font-size: 16px; line-height: 1.6;">
      Votre message personnalisé ici.
    </p>
  </div>
</body>
</html>"""
# ────────────────────────────────────────────────────────────

_log_fh = open(LOG_FILE, 'w', encoding='utf-8', buffering=1)


def log(msg):
    print(msg, flush=True)
    _log_fh.write(msg + '\n')
    _log_fh.flush()


def send_email_via_api(to_email, html_body):
    """Envoie un email HTML via l'API Gmail OAuth2 (import direct)."""
    import base64
    from email.mime.text import MIMEText
    from googleapiclient.discovery import build

    creds = google_api.get_credentials()
    service = build('gmail', 'v1', credentials=creds)

    message = MIMEText(html_body, 'html', 'utf-8')
    message['To'] = to_email
    message['From'] = 'searching.murphy@gmail.com'  # adapter
    message['Subject'] = SUBJECT

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw}
    result = service.users().messages().send(userId='me', body=body).execute()
    return result['id'], result.get('threadId', '')


def main():
    if not CSV_FILE.exists():
        log(f"ERREUR: Fichier CSV introuvable: {CSV_FILE}")
        sys.exit(1)

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        contacts = list(reader)

    log(f"Campagne — {len(contacts)} destinataires | Intervalle: {INTERVAL}s")
    log("-" * 60)

    contacts = [c for c in contacts if c.get('Email', '').strip()]
    log(f"Contacts avec email: {len(contacts)}")

    results = []
    for i, c in enumerate(contacts, 1):
        email = c['Email'].strip()
        nom = c.get('Nom_Structure', c.get('prenom', '')).strip() or email.split('@')[0]

        html_perso = HTML_TEMPLATE.replace('{nom}', nom)

        log(f"[{i}/{len(contacts)}] Envoi à {nom} <{email}>...")

        try:
            msg_id, thread_id = send_email_via_api(email, html_perso)
            log(f"  ✅ OK — msg_id={msg_id}")
            results.append({'email': email, 'status': 'OK'})
        except Exception as e:
            log(f"  ❌ ERREUR — {e}")
            results.append({'email': email, 'status': str(e)[:100]})

        if i < len(contacts):
            time.sleep(INTERVAL)

    ok = sum(1 for r in results if r['status'] == 'OK')
    log(f"\nCAMPAGNE TERMINÉE — {ok}/{len(results)} envoyés")
    _log_fh.close()


if __name__ == "__main__":
    main()
