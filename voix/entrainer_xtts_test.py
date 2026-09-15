# -*- coding: utf-8 -*-
"""Etape B de l'essai XTTS : fine-tune court sur le sous-corpus de test.

    "<venv XTTS>\\python.exe" entrainer_xtts_test.py --epoques 1        # essai a blanc
    "<venv XTTS>\\python.exe" entrainer_xtts_test.py --epoques 40       # run long (a borner)

Difference avec la recette officielle (recipes/ljspeech/xtts_v2/train_gpt_xtts.py), adaptee a la
version installee (TTS 0.27.5) :
  - elle importe `XttsAudioConfig`, qui n'existe plus : la configuration audio vient de XttsConfig
    et la frequence est forcee a 22 050 Hz (frequence de XTTS v2) ;
  - elle telecharge le modele depuis internet : ici on utilise le modele XTTS v2 deja present dans
    le cache local (%LOCALAPPDATA%\\TTS\\...) ;
  - elle vise des dizaines de milliers d'etapes : ici le run est borne en epoques, avec un pas
    d'accumulation pour rester en lot 1 (8 Go de VRAM).

Ce que ce script NE fait PAS : aucune modification du modele de reference utilise par le pipeline
(`voix_reference.wav` n'est jamais touche) et aucun ecrasement d'un checkpoint existant.
"""
import argparse
import os
import sys

import torch
from trainer import Trainer, TrainerArgs

from TTS.config.shared_configs import BaseDatasetConfig
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.datasets import load_tts_samples
from TTS.tts.layers.xtts.trainer.gpt_trainer import GPTArgs, GPTTrainer, GPTTrainerConfig

CORPUS = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "data", "xtts", "corpus_test")
CACHE = os.path.join(os.environ["LOCALAPPDATA"], "TTS", "tts_models--multilingual--multi-dataset--xtts_v2")
SORTIE = os.path.join(CORPUS, "entrainement")
HORODATAGE = __import__("time").strftime("%Y%m%d_%H%M%S")

XTTS_CHECKPOINT = os.path.join(CACHE, "model.pth")
TOKENIZER_FILE = os.path.join(CACHE, "vocab.json")
DVAE_CHECKPOINT = os.path.join(CORPUS, "dvae.pth")
MEL_NORM_FILE = os.path.join(CORPUS, "mel_stats.pth")

PHRASES_TEST = [
    "WordPress en local avec Local by Flywheel.",
    "J'installe WooCommerce et je lance WP-CLI pour configurer nginx et MySQL.",
]

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--epoques", type=int, default=1)
    p.add_argument("--lot", type=int, default=1, help="taille de lot (VRAM)")
    p.add_argument("--accumulation", type=int, default=16)
    p.add_argument("--lr", type=float, default=5e-06)
    a = p.parse_args()

    for chemin, quoi in ((XTTS_CHECKPOINT, "modele XTTS v2"), (TOKENIZER_FILE, "vocabulaire"),
                         (DVAE_CHECKPOINT, "dvae.pth"), (MEL_NORM_FILE, "mel_stats.pth"),
                         (os.path.join(CORPUS, "metadata_train.csv"), "metadata_train.csv")):
        if not os.path.exists(chemin):
            raise SystemExit("%s introuvable : %s" % (quoi, chemin))

    os.makedirs(SORTIE, exist_ok=True)
    config_dataset = BaseDatasetConfig(formatter="ljspeech", dataset_name="voix_test",
                                       path=CORPUS, meta_file_train="metadata_train.csv",
                                       language="fr")

    model_args = GPTArgs(
        max_conditioning_length=132300,     # 6 s
        min_conditioning_length=66150,      # 3 s
        debug_loading_failures=False,
        max_wav_length=300000,              # ~13,6 s : mes segments font 12 s = 264 600 echantillons
                                            # (la valeur de la recette, 255995, les rejetait TOUS et le
                                            # chargeur partait en RecursionError silencieuse)
        max_text_length=200,
        mel_norm_file=MEL_NORM_FILE,
        dvae_checkpoint=DVAE_CHECKPOINT,
        xtts_checkpoint=XTTS_CHECKPOINT,
        tokenizer_file=TOKENIZER_FILE,
        gpt_num_audio_tokens=1026,
        gpt_start_audio_token=1024,
        gpt_stop_audio_token=1025,
        gpt_use_masking_gt_prompt_approach=True,
        gpt_use_perceiver_resampler=True,
    )

    config = GPTTrainerConfig(
        output_path=SORTIE,
        model_args=model_args,
        run_name="xtts_essai_%s" % HORODATAGE,
        project_name="hermes_xtts_test",
        run_description="Essai court sur 10 minutes de voix (corpus_test)",
        audio=XttsConfig().audio,
        epochs=a.epoques,
        batch_size=a.lot,
        eval_batch_size=a.lot,
        batch_group_size=0,
        num_loader_workers=0,   # workers DataLoader = RecursionError sous Windows
        print_step=10,
        plot_step=100,
        log_model_step=200,
        eval_split_size=0.02,    # 50 echantillons : en dessous, l'ensemble d'evaluation serait vide
        save_step=1000,
        save_n_checkpoints=1,
        save_checkpoints=True,
        print_eval=False,
        optimizer="AdamW",
        optimizer_wd_only_on_weights=True,
        optimizer_params={"betas": [0.9, 0.96], "eps": 1e-8, "weight_decay": 1e-2},
        lr=a.lr,
        lr_scheduler="MultiStepLR",
        lr_scheduler_params={"milestones": [2000, 6000, 12000], "gamma": 0.5, "last_epoch": -1},
        test_sentences=[{"text": t,
                         "speaker_wav": [os.path.join(CORPUS, "validation", "val_050.wav")],
                         "language": "fr"} for t in PHRASES_TEST],
    )
    config.audio.sample_rate = 22050          # frequence de XTTS v2 (le modele attend 22 050 Hz)

    print("XTTS v2 local : %s" % XTTS_CHECKPOINT, flush=True)
    print("corpus : %d epoques, lot %d, accumulation %d (lot effectif %d), lr %g"
          % (a.epoques, a.lot, a.accumulation, a.lot * a.accumulation, a.lr), flush=True)
    print("VRAM disponible avant depart : %.1f Go"
          % (torch.cuda.get_device_properties(0).total_memory / 1e9
             - torch.cuda.memory_allocated() / 1e9), flush=True)

    modele = GPTTrainer.init_from_config(config)
    donnees_train, donnees_eval = load_tts_samples([config_dataset], eval_split=True,
                                                   eval_split_max_size=config.eval_split_max_size,
                                                   eval_split_size=config.eval_split_size)
    print("echantillons : %d entrainement, %d evaluation" % (len(donnees_train), len(donnees_eval)),
          flush=True)

    entraineur = Trainer(TrainerArgs(restore_path=None, skip_train_epoch=False,
                                     start_with_eval=False, grad_accum_steps=a.accumulation),
                         config, output_path=SORTIE, model=modele,
                         train_samples=donnees_train, eval_samples=donnees_eval)
    entraineur.fit()
