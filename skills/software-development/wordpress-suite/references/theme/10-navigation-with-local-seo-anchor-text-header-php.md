<!-- Source: wordpress-theme/SKILL.md · section 'Navigation with Local SEO Anchor Text (header.php)' -->

## Navigation with Local SEO Anchor Text (header.php)

When the site uses a hardcoded `<nav><ul>` menu (not a WordPress nav menu), update the `<a>` text to include city + service keywords:

```html
<nav>
    <ul>
        <li><a href="#intro">Accueil</a></li>
        <li><a href="#code">Création site WordPress Caen</a></li>
        <li><a href="#Design">Design graphique Caen</a></li>
        <li><a href="#assos">Intelligence Artificielle Caen</a></li>
        <li><a href="#contact">Contact / Devis gratuit</a></li>
    </ul>
</nav>
```

Also update the hardcoded `<meta name="description">` in header.php to reflect the SEO-optimized text with city and service keywords.
