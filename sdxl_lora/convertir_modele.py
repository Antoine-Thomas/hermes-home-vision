# -*- coding: utf-8 -*-
"""Convertit le fichier unique SDXL (format kohya) au format diffusers (dossier).

    "<venv sdxl_lora>\\python.exe" convertir_modele.py

Aucun telechargement : tout se fait localement depuis sd_xl_base_1.0.safetensors (6,94 Go).
Sortie : sdxl_base_diffusers/  (~7 Go) — c'est ce dossier qu'attend train_dreambooth_lora_sdxl.py.
"""
import os
import time

import torch
from diffusers import StableDiffusionXLPipeline

V = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "sdxl_lora")
SOURCE = os.path.join(V, "sd_xl_base_1.0.safetensors")
CIBLE = os.path.join(V, "sdxl_base_diffusers")

if __name__ == "__main__":
    if os.path.exists(os.path.join(CIBLE, "model_index.json")):
        print("deja converti : %s" % CIBLE)
        raise SystemExit(0)
    print("chargement du fichier unique (peut prendre quelques minutes) ...", flush=True)
    t0 = time.time()
    pipe = StableDiffusionXLPipeline.from_single_file(
        SOURCE, torch_dtype=torch.float16, use_safetensors=True, local_files_only=True)
    print("  charge en %.0f s" % (time.time() - t0), flush=True)
    print("ecriture au format diffusers dans %s ..." % CIBLE, flush=True)
    pipe.save_pretrained(CIBLE, safe_serialization=True, max_shard_size="4GB")
    print("  termine en %.0f s" % (time.time() - t0), flush=True)
    for f in sorted(os.listdir(CIBLE))[:14]:
        print("   ", f)
