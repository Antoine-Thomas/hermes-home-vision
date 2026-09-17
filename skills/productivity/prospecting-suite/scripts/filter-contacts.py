#!/usr/bin/env python3
"""
Reference: Contact filtering script.
Adapt INPUT/OUTPUT paths and column mapping per data source.
"""
import csv, re
from pathlib import Path

# ═══ CONFIGURATION — adapt per source ═══

INPUT = Path("contacts.csv")
OUTPUT_KEEP = Path("contacts-gardes.csv")
OUTPUT_DROP = Path("contacts-supprimes.csv")

# Column mapping (adjust for your CSV format)
COL_EMAILS = ["E-mail 1 - Value", "E-mail 2 - Value", "E-mail 3 - Value"]
COL_FIRST = "First Name"
COL_LAST = "Last Name"
COL_ORG = "Organization Name"
COL_TITLE = "Organization Title"

# ═══ BLOCKLISTS ═══

BLOCKED_DOMAINS = [
    "facebookmail.com", "meetic.com", "secondlife.com",
    "lindenlab.com", "skype.com", "dyndns.com",
    "microsoft.com", "rueducommerce.com",
    "prepaiddigitalsolutions.com", "welcome.skype.com",
    "cimail1.msn.com", "message.myspace.com", "m.facebook.com",
    "fr.facebox.com", "ourstage.com", "starbreeze.com",
]

BLOCKED_KEYWORDS = [
    "no-reply", "noreply", "notification", "service",
    "support", "jobs@", "info@", "newsletter",
]

NON_NAME_WORDS = {
    "productions", "production", "project", "projects",
    "info", "contact", "hello", "admin", "webmaster",
    "net", "com", "org", "fr", "de", "uk",
    "the", "la", "le", "of",
}

PUBLIC_PROVIDERS = {
    "gmail.com", "googlemail.com", "hotmail.com", "hotmail.fr",
    "hotmail.co.uk", "live.com", "live.fr", "outlook.com",
    "outlook.fr", "yahoo.com", "yahoo.fr", "yahoo.de",
    "msn.com", "free.fr", "orange.fr", "wanadoo.fr",
    "laposte.net", "laposte.fr", "gmx.de", "gmx.net",
    "numericable.fr", "sfr.fr", "icloud.com", "me.com",
}

# ═══ HELPERS ═══

def get_all_emails(row):
    emails = []
    for key in COL_EMAILS:
        val = row.get(key, "").strip()
        if val and "@" in val:
            emails.append(val)
    return emails

def extract_domain(email):
    return email.rsplit("@", 1)[-1].lower() if "@" in email else ""

def extract_local(email):
    return email.split("@", 1)[0].lower() if "@" in email else ""

def strip_numeric_suffix(s):
    return re.sub(r'[._\-]?\d+$', '', s)

def has_weird_chars(text):
    return bool(re.findall(r'[\^\°\xb0\xa8]', text))

def is_name_field_valid(field, email):
    if not field or not field.strip():
        return False
    val = field.strip()
    if val.lower() == email.lower():
        return False
    if val.lower() == extract_local(email):
        return False
    if val.lower() in ('moi', 'unique', 'service', 'support', 'video',
                       'second', 'life'):
        return False
    if re.match(r'^\d', val):
        return False
    if re.match(r'^[a-zA-Z]+\d+$', val):
        return False
    return True

def looks_like_name(local_part):
    local = strip_numeric_suffix(local_part.strip().lower())
    parts = re.split(r'[._\-+]', local)
    name_parts = [p for p in parts
                  if re.match(r'^[a-zàâäéèêëîïôöùûüç]{2,}$', p)
                  and p not in NON_NAME_WORDS]
    return len(name_parts) >= 2

def looks_like_gibberish(local_part):
    local = local_part.strip().lower()
    if len(local) > 25 and not re.search(r'[._\-]', local):
        return True
    alpha_only = re.sub(r'[^a-z]', '', local)
    if len(alpha_only) > 10:
        vowels = sum(1 for c in alpha_only if c in 'aeiouy')
        if vowels == 0 or vowels / len(alpha_only) < 0.15:
            return True
    return False

