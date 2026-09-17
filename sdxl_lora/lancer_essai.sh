#!/bin/bash
# Essai court LoRA visage — 1500 pas, plafond 3 h, surveillance VRAM.
#   bash lancer_essai.sh
# Journal : entrainement.log (sortie kohya/diffusers) | vram.log (une mesure / 30 s)
V="$LOCALAPPDATA/hermes/data/sdxl_lora"
cd "$V" || exit 1
rm -f vram.log entrainement.log

# --- moniteur VRAM en tache de fond (3 h max de mesures) ---
(
  for i in $(seq 1 380); do
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits >> vram.log 2>/dev/null
    sleep 30
  done
) &
MON=$!

# --- entrainement, plafond strict de 3 h ---
timeout 10800 "$V/venv/Scripts/python.exe" -m accelerate.commands.launch \
  --num_processes 1 --mixed_precision fp16 \
  "$V/train_lora_sdxl.py" \
  --pretrained_model_name_or_path="$V/sdxl_base_diffusers" \
  --instance_data_dir="C:/Users/searc/Desktop/40 tof de moi/lora_visage/essai_court" \
  --instance_prompt="thomasl, photo de Thomas Leroyer, homme français" \
  --resolution=768 --train_batch_size=1 --gradient_accumulation_steps=4 \
  --gradient_checkpointing --use_8bit_adam --allow_tf32 \
  --learning_rate=1e-4 --lr_scheduler=cosine --lr_warmup_steps=100 \
  --max_train_steps=1500 --rank=16 --checkpointing_steps=500 --seed=42 \
  --output_dir="$V/lora_essai" --mixed_precision=fp16 \
  --checkpoints_total_limit=4 --report_to=tensorboard \
  > entrainement.log 2>&1
echo "code : $?" >> entrainement.log
kill $MON 2>/dev/null
