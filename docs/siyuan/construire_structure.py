# -*- coding: utf-8 -*-
"""Construit la structure du second cerveau SiYuan.

6 notebooks :
  hermes-projets       5 sites Local (donnees lues sur disque : versions, extensions, sauvegardes)
  hermes-skills        un document par skill reellement utilise (extrait du SKILL.md, verbatim)
  video-ia             3 branches A / B / C avec les parametres et mesures valides
  apprentissage-continu  (vide, volontairement : a remplir avec la Phase 1)
  journal              1 document : la panne LTX-2.3 du 15/09
  veille               2 documents : sources suivies, idees en attente

Usage : python construire_structure.py [--dry]
Ne touche a aucun document existant : il ajoute seulement ce qui manque.
"""
import io
import json
import os
import re
import sys
import urllib.request

BASE = os.environ.get("SIYUAN_URL", "http://127.0.0.1:6806")
SKILLS = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "skills")
MAJ = "15/09/2026"


def jeton():
    env = os.path.join(os.environ["LOCALAPPDATA"], "hermes", ".env")
    with io.open(env, encoding="utf-8") as f:
        for ligne in f:
            if ligne.startswith("SIYUAN_TOKEN="):
                return ligne.split("=", 1)[1].strip()
    raise SystemExit("SIYUAN_TOKEN introuvable")


TOKEN = jeton()


