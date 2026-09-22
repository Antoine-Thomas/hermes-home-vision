# Commandes du bot de surveillance — @Omaths2_watch_bot (« Bot video »)

Document de référence. Établi le 17/09/2026 après diagnostic.
Racine : `C:\Users\searc\AppData\Local\hermes\`

---

## 1. Ce que sont réellement ces commandes

Les fonctions « vidéo + son + alerte bruit » **ne sont pas des skills Hermes** et
**ne sont pas des commandes du profil `watch`**. Ce sont deux programmes Windows
autonomes rangés dans `data\surveillance\` :

| Composant | Rôle | Écoute Telegram ? |
|---|---|---|
| `surveillance.ps1` | Bot PowerShell : commandes vidéo/photo + surveillance continue | **OUI** — c'est le poller du bot |
| `stealth.ps1` | Outil appelé par le bot : mute/démute le son, éteint/rallume l'écran | non |
| `audio_guardian\guardian.py` | Détection de bruit YAMNet → envoi vidéo automatique | **NON** — émetteur seul (n'appelle jamais `getUpdates`) |

Le profil Hermes `watch` est un profil **agent** distinct (skills, cron, mémoire).
Il n'implémente aucune de ces fonctions.

---

## 2. Commandes à envoyer au bot @Omaths2_watch_bot

Source de vérité : `data\surveillance\surveillance.ps1` (`$COMMAND_INDEX`, lignes 64-72).

| Commande | Effet | Exemple |
|---|---|---|
| `/com` | Affiche la liste des commandes | `/com` |
| `/help` | Alias de `/com` | `/help` |
| `/start` | Alias de `/com` | `/start` |
| `/watch` | Démarre la surveillance : coupe le son système, éteint l'écran, bloque la veille, puis envoie **1 image toutes les 3 s** + **1 extrait audio de 15 s toutes les 60 s** | `/watch` |
| `/stopcam` | Arrête la surveillance, rétablit son + écran + veille | `/stopcam` |
| `/video [s]` | Enregistre une vidéo webcam + micro (h264/aac) et l'envoie. Défaut **15 s**, plafond **60 s** | `/video` ou `/video 30` |
| `/photo` | Photo unique (webcam) et envoi immédiat | `/photo` |
| `/status` | État : surveillance active ou au repos | `/status` |

Réglages codés en dur dans `surveillance.ps1` (bloc CONFIG, lignes 22-35) :

| Variable | Valeur | Signification |
|---|---|---|
| `$CAMERA` | `Microsoft LifeCam VX-800` | Périphérique vidéo |
| `$MIC` | `Microphone (2- Microsoft LifeCam VX-800)` | Périphérique audio |
| `$INTERVAL` | `3` s | Intervalle entre deux images en mode `/watch` |
| `$QUALITY` | `8` | Qualité JPEG (échelle ffmpeg `-q:v`) |
| `$AUDIO_ENABLED` | `$true` | Extraits audio activés en mode `/watch` |
| `$AUDIO_INTERVAL` | `60` s | Intervalle entre deux extraits audio |
| `$AUDIO_DURATION` | `15` s | Durée d'un extrait audio |
| `$VIDEO_DEFAULT` / `$VIDEO_MAX` | `15` / `60` s | Bornes de `/video` |
| `$CHAT_ID` | `8956868107` | Destinataire (ton compte) |

---

## 3. Alerte bruit — le gardien audio (autonome, sans commande)

`audio_guardian\guardian.py` écoute le micro en continu et déclenche **tout seul**
l'envoi d'une vidéo quand un son d'effraction est reconnu par YAMNet.

**Aucune commande Telegram ne le contrôle.** Il n'y a pas de `/bruit on|off`.

| Réglage | Valeur actuelle | Où |
|---|---|---|
| `THRESHOLD` | **0.8** | `guardian.py` ligne 36 |
| `COOLDOWN_SECONDS` | **60** s | ligne 37 |
| `VIDEO_DURATION` | **15** s | ligne 38 |
| `TARGET_KEYWORDS` | glass, shatter, break, smash, door, slam, bang, knock, crash, impact | ligne 41 |
| `CHAT_ID` | `8956868107` | ligne 29 |

> Le `README.md` du dossier audio_guardian annonce encore `THRESHOLD = 0.5` et
> 9 classes. Le **code** fait foi : seuil **0,8** (relevé volontairement pour
> éliminer les faux positifs du ventilateur GPU, ~0,6).

Preuves de fonctionnement (journal réel, `audio_guardian\guardian.log`) :

```
[2026-09-17 13:01:25] 🚨 DÉTECTION: 'Glass' (score=0.83) → déclenchement vidéo
[2026-09-17 13:01:48] sendVideo -> ok=True
[2026-09-17 16:31:43] 🚨 DÉTECTION: 'Knock' (score=0.95) → déclenchement vidéo
[2026-09-17 16:32:03] sendVideo -> ok=True
```

Seuil conseillé si tu veux plus sensible : `0.6` (compromis), `0.5` (bavard).
Au-dessus de `0.8` : très peu de faux positifs, mais rate les sons faibles.

---

## 4. Logs

| Fichier | Contenu |
|---|---|
| `data\surveillance\audio_guardian\guardian.log` | Journaux de détection bruit + `sendVideo -> ok=` |
| `data\surveillance\audio_guardian\out.log` | Démarrage du gardien (micro, classes chargées) |
| `data\surveillance\audio_guardian\err.log` | Avertissements TensorFlow (bénins) |
| `profiles\watch\logs\gateway.log` | Gateway **du profil Hermes `watch`** — sans rapport avec la surveillance |
| `data\surveillance\frame.jpg` | Dernière image capturée |
| `data\surveillance\video_*.mp4`, `alarm_*.mp4` | Dernières vidéos produites |

`surveillance.ps1` **n'écrit aucun journal** : il est lancé en fenêtre masquée et
tout ce qu'il envoie part sur Telegram.

---

## 5. Démarrer / arrêter

### Le bot de commandes (`surveillance.ps1`)

Démarrage (fenêtre masquée) :

```powershell
Start-Process pwsh -ArgumentList @('-NoProfile','-WindowStyle','Hidden','-File',
  'C:\Users\searc\AppData\Local\hermes\data\surveillance\surveillance.ps1') -WindowStyle Hidden
