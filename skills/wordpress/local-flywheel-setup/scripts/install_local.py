#!/usr/bin/env python3
"""
Telecharge et installe Local by Flywheel pour le systeme courant.

Usage:
    python install_local.py [--download-dir DIR]

Note: l'installation silencieuse n'est verifiee que sur Windows/macOS.
Sur Linux, l'AppImage est copiee dans ~/.local/bin.
"""

import argparse
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

INSTALLERS = {
    "windows": ("https://cdn.localwp.com/releases/stable/windows/Local.exe", ".exe"),
    "darwin": ("https://cdn.localwp.com/releases/stable/mac/Local.dmg", ".dmg"),
    "linux": ("https://cdn.localwp.com/releases/stable/linux/Local.AppImage", ".AppImage"),
}


def get_platform_key(system=None):
    """Retourne la cle de plateforme utilisee par INSTALLERS."""
    system = (system or platform.system()).lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "darwin"
    if system == "linux":
        return "linux"
    raise OSError(f"Plateforme non supportee: {system}")


def download(url, destination):
    """Telecharge un fichier avec un affichage de progression simple."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    def hook(blocks, block_size, total_size):
        if total_size <= 0:
            return
        done = min(blocks * block_size, total_size)
        percent = done * 100 / total_size
        print(f"\r  {percent:5.1f} % ({done // 1048576} / {total_size // 1048576} Mo)", end="")

    print(f"Telechargement: {url}")
    urllib.request.urlretrieve(url, destination, reporthook=hook)
    print()
    return destination


def install_windows(installer):
    """Installe Local sur Windows (mode silencieux)."""
    print("Installation de Local (Windows, mode silencieux)...")
    result = subprocess.run(
        [str(installer), "/S", "/D=C:\\Program Files\\Local"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Echec de l'installation ({result.returncode}): {result.stderr.strip()}")
    if not Path("C:/Program Files/Local/Local.exe").exists():
        print("  Installation terminee mais Local.exe introuvable a l'emplacement par defaut.")
        print("  Verifier le dossier d'installation ou relancer l'installateur manuellement.")


def install_macos(installer):
    """Monte le DMG et copie Local.app dans /Applications."""
    print("Installation de Local (macOS)...")
    mount = subprocess.run(["hdiutil", "attach", str(installer)], capture_output=True, text=True)
    if mount.returncode != 0:
        raise RuntimeError(f"Montage du DMG impossible: {mount.stderr.strip()}")

    volume = None
    for line in mount.stdout.splitlines():
        if "/Volumes/" in line:
            volume = line.split("\t")[-1].strip() or line.split()[-1]
            break

    if not volume:
        raise RuntimeError("Point de montage introuvable dans la sortie de hdiutil")

    try:
        subprocess.run(["cp", "-R", f"{volume}/Local.app", "/Applications/"], check=True)
    finally:
        subprocess.run(["hdiutil", "detach", volume], capture_output=True)


def install_linux(installer):
    """Rend l'AppImage executable et la copie dans ~/.local/bin."""
    print("Installation de Local (Linux)...")
    installer.chmod(0o755)
    destination = Path.home() / ".local" / "bin" / "Local.AppImage"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(installer, destination)
    destination.chmod(0o755)
    print(f"  Installe: {destination}")


def main():
    parser = argparse.ArgumentParser(description="Installer Local by Flywheel")
    parser.add_argument(
        "--download-dir",
        default=str(Path.home() / "Downloads"),
        help="Dossier de telechargement (defaut: ~/Downloads)",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Telecharger sans lancer l'installation",
    )
    args = parser.parse_args()

    try:
        key = get_platform_key()
    except OSError as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)

    url, extension = INSTALLERS[key]
    target = Path(args.download_dir) / f"Local{extension}"

    try:
        download(url, target)

        if args.download_only:
            print(f"Installateur telecharge: {target}")
            return

        if key == "windows":
            install_windows(target)
        elif key == "darwin":
            install_macos(target)
        else:
            install_linux(target)

        print("\nLocal by Flywheel est pret. Lancer l'application puis creer un site.")
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        print(f"Installateur conserve pour installation manuelle: {target}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
