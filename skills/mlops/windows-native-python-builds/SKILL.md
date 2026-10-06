---
name: windows-native-python-builds
description: "Compiler des paquets Python natifs sous Windows."
version: "1.0.0"
author: Searching Murphy
license: MIT
tags:
  - python
  - windows
  - compilation
  - cmake
  - visual-studio
  - dlib
---

# windows-native-python-builds

Compiler des paquets Python natifs sous Windows quand aucun wheel
précompilé n'existe (dlib, insightface, fairseq, deepspeed, etc.) avec
Visual Studio 2026 BuildTools et cmake.

## Quand utiliser ce skill

- pip install échoue avec "no matching distribution" ou tente un build
  source qui plante
- le paquet a des wheels Linux/macOS mais pas Windows
- Visual Studio 2026 BuildTools (MSVC 14.51) est installé
- Python 3.8-3.11 selon les cas

## CHAÎNE PROUVÉE : dlib 19.24.0 sur Windows + Python 3.8 + VS 2026

CONTEXTE : ce poste a Visual Studio 2026 BuildTools (MSVC 14.51),
Python 3.8.20 (uv cpython-3.8-windows-x86_64-none), et n'a AUCUN wheel
Windows pour dlib==19.24.0 (seulement des wheels Linux/macOS sur PyPI).

Trois obstacles en chaîne, tous résolus :

OBSTACLE 1 — cmake du venv invisible du process natif
Le PATH git-bash (forme MSYS /c/Users/...) est mal traduit quand on lance
python.exe natif. cmake.exe est bien dans .venv/Scripts mais l'enfant ne
le voit pas.
SOLUTION : construire un PATH natif côté Python, ne pas compter sur bash.

    SCRIPTS = D.replace("/", "\\") + "\\.venv\\Scripts"
    env = dict(os.environ)
    env["PATH"] = SCRIPTS + os.pathsep + env.get("PATH", "")
    for k in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        env.pop(k, None)
    subprocess.run([PY, "setup.py", "bdist_wheel"], env=env, cwd=SRC)

OBSTACLE 2 — CMake 4.4.4 a supprimé la compatibilité < 3.5
Erreur : « Compatibility with CMake < 3.5 has been removed ».
Le code de dlib 19.24.0 utilise cmake_minimum_required(VERSION 2.8).
SOLUTION : passer la variable CMAKE_POLICY_VERSION_MINIMUM=3.5.

OBSTACLE 3 — le -D ne propage pas dans les try_compile imbriqués
dlib teste SSE4 via un try_compile qui lance un cmake enfant. Le -D passé
au cmake racine n'est PAS hérité par ce sous-cmake → le test SSE4 échoue.
SOLUTION : passer CMAKE_POLICY_VERSION_MINIMUM=3.5 en VARIABLE
D'ENVIRONNEMENT (pas en -D), ce qui la propage aux cmake imbriqués.

    env["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    rc = run([PY, "setup.py", "--clean", "--set",
              "CMAKE_POLICY_VERSION_MINIMUM=3.5", "bdist_wheel"], cwd=SRC)

POURQUOI PAS CMake 3.31.6 : cette version ne connaît PAS le générateur
« Visual Studio 18 2026 » (VS 2026 BuildTools) et retombe sur NMake, que
dlib refuse (« You must use Visual Studio »). Il FAUT cmake ≥ 4.x, donc
il FAUT le contournement du policy minimum.

COMMANDE MINIMALE QUI MARCHE :
1. pip install cmake==4.4.4
2. Télécharger le sdist dlib-19.24.0.tar.gz, extraire
3. Dans le dossier extrait :
   set CMAKE_POLICY_VERSION_MINIMUM=3.5
   python setup.py --clean --set CMAKE_POLICY_VERSION_MINIMUM=3.5 bdist_wheel
4. pip install dist/dlib-19.24.0-cp38-cp38-win_amd64.whl
5. CONSERVER le wheel :
   wheels/dlib-19.24.0-cp38-cp38-win_amd64.whl
   sha256 3bac1bd348b1f701c6a8daf5d98439be0c101e759cc6a989299061eb4b95b370

AUTRES PINS UTILES (découverts dans la même session) :
- lmdb==1.8.1              (seul wheel cp38 win_amd64 ; 3.0.0 échoue au link)
- opencv-python==4.8.1.78  (pip choisit 5.x par défaut, incompatible
                            numpy 1.23.4)
- torch==2.1.0+cu121, torchvision==0.16.0+cu121 via
  pip install torch==2.1.0 torchvision==0.16.0 --index-url
  https://download.pytorch.org/whl/cu121

PRÉ-TÉLÉCHARGEMENT DES POIDS RUNTIME :
Certains modèles (ex. s3fd-619a316812.pth du face_detection de VR) se
téléchargent au runtime depuis un domaine parfois mort. Les pré-placer
dans ~/.cache/torch/hub/checkpoints/ et valider avec load_state_dict
avant la session.
