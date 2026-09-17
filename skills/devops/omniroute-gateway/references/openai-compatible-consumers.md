# Brancher un consommateur local sur OmniRoute (OpenAI-compatible)

Une app locale (SiYuan, un script, un IDE) doit consommer les modeles via `http://127.0.0.1:20128/v1`
avec **sa propre cle dediee**, et la chaine doit etre verifiee de bout en bout avant d'annoncer que
c'est configure.

## Regles

1. **Ne jamais poser la cle du poste dans un fichier de config d'application.** La cle du poste est
   aussi le jeton d'administration (`Bearer` sur `/api/keys`) : la stocker dans un fichier lu par un
   agent, c'est donner les droits d'administration a cet agent. Creer une cle dediee restreinte (voir
   la section « Cles API dediees » de SKILL.md).
2. **Le jeton n'est lisible qu'a la creation** (`POST /api/keys`) ; `GET /api/keys` le masque. Capturer
   la cle et la poser chez le consommateur **dans le meme appel** — sinon il faut recreer une cle.
3. **Autoriser les modeles qu'on va reellement configurer, plus les alias de repli.** Une cle
   restreinte a un `auto/*` sans ses cibles concretes renvoie `503 ALL_TARGETS_SKIPPED`.
4. **Prouver la portee cote client** : `GET /v1/models` avec la cle restreinte ne doit annoncer que les
   modeles autorises. C'est la verification la plus lisible que la restriction est active.
5. **Prouver la chaine cote application** : chaque app a un chemin de test (voir ci-dessous) — une
   ecriture de config qui repond `200` ne prouve rien du dechiffrement ni de la connectivite.

## Recette : SiYuan (kernel :6806)

- Config : `<workspace>/conf/conf.json`, section `ai`. **Ne pas editer ce fichier a la main pendant que
  SiYuan tourne** (il reecrit sa config a chaque changement) : passer par l'API de reglage. Les routes
  `/api/setting/*` et `/api/ai/*` sont **POST-only** — un `GET` rend `404 page not found`.
- `POST /api/setting/setAI` **ecrit meme avec un corps vide** : une sonde `{}` a regenere les ids
  internes de `embedding` / `rerank` / `providers`. Ne jamais s'en servir pour tester l'existence.
- Schema : `providers[]` = `{id, displayName, enabled, apiKey, baseURL, protocol, requestTimeout,
  models[]}` · `models[]` = `{id, displayName, enabled, name, contextLength}` · `protocol: "openai"`
  (vide = OpenAI chat completions par defaut) · `editing.modelId` / `agent.modelId` /
  `imageGeneration.modelId` referencent l'`id` **ou** le `name` d'un modele.
- **Toujours envoyer la cle BRUTE** : SiYuan chiffre `apiKey` au repos (une cle de 35 caracteres
  revient en blob de ~160). Ne jamais renvoyer le blob stocke.
- **SiYuan regenere les ids a l'enregistrement et remappe les references ; un `modelId` non resolu
  retombe silencieusement sur le PREMIER modele utilisable.** Procedure : poster une fois, relire
  `conf.json`, poster une seconde fois avec les ids **resolus**, puis verifier que les deux `modelId`
  pointent bien sur les `models[].id` vises.
- Verification de bout en bout : `POST /api/ai/testModel {"model": "<name>", "provider": "<id du
  provider enregistre>"}` → `data.available[]` (la liste `/v1/models` recuperee avec la cle stockee) et
  `data.matched`. Les noms de champs comptent : `modelId` / `providerId` rendent respectivement
  `Field [model] is required` et `provider not found`.
- Le meme `conf.json` porte `sync` (`enabled`, `provider`, `cloudName`, `s3`, `webdav`) et `repo`
  (retention, cadence de snapshots) : les lire avant de repondre a une question de synchronisation — un
  ecran de reglages peut afficher un fournisseur qui est en fait desactive (`sync.enabled: false`).

## Choix du modele par usage

| Usage | Cible conseillee | Pourquoi |
|---|---|---|
| Edition de texte (latence) | un combo determineste dont **tous** les membres sont autorises | la rotation ne peut pas le sortir de la liste |
| Agent (tool calling) | l'alias `auto/best-reasoning`, **si** ses cibles concretes sont autorisees | sans allowlist complete, `503` par vagues |
| Repli | declarer le meme modele dans `allowedModels` que dans le `fallback_model` de l'app | un repli hors liste echoue en `403` |
