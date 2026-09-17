1|---
2|name: wordpress-theme-modification
3|description: Guidelines for safely modifying a WordPress child theme, including removing sections and adding custom JavaScript behaviors.
4|version: 1.0
5|author: Hermes Agent
6|---
7|# WordPress Theme Modification
8|
9|## Description
10|Guidelines for safely modifying a WordPress child theme, specifically the Searching-Murphy Astra child theme, including removing sections (e.g., `<article id="devis">`) and adding custom JavaScript event listeners (e.g., on `.next a`) inside initialized scripts like Swiper initialization.
11|
12|## When to Use
13|- You need to remove or comment out specific sections from theme templates.
14|- You need to add custom event listeners to existing DOM elements inside initialized scripts.
15|- You must ensure that theme layout and JavaScript dependencies (like Swiper) remain functional after changes.
16|
17|## Steps
18|
19|### 1. Backup the original file
20|Always create a backup before editing:
21|```bash
22|cp path/to/file.ext path/to/file.ext.bak
23|```
24|
25|### 2. Editing PHP templates (e.g., front-page.php)
26|- Always verify the element exists before attempting modification by checking for its presence in the file.
27|- Locate the section to modify by searching for unique identifiers (e.g., `id="devis"`, `data-action="close"`).
28|- Use a precise regex that matches the entire element including opening and closing tags.
29|- When removing elements, ensure you remove the complete block from opening to closing tag.
30|- When replacing elements (e.g., changing `<div>` to `<a>`), preserve any attributes that should be transferred and maintain proper HTML structure.
31|- Verify the modification by checking that the change is correct and no unintended changes were made.
32|- After modification, verify that the file still has valid PHP syntax (if applicable).
33|
34|### 3. Adding JavaScript listeners inside existing functions
35|- Identify the target function where initialization occurs (e.g., `ensureSwiperInitialized`).
36|- Find the closing brace of the function (matching opening/closing braces).
37|- Insert your code just before the closing brace, maintaining the same indentation level (typically three tabs `\t\t\t`).
38|- Example snippet to add click listeners:
39|```javascript
40|// Add click listeners to .next a for manual slide navigation
41|document.querySelectorAll(".next a").forEach(function(link) {
42|    link.addEventListener("click", function(e) {
43|        e.preventDefault();
44|        if (window._homeSwiper) {
45|            window._homeSwiper.slideNext();
46|        }
47|    });
48|});
49|```
50|- Ensure you prevent default link behavior to avoid navigation conflicts.
51|
52|### 4. Verify Swiper looping
53|- Confirm that Swiper is initialized with `loop: true` option.
54|- After removal of sections, test that navigation still loops infinitely (Swiper handles duplicate slides).
55|- No further changes needed if loop option remains.
56|
57|### 5. Test changes
58|- Refresh the theme frontend and verify:
59|  - Removed section no longer appears.
60|  - Clicking `.next a` advances the slide without jumping to hash.
61|  - Navigation loops correctly.
62|- Check browser console for any errors.
63|
## Pitfalls
- Removing the wrong article block: always verify surrounding context.
- Adding listeners outside the Swiper initialization scope: `window._homeSwiper` may be undefined.
- Forgetting `e.preventDefault()` causing hash jumps.
- Incorrect indentation breaking JavaScript formatting.
- Not preserving the original function's brace balance leading to syntax errors.
- **Double Swiper initialization from `home-swiper.js` fallback** — the theme has two Swiper init scripts: `js/main.js` (primary, with full config) and `assets/js/home-swiper.js` (fallback). If both fire, two Swiper instances compete on the same element, causing erratic positioning. Fix: primary init sets `el.setAttribute('data-swiper-ready', '1')`; fallback checks `hasAttribute('data-swiper-ready')` and returns early. See `references/swiper-custom-navigation.md` → Double Swiper Initialization.
- **Navigating before showing causes offset** — `navigateToArticle()` calls `swiper.update()` which needs visible dimensions. If `$main.show()` runs AFTER `navigateToArticle()`, the update happens at zero size. Always show first, then navigate. See `references/swiper-custom-navigation.md` → Resilience section.
70|
71|## Verification
72|- Use `grep -n 'id=\"devis\"' front-page.php` to confirm removal.
73|- Search for added snippet in js/main.js to ensure presence.
74|- Manually test click behavior.
75|
76|## References
77|- See `references/swiper-custom-navigation.md` for detailed Swiper API usage.
78|- See `references/searching-murphy-session-lessons.md` for lessons from the Searching-Murphy theme session.
79|- See `templates/swiper-nav-listener.js` for a ready-to-use snippet.
80|- See `templates/swiper-immediate-transition.js` for immediate slide transition without animation.
81|
82|## Theme-Specific Modifications for Searching-Murphy
83|When working on the Searching-Murphy Astra child theme, consider these additional patterns:
84|
85|- Replace `<div data-action="close"></div>` elements with `<a href="<?php echo home_url(); ?>" class="close-btn">Accueil</a>` to make close buttons link to the homepage. Ensure any legacy `<div class="close">Close</div>` is not added via JavaScript (remove or comment out such lines).
86|- Adjust Swiper configuration in `ensureSwiperInitialized` to set `loop:true`, `allowSlideNext:true`, and `allowSlidePrev:true` for true infinite looping in both directions.
87|- For immediate article display without animation when navigating via tabs, use `window._homeSwiper.slideTo(index, 0)` (duration 0) followed by `window._homeSwiper.update()` to layout the slide instantly.
88|- Center slide content perfectly: set the Swiper container to `height:100vh`, then use Flexbox on slides: `.swiper-slide { display:flex; justify-content:center; align-items:center; }`. Limit article width with `.swiper-slide article { max-width:800px; margin:0 auto; width:90%; text-align:center; }`.
89|- Hide Swiper navigation arrows if not needed via CSS: `.swiper-button-prev, .swiper-button-next { display:none !important; }`.
90|- Prevent overlay issues: if a pseudo‑element `::after` on `.close` creates a full‑height overlay, hide it with `.close::after { display:none !important; content:none !important; }`.
91|- When initializing Swiper, do it only once (check a flag) and build the Swiper wrapper dynamically around existing `<article>` elements without altering their HTML structure.
92|- In the `hashchange` event, if Swiper is initialized, navigate to the corresponding slide with `slideToLoop(index)` instead of hiding/showing articles, preserving the Swiper state and active tab synchronization.
93|- After any DOM change that affects layout (e.g., showing/hiding articles), call `window._homeSwiper.update()` to ensure Swiper recalculates slide sizes.
94|- Style slides as cards for better readability: `.swiper-slide article { max-width:800px; margin:40px auto; padding:30px; background:#fff; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.15); text-align:center; }`.
95|- Enlarge header image on large screens via media query: `@media (min-width: 1200px) { .content .inner img { width:80%; height:auto; } }`.
96|- For toggling between header and Swiper views, use CSS classes rather than inline hide/show: add `.header-hidden { display:none!important; }` to header and make `#main.swiper.home-swiper` fixed positioned with `width:100vw!important; height:100vh!important; position:fixed; top:0; left:0; z-index:999; background:#cbe8e8;` when active.
97|- Use JavaScript to toggle these classes: `$header.addClass('header-hidden')` to hide header and `$header.removeClass('header-hidden')` to show it, while controlling `#main` visibility through Swiper initialization state.
98|- Add click listeners to logo link (`.logo-link`) and close buttons (`.close-btn`) to trigger the header hide/show toggle for returning to homepage.