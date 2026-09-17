#!/usr/bin/env python3
"""
Configure un site WordPress : plugins, theme, options.

Usage:
    python configure_site.py --site mon-site --plugins woocommerce,yoast-seo --theme astra
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_sites_dir():
    """Retourne le dossier des sites Local."""
    return Path.home() / "Local Sites"


def find_wp_cli():
    """Retourne la commande WP-CLI a utiliser."""
    system = platform.system().lower()
    candidates = []
    if system == "windows":
        candidates = [
            Path("C:/Program Files/Local/resources/extraResources/bin/wp-cli/wp-cli.phar"),
            Path.home() / "AppData/Local/Local/resources/extraResources/bin/wp-cli/wp-cli.phar",
        ]
    elif system == "darwin":
        candidates = [
            Path("/Applications/Local.app/Contents/Resources/extraResources/bin/wp-cli/wp-cli.phar"),
            Path("/usr/local/bin/wp"),
        ]
    else:
        candidates = [Path("/usr/local/bin/wp"), Path.home() / ".local/bin/wp"]

    for candidate in candidates:
        if candidate.exists():
            return [sys.executable, str(candidate)] if candidate.suffix == ".phar" else [str(candidate)]

    found = shutil.which("wp")
    if not found:
        raise FileNotFoundError("WP-CLI introuvable")
    return [found]


def run_wp(wp, public_path, args, label):
    """Execute une commande WP-CLI et rapporte le resultat."""
    print(f"  - {label}")
    result = subprocess.run(wp + args + [f"--path={public_path}"], capture_output=True, text=True)
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        print(f"    echec: {message}", file=sys.stderr)
        return False
    return True


def configure_site(site_name, sites_dir, plugins, remove_plugins, theme, options, activate_plugins):
    """Applique la configuration demandee."""
    public_path = Path(sites_dir) / site_name / "app" / "public"
    if not public_path.exists():
        raise FileNotFoundError(f"Site '{site_name}' introuvable: {public_path}")

    wp = find_wp_cli()
    results = {"ok": 0, "fail": 0}

    def track(ok):
        results["ok" if ok else "fail"] += 1

    if plugins:
        for slug in [p.strip() for p in plugins.split(",") if p.strip()]:
            args = ["plugin", "install", slug]
            if activate_plugins:
                args.append("--activate")
            track(run_wp(wp, public_path, args, f"installation du plugin {slug}"))

    if remove_plugins:
        for slug in [p.strip() for p in remove_plugins.split(",") if p.strip()]:
            if run_wp(wp, public_path, ["plugin", "deactivate", slug], f"desactivation de {slug}"):
                track(run_wp(wp, public_path, ["plugin", "uninstall", slug, "--yes"], f"suppression de {slug}"))

    if theme:
        install_ok = run_wp(wp, public_path, ["theme", "install", theme], f"installation du theme {theme}")
        if install_ok:
            track(run_wp(wp, public_path, ["theme", "activate", theme], f"activation du theme {theme}"))
        else:
            track(run_wp(wp, public_path, ["theme", "activate", theme], f"activation du theme {theme}"))

    for option in options or []:
        if "=" not in option:
            print(f"    option ignoree (format attendu cle=valeur): {option}", file=sys.stderr)
            results["fail"] += 1
            continue
        key, value = option.split("=", 1)
        track(run_wp(wp, public_path, ["option", "update", key, value], f"option {key}"))

    return results


def main():
    parser = argparse.ArgumentParser(description="Configurer un site WordPress local")
    parser.add_argument("--site", required=True, help="Nom du site")
    parser.add_argument("--sites-dir", default=str(get_sites_dir()), help="Racine des sites")
    parser.add_argument("--plugins", help="Plugins a installer (slugs separes par des virgules)")
    parser.add_argument("--remove-plugins", help="Plugins a desinstaller (slugs separes par des virgules)")
    parser.add_argument("--theme", help="Theme a installer et activer")
    parser.add_argument("--option", dest="options", action="append", help="Option WordPress cle=valeur (repetable)")
    parser.add_argument("--no-activate", action="store_true", help="Installer les plugins sans les activer")
    args = parser.parse_args()

    try:
        results = configure_site(
            args.site,
            args.sites_dir,
            args.plugins,
            args.remove_plugins,
            args.theme,
            args.options,
            not args.no_activate,
        )
        print(f"\nTermine - operations reussies: {results['ok']} - echecs: {results['fail']}")
        if results["fail"]:
            sys.exit(1)
    except Exception as exc:
        print(f"Erreur: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
