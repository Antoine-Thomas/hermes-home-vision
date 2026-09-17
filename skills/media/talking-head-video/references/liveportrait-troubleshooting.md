# LivePortrait Troubleshooting (Windows/CUDA)

## ONNX Runtime CUDA Conflict
On Windows with CUDA 13.3 (or any version > 12.x) and `onnxruntime-gpu` 1.18, attempts to use `CUDAExecutionProvider` for face detection or landmarks will crash the process.

### InsightFace Fix
In `liveportrait/repo/src/utils/dependencies/insightface/model_zoo/model_zoo.py`:
Force `providers=['CPUExecutionProvider']` in the `get_model` function or where the `InferenceSession` is created.

### HumanLandmark (Cropper) Fix
In `liveportrait/repo/src/utils/cropper.py`:
Identify the `Landmark` or `HumanLandmark` class. In `__init__`, if `onnx_provider` is passed, override it or hardcode it to `'cpu'`.

```python
# Example patch for cropper.py
self.onnx_session = onnxruntime.InferenceSession(model_path, providers=['CPUExecutionProvider'])
```

This allows the heavy motion transfer (Torch/LivePortrait) to run on the GPU while the lighter detection stages run safely on the CPU.
