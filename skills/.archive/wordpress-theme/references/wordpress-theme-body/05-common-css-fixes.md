<!-- Source: wordpress-theme/SKILL.md · section 'Common CSS Fixes' -->

## Common CSS Fixes

```css
/* Footer always visible */
#footer { display:block!important; opacity:1!important; visibility:visible!important; }
body.is-article-visible #footer { display:none!important; }

/* Hide Swiper navigation arrows */
.swiper-button-prev, .swiper-button-next { display:none !important; }

/* Fix overlay issues */
.close::after { display:none !important; content:none !important; }

/* Center slide content */
.swiper-slide { display:flex; justify-content:center; align-items:center; }
.swiper-slide article { max-width:800px; margin:40px auto; padding:30px; }
```
