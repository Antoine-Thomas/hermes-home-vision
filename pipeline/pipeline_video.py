# -*- coding: utf-8 -*-
"""Orchestrateur du pipeline video complet : un seul point d'entree pour toute la chaine.

    python pipeline_video.py --script mon_script.txt --voix v9 --qualite --source p1002837

Etapes, dans l'ordre :
  1. preparation du script      -> preparer_script_tts.py (lexique de diction)  => script_tts.txt
  2. synthese vocale            -> gen_voice_v<N>.py (detecte automatiquement)  => volet4_voice_<voix>.wav
  3. plan de decoupe            -> controle du decoupage en segments multiples du cycle ping-pong (48 s)
  4. lissage video              -> run_latentsync_v8b.py                        => latentsync_<source>_<voix>.mp4
  5. assemblage                 -> assemble_v6.py run (parametre par variables d'environnement)
  6. controle qualite           -> controle_qualite.py (seuils + verdict)        => rapport_qualite_*.json

Options :
  --dry-run           liste les etapes et les fichiers attendus, n'execute rien
  --sans-etape N      reprend a l'etape N (apres une coupure) : les sorties des etapes precedentes
                      doivent exister, elles ne sont pas refaites
  --force             autorise l'ecrasement d'un fichier de sortie deja present
  --qualite           ajoute l'etape 6 (controle qualite)
  --nom-etapes        affiche le detail des commandes sans executer (implique --dry-run)

Comment l'orchestrateur appelle les scripts existants
----------------------------------------------------
Aucun script existant n'est modifie ni remplace.

- `assemble_v6.py` est parametrable par variables d'environnement : il est appele tel quel.
- `gen_voice_v<N>.py` et `run_latentsync_v8b.py` n'ont NI argument NI variable d'environnement :
  leurs chemins sont des constantes figees dans le fichier. L'orchestrateur les execute donc via un
  lanceur temporaire qui substitue ces constantes **en memoire** (le fichier sur disque n'est jamais
  touche, son empreinte est verifiee avant et apres). Le lanceur vit dans le dossier temporaire et
  disparait apres coup.
- L'etape 3 ne decoupe PAS l'audio : la decoupe reelle est faite par `run_latentsync_v8b.py`, qui
  gere la phase du ping-pong ET la coupe des silences de fin de segment. L'orchestrateur verifie le
  plan (duree, nombre de segments, reste) et le consigne, pour ne pas couper deux fois.
"""
import argparse
import datetime
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOCALAPPDATA = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
DATA_VIDEO = os.path.join(LOCALAPPDATA, "hermes", "data", "video_youtube")
VENV_XTTS = os.path.join(LOCALAPPDATA, "hermes", "data", "xtts", "venv", "Scripts", "python.exe")
VENV_LS = os.path.join(DATA_VIDEO, "LatentSync", "venv", "Scripts", "python.exe")
PY_STD = sys.executable

CYCLE_PINGPONG = 16.0     # 2 x 200 frames a 25 i/s (voir run_latentsync_v8b.py)

NOMS_ETAPES = {
    1: "preparation du script (lexique de diction)",
    2: "synthese vocale (XTTS)",
    3: "plan de decoupe (multiples du cycle ping-pong)",
    4: "lissage video (LatentSync)",
    5: "assemblage final",
    6: "controle qualite",
}


# --------------------------------------------------------------------------- outils

def empreinte(chemin):
    h = hashlib.sha256()
    with io.open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()[:16]


def duree_media(chemin):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", chemin], capture_output=True, text=True)
    try:
        return float((r.stdout or "").strip())
    except ValueError:
        return None


def plus_recent(motif, cle=None):
    """Choisit le fichier le plus avance : gen_voice_v8.py l'emporte sur gen_voice_v7.py."""
    trouves = [f for f in glob.glob(os.path.join(HERE, motif))
               if not os.path.basename(f).endswith("_full.py")]
    if not trouves:
        return None
    def rang(chemin):
        m = re.search(r"_v(\d+)([a-z]*)\.py$", os.path.basename(chemin))
        return (int(m.group(1)), m.group(2)) if m else (0, "")
    return max(trouves, key=cle or rang)


def lancer(cmd, environnement=None, etiquette="", budget_s=None):
    """Execute une commande, rend (code, sortie, duree). N'affiche rien qui ne soit dans le rapport."""
    env = dict(os.environ)
    if environnement:
        env.update(environnement)
    debut = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=HERE)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - debut


