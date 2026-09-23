# Taches planifiees : verification obligatoire (lecon volet 6)

## La regle

**Une tache planifiee creee par un script doit etre verifiee apres coup, avec une preuve
verifiable — pas un « j'ai lance la commande ».** Deux verifications sont necessaires, et elles
sont differentes :

1. **La tache existe et va se declencher** : `Get-ScheduledTask -TaskName "<nom>"` -> `State: Ready`,
   action (chemin + arguments), `Repetition.Interval = PT15M`, `NextRunTime`. Un `schtasks /create`
   reussi ne dit rien de l'etat final (une tache creee puis desactivee repond OK).
2. **Elle execute reellement le script** : `schtasks /run /tn "<nom>"` puis
   `Get-ScheduledTaskInfo` -> `LastTaskResult: 0` **et** une trace cote script (fichier d'etat
   reecrit, mtime qui bouge, ligne de log). Le `LastTaskResult` seul ne prouve pas que le corps du
   script est alle au bout : c'est le fichier d'etat qui le prouve.

```bash
schtasks /create /tn "volet6-watchdog" /tr "\"<python.exe>\" \"<script.py>\"" /sc minute /mo 15 /f
powershell.exe -NoProfile -Command "Get-ScheduledTask -TaskName 'volet6-watchdog' | Format-List State,Actions"
schtasks /run /tn "volet6-watchdog"
sleep 25
powershell.exe -NoProfile -Command "Get-ScheduledTaskInfo -TaskName 'volet6-watchdog' | Format-List LastRunTime,LastTaskResult"
stat -c '%y' "<fichier d'etat du script>"     # mtime doit avoir bouge = le script a tourne
```

`LastTaskResult: 267011` avant tout tick = « la tache n'a jamais tourne » (0x41303), pas un echec.

## Les deux pieges qui ont fait croire a un watchdog absent

**Piege 1 — chercher au mauvais endroit.** Un watchdog Hermes est un **cron job Hermes**
(`helvetica cron/jobs.json`), il n'apparait PAS dans le Planificateur de taches Windows :
`schtasks /query /tn "<nom>"` repond « Le fichier specifie est introuvable » alors que le job
existe et tourne. Verifier par `cronjob action='list'` / lecture de `%LOCALAPPDATA%\hermes\cron\jobs.json`
(cles utiles : `enabled`, `state`, `last_run_at`, `last_status`, `repeat.completed`). Cas reel :
le watchdog du volet 6 existait bien (job `4a646bb6eab4`, `no_agent: true`, `every 15m`) et avait
46 ticks a son actif, avec 8 envois Telegram OK dans `envois_6.log`.

**Piege 2 — un watchdog en pause pendant l'etape la plus longue.** Le meme job a ete mis en
`paused` a 13:10, au moment precis ou l'assemblage final (le plus long, ~1 h) demarrait : plus
personne ne surveillait pendant l'etape critique, et le MP4 est reste tronque sans alerte.
Ne jamais mettre en pause un watchdog avant que **l'artefact final** soit verifie
(`ffprobe` du fichier livre), et ne jamais considerer la fin du calcul GPU comme la fin du run.

## Garde-fou : tester un tick sans declencher l'action lourde

Un watchdog « run termine » relance souvent la derniere etape quand son fichier d'etat ne porte pas
le drapeau de fin (ici `assemble_fait`) : un tick de test declenche alors un encodage d'une heure
qui ecrase le fichier livre. Pour prouver que la tache tourne sans payer ce prix :

1. sauvegarder le fichier d'etat, poser le drapeau de fin (`"assemble_fait": true`) ;
2. `schtasks /run` + verification (`LastTaskResult`, mtime du fichier d'etat) ;
3. **retirer le drapeau** et restaurer le fichier d'etat a l'identique.

Et si la tache ne doit pas partir toute seule (fichier de livraison encore a retravailler) :
la laisser **`/disable`**, le tick manuel `schtasks /run` fonctionnant quand meme, et livrer la
commande d'activation (`schtasks /change /tn "<nom>" /enable`) avec sa consequence exacte.

## Ne pas donner le meme nom a deux mecanismes

`volet6-watchdog` existait a la fois comme cron Hermes (en pause) et, apres ce correctif, comme
tache Windows : le meme nom pour deux planificateurs rend toute verification ambigue.
- Convention : prefixe `hermes ` / suffixe selon le mecanisme (`...-schtask` pour Windows).

## Detacher ce qu'un tick lance (correctif 5, volet 6)

Un tick cron Hermes a un **timeout de 3600 s**. Un watchdog qui termine son travail par une etape
longue (`subprocess.run([... assemble_v6.py ...])`, 15-25 min) voit son tick timeout a chaque
passage, et l'etape peut etre relancee en double au tick suivant.

**Regle : un tick ne lance jamais un travail long en `subprocess.run`, il le detache.**

```python
with open(log, "w", encoding="utf-8") as f:
    subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=VID,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
etat["assemble_lance"] = True   # sinon le tick suivant relance une deuxieme fois
```

- Le tick rend la main immediatement ; le suivi se fait sur l'**artefact final** (existence du
  fichier livre + `ffprobe`), pas sur le code retour du process detache.
- Poser un drapeau dans le fichier d'etat (`assemble_lance`) des le lancement : sans lui, chaque
  tick de 15 min redemarre l'etape lourde.
- Le log du process detache (`assemble_v6.log`) est la seule trace de son echec : le lire avant de
  conclure.
- Verifier : `grep -n Popen scripts/surveiller_v6.py` doit montrer le `DETACHED_PROCESS`, et
  `subprocess.run([sys.executable, ASSEMBLE])` ne doit plus apparaitre.
