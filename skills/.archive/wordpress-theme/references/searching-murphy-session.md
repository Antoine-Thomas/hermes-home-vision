# Searching-Murphy Theme Session Lessons

## Key Fixes Applied
- **Overlay removal**: The pseudo-element `::after` on `.close` was causing a full-height overlay on large screens. Fixed with `.close::after { display:none !important; content:none !important; }`.
- **Centering articles**: Used Flexbox on `.swiper-slide` with `justify-content:center; align-items:center;` and set container to `height:100vh`.
- **Swiper initialization**: Built Swiper wrapper dynamically around existing `<article>` elements only once, added navigation elements (hidden via CSS), and initialized with `loop:true`, `keyboard:true`, `grabCursor:true`, `simulateTouch:true`.
- **Immediate slide transition**: On tab click, use `swiper.slideTo(index, 0)` (no animation) then `swiper.update()` to avoid scroll/jump.
- **Close buttons**: Ensured `.close` buttons are links to homepage via `<a href="<?php echo home_url(); ?>" class="close-btn">Accueil</a>` and removed any JS-generated `<div class="close">Close</div>`.
- **Hashchange handling**: When Swiper is ready, navigate via `slideToLoop(index)` instead of show/hide to preserve Swiper state.
- **Styling slides as cards**: Added white background, padding, border-radius, box-shadow, and max-width to `.swiper-slide article` for readability.
- **Header image enlargement**: On large screens (min-width:1200px), set `.content .inner img { width:80%; height:auto; }`.

## Devis-Custom Popup Fix (June 2026)

### Bugs Found
1. **DOM coherence**: JS referenced `error-popup-close-btn` via `getElementById` but the PHP template had no such element — `addEventListener` never fired. Classic silent JS failure.
2. **Aggressive click handler**: Clicking anywhere on the success popup redirected to `/` — even clicking the message text. User lost form state.
3. **No overlay**: Form fields behind popups remained interactive.
4. **Inline styles everywhere**: Popups had all CSS inlined (`style="display: none; position: fixed; ..."`), unmaintainable.
5. **No animations**: Popups appeared/disappeared abruptly.
6. **Inconsistent structure**: Success popup had a close (×) button, error popup did not.

### Fix Applied
- **PHP (`page-devis-custom.php`)**:
  - Added `<div id="popup-overlay">` before popups
  - Replaced inline styles with CSS classes: `devis-popup`, `devis-popup-close`, `popup-icon`
  - Added `<button id="error-popup-close-btn" class="devis-popup-close">` to error popup
  - New CSS: overlay fade, popup scale+fade transition (0.3s), icon bounce animation, button hover/active 3D effects, body scroll lock
- **JS (`assets/js/devis-custom.js`)**:
  - Added `popupOverlay` DOM reference
  - New `showPopup(popup)` helper: adds `active` class to overlay + popup, locks body scroll
  - `hidePopups()`: removes `active` class, restores scroll
  - Success popup: only buttons redirect to `/`; background click only closes
  - Error popup: all close methods work (button, ×, overlay, Esc)
  - `document.addEventListener('keydown', ...)` for Escape key

### Pattern: JS / HTML DOM Audit
1. grep `getElementById` in JS → list all IDs
2. grep `id="` in PHP → list all IDs
3. diff the two lists → every JS ID must exist in PHP
4. Also check `querySelector`/`querySelectorAll` selectors

## Files Modified
- `js/main.js`: Rewrote to include `initHomeSwiper()`, updated `_show` and `hashchange` handlers.
- `style.css`: Added centering, overlay hide, swipe navigation hide, and card styles.
- `page-devis-custom.php`: Popup HTML/CSS overhaul (overlay, animations, classes).
- `assets/js/devis-custom.js`: Popup logic overhaul (classList API, overlay, Escape key).

## Theme Cards v1.0 QA — Puppeteer Headless (July 2026)