def lanceur_substitution(script, remplacements):
    """Ecrit dans le dossier temporaire une copie de `script` aux constantes substituees.

    Le fichier d'origine n'est jamais ecrit : on lit son source, on remplace les affectations de
    constantes en memoire, et on ecrit le resultat dans un fichier temporaire execute ensuite comme
    un script ordinaire. Toute constante absente fait echouer l'orchestrateur avant l'execution.

    (Ne pas passer par exec() d'une chaine : l'encodage des antislashs y est decode deux fois, ce
    qui casse les chemins Windows — c'est un piege constate sur cette machine.)
    """
    source = io.open(script, encoding="utf-8").read()
    for nom, valeur in remplacements.items():
        motif = re.compile(r"^%s\s*=\s*(r?)([\"']).*?\2\s*$" % re.escape(nom), re.M)
        if not motif.search(source):
            raise SystemExit("constante %s introuvable dans %s : arret avant execution"
                             % (nom, os.path.basename(script)))
        # remplacement par fonction : avec une chaine, re.sub interprete les antislashs du texte
        # insere comme des references de groupe et casse les chemins Windows (piege constate ici).
        source = motif.sub(lambda m, n=nom, v=valeur: "%s = %s" % (n, json.dumps(v)),
                           source, count=1)
    chemin = os.path.join(tempfile.gettempdir(),
                          "lanceur_%s_%d.py" % (os.path.splitext(os.path.basename(script))[0],
                                                os.getpid()))
    with io.open(chemin, "w", encoding="utf-8", newline="\n") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# Copie temporaire de %s, constantes substituees par pipeline_video.py.\n"
                "# Le fichier d'origine n'est pas modifie. Ce fichier disparait apres l'etape.\n"
                % os.path.basename(script))
        f.write(source)
    return chemin


def verifier_constantes(script, noms):
    source = io.open(script, encoding="utf-8").read()
    manquantes = [n for n in noms
                  if not re.search(r"^%s\s*=" % re.escape(n), source, re.M)]
    return manquantes


# --------------------------------------------------------------------------- pipeline

def construire_plan(a):
    """Rend la liste des etapes a executer, chacune avec ses fichiers d'entree et de sortie."""
    script = os.path.abspath(a.script)
    voix = a.voix
    source_nom = a.source
    dossier_source = os.path.join(DATA_VIDEO, source_nom)

    gen = plus_recent("gen_voice_v*.py")
    ls = plus_recent("run_latentsync_v8*.py")
    if not gen or not ls:
        raise SystemExit("generateur ou script LatentSync introuvable dans %s" % HERE)

    seg_ls = re.search(r"^SEG\s*=\s*([\d.]+)", io.open(ls, encoding="utf-8").read(), re.M)
    seg = float(seg_ls.group(1)) if seg_ls else None

    tts = os.path.join(HERE, "scripts_tts", "%s_tts.txt" % os.path.splitext(os.path.basename(script))[0])
    audio = os.path.join(HERE, "volet4_voice_%s.wav" % voix)
    segments_x = os.path.join(HERE, "segments_%s" % voix)
    work = os.path.join(HERE, "ls_segments_%s_%s" % (source_nom, voix))
    video_ls = os.path.join(HERE, "latentsync_%s_%s.mp4" % (source_nom, voix))
    final = os.path.join(HERE, "youtube_volet4_hermes_FINAL_%s.mp4" % voix)
    source_720 = os.path.join(dossier_source, "source_720p_25fps_clean.mp4")
    source_4k = os.path.join(dossier_source, "source_4k_25fps_clean.mp4")

    etapes = []
    etapes.append({"n": 1, "nom": NOMS_ETAPES[1], "entre": [script], "sort": [tts],
                   "cmd": [PY_STD, os.path.join(HERE, "preparer_script_tts.py"), script,
                           "-o", tts, "--rapport"]})
    etapes.append({"n": 2, "nom": NOMS_ETAPES[2], "entre": [tts], "sort": [audio],
                   "genere": (gen, {"SCRIPT": tts, "FULL": audio, "OUT_DIR": segments_x}),
                   "env": {"PYTHON": VENV_XTTS}})
    etapes.append({"n": 3, "nom": NOMS_ETAPES[3], "entre": [audio], "sort": [],
                   "plan": {"seg": seg, "cycle": CYCLE_PINGPONG}})
    etapes.append({"n": 4, "nom": NOMS_ETAPES[4], "entre": [audio, source_720], "sort": [video_ls],
                   "genere": (ls, {"AUDIO": audio, "WORK": work, "FINAL": video_ls,
                                   "SRC": source_720})})
    etapes.append({"n": 5, "nom": NOMS_ETAPES[5], "entre": [video_ls, audio, source_4k],
                   "sort": [final],
                   "cmd": [VENV_LS, os.path.join(HERE, "assemble_v6.py"), "run"],
                   "env": {"V4_LSOUT": video_ls, "V4_WAV": audio, "V4_SEGDIR": work,
                           "V4_SRC4K": source_4k, "V4_OUT": final, "V4_SANS_QUALITE": "1"}})
    etapes.append({"n": 6, "nom": NOMS_ETAPES[6], "entre": [final, source_4k], "sort": [],
                   "cmd": [VENV_LS, os.path.join(HERE, "controle_qualite.py"), final,
                           "--source", source_4k]})
    return etapes