def api(route, charge):
    req = urllib.request.Request(
        BASE + route,
        data=json.dumps(charge, ensure_ascii=True).encode("utf-8"),
        headers={"Authorization": "Token " + TOKEN, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def notebook(nom):
    r = api("/api/notebook/lsNotebooks", {})
    for nb in (r.get("data") or {}).get("notebooks") or []:
        if nb.get("name") == nom:
            return nb["id"]
    r = api("/api/notebook/createNotebook", {"name": nom})
    if r.get("code") != 0:
        raise SystemExit("notebook %s refuse : %s" % (nom, r))
    return r["data"]["notebook"]["id"]


def docs_existants(nb_id):
    r = api("/api/query/sql",
            {"stmt": "SELECT content FROM blocks WHERE type='d' AND box='%s'" % nb_id})
    return {b["content"] for b in (r.get("data") or [])}


def entete(statut="actif"):
    return "> **Statut** : %s\n> **Dernière mise à jour** : %s\n" % (statut, MAJ)


# --------------------------------------------------------------------------
# 1. hermes-projets : un document par site, donnees reelles
# --------------------------------------------------------------------------
def doc_site(nom, s):
    ext = s["extensions"]
    actives = s.get("actives")
    actifs = set(actives or [])
    lignes = ["# %s\n" % nom, entete(),
              "## Fait",
              "- Site Local **%s**, adresse http://%s" % (nom, s["domain"]),
              "- WordPress **%s** · PHP **%s** · MySQL **%s** · %s **%s**"
              % (s["wp"] or "?", s["php"], s["mysql"], s["web_nom"], s["web"]),
              "- %d extensions installées%s" % (
                  len(ext), (", %d actives" % len(actifs)) if actives is not None else
                  " (état actif non déterminé)"),
              "- Dernière sauvegarde : %s (%s Mo, %s)"
              % ((s["sauvegarde"] or {}).get("fichier", "aucune"),
                 (s["sauvegarde"] or {}).get("taille_Mo", "-"),
                 (s["sauvegarde"] or {}).get("date", "-")),
              "- Dossier : `%s`" % s["path"],
              "", "## Reste à faire",
              "- Confirmer la liste des extensions actives depuis l'administration du site",
              "- Programmer une sauvegarde à jour (la dernière date de la sauvegarde ci-dessus)",
              "", "## Pièges",
              "- Les identifiants de base sont ceux de Local (`root` / `root`), inutilisables tels"
              " quels hors de la machine",
              "- Toutes les extensions ne sont pas actives : ne pas conclure d'un dossier présent"
              " dans `wp-content/plugins` qu'il est chargé",
              "", "## Commandes",
              "```",
              'cd "%s"' % os.path.join(s["path"], "app", "public"),
              '"C:\\wp-cli\\wp.bat" core version',
              '"C:\\wp-cli\\wp.bat" plugin list --status=active',
              '"C:\\wp-cli\\wp.bat" db export "%s"' % os.path.join(s["path"], "app", "sql", "local.sql"),
              "```",
              "", "## Extensions (%d)" % len(ext),
              "", "| Extension | Version | Active |", "|---|---|---|"]
    for e in ext:
        marque = "oui" if e["dossier"] in {a.split("/")[0] for a in actifs} else (
            "non" if actives is not None else "?")
        lignes.append("| %s | %s | %s |" % (e["nom"], e["version"], marque))
    if actives is not None:
        lignes += ["", "*État actif déduit du dump SQL de sauvegarde, pas d'une instance en cours.*"]
    return "\n".join(lignes) + "\n"


# --------------------------------------------------------------------------
# 2. hermes-skills : un document par skill, extrait verbatim du SKILL.md
# --------------------------------------------------------------------------
def doc_skill(chemin_relatif, note=None):
    chemin = os.path.join(SKILLS, chemin_relatif, "SKILL.md")
    if not os.path.exists(chemin):
        return None
    txt = io.open(chemin, encoding="utf-8").read()
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    corps = txt
    if m:
        for ligne in m.group(1).splitlines():
            mm = re.match(r'^(\w+):\s*"?(.*?)"?\s*$', ligne)
            if mm:
                fm[mm.group(1)] = mm.group(2)
        corps = txt[m.end():]
    desc = fm.get("description", "(description absente)")
    version = fm.get("version", "non déclarée")

    # commandes : lignes de blocs de code qui ressemblent a une commande
    cmds = []
    for bloc in re.findall(r"```[a-z]*\n(.*?)```", corps, re.S):
        for ligne in bloc.splitlines():
            l = ligne.strip()
            if not l or l.startswith("#"):
                continue
            if re.match(r"^(\$ |sudo |cd |python|pip|npm|npx|git |curl|wget|docker|hermes|"
                        r"C:\\\\|/c/|\"C:|ffmpeg|wsl|schtasks|powershell|winget)", l):
                cmds.append(l)
    # pieges : puces qui parlent d'erreur, d'attention ou d'interdit
    pieges = []
    for ligne in corps.splitlines():
        l = ligne.strip()
        if not l.startswith(("-", "*", "|")) and not re.match(r"^\d+\.", l):
            continue
        if re.search(r"pi[eè]ge|pitfall|erreur|attention|jamais|ne pas|REFUSER|danger|"
                     r"[eé]chec|casse|plant", l, re.I):
            pieges.append(l.lstrip("-*| ").strip())
    lignes = ["# %s\n" % fm.get("name", chemin_relatif.split("/")[-1]), entete(),
              "## Fait", "- Rôle : %s" % desc, "",
              "| | |", "|---|---|",
              "| Version | %s |" % version,
              "| Dossier réel | `%s` |" % os.path.join(SKILLS, chemin_relatif),
              "| Fichier | SKILL.md (%d lignes) |" % len(txt.splitlines()), ""]
    if note:
        lignes += [note, ""]
    lignes += ["## Reste à faire", "- (rien de connu ; à compléter à l'usage)", ""]
    lignes += ["## Pièges"]
    if pieges:
        lignes += ["- " + p for p in dict.fromkeys(pieges)][:14]
    else:
        lignes += ["- Aucun piège formulé dans le skill."]
    lignes += ["", "## Commandes"]
    if cmds:
        lignes += ["```"] + list(dict.fromkeys(cmds))[:22] + ["```"]
    else:
        lignes += ["- Aucune commande explicite dans le skill (procédure en prose)."]
    lignes += ["", "*Extrait verbatim du skill ; le fichier complet reste la référence.*"]
    return "\n".join(lignes) + "\n"


def doc_libre(titre, statut, fait, reste, pieges, commandes, extra=""):
    l = ["# %s\n" % titre, entete(statut), "## Fait"] + ["- " + x for x in fait]
    l += ["", "## Reste à faire"] + ["- " + x for x in reste]
    l += ["", "## Pièges"] + ["- " + x for x in pieges]
    l += ["", "## Commandes", "```"] + commandes + ["```"]
    if extra:
        l += ["", extra]
    return "\n".join(l) + "\n"


VIDEO_IA = [
    ("/Branche A - LatentSync (source video)", doc_libre(
        "Branche A — LatentSync (source vidéo tournée)", "terminé",
        ["Principe : une prise de vue réelle (4K) + une voix de synthèse XTTS, les lèvres sont "
         "resynchronisées par LatentSync.",
         "Segments de 48 s = 1200 images = 3 cycles ping-pong exacts (le cycle de la source fait "
         "400 images, soit 16 s) : c'est ce découpage qui a supprimé les 5 sauts d'image aux raccords.",
         "Audio découpé en WAV, jamais en AAC.",
         "Silences de fin de segment XTTS ramenés de ~575 ms à 120 ms (audio 287,9 s → 271,2 s).",
         "Transfert passe-haut 4K sur toute l'image : sans lui, les côtés restaient sur l'upscale "
         "720p et perdaient 62 % de netteté.",
         "Bout des lèvres : recadrage par image (les contours servent de référence), pas "
         "d'accentuation locale.",
         "Livrable : youtube_volet4_hermes_FINAL.mp4 — 1920×1080, 25 i/s, 6780 images, 271,20 s, "
         "MD5 0351c5ff3540b43aefc051c368426a52, 0 saut (MAD aux raccords 0,96 à 1,22)."],
        ["Aucune reprise prévue sur ce volet ; la recette est validée et documentée dans le skill "
         "talking-head-video-8gb."],
        ["Aucun fondu enchaîné sur la source : LatentSync boucle déjà la vidéo en ping-pong, un "
         "fondu ajoute un mélange de deux poses toutes les 8 s (~80 événements sur la vidéo).",
         "Rendu tombé à 45 s/it au lieu de 6,3 s/it : relancer le processus LatentSync, pas la "
         "machine — la lenteur vient de son état, pas d'une contention GPU.",
         "Ne pas définir PYTORCH_CUDA_ALLOC_CONF sur cette configuration."],
        ['cd "/c/Users/searc/Desktop/hermes_tuto_v4"',
         'V4_LIPALIGN=1 V4_KEEP=0.70 "$LOCALAPPDATA/hermes/data/video_youtube/LatentSync/venv/'
         'Scripts/python.exe" assemble_v6.py run',
         'bash wait_ls_v8b.sh   # enchaine LatentSync puis l assemblage',
         'nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader'])),
    ("/Branche B - source photo", doc_libre(
        "Branche B — source photo fixe (LivePortrait, SadTalker, Wav2Lip)", "actif",
        ["Principe : une photo fixe, animée par LivePortrait (mouvements) ou SadTalker / Wav2Lip "
         "(parole), MuseTalk et EchoMimicV2 également installés. Restauration par GFPGAN.",
         "Environnements vérifiés ce jour : les sept venvs IA répondent et voient CUDA.",
         "Contrainte mesurée : LivePortrait en source-max-dim 320 = 5,2 Go de VRAM pour ~3 images/s ; "
         "256 = 3,5 Go pour ~5 images/s."],
        ["Aucun rendu en cours ; à reprendre quand un volet partira d'une photo.",
         "Débruitage de la source à faire avant tout rendu, pour la stabilité des images."],
        ["REFUSER LivePortrait en 512p ou 384p sur cette machine : 7,7 Go de VRAM sur 8 → "
         "thrashing, 1,3 image/s.",
         "Ce qui ne transfère PAS depuis la branche A : la boucle ping-pong, le découpage "
         "LatentSync, le recadrage des lèvres, le transfert passe-haut 4K.",
         "Cohérence de cadence obligatoire entre la source et la sortie."],
        ['"$LOCALAPPDATA/hermes/data/video_youtube/liveportrait/venv/Scripts/python.exe" '
         'inference.py --source-max-dim 320',
         '"$LOCALAPPDATA/hermes/data/video_youtube/sadtalker/venv/Scripts/python.exe" inference.py'])),
    ("/Branche C - LTX-2.3 (generation IA)", doc_libre(
        "Branche C — génération IA (LTX-2.3 GGUF dans ComfyUI)", "actif",
        ["Principe : aucun tournage, la vidéo est générée depuis un texte. Modèle audio-vidéo : la "
         "sortie contient une piste audio.",
         "Installation : C:\\Users\\searc\\ComfyUI-LTX — ComfyUI v0.35 portable, nœuds "
         "ComfyUI_LTX2_SM et ComfyUI-GGUF, serveur sur le port 8188. 34 Go de poids : transformer "
         "Q4_K_S (12,96 Go), encodeur Gemma 3 12B Q4_0 (8,70), connecteurs connector-11 (6,34), "
         "VAE vidéo et audio (1,81).",
         "Mesures du 15/09 à 640×384, 25 images, 24 i/s, 8 étapes, mode distilled, offload=True : "
         "132,79 s à froid (chargement du modèle compris) et 205,11 s à chaud, soit 5,31 à "
         "8,20 s par image et 16,60 à 25,64 s par étape — 127 à 197 fois le temps réel.",
         "Contenu vérifié par mesure, pas seulement par l'absence d'erreur : écart-type spatial "
         "de 54,7 puis 75,3, mouvement présent, et l'image extraite correspond au prompt demandé."],
        ["Tester des formats plus longs (le temps croît avec les pixels × les images).",
         "Le mode one_stage n'a pas abouti ; c'est distilled qui fonctionne."],
        ["Le GGUF quantifié d'unsloth n'embarque ni les connecteurs ni les projections d'agrégat : "
         "il faut connector-11.safetensors (6,34 Go) dans models/checkpoints.",
         "Environnement figé : transformers 4.57.6 (la version 5 casse le nœud) et diffusers 0.36.0.",
         "Un dictionnaire de poids vide ne se voit pas tout de suite : l'erreur n'arrive qu'à "
         "l'échantillonneur, sous la forme « Cannot copy out of meta tensor ». Voir le journal du "
         "15/09."],
        ['cd "/c/Users/searc/ComfyUI-LTX/ComfyUI_windows_portable"',
         './python_embeded/python.exe -s ComfyUI/main.py --listen 127.0.0.1 --port 8188',
         'cd /c/Users/searc/ComfyUI-LTX && "$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/'
         'python.exe" ltx_test.py 1280 704 97 8 "ton prompt"'])),
]

JOURNAL = [
    ("/Panne LTX-2.3 du 15-09-2026", doc_libre(
        "Journal — panne LTX-2.3 du 15/09/2026 : poids jamais chargés", "terminé",
        ["Symptôme : l'échantillonneur du nœud LTX2_SM_KSampler échouait avec "
         "« NotImplementedError: Cannot copy out of meta tensor; no data! », quel que soit le "
         "réglage.",
         "Première mesure : le constructeur du nœud avertissait lui-même « Uninitialized "
         "parameters or buffers: ['scale_shift_table', 'patchify_proj.weight', …] » — il avertit "
         "et continue, il ne plante pas.",
         "Deuxième mesure : 4186 paramètres sur 4186 étaient sur le disque virtuel (modèle "
         "entièrement vide).",
         "Troisième mesure, décisive : le dictionnaire d'état chargé depuis le GGUF contenait "
         "0 clé sur 4444.",
         "Cause racine : les opérations de renommage du nœud vident le dictionnaire sur ce GGUF, "
         "alors que ses noms bruts correspondent exactement à ceux du modèle.",
         "Correctif : relire le GGUF sans ces opérations quand le dictionnaire revient vide "
         "(LTX2/ltx_core/loader/single_gpu_model_builder.py, fonction load_sd). Après correctif : "
         "4444 clés, intersection complète, 0 paramètre fantôme — et la génération fonctionne.",
         "Coût évité : un téléchargement de 18,14 Go qui n'aurait rien réglé."],
        ["Aucune — incident clos. Réutiliser la méthode de diagnostic sur tout GGUF quantifié."],
        ["Ne jamais conclure « pièce manquante » avant d'avoir comparé le nombre de clés du "
         "dictionnaire au nombre de paramètres du modèle.",
         "Éviter les heures perdues sur des chemins graphiques : le noyau et les API se testent "
         "en ligne de commande.",
         "Les durées affichées pendant un échec ne sont pas des mesures de génération."],
        ['grep -a "Uninitialized parameters" comfyui.log',
         'python -c "from gguf import GGUFReader; r=GGUFReader(\'chemin.gguf\'); '
         'print(len(r.tensors))"'],
        "*Leçon générale : mesurer avant de télécharger. Trois comptages ont suffi à éviter 18 Go "
        "et une journée de doute.*")),
]

VEILLE = [
    ("/Sources suivies", doc_libre(
        "Veille — sources suivies", "veille",
        ["Sources déjà balisées dans les notes importées : OpenRouter API (derniers modèles "
         "ajoutés), Replicate / fal.ai, huggingface.co/models (nouveautés 48 h), arXiv cs.AI, "
         "cs.CL, cs.LG, VentureBeat / TechCrunch / TheVerge (IA), X/Twitter @OpenAI, "
         "@AnthropicAI, @kimmonismus.",
         "Dépôts suivis parce qu'ils portent les outils réellement utilisés : "
         "NousResearch/hermes-agent, siyuan-note/siyuan, comfyanonymous/ComfyUI, "
         "Lightricks/ComfyUI-LTXVideo, unsloth/LTX-2.3-GGUF, smthemex/ComfyUI_LTX2_SM.",
         "Versions à surveiller : localwp.com/releases (Local), la branche stable de SiYuan "
         "(CVE corrigée en 3.8.2)."],
        ["Compléter avec les chaînes YouTube et les blogs suivis — à préciser.",
         "Décider de la cadence du rapport techno quotidien et de sa livraison (Telegram ?)."],
        ["Une source non citée ne doit pas produire d'affirmation : les rapports indiquent ce "
         "qui est revendiqué par le constructeur et ce qui est mesuré par un tiers."],
        ['curl -s "https://openrouter.ai/api/v1/models" | jq -r \'.data[-5:][] | .id\'',
         'curl -s "https://huggingface.co/api/models?sort=createdAt&limit=10" | jq -r \'.[].id\''])),
    ("/Idees en attente", doc_libre(
        "Veille — idées en attente", "veille",
        ["Phase 1 du système d'amélioration continue : audit des cibles entraînables sur la "
         "machine (prochaine étape annoncée).",
         "Automatisation des réseaux sociaux par CLI (Twitter, LinkedIn, Discord, Telegram, "
         "Instagram) et mise à jour quotidienne des dépôts — note déjà importée.",
         "Réglages Local non appliqués : memory_limit PHP 256M → 512M, innodb_buffer_pool_size "
         "32M → 256M.",
         "Synchronisation SiYuan (S3 ou WebDAV) — volontairement reportée.",
         "Serveur MCP SiYuan pour Hermes — exige une modification de config.yaml, donc en attente.",
         "Piste LTX : transformer appairé Q6_K (18,14 Go) si la qualité du Q4_K_S ne suffit pas — "
         "inutile pour l'instant, la chaîne fonctionne.",
         "Volet 5 de la série YouTube — sujet à définir."],
        ["Toutes ces idées sont à arbitrer une par une ; aucune n'est engagée."],
        ["Ne rien engager qui touche config.yaml ou les venvs IA sans accord explicite."],
        ['(aucune commande : liste de sujets)'])),
]


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    sites = json.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "sites_data.json"), encoding="utf-8"))
    plan = []

    # 1. projets
    for nom, s in sorted(sites.items()):
        plan.append(("hermes-projets", "/" + nom, doc_site(nom, s)))
    # 2. skills
    skill_liste = [
        ("talking-head-video-8gb", "media/talking-head-video-8gb", None),
        ("local-flywheel-setup", "wordpress/local-flywheel-setup", None),
        ("wordpress-site-management", "wordpress/wordpress-site-management", None),
        ("wp-cli-automation", "wordpress/wp-cli-automation", None),
        ("wordpress-backup-restore", "wordpress/wordpress-backup-restore", None),
        ("wordpress-deployment", "wordpress/wordpress-deployment", None),
        ("omniroute-suite", "devops/omniroute-suite", None),
        ("hermes-operations", "hermes-operations", None),
        ("tts-voice-cloning", "mlops/tts-voice-cloning", None),
        ("ai-video-pipeline", "ai-video-pipeline", None),
    ]
    for titre, rel, note in skill_liste:
        doc = doc_skill(rel, note)
        if doc:
            plan.append(("hermes-skills", "/" + titre, doc))
        else:
            print("  ! skill introuvable : %s" % rel)
    # 3. video-ia, journal, veille
    for chemin, contenu in VIDEO_IA:
        plan.append(("video-ia", chemin, contenu))
    for chemin, contenu in JOURNAL:
        plan.append(("journal", chemin, contenu))
    for chemin, contenu in VEILLE:
        plan.append(("veille", chemin, contenu))

    print("documents a creer : %d" % len(plan))
    from collections import Counter
    for nb, n in sorted(Counter(a for a, _, _ in plan).items()):
        print("   %-22s %d" % (nb, n))
    if dry:
        raise SystemExit(0)
    for nb_nom, chemin, contenu in plan:
        nb = notebook(nb_nom)
        existants = docs_existants(nb)
        titre = chemin.strip("/").split("/")[-1]
        if titre in existants:
            print("  deja present, ignore : %s / %s" % (nb_nom, titre))
            continue
        r = api("/api/filetree/createDocWithMd",
                {"notebook": nb, "path": chemin, "markdown": contenu})
        print("  %-22s %-34s %s" % (nb_nom, chemin, "ok" if r.get("code") == 0 else r))
