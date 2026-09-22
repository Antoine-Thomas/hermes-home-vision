#!/usr/bin/env python
"""Sonde lecture seule : le snapshot du prompt des skills est-il a jour ?

Le snapshot (%%LOCALAPPDATA%%/hermes/.skills_prompt_snapshot.json) n'est reutilise que si sa
`version` ET son `manifest` (signature fichier de chaque SKILL.md/DESCRIPTION.md sous skills/)
correspondent encore au disque. Ajouter / retirer / editer un skill change le manifest =>
reconstruction au prochain prompt, sans redemarrage de gateway. A l'inverse, un changement qui
ne touche AUCUN fichier (ex. `skills.disabled` dans config.yaml) laisse le manifest identique :
là, et là seulement, le snapshot doit etre supprime a la main.

Usage (interpreteur du venv Hermes : le script importe le code installe) :
    PY="C:/Users/<user>/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
    "$PY" check_skills_snapshot.py [nom_de_skill ...]

Pieges encodés ici :
  * `get_hermes_home` vit dans `hermes_constants`, PAS dans `agent.config`.
  * le code Hermes n'est importable qu'apres ajout du dossier d'install a `sys.path`.
  * `_build_skills_manifest` / `_load_skills_snapshot` sont prives : si un import casse apres
    une mise a jour de Hermes, relire `agent/prompt_builder.py` et realigner les noms.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    install = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "hermes-agent"
    if not install.is_dir():
        print("Install Hermes introuvable :", install)
        return 2
    sys.path.insert(0, str(install))

    from hermes_constants import get_hermes_home  # noqa: E402
    from agent.prompt_builder import (  # noqa: E402
        _SKILLS_SNAPSHOT_VERSION,
        _build_skills_manifest,
        _load_skills_snapshot,
    )

    home = get_hermes_home()
    skills_dir = home / "skills"
    snap_path = home / ".skills_prompt_snapshot.json"

    manifest = _build_skills_manifest(skills_dir)
    try:
        snap = json.loads(snap_path.read_text(encoding="utf-8"))
    except Exception as exc:  # absent, illisible ou corrompu -> rebuild
        print("snapshot  : illisible ou absent (%s)" % type(exc).__name__)
        snap = None

    if snap is None:
        print("etat      : aucun snapshot exploitable -> prompt reconstruit au prochain appel")
    else:
        same = snap.get("manifest") == manifest
        print("version   : code=%s / snapshot=%s" % (_SKILLS_SNAPSHOT_VERSION, snap.get("version")))
        print("etat      :", "a jour (manifest identique) -> snapshot reutilise"
              if same else "invalide (manifest different) -> reconstruit au prochain prompt")

    print("disque    : %d entrees SKILL.md/DESCRIPTION.md" % len(manifest))
    for name in argv:
        hits = sorted(k for k in manifest if name in k)
        print("  %-24s %s" % (name, "vu -> " + ", ".join(hits) if hits
                              else "ABSENT du manifest (dossier ou nom de frontmatter different ?)"))
    print("sonde     : _load_skills_snapshot() ->",
          "None (reconstruit)" if _load_skills_snapshot(skills_dir) is None else "snapshot reutilise")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
