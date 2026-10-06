"""Releve de remise d'un mail de campagne deja parti.

Etablit le dossier reel d'arrivee par les LABELS du serveur (fiable) au lieu d'un
balayage de dossiers (faux negatif des qu'un SELECT echoue), puis controle les en-tetes
d'authentification et, dans le corps du message RECU, les liens/images attendus.

Usage :
  python check_delivery_imap.py --from dev@exemple.com --since 28-Sep-2026 \
      [--subject-contains "[TEST]"] [--expect https://youtube.com/playlist?list=XXX https://github.com/o/r] \
      [--eml-out recu.eml] [--any-folder] [--expect-absent <url> ...]

Boite d'hebergeur (cPanel/o2switch, hote IMAP du domaine, pas de labels Gmail) :
  python check_delivery_imap.py --any-folder --since 28-Sep-2026 --from dev@exemple.com \
      --imap-host mail.exemple.com --user-env REENG_SMTP_USER --pwd-env REENG_SMTP_PASSWORD
  Sur un serveur sans extension Gmail le placement est lu dans le CHEMIN du dossier ou le
  message a ete trouve (INBOX, INBOX.Junk, INBOX.Sent...) : l'absence de labels n'est pas
  un « placement inconnu ».

Identifiants lus dans %LOCALAPPDATA%\hermes\.env (EMAIL_IMAP_HOST / EMAIL_ADDRESS /
EMAIL_PASSWORD, ou HERMES_ENV pour un autre chemin). Aucun secret n'est affiche.
Codes de sortie : 0 = message trouve et controle, 2 = introuvable, 3 = erreur IMAP.
"""

import argparse
import email
import imaplib
import os
import re
import sys
from email.header import decode_header

ALL_MAIL = "[Gmail]/Tous les messages"
SPAM = "[Gmail]/Spam"


def env_path():
    return os.environ.get("HERMES_ENV") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local", "hermes", ".env")


