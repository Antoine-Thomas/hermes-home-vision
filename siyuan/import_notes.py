# -*- coding: utf-8 -*-
"""Importe des notes Markdown dans le second cerveau SiYuan.

Lit le jeton d'API dans %LOCALAPPDATA%\\hermes\\.env (SIYUAN_TOKEN).
Depose un document par note dans le notebook « hermes-skills ».
L'API SiYuan n'accepte que des POST JSON ; le jeton passe dans l'en-tete
« Authorization: Token <api.token> ».
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("SIYUAN_URL", "http://127.0.0.1:6806")
NOTEBOOK = "hermes-skills"


def jeton():
    env = os.path.join(os.environ["LOCALAPPDATA"], "hermes", ".env")
    with open(env, encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("SIYUAN_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    raise SystemExit("SIYUAN_TOKEN introuvable dans .env")


TOKEN = jeton()


def api(route, charge):
    req = urllib.request.Request(
        BASE + route,
        data=json.dumps(charge, ensure_ascii=True).encode("utf-8"),
        headers={"Authorization": "Token " + TOKEN, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def notebook_id(nom):
    r = api("/api/notebook/lsNotebooks", {})
    for nb in (r.get("data") or {}).get("notebooks") or []:
        if nb.get("name") == nom:
            return nb["id"]
    r = api("/api/notebook/createNotebook", {"name": nom})
    if r.get("code") != 0:
        raise SystemExit("creation du notebook refusee : %s" % r)
    return r["data"]["notebook"]["id"]


def docs_existants(nb_id):
    """Titres et ids des documents deja presents dans le notebook."""
    r = api("/api/query/sql",
            {"stmt": "SELECT id, content FROM blocks WHERE type='d' AND box='%s'" % nb_id})
    return {b["content"]: b["id"] for b in (r.get("data") or [])}


def supprimer(doc_id):
    r = api("/api/filetree/removeDocByID", {"id": doc_id})
    return r.get("code") == 0


def creer(nb_id, chemin, markdown):
    r = api("/api/filetree/createDocWithMd",
            {"notebook": nb_id, "path": chemin, "markdown": markdown})
    if r.get("code") != 0:
        raise SystemExit("creation de %s refusee : %s" % (chemin, r))
    return r["data"]


NOTES = [
    ("Automatisation des réseaux sociaux", """/Automatisation des réseaux sociaux""", """# Automatisation des réseaux sociaux

*Note Hermes — importée le 15/09/2026.*

Grâce a Hermes vous pouvez automatiser la plupart des réseaux sociaux : je vous recommande d'utiliser des GitHub déjà prêt et de les garder a jour pour ne pas avoir des problèmes de bannissement sur les plateformes.

## X / Twitter Cli

Prompt :

```
Installe moi Twitter cli pour que tu puisse l'utiliser :
https://github.com/public-clis/twitter-cli
```

## Linkedin Cli

Prompt :

```
Installe moi Linkedin cli pour que tu puisse l'utiliser :
https://github.com/Linked-API/linkedin-cli
```

## Discord Cli

Prompt :

```
Installe moi Discord cli pour que tu puisse l'utiliser :
https://github.com/jackwener/discord-cli
```

## Telegram Cli

Prompt :

```
Installe moi Telegram cli pour que tu puisse l'utiliser :
https://github.com/jackwener/tg-cli
```

## Instagram Cli

Prompt :

```
Installe moi Instagram cli pour que tu puisse l'utiliser :
https://github.com/supreme-gg-gg/instagram-cli
```

## Utilisation

Généralement cela s'utilise avec des prompts classique de manière a ce que vous dites simplement ce que vous souhaitez faire et a quelles fréquences. Vous pouvez généralement automatiser autant de compte que vous souhaitez.

Pour les mettre à jour continuellement (remplacer les XXX) :

Prompt :

```
Mets à jour le github XXX tous les jours à 8h pour que l'automatisation soit toujours à jour
```
"""),
    ("Veille technologique et mise à jour", """/Veille technologique et mise à jour""", """# Veille technologique et mise à jour

*Note Hermes — importée le 15/09/2026.*

## Mise à jour automatique de Hermes

Vous pouvez mettre à jour votre Hermes en automatiqu avec le prompt ci-dessous.

Prompt :

```
Tous les jours à 8h30 mets toi à jour et redémarre la gateway fais que cela soit automatique.
```

Vous pouvez aussi ajouter dans le prompt :

```
Aussi pour que je sache les mise à jour :
1. Récupérer les dernières modifications (git pull)
2. Capturer le hash avant/après pour détecter les changements
3. Résume et prends les modifications les plus importantes dans les changements et envoie moi un message en liste à puce
```

## Veille Technologique

Il peut aussi très bien vous proposer des news tous les jours.

Prompt :

```
RAPPORT TECHNO QUOTIDIEN - FEU

Tu es mon agent de veille technologique.
Ta mission : scanner, analyser et formater les nouveautés IA du jour.

STRUCTURE DU MESSAGE:
📰 RAPPORT TECHNO — [DATE]

🤖 NOUVEAUX MODÈLES (48h)
[N°]. [Nom modèle] [⭐ si challenger Opus 4.8]
◆ Architecture
  • Contexte: X tokens
  • Max output: X tokens
  • Params: [si mentionné]
◆ Capacités & Use Cases (UNIQUEMENT d'après sources trouvées)
  • [Use case 1 : expliquer ce que fait le modèle concrètement]
  • [Use case 2 : applications réelles]
◆ Benchmarks revendiqués
  • [Mentionner seulement si constructeur ou tiers crédible]
◆ Pricing
  • Input: $X.XX/M
  • Output: $X.XX/M
◆ Disponibilité
  • OpenRouter: [✅/❌] | API directe: [✅/❌]

🛠️ NOUVEAUX TOOLS & SAAS (7 derniers jours)
• [Nom tool] — Lancé: [JJ/MM/AAAA]
◆ Fonction: [description concise]
◆ Différenciation: [ce qui le distingue]
◆ Accès: [waitlist/public/beta] | Prix: [gratuit/payant]

🔥 FAILLES & LEAKS MAJEURS
[Aucune détection (24h) OU description avec source]

📊 RÉFÉRENCE: Claude Opus 4.6
◆ Contexte: 200K tokens
◆ Pricing: ~$15.00/M input, ~$75.00/M output
◆ SOTA: Coding, reasoning, long-context

SOURCES PRIORITAIRES:
1. OpenRouter API (derniers modèles ajoutés)
2. Replicate / fal.ai
3. huggingface.co/models (filtre: nouveautés 48h)
4. arXiv cs.AI / cs.CL / cs.LG (48h)
5. VentureBeat / TechCrunch / TheVerge IA
6. X/Twitter @OpenAI @AnthropicAI @kimmonismus
```
"""),
]

if __name__ == "__main__":
    nb = notebook_id(NOTEBOOK)
    print("notebook %s -> %s" % (NOTEBOOK, nb))
    existants = docs_existants(nb)
    if "--remplacer" in sys.argv:
        for titre, doc_id in existants.items():
            if supprimer(doc_id):
                print("  ancien document supprime : %s" % titre)
    for titre, chemin, contenu in NOTES:
        doc = creer(nb, chemin, contenu)
        print("  document : %-40s id %s" % (titre, doc))
