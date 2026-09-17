"""
Campagne email de prospection — envoi personnalisé depuis un CSV.
Utilisation :
  1. Remplir prospects.csv (email, prenom, nom, entreprise)
  2. Ajuster SENDER, APP_PASSWORD, HTML_TEMPLATE ci-dessous
  3. Lancer : python campagne.py
  4. Suivre : cat campagne-log.txt  (log en temps réel)
"""
import csv
import smtplib
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr


# Log fichier (line-buffered) + stdout (flushé) — indispensable sous Windows
_log_fh = open(LOG_FILE, 'w', encoding='utf-8', buffering=1)

def log(msg):
    """Print + fichier, flush immédiat pour suivi en temps réel."""
    print(msg, flush=True)
    _log_fh.write(msg + '\n')
    _log_fh.flush()

# ── CONFIG ──────────────────────────────────────────
SENDER = 'searching.murphy@gmail.com'
APP_PASSWORD = 'xxxx xxxx xxxx xxxx'  # Gmail App Password
BCC = SENDER                          # Copie de suivi
INTERVAL = 120                        # Secondes entre envois
HTML_TEMPLATE = 'templates/searching-murphy-prospection.html'
CSV_FILE = 'prospects.csv'
LOG_FILE = 'campagne-log.txt'         # Fichier de suivi en temps réel
SUBJECT = "Donnez un coup de neuf à votre site avec l'IA"
FROM_NAME = 'Thomas Leroyer - Searching Murphy'
# ─────────────────────────────────────────────────────

with open(HTML_TEMPLATE, 'r', encoding='utf-8') as f:
    html_template = f.read()

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    prospects = list(reader)

log(f"Campagne : {len(prospects)} destinataires | Intervalle : {INTERVAL}s | BCC : {BCC}")
log("-" * 50)

results = []

for i, p in enumerate(prospects, 1):
    email = p['email'].strip()
    prenom = p['prenom'].strip()
    nom = p['nom'].strip()
    entreprise = p.get('entreprise', '').strip()

    html_perso = html_template.replace('{prenom}', prenom)

    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((FROM_NAME, SENDER))
    msg['To'] = email
    msg['Subject'] = SUBJECT

    plain = f"""Bonjour {prenom},

Je suis Thomas Leroyer, fondateur de Searching Murphy à Caen.
Je conçois des sites WordPress résilients guidés par le design défensif.
Inspiré par la loi de Murphy, chaque site anticipe les pannes et s'auto-répare
grâce à l'intelligence artificielle.

Ce que j'apporte à votre projet :
- Un site plus rapide — performances optimisées, expérience fluide.
- Un site plus intelligent — IA embarquée, corrections automatiques.
- Un site qui convertit mieux — design orienté utilisateur, SEO renforcé.

Je vous propose un audit gratuit → https://www.searching-murphy.com

Thomas Leroyer, Fondateur — Searching Murphy
searching.murphy@gmail.com | Caen, Normandie
"""
    msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_perso, 'html', 'utf-8'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.starttls()
            server.login(SENDER, APP_PASSWORD)
            server.sendmail(SENDER, [email, BCC], msg.as_string())
        status = "OK"
    except Exception as e:
        status = f"ERREUR: {e}"

    log(f"[{i}/{len(prospects)}] {status} → {prenom} {nom} ({email}) [{entreprise}]")
    results.append({'email': email, 'prenom': prenom, 'nom': nom,
                    'entreprise': entreprise, 'status': status})

    if i < len(prospects):
        log(f"  Attente {INTERVAL}s...")
        time.sleep(INTERVAL)

log("-" * 50)
ok = sum(1 for r in results if r['status'] == 'OK')
log(f"CAMPAGNE TERMINÉE — Succès : {ok}/{len(results)}")
for r in results:
    log(f"  {r['status']:5s} | {r['prenom']} {r['nom']} | {r['email']} | {r['entreprise']}")