def extract_names_from_email(email):
    local = extract_local(email)
    local_clean = strip_numeric_suffix(local)
    parts = re.split(r'[._\-+]', local_clean)
    name_parts = [p for p in parts
                  if re.match(r'^[a-zàâäéèêëîïôöùûüç]{2,}$', p)
                  and p not in NON_NAME_WORDS]
    if len(name_parts) >= 2:
        return name_parts[0].capitalize(), name_parts[-1].capitalize()
    return "", ""

def is_blocked_domain(domain):
    domain_lower = domain.lower()
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain_lower:
            return True
    if "newsletter." in domain_lower or domain_lower.startswith("lists."):
        return True
    return False

def has_blocked_keyword(email, prenom, nom):
    combined = f"{email} {prenom} {nom}".lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in combined:
            if kw in ("info@", "jobs@") and (
                is_name_field_valid(prenom, email)
                or is_name_field_valid(nom, email)):
                continue
            return True
    return False

# ═══ MAIN ═══

def main():
    with open(INPUT, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    with_email = [r for r in rows if get_all_emails(r)]
    without_email = [r for r in rows if not get_all_emails(r)]

    kept, dropped = [], []
    stats = {}

    for row in with_email:
        emails = get_all_emails(row)
        email = emails[0]
        prenom = row.get(COL_FIRST, "").strip()
        nom = row.get(COL_LAST, "").strip()
        domain = extract_domain(email)
        local = extract_local(email)

        if is_blocked_domain(domain):
            dropped.append((row, f"domaine bloqué: {domain}")); continue
        if has_blocked_keyword(email, prenom, nom):
            dropped.append((row, "mot-clé interdit")); continue
        if has_weird_chars(f"{prenom} {nom} {email}"):
            dropped.append((row, "caractères bizarres")); continue
        if looks_like_gibberish(local):
            dropped.append((row, "email suspect (charabia)")); continue

        has_valid_prenom = is_name_field_valid(prenom, email)
        has_valid_nom = is_name_field_valid(nom, email)
        has_name_in_email = looks_like_name(local)
        is_pro = domain not in PUBLIC_PROVIDERS

        has_explicit_name = has_valid_prenom or has_valid_nom
        if not has_explicit_name and not has_name_in_email and not is_pro:
            dropped.append((row, "pas de nom/prénom identifiable")); continue
        if is_pro and not has_explicit_name and not has_name_in_email:
            if looks_like_gibberish(local) or len(local) > 30:
                dropped.append((row, "email pro sans nom identifiable")); continue

        if prenom.lower() == email.lower() or prenom.lower() == local:
            prenom = ""
        if nom.lower() == email.lower() or nom.lower() == local:
            nom = ""

        if not has_valid_prenom and not has_valid_nom and has_name_in_email:
            ep, en = extract_names_from_email(email)
            if ep: prenom = ep
            if en: nom = en

        clean_row = dict(row)
        clean_row[COL_FIRST] = prenom
        clean_row[COL_LAST] = nom
        kept.append(clean_row)

    # Write kept
    with open(OUTPUT_KEEP, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fieldnames))
        w.writeheader(); w.writerows(kept)

    # Write dropped with reason
    drop_fields = list(fieldnames) + ["Motif du rejet"]
    with open(OUTPUT_DROP, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=drop_fields)
        w.writeheader()
        for row, reason in dropped:
            r = dict(row); r["Motif du rejet"] = reason
            w.writerow(r)

    # Report
    for _, reason in dropped:
        cat = reason.split(":")[0] if ":" in reason else reason[:40]
        stats[cat] = stats.get(cat, 0) + 1

    print(f"Total: {len(rows)} | Avec email: {len(with_email)}")
    print(f"Conservés: {len(kept)} | Supprimés: {len(dropped)}")
    print(f"Sans email ignorés: {len(without_email)}")
    for cat, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")

if __name__ == "__main__":
    main()