def verifier(a, etapes):
    """Verifications avant execution : entrees presentes, sorties non ecrasees, outils la."""
    problemes, avertissements = [], []
    for chemin, pourquoi in ((VENV_XTTS, "venv XTTS"), (VENV_LS, "venv LatentSync"),
                             (os.path.join(HERE, "assemble_v6.py"), "assemble_v6.py"),
                             (os.path.join(HERE, "controle_qualite.py"), "controle_qualite.py"),
                             (os.path.join(HERE, "preparer_script_tts.py"), "preparer_script_tts.py")):
        if not os.path.exists(chemin):
            problemes.append("%s introuvable : %s" % (pourquoi, chemin))
    if not os.path.exists(a.script):
        problemes.append("script introuvable : %s" % a.script)
    produites = set()
    for e in etapes:
        produites.update(e["sort"])
    for e in etapes:
        for f in e["entre"]:
            if not os.path.exists(f) and f not in produites:
                problemes.append("etape %d : entree absente et non produite par le pipeline : %s"
                                 % (e["n"], f))
        for f in e["sort"]:
            if os.path.exists(f) and not a.force:
                if a.sans_etape and e["n"] < a.sans_etape:
                    continue
                problemes.append("etape %d : %s existe deja — rien n'est ecrase sans --force"
                                 % (e["n"], os.path.basename(f)))
    if os.path.exists(a.script):
        if "FINAL" in os.path.basename(a.script).upper():
            avertissements.append("le script fourni est un fichier livre : l'orchestrateur ne le "
                                  "modifie jamais, mais verifier que c'est bien l'intention")
    return problemes, avertissements


