# Inliner le CSS d'un mail HTML pour Gmail

## Symptome

Le mail part correctement (SMTP 250, test recu) mais s'affiche en TEXTE BRUT dans Gmail :
pas de bandeau teal, pas de bouton, liens dans le bleu par defaut. Ce n'est pas un probleme
d'envoi, c'est un probleme de rendu.

## Cause

Gmail (web et application) supprime le bloc `<style>` du `<head>`. Un template qui ne declare
ses couleurs, tailles et boutons que par classes (`.cta a`, `.band`, `h1`, `p`) perd tout son
habillage. Les clients Apple Mail / Thunderbird conservent le `<style>` : un rendu qui parait
bon dans un apercu local peut etre plat dans Gmail, d'ou la necessite de tester dans Gmail.

## Regle

Tout style qui doit survivre a Gmail doit etre en attribut `style="..."` sur la balise
elle-meme. Un template dont l'habillage depend du `<style>` ne doit jamais partir tel quel.

## Procede (premailer)

1. Backup horodate du template AVANT toute ecriture (`cp` + `sha256sum` des deux fichiers).

2. Installer premailer avec le python qui porte les outils Hermes (`python3`/`pip` systeme
   n'existent pas forcement sur cet hote) :

   ```bash
   /c/Users/<user>/AppData/Local/hermes/tools/python-3.14.7+*/python -m pip install premailer
   ```

3. Inliner vers un fichier INTERMEDIAIRE (ne pas ecraser le template d'un coup, on veut
   pouvoir differ) :

   ```python
   import premailer
   html = open('Mail.html', encoding='utf-8').read()
   out = premailer.transform(html, remove_classes=False, keep_style_tags=True)
   open('Mail_inline.html', 'w', encoding='utf-8').write(out)
   ```

   - L'option s'appelle `keep_style_tags`, pas `keep_styles` (`TypeError` sinon).
   - `keep_style_tags=True` inline les regles MAIS laisse aussi le bloc `<style>` en place :
     le residuel doit etre elague a la main apres coup (etape 4).

4. Reduire le `<style>` residuel aux seules regles non inlinables : media queries et
   pseudo-classes (`:hover`, `:focus`). Supprimer du bloc toutes les regles de classes et de
   balises desormais portees en inline.

5. **Conserver le `!important` de la media query.** Les styles inline ont une specificite
   superieure a une regle de feuille normale : pour qu'une media query responsive puisse
   ecraser un `padding` / `font-size` inline, elle a besoin de `!important`. Premailer le
   supprime silencieusement — le restaurer, sinon le responsive mobile ne s'applique plus.

6. Verifier que les balises critiques portent bien un `style=` inline : `<body>` (font,
   background), bandeau (`.band` / `.band-txt`), `<h1>`, chaque `<p>`, chaque `<a>` bouton
   (background, couleur, `padding`, `border-radius`, `text-decoration`, `display:inline-block`),
   et toute balise a habillage propre (`<code>` : background, padding, border-radius).

7. Re-controler le HTML (`HTMLParser`) puis renvoyer un test. Le rendu ne se prouve pas par
   un `--test-email` reussi : il se prouve par l'absence de dependance au `<style>` dans le
   fichier envoye.

## Effets de bord premailer

- Decode les entites HTML (`&middot;` -> `·`, `&#847;` -> caractere Unicode) : rendu visuel
  identique, ne pas s'en alarmer.
- Normalise les fins de ligne (LF -> CRLF) : le `diff -u` backup/fichier apparait comme un
  remplacement integral. Le dire dans le rapport et fournir un resume des changements reels
  plutot qu'un diff brut illisible.
- Ajoute parfois des attributs repris de la regle CSS (ex. `width="44"` sur un `<div>`).
