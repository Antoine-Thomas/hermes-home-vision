# EchoMimicV2 — Windows / 8 GB setup (verified 2026-09)

Repo: https://github.com/antgroup/echomimic_v2 (Ant Group). Audio-driven portrait
animation — the best free alternative to SadTalker when the user wants a LESS RIGID
face. Needs image + audio + a driving POSE sequence.

## venv (separate from the wav2lip venv — deps clash)

```bash
cd echomimic_v2
uv venv --python "C:/Users/<you>/AppData/Local/Programs/Python/Python311/python.exe" venv
uv pip install --python venv/Scripts/python.exe torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python venv/Scripts/python.exe -r requirements_min.txt
```

`requirements_min.txt` (repo `requirements.txt` minus the packages that fail or are
unused — verified working):

```
diffusers==0.31.0
transformers==4.46.3
einops==0.8.0
omegaconf==2.3.0
numpy==1.26.4
accelerate==1.1.1
decord==0.6.0
moviepy==1.0.3
av==13.1.0
imageio==2.36.0
imageio-ffmpeg==0.5.1
opencv-python
mediapipe
onnxruntime==1.19.2
safetensors
scikit-image==0.24.0
scipy==1.14.1
librosa
tqdm
Pillow
ffmpeg-python
soundfile
openai-whisper
more-itertools
regex
matplotlib
```

## Dependency pitfalls (each one blocks inference)

1. **`clip @ https://github.com/openai/CLIP/...zip`** fails to build
   (`ModuleNotFoundError: pkg_resources`). EVAL-only — remove it. grep pattern
   `^clip[[:space:]]` (the line is `clip @ https…`, so `^clip@` misses it).
   `open-clip-torch` is also unused by `infer.py` but is a clean wheel — harmless.
2. **`onnxruntime-gpu==1.20.1` does not exist** (`No solution found`). Use
   `onnxruntime==1.19.2` (CPU) — DWPose pose extraction is fast enough on CPU.
3. **`transformers>=4.46.3` resolves to 5.x**, breaking `diffusers==0.31.0`
   (`ImportError: cannot import name 'FLAX_WEIGHTS_NAME' from 'transformers.utils'`).
   PIN `transformers==4.46.3` (uv also pulls `tokenizers==0.20.3`, `huggingface_hub==0.36.2`).
4. **`--refimg_name` must contain a `/`** (e.g. `ref/portrait.png`) or infer.py
   line 170 `refimg_name.split('/')[-2]` raises `IndexError: list index out of range`.

## Model downloads (`git lfs install` first; all under `pretrained_weights/`)

| Path | Source | Size |
|---|---|---|
| denoising_unet.pth, reference_unet.pth, motion_module.pth, pose_encoder.pth (+ `_acc` variants) | `git clone https://huggingface.co/BadToBest/EchoMimicV2` | ~10 GB |
| sd-image-variations-diffusers/ (base SD, has `unet/` subfolder) | `git clone https://huggingface.co/lambdalabs/sd-image-variations-diffusers` | ~5.8 GB |
| sd-vae-ft-mse/ | `git clone https://huggingface.co/stabilityai/sd-vae-ft-mse` | ~638 MB |
| audio_processor/tiny.pt (Whisper) | `curl -sL -o ... https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt` | ~75 MB |

NOT needed for inference (legacy `infer.yaml` keys never imported by `infer.py`):
`audio_mapper-50000.pth`, `wav2vec2-base-960h`, `AutoFlow` — skip them.

## Pose sequence (the extra input SadTalker doesn't need)

`infer.py` loads `args.pose_dir/<pose_name>/{0..L-1}.npy` — DWPose keypoints as
`{'draw_pose_params': ...}` dicts. The repo ships demo sequences under
`assets/halfbody_demo/pose/*` (work with any portrait for a smoke test). To animate
YOUR portrait naturally, extract DWPose from a source (e.g. a SadTalker run of the
same portrait, or a natural talking video) using `src/models/dwpose/` — that
submodule needs its own `.onnx` models (`dw-ll_ucoco_384.onnx`, `yolox_l.onnx`)
which are NOT in the repo.

## Smoke test (verifies the whole stack on 8 GB, no OOM)

```bash
cd echomimic_v2
ffmpeg -y -i portrait.jpg -vf "crop=720:720:280:0,scale=768:768" ref/portrait.png
ffmpeg -y -i voix.wav -t 3 -ac 1 -ar 16000 audio_3s.wav
venv/Scripts/python.exe infer.py --config ./configs/prompts/infer.yaml \
  --ref_images_dir . --refimg_name ref/portrait.png \
  --audio_dir . --audio_name audio_3s.wav \
  --pose_dir ./assets/halfbody_demo/pose --pose_name 01 -L 48 --steps 10 --seed 3407
```

`weight_dtype: 'fp16'` (in `infer.yaml`) keeps VRAM ~6 GB on an 8 GB card. Output:
`outputs/<model_flag>-seed<seed>/.../_sig.mp4`.