```

Arrêter :

```powershell
Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" |
  Where-Object { $_.CommandLine -like '*surveillance.ps1*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Tâche planifiée : `SurveillanceBot` (déclencheur **à l'ouverture de session**).

### Arrêter une surveillance en cours (sans tuer le bot)

Envoyer `/stopcam` au bot depuis Telegram. C'est la seule méthode propre : elle
rétablit le son, rallume l'écran et lève le blocage de veille.
Si le bot est mort pendant une surveillance, lancer :

```powershell
pwsh -NoProfile -File C:\Users\searc\AppData\Local\hermes\data\surveillance\stealth.ps1 -Unmute -ScreenOn
```

### Le gardien audio (`guardian.py`)

Il est relancé automatiquement par la tâche `AudioGuardian-Watchdog` (toutes les
5 min, via `guardian-watchdog.vbs`) tant qu'aucun processus `guardian.py` ne tourne.
Pour l'arrêter durablement : désactiver la tâche `AudioGuardian-Watchdog` **puis**
tuer les processus.

---

## 6. Limitations (mesurées, pas supposées)

1. **Un seul poller par bot.** Un token Telegram n'a qu'un flux `getUpdates`.
   Si un second programme (un gateway Hermes) poll le même token, il **vole** les
   commandes : le bot ne répond plus à `/watch`, `/video`, etc. C'est la panne
   d'origine de ce document — voir §7.
2. **`getMyCommands` est le diagnostic.** Si le menu Telegram du bot affiche
   `/new`, `/model`, `/debug`… c'est un gateway Hermes qui a pris le token. Le
   bot de surveillance, lui, devrait montrer `/com /watch /stopcam /video /photo /status`.
3. **Micro unique.** `guardian.py` et `/watch` capturent tous les deux le micro :
   ils ne peuvent pas tourner ensemble (verrou `dshow`). Le gardien permanent
   étant actif, `/watch` peut échouer sur l'audio — l'image, elle, passe.
   Choix : gardien seul (alerte bruit), ou `/watch` après arrêt du gardien.
