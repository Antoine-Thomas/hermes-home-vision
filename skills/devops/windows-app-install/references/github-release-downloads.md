# Telecharger et verifier des fichiers depuis une release GitHub

Recette pour resoudre une release, prouver le fichier et recuperer des poids de modele. Ecrite pour
le parc Windows de l'utilisateur (shell de l'agent en bash MSYS, chemins natifs `C:/...` obligatoires
pour les binaires natifs).

## Resoudre la release

```bash
cd "/c/Users/<user>/<dossier>/_installer"   # cd builtin : le chemin MSYS est accepte
curl -sL "https://api.github.com/repos/<org>/<repo>/releases/latest" -o release.json
```

Puis lire la liste des assets en Python plutot que de la tronquer :

```python
import json
d = json.load(open(r'C:/Users/<user>/<dossier>/_installer/release.json'))
print('tag:', d['tag_name'], '| published:', d['published_at'])
for a in d['assets']:
    print('%-55s %8.1f Mo  %s' % (a['name'], a['size']/1048576, a['browser_download_url']))
```

- `releases/latest` peut etre **beaucoup plus ancien** que suppose : lire `published_at` et le rapporter.
- Pour un historique complet (l'asset n'est pas dans `latest`), prendre
  `https://api.github.com/repos/<org>/<repo>/releases?per_page=20` : la liste des assets par tag est
  la seule source de verite sur ce qui existe vraiment.

## Telecharger et prouver

```bash
curl -L --retry 3 --retry-delay 3 -f -s -o <nom-fichier> "<browser_download_url>"
# preuve 1 : taille a l'octet contre assets[].size ; preuve 2 : empreinte ; preuve 3 : magic bytes
sha256sum <nom-fichier>
head -c 2 <nom-fichier> | xxd      # 4d5a = MZ (binaire PE) ; 504b = PK (zip / PyTorch .pth)
```

Un fichier de quelques octets, ou deux fichiers differents au **meme sha256**, est un
« Not Found » telecharge : le sha256 de la chaine `Not Found` est
`0019dfc4b32d63c1392aa264aed2253c1e0c2fb09216f8e2cc269bbfb8bb49b5`.

## Cas mesure — Real-ESRGAN / Upscayl

- **Upscayl** (electron-builder, per-user) charge des modeles **NCNN** : paire `.bin` + `.param`,
  deposee dans un dossier passe par Settings -> "Add Custom Models" -> Select Folder. Les `.pth`
  PyTorch ne sont **pas** lus : ils exigent une conversion par chaiNNer (`.chn` -> `.bin` + `.param`,
  puis renommer les entrees `input` en `data` dans le `.param`).
- L'application **embarque deja** des modeles equivalents dans
  `C:\Program Files\Upscayl\resources\models\` : `upscayl-standard-4x` = `realesrgan-x4plus`,
  `digital-art-4x` = `realesrgan-x4plus-anime`, plus `high-fidelity-4x`, `remacri-4x`,
  `ultramix-balanced-4x`, `ultrasharp-4x`, `upscayl-lite-4x`. Un dossier de modeles custom peut donc
  etre **redondant** — le verifier (tailles de `.bin`/`.param` identiques) avant de le presenter comme
  un apport.
- Sources des paires NCNN Real-ESRGAN : le zip `realesrgan-ncnn-vulkan-<date>-windows.zip`
  (tag `v0.2.5.0` et voisins) — extraire son dossier `models/` (`realesrgan-x4plus`,
  `realesrgan-x4plus-anime`, `realesr-animevideov3-x2/x3/x4`).
- Sources des `.pth` (a garder comme sources, pas comme modeles utilisables) :
  `v0.1.0/RealESRGAN_x4plus.pth` (63,9 Mo) et `v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth` (17,1 Mo).
  Le tag `v0.2.5.0` **ne porte pas** ces deux noms malgre des URL qui circulent :
  il ne contient que `realesr-general-x4v3.pth`, `realesr-general-wdn-x4v3.pth`,
  `realesr-animevideov3.pth` et les zips `realesrgan-ncnn-vulkan-*`.
- Utilisation cote Upscayl : l'inference passe par Vulkan sur le GPU. Ne lancer un batch que quand le
  GPU est libre ; installer et preparer les dossiers ne consomme rien.

## Extraire une paire `.bin`/`.param` d'un zip sans polluer le dossier

```python
import zipfile, os
base = r'C:/Users/<user>/<dossier>/models'
z = zipfile.ZipFile(os.path.join(base, 'realesrgan-ncnn-vulkan-<date>-windows.zip'))
for i in z.infolist():
    if i.filename.startswith('models/') and not i.filename.endswith('/'):
        open(os.path.join(base, os.path.basename(i.filename)), 'wb').write(z.read(i))
```

Aplatir a la racine du dossier `models` (pas de sous-dossier `models/models/`) : c'est la forme que
l'application scanne. Laisser l'archive source dans le dossier coute de la place mais ne gene pas le
scan ; si le dossier doit rester propre, la deplacer dans `_source/` **et** le dire.

## Piege d'heritage : ne pas recopier une URL sans la resoudre

Une consigne qui cite une URL de telechargement peut pointer un tag reel **sans** le fichier nomme,
ou une version qui n'existe plus. Le seul controle fiable est la liste `assets[]` de l'API. Quand
l'asset annonce est absent : prendre la release qui le porte, telecharger les deux (l'annonce et le
valide), et rapporter explicitement la substitution — URL fournie, URL utilisee, et pourquoi.
