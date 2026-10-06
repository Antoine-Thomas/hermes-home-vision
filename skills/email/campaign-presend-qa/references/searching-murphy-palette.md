# Palette et style des mails produit Searching Murphy

Tokens releves sur le CSS du site (theme enfant, variables `--sm-*`). C'est la reference :
des valeurs plus anciennes circulaient avec un fond sombre `#1a1a2e` / `#222240` qui
n'existe pas dans le theme — ne pas les utiliser.

| Usage | Hex |
|---|---|
| Accent jaune (`--sm-accent`, `--sm-card-accent`) : CTA, filets sous les titres | `#fdc502` |
| Teal (`--sm-card-bg`) : liens du corps | `#0c9f93` |
| Dark teal (`--sm-border`) : bandeau d'en-tete, pied de page, titres de section | `#284543` |
| Light teal (`--sm-bg`) : encart, bordures de carte | `#cbe8e8` |
| Texte `#1b1f22` ; carte `#ffffff` | |

Derives neutres acceptes : fond de page eclairci `#eef4f4`, filets `#e7efef`, texte
secondaire `#5c6b6a` / `#9aa8a8`.

Typographies : `'Source Sans Pro', 'Segoe UI', Arial, sans-serif` (le site charge Source
Sans Pro 400/600/700 via Google Fonts ; garder les replis) + `'Courier New', monospace`
pour les libelles et kickers. Boutons : `border-radius: 8px` (`--sm-btn-radius`), sans
ombre lourde en email. Couleurs Astra a ignorer : `#046bd2`, `#045cb4`, `#1e293b`,
`#334155`.

Adresse postale a utiliser dans les pieds de mail : reprise des mentions legales du site
(`/mentions-legales/`) — raison sociale, adresse, email.

Style des mails produit (preferences du destinataire) : fond clair, noir/blanc + un seul
accent, titres de section en petites capitales, 600 px max, responsive, aucune image, liens
externes explicites et libelles en clair.
