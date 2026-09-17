# LatentSync 1.5 — installation (Windows, Python 3.10, RTX 3070 Ti 8 GB)

Le plus qualitatif des moteurs lip-sync locaux, et le plus lourd. Install dir sur cette machine :
`C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync`,
venv python `venv\Scripts\python.exe` (base : `...\Programs\Python\Python310\python.exe`).

**Venv séparé obligatoire.** Le `requirements.txt` épingle `torch==2.5.1` + cu121, incompatible
avec le `torch==2.0.1` + cu118 de MuseTalk. Un venv partagé casse l'un des deux.

## Install order

1. `git clone https://github.com/bytedance/LatentSync.git` puis `git checkout main`
2. `<Python310>\python.exe -m venv venv`
3. `./venv/Scripts/python.exe -m pip install --upgrade pip`
4. `./venv/Scripts/python.exe -m pip install -r requirements.txt`
5. Télécharger les poids 1.5 (voir plus bas) **avant** toute montée de `huggingface_hub`

`requirements.txt` utilise `--extra-index-url https://download.pytorch.org/whl/cu121` (pas
`--index-url`) : ne pas le remplacer, il a besoin de PyPI en plus de l'index CUDA.
Le fichier s'installe d'un bloc, sans les contorsions OpenMMLab de MuseTalk — résolu en une
passe (torch 2.5.1+cu121, torchvision 0.20.1+cu121, diffusers 0.32.2, transformers 4.48.0,
insightface 0.7.3, onnxruntime-gpu 1.21.0, mediapipe 0.10.11, decord 0.6.0, numpy 1.26.4).

## Piège principal : le repo `main` est 1.6, les poids 1.5 sont ailleurs

`github.com/bytedance/LatentSync` n'a **aucun tag** (`git tag` vide) et une seule branche
`origin/main`. Le README, `setup_env.sh` et le lien HuggingFace du README ciblent tous
`ByteDance/LatentSync-1.6`. Les poids 1.5 vivent dans un repo séparé,
**`ByteDance/LatentSync-1.5`**.

Frontière VRAM (README, section Inference) : **8 GB = 1.5**, **18 GB = 1.6**.

Conséquence directe sur 8 GB : `inference.sh` passe par défaut
`--unet_config_path "configs/unet/stage2_512.yaml"`, et ce fichier porte
`resolution: 512` — c'est la config 1.6, OOM attendu sur une 3070 Ti.

| Config | resolution | Pour |
|---|---|---|
| `configs/unet/stage2.yaml` | 256 | **1.5 — à utiliser sur 8 GB** |
| `configs/unet/stage2_efficient.yaml` | 256 | variante allégée |
| `configs/unet/stage2_512.yaml` | 512 | 1.6 — défaut de `inference.sh` |
| `configs/unet/stage1*.yaml` | — | entraînement, pas inférence |

Toujours vérifier avant de lancer : `grep -n resolution configs/unet/*.yaml`.

> Statut : l'installation et le chargement des checkpoints ont été validés ; l'inférence
> end-to-end 1.5 avec `stage2.yaml` n'a pas encore été exécutée sur cette machine.

## Poids requis

`setup_env.sh` ne télécharge que deux fichiers, et ils suffisent pour l'inférence :

```bash
./venv/Scripts/python.exe -c "
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id='ByteDance/LatentSync-1.5', filename='latentsync_unet.pt', local_dir='checkpoints')
hf_hub_download(repo_id='ByteDance/LatentSync-1.5', filename='whisper/tiny.pt', local_dir='checkpoints')"
```

Cible : `checkpoints/latentsync_unet.pt` (5 072 348 184 o) et
`checkpoints/whisper/tiny.pt` (75 572 083 o).

`hf_hub_download` crée l'arborescence intermédiaire (`checkpoints/whisper/`) — pas besoin de
`mkdir` préalable. Sans `hf_xet` installé, il retombe sur du HTTP classique :
`Xet Storage is enabled for this repo, but the 'hf_xet' package is not installed` —
avertissement, pas échec ; `pip install hf_xet` accélère.

## Vérifier les poids

**Ne jamais valider une taille de checkpoint à l'œil.** L'API HF donne la taille exacte en
octets et la liste des fichiers du repo :

```bash
curl -s "https://huggingface.co/api/models/ByteDance/LatentSync-1.5?blobs=true" | python -c "
import json,sys
for s in json.load(sys.stdin)['siblings']:
    sz = s.get('size'); print(f\"{(sz/1e6 if sz else 0):9.1f} MB  {s['rfilename']}\")"
```

Charger ensuite les `.pt` sans mettre 5 Go en RAM (`mmap=True`, torch >= 2.1) :

```bash
./venv/Scripts/python.exe -c "
import torch
for f in ['checkpoints/latentsync_unet.pt', 'checkpoints/whisper/tiny.pt']:
    d = torch.load(f, map_location='cpu', mmap=True)
    print(f, '->', list(d.keys()))"
```

Attendu : `['state_dict']` pour l'UNet, `['dims', 'model_state_dict']` pour `tiny.pt`.
`weights_only=False` émet un `FutureWarning` — normal, ce n'est pas une erreur.

Le repo contient aussi `auxiliary/` (vgg16, s3fd, i3d, syncnet, 2DFAN4 — dont un fichier de
2 Go) et `stable_syncnet.pt` (1,6 Go) : uniquement utiles pour l'entraînement et l'évaluation,
pas pour l'inférence. Ne pas les télécharger par défaut.

## Lancement

`python gradio_app.py` pour la GUI, ou `./inference.sh` en CLI — en corrigeant le config path
sur 8 GB (voir le tableau ci-dessus). Paramètres exposés : `inference_steps` [20-50]
(plus haut = meilleure qualité, plus lent), `guidance_scale` [1.0-3.0] (plus haut = sync plus
précise, mais distorsion/jitter possibles), `--enable_deepcache`.
