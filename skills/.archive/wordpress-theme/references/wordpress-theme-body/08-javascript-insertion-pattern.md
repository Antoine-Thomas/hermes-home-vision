<!-- Source: wordpress-theme/SKILL.md · section 'JavaScript Insertion Pattern' -->

## JavaScript Insertion Pattern

Always insert new code inside the initialization function's scope, before the closing brace, at the correct indentation level:

```javascript
// Add click listeners for manual slide navigation
document.querySelectorAll(".next a").forEach(function(link) {
    link.addEventListener("click", function(e) {
        e.preventDefault();
        if (window._homeSwiper) {
            window._homeSwiper.slideNext();
        }
    });
});
```
