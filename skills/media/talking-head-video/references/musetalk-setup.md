# MuseTalk v1.5 — installation (Windows, Python 3.10, RTX 3070 Ti 8 GB)

Lips-only redubbing, fast: ~8.3 it/s UNet on a 3070 Ti, ~4 GB VRAM, ~7 GB of weights.
Install dir used on this machine: `C:\Users\searc\AppData\Local\hermes\data\video_youtube\musetalk`,
venv python `venv\Scripts\python.exe` (base: `C:\Users\searc\AppData\Local\Programs\Python\Python310\python.exe`).

## Install order (the order matters — do not reorder)

Run from the repo dir, one command at a time, checking between each.

1. `git clone https://github.com/TMElyralab/MuseTalk.git musetalk`
2. `<Python310>\python.exe -m venv venv`
3. `./venv/Scripts/python.exe -m pip install --upgrade pip`
4. torch CUDA 11.8:
   `pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118`
5. `pip install -r requirements.txt`
6. `pip install --no-cache-dir -U openmim`
7. `mim install mmengine`
8. **`pip install "mmcv==2.1.0"`** — NOT `mim install "mmcv>=2.0.1"` (pitfall 1)
9. `mim install "mmdet>=3.1.0"` (resolves to 3.3.0)
10. `pip install --no-build-isolation chumpy` THEN `mim install "mmpose>=1.1.0"` (pitfall 2)
11. Download the weights (pitfall 3), and only AFTER that `pip install huggingface_hub==0.30.2`

## Pitfalls

### 1. mmcv must be pinned to 2.1.0, never "mmcv>=2.0.1"

`mim install "mmcv>=2.0.1"` resolves to **2.2.0**, which mmdet 3.3.0 rejects:

```
AssertionError: MMCV==2.2.0 is used but incompatible. Please install mmcv>=2.0.0rc4, <2.2.0.
```

The mmdet import then fails, and with it every MuseTalk entry point. Install `mmcv==2.1.0`
explicitly, then verify the trio:

```bash
./venv/Scripts/python.exe -c "import mmcv, mmdet, mmengine; print(mmcv.__version__, mmdet.__version__)"
```

The openmmlab index URL is not needed for the pure-python mmcv build and does not change this.

### 2. mmpose: `chumpy` fails to build first

`mim install "mmpose>=1.1.0"` dies compiling `chumpy`:
`ModuleNotFoundError: No module named 'pip'` raised from the isolated build environment.
Passing an openmmlab index with `-f` does not help. Pre-install chumpy without build isolation:

```bash
./venv/Scripts/python.exe -m pip install --no-build-isolation chumpy
```

Then re-run the mmpose install (yields 1.3.2).

**mmpose is NOT optional.** `musetalk/utils/preprocessing.py` does
`from mmpose.apis import inference_topdown, init_model`. Without it there is no face-landmark
step, so nothing runs.

### 3. huggingface_hub: download all weights BEFORE downgrading it

The repo's `download_weights.sh`/`.bat` call `huggingface-cli`, which is deprecated
("use `hf` instead"). Following that advice installs `huggingface_hub` 1.x, which breaks the
`transformers==4.39.2` pinned in `requirements.txt` (VAE loading goes through
diffusers → transformers):

```
ImportError: huggingface-hub>=0.19.3,<1.0 is required for a normal functioning of this
module, but found huggingface-hub==1.31.0
```

Correct order:

1. `export HF_ENDPOINT=https://hf-mirror.com`
2. download ALL weights with `hf download` (works while hub is still 1.x)
3. only then `pip install "huggingface_hub==0.30.2"`

The `hf` CLI is only needed for the download step, so losing it afterwards is fine.

### 4. Two config.json are missing from the repo's download script

`download_weights.sh` / `.bat` do not fetch `models/sd-vae/config.json` or
`models/whisper/config.json`, yet the startup guard in `app.py` requires both. Fetch them:

```bash
./venv/Scripts/hf download stabilityai/sd-vae-ft-mse --local-dir models/sd-vae config.json
./venv/Scripts/hf download openai/whisper-tiny --local-dir models/whisper config.json preprocessor_config.json
```

Pass filenames positionally: `--include` is ignored as soon as any filename is given
explicitly (harmless warning, not a failure).

## Required weight set

The `download_model()` guard in `app.py` checks exactly this list — treat it as the pre-flight
checklist:

```
models/musetalkV15/unet.pth
models/musetalkV15/musetalk.json
models/sd-vae/config.json
models/whisper/config.json
models/dwpose/dw-ll_ucoco_384.pth
models/syncnet/latentsync_syncnet.pt
models/face-parse-bisent/79999_iter.pth
models/face-parse-bisent/resnet18-5c106cde.pth
```

v1.0 (`models/musetalk/pytorch_model.bin`) is dead weight when running v1.5.
`face-parse-bisent/79999_iter.pth` comes from gdown (`154JgKpzCPW82qINcVieuPH3fZ2e0P812`) and
`resnet18-5c106cde.pth` from `download.pytorch.org` — create the target dir before calling gdown
(it will not create it).

## Running inference

Minimal YAML config (single task — use this for a smoke test instead of the repo's 2-task file):

```yaml
task_0:
 video_path: "data/video/yongen.mp4"
 audio_path: "data/audio/yongen.wav"
```

```bash
./venv/Scripts/python.exe -m scripts.inference \
  --inference_config ./configs/inference/test.yaml \
  --result_dir ./results/test \
  --unet_model_path ./models/musetalkV15/unet.pth \
  --unet_config ./models/musetalkV15/musetalk.json \
  --version v15
```

Output lands in `<result_dir>/v15/<video>_<audio>.mp4`. ffmpeg must be on PATH — the repo shells
out to it for frame encoding and for muxing the audio back in.

## Verifying the install (validated)

Loading all models without rendering anything catches mmcv, mmpose AND the hub pin in one shot:

```bash
./venv/Scripts/python.exe -c "
import torch
from musetalk.utils.utils import load_all_model
from musetalk.utils.face_parsing import FaceParsing
from musetalk.utils.audio_processor import AudioProcessor
from transformers import WhisperModel
dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
vae, unet, pe = load_all_model(unet_model_path='./models/musetalkV15/unet.pth', vae_type='sd-vae', unet_config='./models/musetalkV15/musetalk.json', device=dev)
WhisperModel.from_pretrained('./models/whisper')
AudioProcessor(feature_extractor_path='./models/whisper')
FaceParsing()
print('OK')
"
```

Measured reference: `yongen.mp4` (10.7 s, 268 frames, 704x1216 source) → 8 s output,
h264 + aac, 25 fps libx264, UNet ~8.3 it/s, 6.7 GB VRAM free at start.

## Version / VRAM constraint

MuseTalk v1.5 fits 8 GB (~4 GB used). LatentSync **1.5** (~6.5–8 GB) is the quality alternative;
LatentSync **1.6** needs ~18 GB and is not installable on this machine — check the version
before committing to a multi-GB download.
