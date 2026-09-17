# -*- coding: utf-8 -*-
"""GFPGAN + Real-ESRGAN: restore faces + 2x upscale the frames of a talking-head
video, then reassemble with the original audio.

Usage (run inside the venv that has torch/gfpgan/basicsr/realesrgan):
    python gfpgan_upscale.py --in input_256.mp4 --out output_512.mp4 \
        --gfpgan GFPGANv1.4.pth --esrgan RealESRGAN_x2plus.pth

Frame extraction/reassembly use ffmpeg (must be on PATH).
Requires: `uv pip install --python venv/Scripts/python.exe realesrgan --no-deps`
(the venv has no pip; realesrgan is NOT bundled with gfpgan/basicsr).
"""
import argparse, os, subprocess, sys, time, tempfile, shutil

import cv2
import torch
from gfpgan import GFPGANer
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--gfpgan", default="GFPGANv1.4.pth")
    ap.add_argument("--esrgan", default="RealESRGAN_x2plus.pth")
    ap.add_argument("--fps", type=int, default=25)
    ap.add_argument("--weight", type=float, default=0.5)
    args = ap.parse_args()

    print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU", flush=True)

    m = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
    up = RealESRGANer(scale=2, model_path=args.esrgan, model=m, tile=0, tile_pad=10, pre_pad=0, half=True)
    r = GFPGANer(model_path=args.gfpgan, upscale=2, arch="clean", channel_multiplier=2, bg_upsampler=up)
    print("models loaded", flush=True)

    work = tempfile.mkdtemp(prefix="gfpgan_")
    frames = os.path.join(work, "in")
    outdir = os.path.join(work, "out")
    os.makedirs(frames); os.makedirs(outdir)

    subprocess.run(["ffmpeg", "-y", "-i", args.inp, "-qscale:v", "1", os.path.join(frames, "%05d.png")],
                   check=True, capture_output=True)
    names = sorted(os.listdir(frames))
    total = len(names)
    print(f"{total} frames extracted", flush=True)

    t0 = time.time()
    for i, fname in enumerate(names):
        img = cv2.imread(os.path.join(frames, fname), cv2.IMREAD_COLOR)
        _, _, out = r.enhance(img, has_aligned=False, only_center_face=True, paste_back=True, weight=args.weight)
        cv2.imwrite(os.path.join(outdir, fname), out)
        if (i + 1) % 250 == 0:
            el = time.time() - t0
            print(f"{i+1}/{total} ({el:.0f}s, {(i+1)/el:.1f} img/s)", flush=True)

    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(args.fps), "-i", os.path.join(outdir, "%05d.png"),
        "-i", args.inp, "-map", "0:v", "-map", "1:a",
        "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "18", "-b:v", "0",
        "-c:a", "copy", args.out,
    ], check=True, capture_output=True)
    shutil.rmtree(work, ignore_errors=True)
    print("=== DONE:", args.out, "===", flush=True)


if __name__ == "__main__":
    main()
