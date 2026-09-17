<!-- Source: wordpress-theme/SKILL.md · section 'Breadcrumb + Category-to-Pillar Pattern (content.php)' -->

## Breadcrumb + Category-to-Pillar Pattern (content.php)

When modifying `template-parts/content.php` for SEO, add a `$pilier_map` array at the top to map category slugs to pillar page URLs:

```php
$pilier_map = array(
    'wordpress' => '/developpeur-web-wordpress-caen/',
    'design'    => '/creation-site-design-graphique-caen/',
    'ia'        => '/developpeur-ia-agentique-caen/',
    'photo'     => '/photographe-professionnel-caen/',
    'video'     => '/photographe-professionnel-caen/',
);
```

### Breadcrumb (single posts only)
```php
if ( is_singular() && 'post' === get_post_type() ) :
    $cats = get_the_category();
    if ( ! empty( $cats ) ) :
        echo '<nav class="breadcrumb">';
        echo '<a href="' . esc_url( home_url( '/' ) ) . '">Accueil</a>';
        foreach ( $cats as $cat ) {
            $cat_slug = strtolower( $cat->slug );
            echo ' / ';
            if ( isset( $pilier_map[ $cat_slug ] ) ) {
                echo '<a href="' . esc_url( home_url( $pilier_map[ $cat_slug ] ) ) . '">'
                    . esc_html( $cat->name ) . '</a>';
            } else {
                echo '<a href="' . esc_url( get_category_link( $cat->term_id ) ) . '">'
                    . esc_html( $cat->name ) . '</a>';
            }
        }
        echo '</nav>';
    endif;
endif;
```

### CTA Block (bottom of single posts)
```php
<?php if ( is_singular() && 'post' === get_post_type() ) : ?>
<div class="post-cta-devis" style="margin-top:40px;padding:25px;background:var(--surface);
     border-radius:var(--radius);border-left:4px solid var(--primary);text-align:center;">
    <p style="margin:0 0 12px 0;font-size:1.1em;">
        <strong>Besoin d'un service similaire à Caen ?</strong>
    </p>
    <p style="margin:0 0 16px 0;color:var(--muted);font-size:0.95em;">
        Développement WordPress, design, IA, photo — je réalise votre projet sur mesure.
    </p>
    <a href="https://www.searching-murphy.com/devis-automatique" class="button primary"
       style="display:inline-block;padding:12px 28px;background:var(--primary);
              color:#fff;text-decoration:none;border-radius:8px;font-weight:600;">
        <i class="fas fa-file-invoice" style="margin-right:8px;"></i>
        Demander un devis gratuit à Caen
    </a>
</div>
<?php endif; ?>
```
