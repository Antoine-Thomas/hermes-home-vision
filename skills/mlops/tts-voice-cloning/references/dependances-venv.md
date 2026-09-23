# Dependances de venv : Python / numpy / scikit-image (volet 6, 22-23/09/2026)

Ce fichier est range ici a la demande de l'utilisateur ; le venv concerne est celui du pipeline
talking-head (LatentSync), pas celui de XTTS. Il s'applique a **tout venv Python de cette machine**
qui contient `scikit-image`, `insightface` ou `opencv-python`.

## Compatibilites Python / numpy / skimage

| Python | numpy | scikit-image | Etat |
|--------|-------|--------------|------|
| 3.10 (venv LatentSync, `Python 3.10.11`) | **1.26.4** | **0.22.0** | verifie OK (`import numpy, skimage` passe) |
| 3.11 | numpy 2.x | skimage >= 0.23 | OK (les roues 2.x sont compilees cp311) |

Contradiction a ne jamais oublier : `numpy 2.x` **fonctionne** en 3.11 et **casse** un venv 3.10
qui contient scikit-image 0.22.0 (compile contre l'ABI numpy 1.x).

## Erreurs reelles et leurs messages exacts

**numpy non pin dans un venv 3.10 (E1, 23/09 03:02 — `etapes_hfi_6.log`)**

```
No module named 'numpy._core._multiarray_umath'
  * _multiarray_umath.cp311-win_amd64.lib
  * _multiarray_umath.cp311-win_amd64.pyd
  * The Python version is: Python 3.10 from "...LatentSync\venv\Scripts\python.exe"
  * The NumPy version is: "2.4.3"
```

Cause : `pip install numpy` (sans pin) a installe une roue **cp311** dans un venv **3.10**.
Le suffixe du fichier manquant (`cp311`) EST le diagnostic : il nomme la version de Python pour
laquelle la roue a ete compilee. Remede : `numpy==1.26.4`.

**skimage casse par numpy 2.x (E2, 18/09 20:12)**

```
File "...\skimage\__init__.py", line 122, in <module>
  from ._shared import geometry
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
            Expected 96 from C header, got 88 from PyObject
```

Cause : scikit-image 0.22.0 est compile contre l'ABI numpy 1.x ; numpy 2.x change la taille de
`numpy.dtype` (96 -> 88) et casse l'import au premier module Cython (`geometry.pyx`).
Remede : `numpy==1.26.4` (le couple 1.26.4 + skimage 0.22.0 est le dernier de la branche 1.x).

Symptome voisin, meme cause, hors skimage : `OpenCV bindings requires "numpy" package / pip install
numpy` en tete de log = cv2 importe avant un numpy casse. Ne pas croire qu'il faut installer numpy :
verifier d'abord la version installee.

## Regle

**Ne jamais faire `pip install numpy` sans pin dans un venv qui contient scikit-image ou
insightface.** Installer par le fichier de contraintes :

```bash
# chemin du fichier (hors depot git : data/ est ignore)
C:\Users\searc\AppData\Local\hermes\data\video_youtube\requirements-latentsync.txt

C:/Users/searc/AppData/Local/hermes/data/video_youtube/LatentSync/venv/Scripts/python.exe \
    -m pip install -r requirements-latentsync.txt
```

Les roues cu121 de torch exigent en plus `--extra-index-url https://download.pytorch.org/whl/cu121`
(un simple `pip install torch==2.5.1+cu121` sans cet index echoue).

## Verifier (30 s, avant tout run long)

```bash
VP=C:/Users/searc/AppData/Local/hermes/data/video_youtube/LatentSync/venv/Scripts/python.exe
"$VP" -c "import sys,numpy,skimage,cv2,insightface,onnxruntime,torch;\
print(sys.version.split()[0],numpy.__version__,skimage.__version__,cv2.__version__,torch.__version__)"
```

Une version qui s'affiche vaut une preuve d'import ; un `ls` du venv ne prouve rien (le dossier
survit a la casse). Etat attendu : `3.10.11 1.26.4 0.22.0 4.11.0 2.5.1+cu121`.
