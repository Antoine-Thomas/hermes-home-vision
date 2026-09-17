import sys, os, pathlib, datetime, time, subprocess, shutil, re
from pathlib import Path
HERMES_HOME = Path(os.environ.get("HERMES_HOME", r"C:/Users/searc/AppData/Local/hermes"))
ESTOP = HERMES_HOME / "ESTOP"
OUT = HERMES_HOME / "captures"
OUT.mkdir(parents=True, exist_ok=True)

if ESTOP.exists():
    print("Pause active (ESTOP). Envoie /pause off puis reessaie /record.")
    sys.exit(0)

# parse duree
try:
    dur = int(sys.argv[1]) if len(sys.argv)>1 else 30
except:
    dur=30
dur = max(5, min(60, dur))
print(f"Enregistrement {dur}s ... voyant rouge actif")

# voyant thread
import threading
stop_flag = threading.Event()
def voyant():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        w,h=520,60
        sw,sh=root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{(sw-w)//2}+30")
        lbl=tk.Label(root, text=f"  ENREGISTREMENT {dur}s EN COURS  ", bg="red", fg="white", font=("Segoe UI", 13, "bold"))
        lbl.pack(expand=True, fill="both")
        def blink():
            if stop_flag.is_set():
                try: root.destroy()
                except: pass
                return
            cur=lbl.cget("bg")
            lbl.configure(bg="#ff3333" if cur=="red" else "red")
            root.after(400, blink)
        root.after(400, blink)
        root.after(dur*1000+500, lambda: (stop_flag.set(), root.destroy()))
        root.mainloop()
    except Exception as e:
        print(f"[voyant record skip: {e}]")
        time.sleep(dur)
        stop_flag.set()

th=threading.Thread(target=voyant, daemon=True)
th.start()

ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
dest=OUT / f"record_{ts}.mp4"

made=False

# === METHODE 1 : ffmpeg dshow webcam + micro (vrai audio/video) ===
def try_ffmpeg():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[ffmpeg] binaire introuvable")
        return False
    video_dev = 'video=Microsoft LifeCam VX-800'
    audio_dev = 'audio=Microphone (2- Microsoft LifeCam VX-800)'
    # auto-detect si noms ont change
    try:
        out = subprocess.run([ffmpeg, "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                             capture_output=True, text=True, timeout=8)
        txt = (out.stderr or "") + (out.stdout or "")
        m = re.search(r'"([^"]+)"\s*\(video\)', txt)
        if m and m.group(1) not in video_dev:
            video_dev = f'video={m.group(1)}'
        m2 = re.search(r'"([^"]+)"\s*\(audio\)', txt)
        if m2 and m2.group(1) not in audio_dev:
            audio_dev = f'audio={m2.group(1)}'
        print(f"[ffmpeg] devices: {video_dev} | {audio_dev}")
    except Exception as e:
        print(f"[ffmpeg] list_devices err: {e}")

    cmds_to_try = [
        [ffmpeg, "-y", "-f", "dshow", "-i", f'{video_dev}:{audio_dev}',
         "-t", str(dur), "-vcodec", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-acodec", "aac", "-ar", "44100", str(dest)],
        [ffmpeg, "-y", "-f", "dshow", "-i", video_dev,
         "-t", str(dur), "-vcodec", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", str(dest)],
    ]
    for cmd in cmds_to_try:
        try:
            print(f"[ffmpeg] essai: {' '.join(cmd[5:7])} ...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=dur+20)
            if dest.exists() and dest.stat().st_size > 2000:
                probe = subprocess.run(["ffprobe","-v","error","-show_streams",str(dest)],
                                       capture_output=True, text=True, timeout=5)
                if "codec_type=video" in (probe.stdout or ""):
                    print(f"[ffmpeg] OK: {dest} ({dest.stat().st_size} bytes)")
                    return True
                else:
                    print("[ffmpeg] fichier sans video, retry")
                    try: dest.unlink()
                    except: pass
            else:
                err = (result.stderr or "")[-800:]
                print(f"[ffmpeg] echec: {err}")
        except subprocess.TimeoutExpired:
            print("[ffmpeg] timeout")
            try: dest.unlink()
            except: pass
        except Exception as e:
            print(f"[ffmpeg] err: {e}")
    return False

if try_ffmpeg():
    made = True

# === METHODE 2 : OpenCV VideoCapture (fallback sans audio) ===
if not made:
    try:
        import cv2
        cap=cv2.VideoCapture(0)
        if cap.isOpened():
            w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            fps=15.0
            fourcc=cv2.VideoWriter_fourcc(*"mp4v")
            out=cv2.VideoWriter(str(dest), fourcc, fps, (w,h))
            if out.isOpened():
                t0=time.time()
                while time.time()-t0 < dur:
                    ok, frame=cap.read()
                    if not ok or frame is None:
                        time.sleep(0.05)
                        continue
                    out.write(frame)
                    time.sleep(1/fps)
                cap.release()
                out.release()
                made=dest.exists() and dest.stat().st_size>1000
                if made:
                    print(f"[opencv] OK sans audio: {dest} ({dest.stat().st_size} bytes)")
            else:
                cap.release()
                print("[opencv] VideoWriter open failed")
        else:
            try: cap.release()
            except: pass
            print("[opencv] VideoCapture(0) not opened")
    except Exception as e:
        print(f"[opencv] err: {e}")

# === METHODE 3 : dernier fallback rafale screenshots -> GIF ===
if not made:
    try:
        from PIL import ImageGrab
        frames=[]
        t0=time.time()
        while time.time()-t0 < dur:
            im=ImageGrab.grab()
            if im.size[0]>640:
                im.thumbnail((640,480))
            frames.append(im.convert("RGB"))
            time.sleep(2)
        if frames:
            dest_gif=OUT / f"record_{ts}.gif"
            frames[0].save(dest_gif, save_all=True, append_images=frames[1:], duration=2000, loop=0)
            dest=dest_gif
            made=True
            print(f"[fallback GIF] {dest} ({dest.stat().st_size} bytes) - SANS audio ni webcam")
    except Exception as e2:
        print(f"[fallback grab err: {e2}]")

stop_flag.set()
th.join(timeout=2)

if made and dest.exists():
    print(f"Enregistrement sauve: {dest} ({dest.stat().st_size} bytes)")
    print(f"MEDIA:{dest}")
else:
    print("Echec enregistrement: aucune capture possible (webcam absente ?).")
    sys.exit(1)
