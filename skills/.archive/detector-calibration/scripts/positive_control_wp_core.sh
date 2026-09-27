#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Controle positif : integrite d'un core WordPress.
#
# Prouve que le detecteur SE DECLENCHE, pas seulement qu'il se taise.
#
# Principe : AJOUT SEUL. On fabrique une fausse installation dans un dossier
# neuf horodate, on y copie des fichiers core SAINS, puis on injecte une
# anomalie par chemin de detection. Rien n'est supprime, aucun site reel n'est
# modifie, et le script est rejouable a l'identique.
#
# Usage :
#   bash positive_control_wp_core.sh <site_source> <scanner.py> [python]
#
# Exemple :
#   bash positive_control_wp_core.sh \
#     "C:/Users/x/Local Sites/oldstyle/app/public" \
#     bin/security_scan.py \
#     .venv/Scripts/python.exe
# ---------------------------------------------------------------------------
set -euo pipefail

SRC="${1:?usage: $0 <racine_wordpress_source> <scanner.py> [python]}"
SCANNER="${2:?usage: $0 <racine_wordpress_source> <scanner.py> [python]}"
PY="${3:-python}"

[ -f "$SRC/wp-includes/version.php" ] || {
  echo "ERREUR : $SRC n'est pas une racine WordPress (wp-includes/version.php absent)" >&2
  exit 2
}

TMPBASE="${LOCALAPPDATA:-${TMPDIR:-/tmp}}/Temp"
[ -d "$TMPBASE" ] || TMPBASE="${TMPDIR:-/tmp}"
T="$TMPBASE/wp_ctrl_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$T/wp-includes"

# --- entrees SAINES : elles ne doivent PAS etre signalees -------------------
cp "$SRC/wp-includes/version.php"   "$T/wp-includes/"
cp "$SRC/wp-includes/functions.php" "$T/wp-includes/"
cp "$SRC/wp-login.php"              "$T/"
cp "$SRC/wp-settings.php"           "$T/"

# --- anomalie 1 : fichier du core MODIFIE (md5 different) -------------------
printf '\n// ligne ajoutee par le controle positif\n' >> "$T/wp-includes/functions.php"

# --- anomalie 2 : fichier INCONNU dans un dossier du core ------------------
printf '<?php /* faux fichier de test - controle positif */ echo 1;\n' \
  > "$T/wp-includes/evil-test.php"

# --- anomalie 3 : signature d'execution de code dans un fichier critique ---
printf '<?php\n$table_prefix = "wp_";\neval(base64_decode("ZWNobyAxOw=="));\n' \
  > "$T/wp-config.php"

echo "Dossier de controle : $T"
echo
echo "Attendu :"
echo "  [ELEVE] code suspect dans un fichier critique  -> wp-config.php"
echo "  [ELEVE] 1 fichier du core modifie              -> wp-includes/functions.php"
echo "  [ELEVE] 1 fichier inconnu dans le core         -> wp-includes/evil-test.php"
echo "  [MOYEN] N fichiers du core manquants           -> normal, 4 fichiers copies"
echo "  ET wp-login.php / wp-settings.php / version.php NON signales"
echo

"$PY" "$SCANNER" --webroots "$T" --modules wp-integrity --out reports/wp-ctrl

cat <<EOF

--- Grille de lecture -------------------------------------------------------
Le controle est REUSSI si les deux conditions sont vraies :
  1. les 3 chemins de detection ont produit leur finding ;
  2. 'modifies' vaut exactement 1 (et non le nombre de fichiers copies)
     -> les fichiers sains n'ont pas ete signales : le detecteur discrimine.

Le dossier de controle n'est pas supprime automatiquement (aucune suppression
dans ce script, par conception). Il contient un wp-config.php de test avec un
eval() inoffensif, hors de toute racine web. Le retirer manuellement :
  $T
EOF
