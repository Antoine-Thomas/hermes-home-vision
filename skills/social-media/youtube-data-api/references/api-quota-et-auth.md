# Quota et authentification — YouTube Data API v3

## Table de cout (unites, quota par defaut 10 000/jour)

| Endpoint | Cout | Note |
|---|---|---|
| `videos.list` | 1 | 50 `id` maximum par appel |
| `playlistItems.list` | 1 | 50 items maximum par page |
| `channels.list` | 1 | `forHandle=@nom` resout la chaine sans OAuth |
| `playlists.list` | 1 | rarement utile seul |
| `search.list` | **100** | a proscrire : la playlist `uploads` donne la meme liste |
| `commentThreads.list` | 1 | |
| `videos.insert` / `update` / `delete` | 50-1600 | hors perimetre lecture seule |

Balayage complet d'une chaine de ~800 videos : 1 (`channels`) + 17 (`playlistItems`) + 17 (`videos`)
= **35 unites**. Une journee de quota permet donc plusieurs passes — mais un `search.list` mal place
en consomme 100 d'un coup.

Le quota est consomme **meme sur une reponse d'erreur** : un appel qui rend 403 a bien ete paye.
Toujours compter les appels et les reporter.

## Ordre de demarrage

Commencer par `channels.list?forHandle=` pour lire `relatedPlaylists.uploads`, et n'attaquer
`videos.list` qu'une fois la liste des `video_id` construite par `playlistItems.list`. Appeler
`videos.list` « pour voir » avant de connaitre les identifiants facture des appels sans rien construire.

## Cle API ou OAuth2 : la table de decision

| Besoin | Credential |
|---|---|
| Lire titres, vues, duree, tags, `privacyStatus` de videos **publiques** | cle API en query string |
| Voir les videos **privees** ou **non listees** d'une chaine | OAuth2, compte proprietaire de la chaine |
| Ecrire (upload, titre, miniature, suppression) | OAuth2 avec les scopes `youtube.force-ssl` |
| Statistiques d'un compte (analytics) | OAuth2 + YouTube Analytics API (autre API) |

Consequence pour un audit de nettoyage : avec une simple cle API, le total de la chaine lu dans
YouTube Studio peut depasser de plusieurs centaines le nombre de videos recuperees. Ce n'est pas une
erreur d'inventaire : les videos privees sont invisibles. Conclure que l'ecart est *probablement* du a
cela, le presenter comme une deduction (seul OAuth2 le prouve), et ne pas « corriger » le chiffre de
l'utilisateur.

## Formats de cle Google : les reconnaitre avant de depenser un appel

| Format | Longueur | Origine |
|---|---|---|
| `AIza...` | 39 | cle API d'un projet Google Cloud — la forme attendue par la Data API |
| `AQ.Ab8...` | 53 (contient un point) | cle AI Studio / Gemini, non utilisable telle quelle pour YouTube Data v3 |

Verifier longueur + prefixe en premier, puis un seul appel de validite. Si le prefixe est `AQ.`,
prevenir avant de tester plutot que de bruler un audit qui partira en 401. Le test de validite coute
1 unite : le faire avec le `part=` complet du mandat pour que la reponse serve aussi de premier
releve de la chaine.

## Table de decision des codes d'erreur

| HTTP + corps | Interpretation | Action |
|---|---|---|
| 200 | cle valide, reponse exploitable | continuer |
| 403 `accessNotConfigured` / `API has not been used in project` | YouTube Data v3 non activee sur le projet de la cle | activer l'API dans la console Cloud du projet, puis relancer |
| 403 `API_KEY_INVALID` / `API key not valid` | cle invalide ou revoquee | demander une cle valide |
| 401 `UNAUTHENTICATED` + `CREDENTIALS_MISSING`, message *API keys are not supported by this API. Expected OAuth2 access token...* | le serveur rejette le **type** de credential, pas la cle | ne PAS conclure « cle invalide » ; passer a une cle Cloud classique ou a OAuth2 |
| 403 `quotaExceeded` | quota du jour epuise | reprendre le lendemain, ne pas boucler |
| 404 `playlistNotFound` | `playlistId` de uploads errone ou chaine supprimee | re-resoudre via `channels.list?forHandle=` |
| 429 / 5xx | limite transitoire | retry exponentiel (le script le fait deja) |

Regle de rapport : sur toute branche autre que 200, rendre le code HTTP **et** le corps JSON brut, sans
sortie partielle. Masquer les jetons avant impression — un corps d'erreur Google peut citer la cle ou
l'identifiant de projet.

## Criteres de classification par defaut (audit de nettoyage)

**Rouge — a supprimer, confiance haute** (un seul suffit) :
- vues = 0 et publiee depuis > 30 jours
- vues < 10 et publiee depuis > 6 mois (182 j)
- `privacyStatus = unlisted` depuis > 30 jours

**Jaune — a examiner, confiance moyenne** :
- vues < 100 et > 12 mois
- duree < 60 s et > 6 mois (brouillon / test probable)
- marqueur de brouillon dans le titre : `test`, `essai`, `brouillon`, `draft`, `wip`, `todo`,
  `a finir`, `v1`, `v2`, `temp`
- doublon par titre proche (Levenshtein normalise < 0,2 sur titres normalises) — livrer les groupes

**Vert — a garder** : tout le reste (vues >= 100, ou recent < 6 mois, ou contenu structurant).

Ordre de priorite rouge > jaune > vert : une video qui remplit un critere rouge reste rouge meme si
elle porte aussi un marqueur de brouillon. Trier le CSV par verdict puis par vues croissantes.

Deux considerations qui evitent un faux rapport :
- Un critere qui n'a **rien** declenche parce que la donnee est absente de la reponse (aucune video
  `unlisted` dans un inventaire par cle API) n'est pas un critere « respecte » : le nommer comme non
  testable.
- Les seuils ci-dessus sont des **defauts** : les citer dans le rapport pour que l'utilisateur puisse
  les contester, et ne jamais appliquer un seuil different en silence.
