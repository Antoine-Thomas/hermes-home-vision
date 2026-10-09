# kohya / sd-scripts — stack, layout, benchmark, failure table

## The WSL2 stack that works

Run every command from Windows through `wsl.exe` as root: no interactive user creation, no
sudo password.

```bash
wsl.exe -d Ubuntu-22.04 -u root -e bash -lc "<command>"
```

Install a dedicated distro **alongside** the default one — never replace the user's default:

```bash
# Import an official rootfs: no UAC, fully non-interactive.
# Read the index and take the real filename — do not guess it.
curl -sL https://cloud-images.ubuntu.com/wsl/jammy/current/ | grep -oE 'href="[^"]+\.tar\.gz"'
# -> ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz     (~341 MB)
wsl.exe --import Ubuntu-22.04 "C:\Users\<user>\AppData\Local\WSL\Ubuntu-22.04" \
  "C:\Users\<user>\AppData\Local\WSL\Ubuntu-22.04\rootfs.tar.gz" --version 2
wsl.exe -d Ubuntu-22.04 -u root -e uname -a      # verify it answers before continuing
```

`wsl --install -d <distro> --no-launch` also works but is slow and silent — see the
"do not declare failure early" rule in SKILL.md.

A wrong rootfs URL returns a 0-byte file and then fails with `Unrecognized archive format` from
bsdtar, which looks like a broken import method. Check the downloaded size before believing the
method is at fault.

Toolchain:

```bash
apt-get update && apt-get install -y build-essential git curl wget python3.10 python3.10-venv python3-pip
python3.10 -m venv ~/sdxl_lora_wsl/venv && source ~/sdxl_lora_wsl/venv/bin/activate
pip install torch==2.4.1 torchvision --index-url https://download.pytorch.org/whl/cu121
# no CUDA toolkit needed; verify:
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# -> 2.4.1+cu121 True NVIDIA GeForce RTX 3070 Ti
```

Pick the distro release for the Python the AI wheels are built against (22.04 / python3.10 is the
tested pairing; a newer release shipping python3.13+ has no wheels for most AI stacks yet).

Trainer — **two repositories** (this is the usual trap):

```bash
git clone https://github.com/bmaltais/kohya_ss.git         # GUI + launcher, no CLI training script
git clone https://github.com/kohya-ss/sd-scripts.git       # <- sdxl_train_network.py lives HERE
cd sd-scripts && pip install -r requirements.txt
pip install "transformers==4.57.6" "diffusers==0.36.0" accelerate peft
```

## Data

Copy images into WSL's native filesystem for training (do not train across `/mnt/c`); a multi-GB
base model can be read from `/mnt/c` through a symlink instead of being copied.

kohya layout — a subfolder named `<repeats>_<concept>` holding the images **and** their `.txt`
captions side by side:

```
dataset/10_thomasl/
  3-4g_neutre_01.png
  3-4g_neutre_01.txt     <- same basename
```

## Benchmark: 3 steps before any long run

```bash
accelerate launch --num_processes 1 --mixed_precision fp16 sdxl_train_network.py \
  --pretrained_model_name_or_path=<model.safetensors> \
  --train_data_dir=<dataset> --output_dir=<out> --output_name=bench \
  --resolution=1024 --train_batch_size=1 --gradient_accumulation_steps=4 \
  --gradient_checkpointing --learning_rate=1e-4 --lr_scheduler=cosine \
  --max_train_steps=3 --network_module=networks.lora --network_dim=16 --network_alpha=8 \
  --mixed_precision=fp16 --save_every_n_steps=99999 --seed=42 --max_data_loader_n_workers=2
```

Sample VRAM in parallel
(`/usr/lib/wsl/lib/nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` in a loop) and
keep a hard `timeout` around the run. Read the FINAL average `s/it`, not a live bar.

## Failure table — kohya and the diffusers DreamBooth example

| Symptom | Cause | Fix |
|---|---|---|
| `trying to load the model files of the variant=fp16, but no such modeling files are available` | pointing at a diffusers-format folder that holds only default weights | pass the single-file `.safetensors` checkpoint (native kohya format), or write the fp16 variant |
| `./sd-scripts is not a valid editable requirement` | kohya's requirements reference an uncloned sibling repo | clone `kohya-ss/sd-scripts` and install *its* requirements |
| `This example requires a source install from HuggingFace diffusers` | the example script's `check_min_version("X.dev0")` guard rejects the released version | neutralize that single line — a source install is not needed |
| `unrecognized arguments: --use_adafactor` | that flag no longer exists in sd-scripts | use `--optimizer=adafactor` |
| `ValueError: Unsupported logging capability: none` | accelerate rejects `--report_to=none` | install tensorboard and use `--report_to=tensorboard` |
| `PIL.UnidentifiedImageError: cannot identify image file '...txt'` / `PermissionError ... '<dir>'` | the example script opens **every** entry of the instance directory as an image | keep images alone in that directory; put captions in a separate folder |
| 50-500 s/step, GPU at 100 % with the memory controller at ~1 % | compute-side pathology on the Windows stack, not a memory ceiling | move training to WSL2 |

## Windows/WSL command quirks

- `nvidia-smi` is usually not on PATH inside WSL; the binary is `/usr/lib/wsl/lib/nvidia-smi`.
- `wsl.exe` output is UTF-16 — pipe through `tr -d '\0'` before grepping.
- Inside `wsl.exe ... bash -lc "..."`, escape `$(` as `\$(` so the outer shell does not expand it.
- `sd-scripts` is the maintained CLI; `--network_module=networks.lora` is what makes it a LoRA run.