### Pattern: puppeteer-core + Chrome local pour QA theme
- **Chrome path Windows**: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- **Chrome path Mac**: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- **Install**: `npm install puppeteer-core` (pas puppeteer — core utilise Chrome existant)
- **user-data-dir unique** par run (timestamp) pour eviter les locks de profil
- **Cache-buster**: `?cb=TIMESTAMP` dans l'URL pour forcer rendu frais
- **Certificats**: `--ignore-certificate-errors` pour les domaines `.local` en dev
- **Puppeteer v25+**: `page.waitForTimeout()` retire — utiliser `await new Promise(r => setTimeout(r, ms))`
- **Capture DOM post-JS**: `await page.goto(url, { waitUntil: 'networkidle2' })` puis `sleep(900)` puis `await page.content()`
- **Verifications DOM**: `page.evaluate(() => { return { cardEye: document.querySelectorAll('.card__eye').length, ... } })`

### Piege: Chrome headless depuis git-bash (MSYS)
- MSYS traduit les chemins commencant par `/` — `--screenshot=/c/Users/...` devient `C:/Program Files/Git/c/Users/...`
- **Solution**: lancer Chrome via PowerShell, pas bash: `powershell -Command "& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --headless=new --screenshot=C:\path\out.png ..."`
- Alternative: utiliser puppeteer-core en Node (pas de probleme de path)

### Pattern: Devis sandbox POST (curl + cookies)
```bash
# 1. GET pour etablir la session + extraire le nonce
NONCE=$(curl -k -c cookie.jar -s "$URL" | grep -oP 'name="devis_nonce" value="\K[^"]+')
# 2. POST avec cookies de session + prestations[] array
curl -k -b cookie.jar -s -w "\n%{http_code}" -X POST "$URL" \
  --data-urlencode "devis_nonce=$NONCE" \
  --data-urlencode "email=test@local" \
  --data-urlencode "prestations[]=site" \
  --data-urlencode "prestations[]=seo" \
  --data-urlencode "website_honeypot="
```
- Le champ `prestations[]` est un array PHP — utiliser `--data-urlencode` (pas `-d`)
- Le honeypot doit etre vide (sinon bloque comme spam)
- En local (`WP_ENVIRONMENT_TYPE=local`), l'email echoue — c'est normal
- Message succes attendu: `{"status":"success","success":true,"message":"Devis envoyé avec succès."}`

### Piege: Git add + chemins trop longs (Windows)
- Les profils Chrome (`chrome-profile-*/Default/Extensions/...`) contiennent des chemins > 260 caracteres
- `git add` echoue avec `error: open(...): Filename too long`
- **Solution**: ajouter `work-in-progress/chrome-profile-*/` au `.gitignore` AVANT `git add`

## Verification
- All sections (Intro, WordPress, Design, Associations, Contact) appear centered and full-screen.
- Swiping or using keyboard arrows loops infinitely in both directions.
- Clicking navigation tabs shows the correct article instantly without animation.
- Close buttons (logo and .close-btn) return to homepage.
- No console errors; layout stable on resize.
- Popups: overlay blocks background, animations play, Escape closes, error popup × works.
- Theme Cards QA: puppeteer-core screenshots 320/tablet/laptop, DOM dumps, .card__eye/.sm-eye-img/SMCards verified.

## Session 2026-07-21 — Home button final + eye-closed.svg 404 fix

### Home Button — Lessons Learned
- **Start simple.** The user rejected 4 iterations before accepting the final version: circular 30px, teal #0c9f93, bottom-left corner, no label.
- **Don't over-engineer matching.** Trying to pixel-match `.next` (4rem, flex-direction:column, font-size:1.5rem, drop-shadow) was rejected — the user wanted simple, not complex.
- **Incremental > big-bang.** Each iteration was a single commit. The user could roll back any step.
- **Final CSS:** `width:30px; height:30px; border-radius:50%; background:#0c9f93; position:absolute; bottom:0; left:0;` — that's it.

### eye-closed.svg 404 via Cache/Min Plugin
- **Problem:** `document.currentScript.src` derivation in MobileEye module produced wrong path when WP cache plugin rewrites URLs.
- **Fix:** `wp_localize_script('searching-murphy-theme-cards', 'SM_THEME_CARDS', array('eyeClosedSvg' => get_stylesheet_directory_uri() . '/assets/img/eye-closed.svg'))` in functions.php.
- **JS fallback chain:** 1) `SM_THEME_CARDS.eyeClosedSvg`, 2) `currentScript.src` regex, 3) DOM query for script tag.
- Applied to both `theme-cards.js` and `mobile-eye-fallback.js`.

