# XTTS-v2 (Coqui) setup on Windows / 8 GB

## Install
```bash
cd data/xtts
uv venv --python <python3.11.exe> venv
uv pip install --python venv/Scripts/python.exe torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python venv/Scripts/python.exe coqui-tts        # idiap fork, installs the `TTS` package
uv pip install --python venv/Scripts/python.exe "transformers==4.46.3"
```
`coqui-tts` pulls `transformers==5.x` by default, which breaks the fork's imports — pin 4.46.3 (has `isin_mps_friendly`).

## Mandatory import patches
No single transformers version provides all three functions the fork imports:
- `is_torch_greater_or_equal` — removed in transformers >= 4.40
- `isin_mps_friendly` — removed in transformers >= 4.45 (present in 4.46.3)
- `is_torchcodec_available` — added only in transformers >= 4.47 (absent in 4.46.3)

Patch TWO files after install:

1. `venv/Lib/site-packages/TTS/__init__.py` — replace the `from transformers.utils.import_utils import (...)` block (drop `is_torch_greater_or_equal` + `is_torchcodec_available`), use:
```python
from transformers.utils.import_utils import is_torch_available, is_torchaudio_available
import torch as _torch
from packaging import version as _pkg_version

def is_torch_greater_or_equal(v):
    return _pkg_version.parse(_torch.__version__) >= _pkg_version.parse(v)

def is_torchcodec_available():
    return False
```

2. `venv/Lib/site-packages/TTS/tts/datasets/dataset.py` — replace `from transformers.utils.import_utils import is_torch_greater_or_equal` with:
```python
from packaging import version as _pkg_version

def is_torch_greater_or_equal(v):
    return _pkg_version.parse(torch.__version__) >= _pkg_version.parse(v)
```
(`torch` is already imported above line 14.)

## ToS prompt (blocks non-interactive download)
The TTS manager calls `input()` to accept the Coqui CPML license before downloading the ~1.9 GB model — an `EOFError` in any non-TTY run. Bypass at the top of every script:
```python
from TTS.utils.manage import ModelManager
ModelManager.ask_tos = staticmethod(lambda path: True)
```

## Model + runtime
- Model id `tts_models/multilingual/multi-dataset/xtts_v2` (~1.9 GB, auto-downloads on first use).
- RTF ≈ 1.2–1.3× on RTX 3070 Ti (5 min audio in ~3.5 min). Output 24 kHz mono.
- `tts.tts()` returns a numpy-compatible list — `np.asarray(wav, dtype=np.float32)` + `soundfile.write(..., 24000)`.
- Segment-by-segment pattern: split script into paragraphs, `tts.tts()` each to `seg_000.wav...`, concat with `np.zeros(int(24000*0.35))` gaps so a bad segment can be regenerated alone.