def env(name, default=""):
    try:
        with open(env_path(), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return default


def dec(value):
    """En-tete MIME decode et aplati sur une ligne."""
    if not value:
        return ""
    out = []
    for part, enc in decode_header(value):
        out.append(part.decode(enc or "utf-8", "replace") if isinstance(part, bytes) else part)
    return "".join(out).replace("\r", " ").replace("\n", " ")


def folder_names(conn):
    """Noms de dossiers BRUTS (UTF-7 modifie) tels que renvoyes par LIST."""
    typ, data = conn.list()
    names = []
    for raw in data or []:
        s = raw.decode("ascii", "replace") if isinstance(raw, bytes) else str(raw)
        m = re.search(r'"([^"]*)"$', s) or re.search(r"(\S+)$", s)
        if m:
            names.append(m.group(1))
    return names


def select(conn, box):
    """SELECT avec controle du statut : sinon imaplib laisse la connexion en etat AUTH."""
    try:
        typ, _ = conn.select('"%s"' % box, readonly=True)
    except Exception as exc:  # noqa: BLE001
        print("  [select KO] %s : %s" % (box, exc))
        return False
    if typ != "OK":
        print("  [select refuse] %s" % box)
        return False
    return True


def search(conn, args):
    crit = ["FROM", args.sender, "SINCE", args.since]
    if args.subject_contains:
        # Un critere contenant un espace doit partir CITE : imaplib n'echappe rien et le serveur
        # refusait alors toute la recherche (`BAD Unknown argument <2e mot>`).
        val = args.subject_contains
        if " " in val and not (val.startswith('"') and val.endswith('"')):
            val = '"%s"' % val
        crit += ["HEADER", "Subject", val]
    typ, data = conn.search(None, *crit)
    if typ != "OK" or not data or not data[0]:
        return []
    return data[0].split()


def body_parts(msg):
    html = plain = ""
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype not in ("text/html", "text/plain"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", "replace")
        if ctype == "text/html" and not html:
            html = text
        elif ctype == "text/plain" and not plain:
            plain = text
    return html, plain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="sender", required=True, help="adresse d'expedition du mail")
    ap.add_argument("--since", required=True, help="date IMAP, ex. 28-Sep-2026")
    ap.add_argument("--subject-contains", default=None,
                    help="filtre sur un fragment d'objet, ex. [TEST] (les valeurs a espaces sont citees)")
    ap.add_argument("--imap-host", default=None, help="hote IMAP, ex. mail.exemple.com (sinon --host-env du .env)")
    ap.add_argument("--host-env", default="EMAIL_IMAP_HOST", help="variable .env de l'hote IMAP")
    ap.add_argument("--user-env", default="EMAIL_ADDRESS", help="variable .env du compte")
    ap.add_argument("--pwd-env", default="EMAIL_PASSWORD", help="variable .env du mot de passe")
    ap.add_argument("--expect", nargs="*", default=[], help="URLs qui doivent figurer a l'identique dans les href")
    ap.add_argument("--expect-absent", dest="expect_absent", nargs="*", default=[],
                    help="URLs qui ne doivent PLUS figurer dans les href (prouver une correction)")
    ap.add_argument("--eml-out", default=None, help="enregistrer la source complete du message")
    ap.add_argument("--any-folder", action="store_true", help="chercher dans tous les dossiers, pas seulement Tous les messages")
    ap.add_argument("--last", type=int, default=3, help="nombre de messages a detailler (defaut 3)")
    args = ap.parse_args()

    host = args.imap_host or env(args.host_env, "imap.gmail.com")
    user = env(args.user_env)
    pwd = env(args.pwd_env)
    print("IMAP : %s | compte : %s | mot de passe defini : %s"
          % (host, re.sub(r"(.{3}).*@", r"\1***@", user), "oui" if pwd else "NON"))
    if not (user and pwd):
        print("[stop] %s / %s absents de %s" % (args.user_env, args.pwd_env, env_path()))
        return 3

    try:
        conn = imaplib.IMAP4_SSL(host, 993)
        conn.login(user, pwd)
    except Exception as exc:  # noqa: BLE001
        print("[stop] connexion/authentification IMAP : %s" % exc)
        return 3

    # Gmail expose X-GM-EXT-1 (labels) ; un cPanel/Dovecot ne l'expose pas du tout.
    caps = b" ".join(c for c in conn.capabilities if isinstance(c, bytes)).upper()
    gmail = b"X-GM-EXT-1" in caps
    print("extensions   : %s" % ("Gmail (labels X-GM-LABELS disponibles)" if gmail
                                 else "sans extension Gmail -> placement lu dans le chemin du dossier"))

    tout = folder_names(conn)
    ref = ALL_MAIL if ALL_MAIL in tout else "INBOX"
    boxes = tout if args.any_folder else [b for b in (ref,) if b in tout]

    trouves = []
    for box in boxes:
        if not select(conn, box):
            continue
        uids = search(conn, args)
        print("  %s : %d message(s)" % (box, len(uids)))
        for uid in uids[-args.last:]:
            trouves.append((box, uid))

    if not trouves:
        print("RESULTAT : aucun message correspondant a --from %s SINCE %s%s"
              % (args.sender, args.since,
                 " (filtre objet %s)" % args.subject_contains if args.subject_contains else ""))
        print("           objet/destinataire a verifier, ou delai de remise non ecoule.")
        conn.logout()
        return 2

    for box, uid in trouves[-args.last:]:
        if not select(conn, box):
            continue
        typ, raw = conn.fetch(uid, "(RFC822)")
        tuples = [x for x in raw if isinstance(x, tuple)]
        if typ != "OK" or not tuples:
            print("  [fetch KO] %s uid %s" % (box, uid))
            continue
        msg = email.message_from_bytes(tuples[0][1])

        # Ne jamais conclure d'un FETCH groupe : les items demandes peuvent manquer a l'appel.
        # Relire chaque metadonnee seule, et refuser de conclure si les labels ne sont pas relus.
        internaldate = labels = flags = ""
        for item, kind in (("(INTERNALDATE)", "int"), ("(X-GM-LABELS)", "lab"), ("(FLAGS)", "flg")):
            try:
                typ2, raw2 = conn.fetch(uid, item)
            except Exception as exc:  # noqa: BLE001
                print("  [fetch %s KO] %s" % (item, exc))
                continue
            meta = " ".join(b" ".join(x for x in raw2 if isinstance(x, bytes))
                            .decode("utf-8", "replace").split())
            if typ2 != "OK" or not meta:
                print("  [fetch %s vide]" % item)
                continue
            if kind == "int":
                m = re.search(r'INTERNALDATE "([^"]+)"', meta)
                internaldate = m.group(1) if m else internaldate
            elif kind == "lab":
                m = re.search(r"X-GM-LABELS \((.*)\)", meta)
                labels = m.group(1) if m else labels
            else:
                m = re.search(r"FLAGS \((.*)\)", meta)
                flags = m.group(1) if m else flags
        inbox = "\\Inbox" in labels
        spam = "\\Spam" in labels or "\\Junk" in labels
        dossier = box.decode() if isinstance(box, bytes) else box
        if gmail:
            if not labels:
                placement = "INCONNU (labels non relus : relancer la commande, ne pas conclure)"
            else:
                placement = "INBOX" if inbox else ("SPAM" if spam else "ni INBOX ni Spam (archive/label)")
        else:
            # Pas d'extension Gmail : aucun label n'existe. Le placement SE LIT dans le chemin du
            # dossier ou le message a ete trouve (INBOX / INBOX.Junk / INBOX.Sent / ...).
            plat = dossier.lower()
            if re.search(r"(junk|spam|indesirable|pourriel)", plat):
                placement = "SPAM (%s)" % dossier
            elif plat == "inbox":
                placement = "INBOX"
            else:
                placement = "dossier %s (ni INBOX ni spam)" % dossier
        html, plain = body_parts(msg)
        hrefs = re.findall(r'href="([^"]+)"', html)
        imgs = re.findall(r'src="([^"]+)"', html)
        restes = len(re.findall(r"\{\{[^}]*\}\}", html or plain))

        print("-" * 70)
        print("  dossier de reference : %s (uid %s)" % (dossier, uid.decode() if isinstance(uid, bytes) else uid))
        print("  placement            : %s" % placement)
        if gmail:
            print("  labels / flags       : %s | %s" % (labels or "(non relus)", flags or "(non relus)"))
        else:
            print("  labels / flags       : (sans objet hors Gmail) | %s" % (flags or "(non relus)"))
        print("  recu (INTERNALDATE)  : %s" % (internaldate or "(non relu)"))
        print("  objet                : %s" % dec(msg.get("Subject")))
        print("  de / vers            : %s -> %s" % (dec(msg.get("From")), dec(msg.get("To"))))
        print("  date / reply-to      : %s | %s" % (msg.get("Date"), dec(msg.get("Reply-To"))))
        print("  auth                 : %s" % " ".join((msg.get("Authentication-Results") or "(absent)").split()))
        print("  received-spf         : %s" % " ".join((msg.get("Received-SPF") or "(absent)").split()))
        print("  x-spam-status        : %s" % (msg.get("X-Spam-Status") or "(absent)"))
        print("  list-unsubscribe     : %s" % (msg.get("List-Unsubscribe") or "(absent)"))
        print("  partie text/plain    : %s" % ("presente" if plain else "ABSENTE"))
        print("  balises de fusion    : %d restante(s)" % restes)
        print("  images (src)         :")
        for i in imgs or ["(aucune)"]:
            print("     ", i)
        print("  liens (href, tronques a 110 car) :")
        for h in hrefs or ["(aucun)"]:
            print("     ", h if len(h) <= 110 else h[:100] + "...[%d car]" % len(h))
        for url in args.expect:
            print("  attendu %-12s : %s" % ("PRESENT" if url in hrefs else "ABSENT", url))
        for url in args.expect_absent:
            print("  disparue %-11s : %s" % ("OK" if url not in hrefs else "ENCORE PRESENTE", url))
        if args.eml_out:
            with open(args.eml_out, "wb") as fh:
                fh.write(tuples[0][1])
            print("  source enregistree   : %s" % os.path.abspath(args.eml_out))

    conn.logout()
    return 0


if __name__ == "__main__":
    sys.exit(main())
