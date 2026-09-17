# Diagnostic de Landing Page WordPress

## Procédure

1. Inspecter le dossier local (Local by Flywheel, XAMPP, etc.)
2. Identifier le type de site (WordPress, statique, etc.)
3. Vérifier les fichiers clés : `front-page.php`, `style.css`, `functions.php`,
   `llms.txt`, `AGENTS.md`
4. Analyser le message d'accroche vs l'USP réel
5. Comparer avec le rapport stratégique
6. Produire diagnostic + plan de correction prioritaire

## Ce qu'il faut vérifier

| Élément | Question |
|---------|----------|
| llms.txt | Présent ? Complet ? À jour avec les offres ? |
| Hook d'accroche | Reflète-t-il l'USP ou est-il trop générique ? |
| Offres packagées | Prix visibles ? 3 niveaux ? |
| CTA | Présent sur chaque section ? Devis ? Contact ? |
| Preuve sociale | Témoignages ? Portfolio ? Réseaux sociaux ? |
| Formulaire contact | Présent ? Protégé par nonce ? |
| Design system | Cohérent ? Variables CSS ? |
| Accessibilité | aria-labels, sr-only, semantic HTML ? |
| Performance | Lazyload ? WebP ? Fontawesome chargé ? |
| SEO | Yoast Premium ? Sitemap ? Balises title/meta ? |

## Pattern récurrent : le site est bon mais le message est mauvais

Dans ~80% des cas, le problème n'est pas l'absence de contenu mais le
MESSAGE. Le site dit « Développeur WordPress créatif » au lieu de
« Design défensif + sentinelle IA auto-réparatrice ». L'USP est noyé.

## Plan de correction type (3 jours, ~8h)

- **J1 (2h)** : Réécrire le hook + ajouter la section USP + 3 offres packagées
- **J2 (3h)** : Portfolio light + témoignages + formulaire contact
- **J3 (2h)** : SEO titres/meta + mise à jour llms.txt + test version en ligne
