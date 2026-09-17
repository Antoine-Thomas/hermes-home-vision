# -*- coding: utf-8 -*-
"""Motion control via LivePortrait (local) : anime une image avec une vidéo pilote."""
import argparse
import glob
import os
import subprocess

REPO = r"C:\Users\searc\AppData\Local\hermes\data\video_youtube\liveportrait\repo"


def animate_face(image, driving_video, output_dir="results"):
    """Anime `image` avec les mouvements de `driving_video` via LivePortrait (1024×1024)."""
    os.makedirs(output_dir, exist_ok=True)
    venv_py = os.path.join(REPO, "venv", "Scripts", "python.exe")
    subprocess.run(
        [venv_py, "inference.py", "--source", image, "--driving", driving_video,
         "--output_dir", output_dir],
        cwd=REPO, check=True,
    )
    mp4s = sorted(
        [f for f in glob.glob(os.path.join(output_dir, "*.mp4")) if "_concat" not in f],
        key=os.path.getmtime,
    )
    return mp4s[-1] if mp4s else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--driving", required=True)
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()
    out = animate_face(args.source, args.driving, args.output_dir)
    print(f"Vidéo animée -> {out}")
