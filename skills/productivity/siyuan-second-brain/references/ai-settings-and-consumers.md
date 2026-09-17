## IA de SiYuan : editeur, agent, et cles du routeur

La configuration des modeles (editeur, agent, generation d'images, embedding, rerank) vit dans
`conf/conf.json`, section `ai`. Elle s'ecrit **par l'API du noyau**, pas a froid : l'edition manuelle
de `conf.json` exige d'arreter le noyau, et le noyau reecrit le fichier en s'arretant.

### Ecrire par l'API du noyau

`POST /api/setting/setAI` (role admin — jeton `api.token`) prend l'objet `ai` complet et le persiste.

- **Ne jamais sonder cette route avec un corps vide.** `{}` repond `200 code 0` **et reecrit la
  section** : les `id` internes de `embedding` / `rerank` sont regeneres. Lire d'abord `conf.json`,
  modifier ce qui doit l'etre, renvoyer l'objet complet. (Meme famille de piege que `POST /api/keys`
  cote routeur : un POST incomplet cree/ecrase au lieu de refuser.)
- **Schema verifie** — provider : `{id, displayName, enabled, apiKey, baseURL, protocol,
  requestTimeout, models[]}` ; model : `{id, displayName, enabled, name, contextLength}`.
  `protocol: ""` a l'envoi = OpenAI chat completions (le noyau ecrit `openai`). `name` est
  l'identifiant **envoye a l'API** : les `/` sont acceptes (`openai/nvidia/nemotron-…`,
  `auto/best-reasoning`).
- **Le noyau reecrit les `id`** a l'ecriture (forme `<horodatage>-<suffixe>`) : ceux qu'on a proposes
  ne survivent pas. Relire `conf.json` pour relever les `id` reels, puis les poser dans
  `editing.modelId` / `agent.modelId`.
- **Un `modelId` qui ne correspond a aucun modele retombe silencieusement sur le premier modele
  utilisable** : au premier essai, l'agent s'est retrouve sur le modele de l'editeur sans aucune
  erreur. Verifier que chaque `modelId` pointe bien sur le modele voulu fait partie de l'ecriture, pas
  de la finition.
- Resolution cote noyau : `modelId` matche `model.id || model.name`.
- **`apiKey` est chiffree au repos** : une cle de 35 caracteres devient ~160 dans `conf.json`. Une
  comparaison d'empreintes avant/apres ne prouve donc rien — la preuve est fonctionnelle.

### Verifier en bout de chaine, pas sur le retour d'ecriture

`POST /api/ai/testModel` avec `{"model": "<name>", "provider": "<id du provider>"}` rend
`{code: 0, data: {available: [...], matched: true}}`.

- Les **noms de champs comptent** : `providerId` rend `provider not found`, `model` absent rend
  `Field [model] is required`. Le provider se designe par le champ `provider` (= son `id`).
- `available[]` est la liste `/v1/models` **vue par le noyau** : sur une cle de routeur restreinte,
  elle doit etre exactement le perimetre autorise. C'est la meilleure preuve que la cle stockee est la
  bonne, qu'elle est dechiffree, et que la restriction est active.
- Tester **chaque** modele configure, pas seulement le premier.

### Cle de routeur : dediee au consommateur

Le consommateur SiYuan (editeur/agent) parle au routeur en OpenAI-compatible : il lui faut sa propre
cle, **jamais la cle d'administration** du poste (qui sert de jeton Bearer sur `/api/*`). Elle se pose
dans `providers[].apiKey` de la section `ai`. La cle n'est lisible qu'a sa creation cote routeur : la
creer et la poser dans le meme appel.

### Un seul jeton d'API SiYuan — pas un par consommateur

`kernel/conf/api.go` : `type API struct { Token string }`. Il n'existe **qu'un** jeton de workspace :
Hermes (un ou plusieurs profils) et une application tierce le partagent. Consequence a annoncer :
la rotation est **globale** (Reglages > A propos > jeton API) et doit etre repercutee partout
(`conf/conf.json` + chaque `.env` consommateur) — un consommateur oublie casse en silence, avec un
`401` qu'on prendra pour une panne de configuration.

### Archiver un document sans le detruire

Doublon ou version depassee : **ne pas supprimer**, deplacer.

1. `POST /api/filetree/createDocWithMd` pour creer le parent d'archive
   (`{"notebook": "<id>", "path": "/archive", "markdown": "# archive\n\n…"}`) — un document
   nomme `archive`, jamais un titre contenant une barre oblique (qui creerait une hierarchie).
2. `POST /api/filetree/moveDocsByID` avec `{"fromIDs": ["<id a archiver>"], "toID": "<id du parent>"}`.
3. Verifier par `/api/filetree/listDocsByPath` (`notebook` + `path: "/"`) et par `blocks.hpath` :
   l'index SQL est **asynchrone**, donc un `hpath` encore a l'ancien emplacement juste apres le
   deplacement est un retard d'index, pas un echec — relire apres quelques secondes avant de conclure.

### Choisir le modele : deterministe, pas un alias qui tourne

Un alias dynamique de routeur (`auto/*`) resout sa cible a chaque appel : derriere une cle restreinte,
la rotation peut sortir du perimetre autorise et rendre `503 all targets were skipped by pre-dispatch
filters` (l'echec ressemble a une panne de pool et revient par vagues). Preferer un **combo local dont
toutes les cibles sont autorisees** : suffisant pour l'editeur (latence) comme pour l'agent (appels
d'outils).
