import sys, os, pathlib, datetime, time
from pathlib import Path
HERMES_HOME = Path(os.environ.get("HERMES_HOME", r"C:/Users/searc/AppData/Local/hermes"))
ESTOP = HERMES_HOME / "ESTOP"
OUT = HERMES_HOME / "captures"
OUT.mkdir(parents=True, exist_ok=True)

if ESTOP.exists():
    print("Pause active (ESTOP). Envoie /pause off puis reessaie /photo.")
    sys.exit(0)

# Voyant Tkinter 1.5s (non bloquant si pas d ecran)
try:
    import tkinter as tk
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="red")
    w, h = 520, 60
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{w}x{h}+{(sw-w)//2}+30")
    lbl = tk.Label(root, text="  CAPTURE PHOTO EN COURS  ", bg="red", fg="white", font=("Segoe UI", 14, "bold"))
    lbl.pack(expand=True, fill="both")
    root.update()
    root.after(1500, root.destroy)
    # will be closed after capture below via update loop
    start = time.time()
    while time.time() - start < 1.5:
        root.update()
        time.sleep(0.05)
    try: root.destroy()
    except: pass
except Exception as e:
    print(f"[voyant skip: {e}]")

# Capture
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
dest = OUT / f"photo_{ts}.jpg"
img = None
err = None
try:
    import cv2
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        time.sleep(0.4)
        ok, frame = cap.read()
        cap.release()
        if ok and frame is not None:
            cv2.imwrite(str(dest), frame)
            img = dest
except Exception as e:
    err = str(e)

if img is None or not dest.exists():
    try:
        from PIL import ImageGrab
        im = ImageGrab.grab()
        # resize if huge
        if im.size[0] > 1920:
            im.thumbnail((1920,1080))
        im.save(dest, "JPEG", quality=88)
        img = dest
    except Exception as e2:
        print(f"Capture echouee: opencv err={err} grab err={e2}")
        sys.exit(1)

print(f"Photo sauvee: {dest}")
print(f"MEDIA:{dest}")