### Email Campaign — 63 B2B Prospection
- **SMTP App Password** (smtp.gmail.com:587) — 63/63 sent, 0 failures. More reliable than OAuth.
- **execute_code 300s timeout** — campaigns longer than ~189s must use `terminal(background=True)`.
- **File-based script** — write `.py` file first, then `terminal("python campagne.py", background=True)`. Inline `python -c "..."` fails with passwords containing spaces.
- Template: HTML couleurs SM (#cbe8e8 fond, #0c9f93 cartes, #fdc502 accents), bloc "Secrétaire Virtuel IA", mention RGPD STOP.

### .devis-home-btn / .cat-wp-home-btn — bottom-left mirror of .next
- **Final pattern**: identical to `.next` but bottom-left instead of bottom-right
- 4rem×4rem, background #284543, border-radius `0 0 0 0.5rem` (bottom-left corner)
- Icon-only (SVG house, 20×20px), **no label ever** — "le mot accueil casse le visuel"
- Hover: icon turns yellow #fdc502 + translateY(-2px)
- Active click: background turns yellow #fdc502, inset shadow, translateY(1px)
- Position: `#main article.card .devis-home-btn { position:absolute; bottom:0; left:0; z-index:20 }`
- Devis page exception: NOT absolute (normal flow since not inside article.card)
- CSS §14 in theme-cards.css, 135 braces, 762 lines

### User preferences from corrections
- **Icon-only buttons**: never add visible text labels on card navigation buttons. Use aria-label.
- **Match existing patterns**: when adding a new card button, mirror the style of the existing one (.next) rather than inventing new sizes/colors/positions.
- **No desktop-only variants**: buttons must be identical across all screen sizes (mobile/tablet/laptop).
- **No scrollbars on cards**: `overflow-x: hidden !important` on `article.card` and `#main`.
- **CSS non-destructive**: hide elements with CSS rather than removing PHP markup.

### Catalogue & Politiques
- **Catalogue Kimi:** `work-in-progress/catalogue-kimi.json` (242 fichiers inventories)
- **final-collab.json v2.0:** politiques formalisees — fallback (cost_threshold=$0.5, max 5 calls/day, 7 error codes), sandbox (enabled, clone_path_template, auto_tag), learning (2 succès=learned, 2 échecs=obsolete, 168h weight), audit (log calls, alert <$0.5, record stdout/stderr)
- **Kimi credit:** $0.888 restant, 0 appels session v3, seuil alerte $0.50

### QA Launcher
- **Script:** `tools/qa-launcher.py` — lancement combiné QA headless + Devis POST
- Usage: `python tools/qa-launcher.py` (nécessite site Local démarré https://searching-murphy.local)
- Vérifie disponibilité site → lance Puppeteer → POST Devis → sauvegarde logs dans work-in-progress/logs/

### Git
- **10 commits** child-lagoon (7741498 Kimi → 78f8beb Hermes)
- **Tags:** `pre-collab-20260720-214236` (snapshot pre-v3), `pre-collab-20260720-214403-final` (snapshot final)
- **Rollback:** `git reset --hard pre-collab-20260720-214236`
- **Dépôt racine:** `C:\Users\searc\Local Sites\searching-murphy\app\public\wp-content\themes`

### Validations (11/11 pass)
- JS 3/3: theme-cards.js, theme-cards-fx.js, mobile-eye-fallback.js
- CSS 3/3: 121/121, 57/57, 49/49
- SVG 5/5: comet, eye-closed, eye-sprite, starfield, starfield-nebula
- PHP lint: skipped (php absent du PATH git-bash)
- git apply --check: "already exists" (expected, no format errors)

### État QA live
- Site Local offline (connection refused port 443)
- QA headless + Devis sandbox à relancer après démarrage Local
- Résultats v1 en cache: 5 cards, 4 .card__eye, SMCards=true, Devis HTTP 200

### Points d'attention manuels
- Vérifier captures 320px: pas d'overflow, œil positionné correctement
- Sandbox: éviter copie node_modules (timeout) — utiliser `cp -r --exclude=node_modules`
- Surveiller crédit Kimi: alerte si < $0.50, appeler uniquement pour erreurs bloquantes critiques

## Session 2026-07-20 — Hermes v5 final refinements

### Home button final state (after 3 corrections)
- **User rejected over-engineered designs twice**: "tu as complexifié le design", "restaure le comme juste avant et reduit le de 40%"
- **Final CSS**: 30×30px circle, `border-radius:50%`, `background:#0c9f93`, `hover:#fdc502`, `bottom:0; left:0`
- **Icon**: 16px SVG house, no label, no flex-direction column, no drop-shadow, no font-size/weight
- **Lesson**: start SIMPLE, only add properties when explicitly asked

### eye-closed.svg 404 fix (cache/min plugin)
- WP cache plugin rewrites `theme-cards.js` URL → `currentScript.src` derivation breaks
- **Fix**: `wp_localize_script('searching-murphy-theme-cards', 'SM_THEME_CARDS', array('eyeClosedSvg' => ...))`
- JS priority: `SM_THEME_CARDS.eyeClosedSvg` → `currentScript.src` → fallback
- Applied to both `theme-cards.js` (MobileEye module) and `mobile-eye-fallback.js`

### Contact prospection consolidation
- Merged Google Contacts (873 rows → 101 with email after filtering) + 33 Caen manual contacts
- 134 total in `contacts-envoi-final.csv`, categorized into 5 segments
- HTML email template with SM brand colors (teal #0c9f93, yellow #fdc502, light #cbe8e8)
- RGPD-compliant: source identifiable, STOP opt-out, B2B legitimate interest basis

### .card__eye hide on front page (CSS-only, non-destructive)
- **CSS §13, theme-cards.css** — selecteurs `.front-page .card__eye`, `.page-template-front-page .card__eye`, `body.home .card__eye`, `.home .card__eye`
- `display:none !important` + `visibility:hidden` + zero dimensions + `background:transparent`
- Markup PHP conservé intact (`.card__eye` buttons restent dans le DOM)
- Aucun impact sur les pages category/single/archive

### .cat-wp-home-btn / .devis-home-btn — circular yellow → responsive pill
- **Classes partagées** : `.cat-wp-home-btn` et `.devis-home-btn` reçoivent les mêmes styles
- **Mobile (<900px)** : cercle jaune `#fdc502`, 48×48px, `border-radius:50%`, icône SVG seule (label `display:none`)
- **Desktop (≥900px)** : pilule `border-radius:12px`, fond gradient vert `#2C6B63→#244E48`, icône blanche + label "Accueil"
- **Hover** : `translateY(-4px) scale(1.03)`, ombre portée, fond `#f6c43a`; icône `translateY(-1px) rotate(-6deg) scale(1.03)`
- **Focus** : outline `3px solid rgba(29,161,242,0.18)`, offset 3px
- **prefers-reduced-motion** : `transition:none !important; transform:none !important`
- **5 ancres** dans `front-page.php` : `<a class="devis-home-btn cat-wp-home-btn">` avec SVG maison + `<span class="devis-home-label">Accueil</span>`
- Anciennes classes `.card-home-btn` (Font Awesome `fa-home`) complètement remplacées

### Pattern: Responsive button (circle → pill)
- Mobile-first: cercle compact, icône seule, pas de texte
- Desktop breakpoint (≥900px ici, ajustable): pilule avec `width:auto; height:auto`, label révélé
- Transition fluide via `@media (min-width: 900px)` — pas de JS
- Classes partagées entre variantes (`.cat-wp-home-btn`, `.devis-home-btn`) pour cohérence visuelle
- SVG inline (pas de dépendance Font Awesome), `stroke="currentColor"` pour hériter la couleur

### Commits v4
- `da48661` feat(ui): circular yellow .cat-wp-home-btn; responsive pill on desktop
- `6a66e69` chore: theme-cards.patch (83 MB, 12 commits total child-lagoon)

### Validation
- CSS 139/139 braces, 781 lignes
- front-page.php: 5× `.devis-home-btn.cat-wp-home-btn`, 0× `.card-home-btn`
- `.card__eye` hide: 4 sélecteurs CSS ciblant toutes les variantes de front page
