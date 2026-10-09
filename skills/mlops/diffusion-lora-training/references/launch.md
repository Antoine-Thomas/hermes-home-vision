# Launch — the reference command, the sampler, and the flags that bite

Step 4 of the skill, in full detail. The launch is wrapped in a hard cap and paired with an independent
VRAM sampler, so a run that has to be killed still leaves evidence behind.

## The reference launch (SDXL, diffusers DreamBooth LoRA)

```bash
V="$LOCALAPPDATA/hermes/data/sdxl_lora"
cd "$V" && "$V/venv/Scripts/python.exe" -m accelerate.commands.launch \
  --num_processes 1 --mixed_precision fp16 "$V/train_lora_sdxl.py" \
  --pretrained_model_name_or_path="$V/sdxl_base_diffusers" \
  --instance_data_dir="<images only>" --instance_prompt="<trigger>" \
  --resolution=1024 --train_batch_size=1 --gradient_accumulation_steps=4 \
  --gradient_checkpointing --optimizer=adafactor \
  --learning_rate=1e-4 --lr_scheduler=cosine --lr_warmup_steps=100 \
  --max_train_steps=3 --rank=16 --checkpointing_steps=500 --seed=42 \
  --output_dir="$V/lora_essai" --mixed_precision=fp16 --report_to=tensorboard
```

- Wrap the launch in `timeout <seconds>` for a hard cap, and sample VRAM independently in the background
  (`nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` every 30 s into a file) so the max
  survives even if the run is killed at the cap. A ready-made sampler lives in `scripts/sampler_vram.sh`.
- Set `--checkpointing_steps` low enough that a trial actually writes something to test; a 500-step
  interval on a 3-step trial produces no artifact at all.
- Capture the run's log to a file and archive it before the next attempt overwrites it — an eight-line
  traceback is the whole diagnosis.
- For WSL2/kohya, the equivalent 3-step benchmark command (`sdxl_train_network.py`) is in
  `references/kohya-sd-scripts.md`, and it must also be sampled and hard-capped the same way.

## SD 1.5 recipe pitfalls (all hit in practice)

- The script needs `datasets` installed in the venv.
- `--dataloader_num_workers` must stay `0` on Windows, else workers die with
  `AttributeError: Can't pickle local object 'main.<locals>.preprocess_train'`.
- Images + `.txt` sidecars are NOT enough: `load_dataset("imagefolder")` only exposes the `text` column
  when a `metadata.jsonl` (`{"file_name": …, "text": …}` per line) sits in the folder, otherwise
  `--caption_column=text` fails with `needs to be one of: image`.
- `lora_alpha` is hardcoded to `args.rank` upstream — patch it when alpha ≠ rank.
- `--variant=fp16` works with the `stable-diffusion-v1-5/stable-diffusion-v1-5` repo.
- The HF repo is 45 GB total, of which ~23 GB are single-file `.ckpt`/`.safetensors` duplicates the
  diffusers script never reads.

## Checkpoint bookkeeping

- **`--checkpoints_total_limit` silently deletes the older checkpoints.** With `checkpointing_steps=300`
  and `total_limit=3`, only the last three survive (1200/1500/1800), so don't set a limit and then expect
  to inspect every intermediate. Each LoRA checkpoint is only ~13 MB of weights plus optimizer state —
  keeping all of them is cheap; cap the limit only if you truly need the disk.

## Flags that change what the model learns

- **`--random_flip` destroys left/right in captions.** With it on, "de trois-quarts gauche" and "de
  trois-quarts droite" are the same image to the model: it learns "head turned" but never which way.
  Leave it on for small datasets (it regularises), turn it off only once the set is ≥ 30 images, and do
  not advertise left/right control you cannot deliver.
- Check a flag exists in the script's own argparse before using it: `--use_adafactor` does not exist and
  `--optimizer=<name>` is the accepted form. See `references/pitfalls.md` for the flag traps that cost a
  full cycle.
