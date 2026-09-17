# Model URLs + working dependency pins (Windows, Python 3.11, NVIDIA GPU)

## SadTalker models — GitHub releases (direct download, no redirect)
Base: `https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc`
- `checkpoints/mapping_00109-model.pth.tar` (~155 MB)
- `checkpoints/mapping_00229-model.pth.tar` (~155 MB)
- `checkpoints/SadTalker_V0.0.2_256.safetensors` (~691 MB)
- `checkpoints/SadTalker_V0.0.2_512.safetensors` (~691 MB)

Enhancer weights (`gfpgan/weights/`):
- `https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth`
- `https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth`
- `https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth`
- `https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth`

NOTE: the 256 and 512 safetensors are both ~691 MB and have different md5s —
do NOT mistake identical sizes for a failed/duplicate download.

## Wav2Lip models — Hugging Face `camenduru/Wav2Lip` mirror
- `https://huggingface.co/camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth`
- `https://huggingface.co/camenduru/Wav2Lip/resolve/main/face_detection/detection/sfd/s3fd.pth`

## Working dependency set (uv, Python 3.11, torch 2.5.1+cu121)
```bash
# 1) torch CUDA FIRST
uv pip install --python <venv> "torch==2.5.1+cu121" "torchvision==0.20.1+cu121" --index-url https://download.pytorch.org/whl/cu121
# 2) the rest (numpy pinned; kornia/scikit-image pinned for numpy 1.x)
uv pip install --python <venv> "numpy==1.23.5" "kornia==0.7.3" "scikit-image==0.22.0" einops safetensors yacs face-alignment imageio imageio-ffmpeg av pyyaml resampy pydub facexlib basicsr gfpgan
# 3) basicsr/facexlib pulled a CPU torch — re-pin CUDA (cached, fast)
uv pip install --python <venv> "torch==2.5.1+cu121" "torchvision==0.20.1+cu121" --index-url https://download.pytorch.org/whl/cu121
```

## Required source patches
- basicsr: `site-packages/basicsr/data/degradations.py` line ~8
  `from torchvision.transforms.functional_tensor import rgb_to_grayscale`
  → `from torchvision.transforms.functional import rgb_to_grayscale`
- Wav2Lip `audio.py` line ~100: `librosa.filters.mel(sr=..., n_fft=..., n_mels=..., fmin=..., fmax=...)` (keyword-only in librosa ≥0.10).

## Speed reference (RTX 3070 Ti, 8 GB)
- SadTalker 512, no `--still`: ~30–90 min per 5 min of audio.
- Wav2Lip 720p: ~15–30 min.
- NVENC 4K re-encode of a mostly-static talking head: ~10× realtime (minutes).
