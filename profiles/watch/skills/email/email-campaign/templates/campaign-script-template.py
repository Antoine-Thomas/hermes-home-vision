"""
Campagne d'emailing HTML personnalisé via Gmail SMTP.
Lecture d'un fichier prospects.csv, envoi avec intervalle, BCC, log fichier.

Format CSV attendu : email, prenom, nom, entreprise
Template HTML : utiliser le placeholder {prenom} pour la personnalisation
"""
import csv
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

# === CONFIGURATION ===========================================================
SENDER = 'votre-compte@gmail.com'
APP_PASSWORD = 'xxxx xxxx xxxx xxxx'   # App Password Gmail
BCC = 'votre-compte@gmail.com'         # Copie de suivi
INTERVAL = 120                          # secondes entre chaque envoi (120 = 2 min)
HTML_TEMPLATE = r'C:\Users\...\email-template.html'
CSV_FILE = r'C:\Users\...\prospects.csv'
LOG_FILE = r'C:\Users\...\campagne-log.txt'
# =============================================================================

# Log line-buffered pour suivi en arrière-plan
_log_fh = open(LOG_FILE, 'w', encoding='utf-8', buffering=1)

def log(msg):
    print(msg, flush=True)
    _log_fh.write(msg + '\n')
    _log_fh.flush()

# Chargement
with open(HTML_TEMPLATE, 'r', encoding='utf-8') as f:
    html_template = f.read()

with open(CSV_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    prospects = list(reader)

log(f"Campagne démarrée : {len(prospects)} destinataires")
log(f"Intervalle : {INTERVAL // 60} minutes")
log(f"BCC : {BCC}")
log("-" * 50)

results = []

for i, p in enumerate(prospects, 1):
    email = p['email'].strip()
    prenom = p['prenom'].strip()
    nom = p['nom'].strip()
    entreprise = p.get('entreprise', '').strip()

    html_perso = html_template.replace('{prenom}', prenom)

    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr(('Votre Nom - Société', SENDER))
    msg['To'] = email
    msg['Subject'] = "Votre sujet"

    # Version texte brut (fallback)
    plain = f"Bonjour {prenom},\n\n"
    plain += "Votre contenu texte ici...\n\n"
    plain += "Signature"

    msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_perso, 'html', 'utf-8'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
            server.starttls()
            server.login(SENDER, APP_PASSWORD)
            server.sendmail(SENDER, [email, BCC], msg.as_string())
        status = "OK"
        log(f"[{i}/{len(prospects)}] {status} → {prenom} {nom} ({email}) [{entreprise}]")
    except Exception as e:
        status = f"ERREUR: {e}"
        log(f"[{i}/{len(prospects)}] {status}")

    results.append({
        'email': email,
        'prenom': prenom,
        'nom': nom,
        'entreprise': entreprise,
        'status': status
    })

    if i < len(prospects):
        log(f"  Attente {INTERVAL // 60} min...")
        time.sleep(INTERVAL)

log("-" * 50)
log("CAMPAGNE TERMINÉE")
log(f"Succès : {sum(1 for r in results if r['status'] == 'OK')}/{len(results)}")
for r in results:
    log(f"  {r['status']:5s} | {r['prenom']} {r['nom']} | {r['email']} | {r['entreprise']}")