4. **Pas de détection de mouvement.** Il n'existe aucun module motion : `/watch`
   envoie des images à intervalle fixe (3 s). Il n'y a pas de seuil de mouvement
   ni de décibels — la détection de bruit est une **classification de classe
   sonore YAMNet** (score 0..1), pas un niveau en dB.
5. **Un flux vidéo à la fois.** Webcam partagée : une capture simultanée
   (`/photo` + `/video`, ou OBS/NVIDIA Broadcast/Teams ouverts) échoue avec
   « device already in use ».
6. **LED webcam impossible à éteindre** (câblage matériel), même écran éteint.
7. **Le son système est coupé** pendant `/watch` : aucune notification sonore
   ne peut retentir sur la tour.
8. **Pas de journal côté `surveillance.ps1`** — pour auditer, se fier aux
   fichiers reçus sur Telegram et à `guardian.log`.

---

## 7. Panne d'origine — « les commandes ont été perdues »

**Les commandes n'ont jamais été supprimées ni déplacées : les fichiers sont
intacts.** Deux causes cumulées les ont rendues inopérantes :

1. **Hijack du token (cause principale).** La réorganisation du 17/09 a attribué
   le bot `@Omaths2_watch_bot` (id `8967117033`) au profil Hermes `watch` comme
   « son » bot, et a réactivé la tâche `Hermes_Gateway_watch` (watchdog 15 min).
   Ce gateway poll le même token que `surveillance.ps1` et consomme les commandes.
   Preuve : `getMyCommands` sur ce bot renvoie le menu **Hermes**
   (`/new`, `/model`, `/status`, `/debug`, `/commands`…), pas `/watch`.
   *Même incident déjà résolu le 08/09 (profil `watch` désactivé à l'époque).*
2. **Bot arrêté.** Aucun processus `surveillance.ps1` en vie ; la tâche
   `SurveillanceBot` n'a pas relancé depuis le 13/09 16:23 (`LastTaskResult = 3221225786`
   = `0xC000013A`, processus terminé brutalement). Son déclencheur est
   « à l'ouverture de session » : il ne se relance pas en cours de session.

Voir §8 pour la résolution.

---

## 8. Résolution retenue

> À compléter une fois l'arbitrage tranché (voir l'échange du 17/09).

Contrainte structurelle : **un seul des deux peut poller `@Omaths2_watch_bot`.**
Deux voies possibles, exclusives :

- **Voie A — le bot de surveillance est seul poller.** Arrêter le gateway du
  profil `watch` et désactiver la tâche `Hermes_Gateway_watch`. C'est la
  réparation validée le 08/09. `surveillance.ps1` retrouve la main sur
  `/com /watch /stopcam /video /photo /status`. Effet de bord : le profil Hermes
  `watch` perd sa surface Telegram.
- **Voie B — le profil `watch` garde le bot.** Créer un **nouveau** bot via
  @BotFather (`/newbot`) et y pointer `surveillance.ps1` (variable
  `data\surveillance\token.sec`). Les deux coexistent alors sans conflit.
  Effet de bord : une action BotFather de ta part, et l'ancien bot devient
  purement agent.

Dans les deux cas, mettre à jour le menu du bot avec :

```
setMyCommands → /com /watch /stopcam /video /photo /status
```

---

## 9. Ne pas confondre avec l'autre bot

`@Hermes_assistante_2026_bot` (id `8802352038`, gateway du profil `default`) porte
un jeu de commandes **différent**, implémenté par Hermes :

`/com` (index paginé), `/photo` (1 capture), `/record 30|60` (vidéo courte),
`/status`, `/pause` / `/pause off` (ESTOP), `/help`…

Ces commandes-là respectent l'ESTOP, affichent un voyant et écrivent dans
`%LOCALAPPDATA%\hermes\captures\`. Ce sont elles que décrit le skill
`surveillance-control`. **Elles n'existent pas sur `@Omaths2_watch_bot`.**