def executer(a, etapes, journal):
    resultats = []
    t0 = time.time()
    for e in etapes:
        if e["n"] < (a.sans_etape or 1):
            journal.append("etape %d — ignoree (reprise a l'etape %s)" % (e["n"], a.sans_etape))
            continue
        debut = time.time()
        journal.append("")
        journal.append("--- etape %d : %s" % (e["n"], e["nom"]))
        if e["n"] == 3:
            d = duree_media(e["entre"][0])
            seg = e["plan"]["seg"]
            if d is None or not seg:
                journal.append("    duree illisible ou SEG introuvable : plan non verifie")
                resultats.append({"n": 3, "nom": e["nom"], "code": 0, "duree": time.time() - debut})
                continue
            n = int(d // seg)
            reste = d - n * seg
            journal.append("    audio %.2f s | segment 48 s = %.1f cycles ping-pong" % (d, seg / CYCLE_PINGPONG))
            journal.append("    plan : %d segment(s) complet(s) + reste %.2f s -> %d appel(s) LatentSync"
                           % (n, reste, n + (1 if reste > 0.05 else 0)))
            journal.append("    la decoupe reelle est faite par run_latentsync (phase + silences de fin)")
            resultats.append({"n": 3, "nom": e["nom"], "code": 0, "duree": time.time() - debut})
            continue

        if e.get("genere"):
            script, remplacements = e["genere"]
            avant = empreinte(script)
            chemin = lanceur_substitution(script, remplacements)
            environnement = e.get("env") and {"PYTHONPATH": ""} or None
            python = (e.get("env") or {}).get("PYTHON") or PY_STD
            code, sortie, duree = lancer([python, chemin], environnement)
            apres = empreinte(script)
            journal.append("    %s execute avec ses constantes substituees (mempreinte %s -> %s)%s"
                           % (os.path.basename(script), avant, apres,
                              "" if avant == apres else "  *** FICHIER MODIFIE ***"))
            if avant != apres:
                journal.append("    ARRET : le script d'origine a change, ce n'est pas permis")
                return resultats + [{"n": e["n"], "nom": e["nom"], "code": 99, "duree": duree,
                                     "sortie": sortie[-1500:]}], time.time() - t0
            try:
                os.remove(chemin)
            except OSError:
                pass
        else:
            code, sortie, duree = lancer(e["cmd"], e.get("env"))

        journal.append("    duree : %.1f s | code %d" % (duree, code))
        for ligne in [l for l in sortie.splitlines() if l.strip()][-6:]:
            journal.append("    | %s" % ligne[:160])
        resultats.append({"n": e["n"], "nom": e["nom"], "code": code, "duree": duree,
                          "sortie": sortie})
        if code != 0:
            journal.append("    ARRET : l'etape %d a echoue (code %d). Rien n'est supprime, "
                           "reprendre avec --sans-etape %d" % (e["n"], code, e["n"]))
            return resultats, time.time() - t0
    return resultats, time.time() - t0


def main():
    p = argparse.ArgumentParser(description="Orchestrateur du pipeline video (volet Hermes).")
    p.add_argument("--script", required=True)
    p.add_argument("--voix", default="v9")
    p.add_argument("--source", default="p1002837")
    p.add_argument("--qualite", action="store_true", help="ajoute le controle qualite (etape 6)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--sans-etape", type=int, default=None, dest="sans_etape")
    p.add_argument("--force", action="store_true")
    a = p.parse_args()

    etapes = construire_plan(a)
    if not a.qualite:
        etapes = [e for e in etapes if e["n"] != 6]
    problemes, avertissements = verifier(a, etapes)

    journal = []
    journal.append("ORCHESTRATEUR PIPELINE VIDEO — %s"
                   % datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    journal.append("script : %s | voix : %s | source : %s | qualite : %s"
                   % (a.script, a.voix, a.source, "oui" if a.qualite else "non"))
    journal.append("")
    journal.append("ETAPES PREVUES")
    for e in etapes:
        marque = "ignoree" if (a.sans_etape and e["n"] < a.sans_etape) else "a executer"
        journal.append("  %d. %-46s [%s]" % (e["n"], e["nom"], marque))
        for f in e["sort"]:
            journal.append("       -> %s" % f)
        if e.get("genere"):
            journal.append("       appel : %s (constantes substituees)"
                           % os.path.basename(e["genere"][0]))
        elif e.get("cmd"):
            journal.append("       appel : %s" % " ".join(os.path.basename(c) for c in e["cmd"]))
    if avertissements:
        journal.append("")
        journal.append("AVERTISSEMENTS")
        for w in avertissements:
            journal.append("  - %s" % w)
    if problemes:
        journal.append("")
        journal.append("ARRET AVANT EXECUTION")
        for pb in problemes:
            journal.append("  - %s" % pb)
        texte = "\n".join(journal)
        print(texte)
        return 2

    if a.dry_run:
        journal.append("")
        journal.append("--dry-run : rien n'a ete execute.")
        print("\n".join(journal))
        return 0

    t0 = time.time()
    # les dossiers de sortie doivent exister : les scripts appeles n'ont pas tous cette logique
    for e in etapes:
        for f in e["sort"]:
            dossier = os.path.dirname(f)
            if dossier and not os.path.isdir(dossier):
                os.makedirs(dossier, exist_ok=True)
                journal.append("dossier cree : %s" % dossier)
    resultats, total = executer(a, etapes, journal)
    code_final = 0
    verdict = None
    for e in etapes:
        if e["n"] == 6:
            r = [x for x in resultats if x.get("n") == 6]
            if r and r[0].get("code") == 0:
                m = re.search(r"rapport ecrit : (.+)", r[0].get("sortie", ""))
                if m:
                    try:
                        d = json.load(io.open(m.group(1).strip(), encoding="utf-8"))
                        verdict = "%s (code %s)" % (d["verdict"], d["code"])
                    except Exception as ex:
                        verdict = "rapport illisible (%s)" % ex
                else:
                    verdict = "verdict dans la sortie ci-dessus"

    journal.append("")
    journal.append("BILAN")
    journal.append("  duree totale : %.1f s (%.1f min)" % (total, total / 60))
    for r in resultats:
        journal.append("  etape %d %-46s %7.1f s  code %s"
                       % (r["n"], r["nom"], r["duree"], r["code"]))
        if r.get("code") not in (0, None):
            code_final = r["code"]
    if verdict:
        journal.append("  verdict qualite : %s" % verdict)
    for e in etapes:
        for f in e["sort"]:
            if os.path.exists(f):
                journal.append("  fichier : %s (%.1f Mo)" % (f, os.path.getsize(f) / 1e6))
    if code_final:
        journal.append("  ARRET SUR ECHEC — reprendre avec --sans-etape %d"
                       % (resultats[-1]["n"] if resultats else 1))

    texte = "\n".join(journal)
    horodatage = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    chemin = os.path.join(HERE, "pipeline_%s.txt" % horodatage)
    with io.open(chemin, "w", encoding="utf-8") as f:
        f.write(texte + "\n")
    print(texte)
    print("\nrapport ecrit : %s" % chemin)
    return 1 if code_final else 0


if __name__ == "__main__":
    sys.exit(main())
