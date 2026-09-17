# -*- coding: utf-8 -*-
"""Reindexation automatique du RAG local (appelee par la tache planifiee « Hermes - Reindex RAG »).

Ce que fait le script :
  1. verifie que le noyau SiYuan repond sur 127.0.0.1:6806 — sinon il ne fait RIEN (l'index
     sans SiYuan serait ampute) et l'ecrit dans le journal ;
  2. compte les fragments avant ;
  3. lance indexer.py dans le venv du RAG ;
  4. compte les fragments apres, releve la taille de index.faiss, l'ecrit dans reindex.log.

Un verrou evite deux indexations simultanees. Le verrou est toujours retire a la fin, y compris
en cas d'erreur (finally), et un verrou orphelin (processus mort) est nettoye au demarrage.
"""
import datetime
import io
import json
import os
import subprocess
import sys
import urllib.request

RAG = os.path.dirname(os.path.abspath(__file__))
JOURNAL = os.path.join(RAG, "reindex.log")
VERROU = os.path.join(RAG, "reindex.lock")
PYTHON = os.path.join(RAG, "venv", "Scripts", "python.exe")
SIYUAN = "http://127.0.0.1:6806"


def journal(message):
    ligne = "%s | %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
    print(ligne, flush=True)
    with io.open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(ligne + "\n")


def siyuan_vivant():
    """Le noyau repond-il ? On accepte 401/403 : cela prouve qu'il ecoute."""
    for url in ("%s/api/system/version" % SIYUAN, "%s/" % SIYUAN):
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return True
        except Exception:
            continue
    return False


def fragments():
    manifeste = os.path.join(RAG, "manifeste.json")
    if not os.path.exists(manifeste):
        return None
    try:
        d = json.load(io.open(manifeste, encoding="utf-8"))
        return d.get("fragments")
    except Exception:
        return None


def taille_index():
    chemin = os.path.join(RAG, "index.faiss")
    if not os.path.exists(chemin):
        return None
    return round(os.path.getsize(chemin) / 1e6, 1)


def verrou_orphelin():
    """Un verrou dont le processus n'existe plus ne doit pas bloquer les nuits suivantes."""
    if not os.path.exists(VERROU):
        return
    try:
        pid = int(io.open(VERROU, encoding="utf-8").read().strip() or 0)
    except Exception:
        pid = 0
    vivant = False
    if pid:
        try:
            r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid], capture_output=True, text=True)
            vivant = str(pid) in (r.stdout or "")
        except Exception:
            vivant = False
    if vivant:
        journal("une indexation est deja en cours (PID %d) : rien a faire" % pid)
        sys.exit(0)
    os.remove(VERROU)
    journal("verrou orphelin retire (PID %d n'existe plus)" % pid)


if __name__ == "__main__":
    if not os.path.exists(PYTHON):
        journal("ERREUR : venv du RAG introuvable (%s)" % PYTHON)
        sys.exit(1)

    verrou_orphelin()
    if os.path.exists(VERROU):
        journal("verrou present : une autre indexation travaille, rien a faire")
        sys.exit(0)
    io.open(VERROU, "w", encoding="utf-8").write(str(os.getpid()))

    try:
        if not siyuan_vivant():
            journal("SiYuan ne repond pas sur %s : indexation reportee (aucune modification)"
                    % SIYUAN)
            sys.exit(0)

        avant = fragments()
        journal("debut d'indexation (fragments avant : %s)" % avant)
        t0 = __import__("time").time()
        r = subprocess.run([PYTHON, os.path.join(RAG, "indexer.py")],
                           capture_output=True, text=True, cwd=RAG)
        duree = __import__("time").time() - t0
        apres = fragments()
        if r.returncode != 0:
            journal("ECHEC indexation (code %d) : %s" % (r.returncode,
                    (r.stderr or r.stdout or "")[-300:].replace("\n", " ")))
            sys.exit(r.returncode)
        journal("indexation OK en %.0f s | fragments %s -> %s | index %s Mo"
                % (duree, avant, apres, taille_index()))
    finally:
        if os.path.exists(VERROU):
            os.remove(VERROU)
