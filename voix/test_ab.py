# -*- coding: utf-8 -*-
"""Etape C de l'essai XTTS : test A/B entre la voix actuelle et le modele affine.

    "<venv XTTS>\\python.exe" test_ab.py --checkpoint "<chemin>/best_model.pth"

Pour chaque phrase :
  1. generation avec le modele XTTS v2 NON modifie (voix actuelle) ;
  2. generation avec le modele affine ;
  3. transcription des deux par Whisper, pour comparer la diction des termes techniques.

Sortie : corpus_test/ab/ (WAV + transcription.txt), plus un tableau recapitulatif a l'ecran.

Le modele de reference et `voix_reference.wav` ne sont jamais modifies : le modele affine est
charge depuis une copie du dossier XTTS v2 ou seule la ponderation change.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys

CORPUS = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "xtts", "corpus_test")
CACHE = os.path.join(os.environ["LOCALAPPDATA"], "TTS", "tts_models--multilingual--multi-dataset--xtts_v2")
SORTIE = os.path.join(CORPUS, "ab")
REFERENCE = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "xtts", "voix_reference.wav")
VENV_WHISPER = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "video_youtube",
                            "echomimic_v2", "venv", "Scripts", "python.exe")

PHRASES = [
    ("p1", "WordPress en local avec Local by Flywheel."),
    ("p2", "J'installe WooCommerce et je lance WP-CLI pour configurer nginx et MySQL."),
    ("p3", "La sauvegarde s'execute par cronne, puis Docker synchronise les fichiers."),
    ("p4", "Abonnez-vous pour ne pas rater le prochain volet."),
]
# termes que la diction doit rendre reconnaissables
TERMES = ["WordPress", "Flywheel", "WooCommerce", "WP-CLI", "nginx", "MySQL", "Docker",
          "cron", "sauvegarde", "abonnez"]


def preparer_modele(affine):
    """Copie le dossier XTTS v2 avec la ponderation affine (le cache d'origine reste intact)."""
    cible = os.path.join(CORPUS, "modele_affine")
    if os.path.exists(cible):
        return cible
    os.makedirs(cible, exist_ok=True)
    for f in ("config.json", "vocab.json", "speakers_xtts.pth", "model.pth"):
        source = os.path.join(CACHE, f)
        if os.path.exists(source):
            shutil.copy2(source, os.path.join(cible, f))
    shutil.copy2(affine, os.path.join(cible, "model.pth"))
    return cible


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", required=True)
    a = p.parse_args()
    if not os.path.exists(a.checkpoint):
        raise SystemExit("checkpoint introuvable : %s" % a.checkpoint)
    os.makedirs(SORTIE, exist_ok=True)

    dossier_affine = preparer_modele(a.checkpoint)
    print("modele affine prepare : %s" % dossier_affine, flush=True)

    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    import torch
    import torchaudio

    def charger(dossier):
        config = XttsConfig()
        config.load_json(os.path.join(dossier, "config.json"))
        modele = Xtts.init_from_config(config)
        modele.load_checkpoint(config, checkpoint_dir=dossier, eval=True)
        modele.cuda()
        return config, modele

    def generer(config, modele, texte, sortie):
        gpt_cond, haut_parleur = modele.get_conditioning_latents(audio_path=[REFERENCE])
        res = modele.inference(text=texte, language="fr", gpt_cond_latent=gpt_cond,
                               speaker_embedding=haut_parleur, temperature=0.75,
                               enable_text_splitting=True)
        torchaudio.save(sortie, torch.tensor(res["wav"]).unsqueeze(0), 24000)

    print("chargement de la voix actuelle (XTTS v2 d'origine) ...", flush=True)
    config_actuel, modele_actuel = charger(CACHE)
    print("chargement du modele affine ...", flush=True)
    config_affine, modele_affine = charger(dossier_affine)

    produits = []
    for cle, texte in PHRASES:
        for nom, (cfg, mod) in (("actuel", (config_actuel, modele_actuel)),
                                ("affine", (config_affine, modele_affine))):
            chemin = os.path.join(SORTIE, "%s_%s.wav" % (cle, nom))
            try:
                generer(cfg, mod, texte, chemin)
                print("  %s %s -> %s" % (cle, nom, os.path.basename(chemin)), flush=True)
                produits.append({"phrase": cle, "version": nom, "fichier": chemin, "texte": texte})
            except Exception as e:
                print("  %s %s : ECHEC (%s)" % (cle, nom, e), flush=True)
    io.open(os.path.join(SORTIE, "produits.json"), "w", encoding="utf-8").write(
        json.dumps(produits, ensure_ascii=False, indent=1))

    # transcription Whisper des deux versions
    if os.path.exists(VENV_WHISPER) and produits:
        script = os.path.join(SORTIE, "_transcrire.py")
        io.open(script, "w", encoding="utf-8").write(
            "import io, json, os, whisper\n"
            "racine = r'%s'\n"
            "modele = whisper.load_model('medium')\n"
            "donnees = json.load(io.open(os.path.join(racine, 'produits.json'), encoding='utf-8'))\n"
            "for d in donnees:\n"
            "    r = modele.transcribe(d['fichier'], language='fr', fp16=True)\n"
            "    d['transcription'] = r['text'].strip()\n"
            "io.open(os.path.join(racine, 'produits.json'), 'w', encoding='utf-8').write(\n"
            "    json.dumps(donnees, ensure_ascii=False, indent=1))\n" % SORTIE)
        r = subprocess.run([VENV_WHISPER, script], capture_output=True, text=True)
        if r.returncode != 0:
            print("transcription en echec : %s" % (r.stderr or "")[-300:])
    else:
        print("Whisper indisponible : pas de transcription")

    # tableau comparatif
    donnees = json.load(io.open(os.path.join(SORTIE, "produits.json"), encoding="utf-8"))
    lignes = ["ANALYSE DU TEST A/B", ""]
    for cle, texte in PHRASES:
        lignes.append("Phrase %s : %s" % (cle, texte))
        for version in ("actuel", "affine"):
            d = next((x for x in donnees if x["phrase"] == cle and x["version"] == version), None)
            if not d or "transcription" not in d:
                lignes.append("  %-7s : (pas de transcription)" % version)
                continue
            t = d["transcription"]
            trouves = [m for m in TERMES if re.search(m, t, re.I)]
            lignes.append("  %-7s : %s" % (version, t))
            lignes.append("            termes reconnus : %d/%d -> %s"
                          % (len(trouves), len(TERMES), ", ".join(trouves)))
        lignes.append("")
    texte_final = "\n".join(lignes)
    io.open(os.path.join(SORTIE, "analyse_ab.txt"), "w", encoding="utf-8", newline="\n").write(
        texte_final + "\n")
    print(texte_final)
    print("analyse ecrite : %s" % os.path.join(SORTIE, "analyse_ab.txt"))
