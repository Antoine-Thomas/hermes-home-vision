# Playlists d'une chaine : audit, comptage, quota

Approfondissement de l'etape « auditer les playlists » : mesurer l'existant AVANT de proposer une
strategie de playlists, parce qu'une chaine ancienne a deja des playlists — souvent redondantes.

## 1. Enumeration

`playlists.list?part=snippet,contentDetails,status&channelId=<UC...>&maxResults=50`, boucle sur
`nextPageToken`. Elle ne retourne PAS la playlist systeme `uploads` (`UU...`) : la mentionner a part si
le rapport doit couvrir « toutes les playlists ».

## 2. Comptage : declare contre mesure

`contentDetails.itemCount` est le compte DECLARE par YouTube ; `playlistItems` pagine est la mesure.
Comparer les deux et publier l'ecart : il designe une video comptee dans la playlist mais plus
recuperable (supprimee ou passee en prive). Mesure d'un audit de 33 playlists : 0 ecart sur 33 — un
resultat a publier, pas une absence de resultat.

## 3. Budget quota : les playlists fourre-tout explosent le cout

Chaque page de `playlistItems` coute 1 unite. Un inventaire complet de ~800 videos coute ~35 unites ;
l'audit des playlists de la MEME chaine en a coute 112 pour un seul passage, parce que les grosses
playlists sont des fourre-tout (727 items = 15 pages, 610 = 13, 580 = 12, 364 = 8).

- Annoncer le cout AVANT de lancer, et se demander si le comptage suffit : `playlists.list` avec
  `part=contentDetails` donne `itemCount` pour 50 playlists en 1 unite, sans paginer un seul item.
- Ne paginer les items que pour les playlists dont on veut reellement les `video_id`.

## 4. Ce que l'audit revele — a remonter AVANT toute strategie de playlists

- **Redondance** : sur une chaine ancienne, plusieurs playlists recouvrent la quasi-totalite de la
  chaine (mesure : une playlist de 727 items pour 732 videos, plus deux autres a 610 et 580). Toute
  nouvelle playlist thematique nait en DOUBLON d'une existante : decider d'abord du sort des anciennes
  (fusion / archivage / renommage), sinon le spectateur trouve deux portes pour la meme piece, et la
  nouvelle vitrine ne se distingue pas du fourre-tout.
- **Playlists sans description** : compter celles dont la description fait moins de 20 caracteres
  (14 sur 33 mesurees). C'est la liste de travail la moins couteuse et la plus rentable avant de
  creer quoi que ce soit de neuf.
- **Classer par nombre d'items, pas par nom** : une playlist nommee « gaming » ou « musique » est
  souvent un fourre-tout inutilisable comme vitrine, quel que soit son intitule.
- Croiser les playlists avec les listes de tri (a garder / a deplacer) : une playlist thematique qui
  ne contient que des videos « a deplacer » suivra la migration de chaine, elle ne sert a rien a
  restructurer ici.

## 5. Livrable

`yt_playlists_actuelles.json` : `{playlists: [{playlist_id, titre, description, privacyStatus,
itemCount_declare, items_retournes, video_ids}]}` + un resume (`nb_playlists`, total des items).
Conserver `video_ids` : c'est ce qui permet de croiser playlists et listes de decision sans re-payer
le quota.
