# Moniteur à état : schéma, harnais de test, vérification d'un run planifié

Approfondissement des règles de la SKILL.md pour un moniteur maison (cas de référence :
`data/route_ia_fix/health_architecture.py`, tâche « Hermes - Health Architecture » toutes les
15 min, état `health_state.json`, rapport `health.json` — ports, tâches planifiées, fraîcheur
d'index, verrous, orphelins).

## 1. Schéma d'état qui ne ment pas

```json
{
  "reindex": {"statut": "ok", "last_alert": 1790657843.58, "dernier_retour_ts": 1790678471.01},
  "reindex_depassement": {"actif": false, "detecte_ts": 1790654200, "age_s": 100000,
                          "clos_ts": 1790678471, "clos_par": "index rafraichi (manuel ou planifie)"},
  "verrou:<fichier>.lock": {"statut": "ok", "last_alert": 0}
}
```

- `last_alert` = horodatage du dernier envoi **réussi** ; ne jamais le remettre à 0 sur un retour à la
  normale, ajouter `dernier_retour_ts` à la place.
- L'entrée de franchissement (`*_depassement`) reste écrite même quand la métrique est revenue au
  vert : c'est elle qui garde la preuve qu'un run planifié a été manqué.
- Une seule entrée par composant réellement observé au run courant ; toute entrée `verrou:` /
  `orphelin:` absente de la liste surveillée est purgée.

Anti-spam type : alerter quand `statut` passe à `anomalie`, ou quand `now - last_alert` dépasse la
fenêtre, et limiter le retour au vert à un seul message. Une entrée figée sur `anomalie` pour un
composant qui n'existe plus ne reçoit jamais son « retour à la normale » : d'où la purge.

## 2. Harnais de test : copie, jamais la production

```python
src = io.open(SRC, encoding="utf-8").read()
copie = src.replace('HERMES = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes")',
                    'HERMES = r"%s"' % TESTDIR)
copie = copie.replace("def _telegram_send(texte):",
                      'def _telegram_send(texte):\n'
                      '    try:\n'
                      '        io.open(os.path.join(ROUTE, "alertes_test.txt"), "a", '
                      'encoding="utf-8").write(texte + "\\n")\n'
                      '    except Exception:\n'
                      '        pass\n'
                      '    return True\n\n\ndef _telegram_send_desactive(texte):', 1)
io.open(SCRIPT, "w", encoding="utf-8").write(copie)
```

Le remplacement renomme le corps d'origine en fonction morte (`_telegram_send_desactive`) plutôt que
de le supprimer : la copie reste comparable à l'original. Lancer ensuite la copie avec le python du
venv, chaque scénario étant rejoué par un sous-processus indépendant.

| # | Scénario | Attendu |
|---|----------|---------|
| T1 | artefact daté au-delà du seuil | anomalie + alerte + entrée de franchissement `actif` |
| T2 | artefact rafraîchi (manuel) | retour au vert, `last_alert` CONSERVÉ, franchissement clos avec `clos_ts` |
| T3 | entrée fantôme pré-remplie, composant absent | entrée purgée, entrée réelle conservée |
| T4 | anti-spam | 1 alerte, 2e run bloqué, 3e après la fenêtre (`last_alert -= fenetre + 1`) |
| T5 | anti-fuite | 0 occurrence du jeton dans l'état, la sortie et le journal d'alertes |
| T6 | production | SHA256 des fichiers réels identiques avant/après la campagne |

Un harnais qui importe les modules réels laisse un `.lock` par notebook touché : après une campagne,
contrôler `data/siyuan/locks/`, sauvegarder puis supprimer les résidus (voir §4).

## 3. Vérifier qu'un run planifié a bien tourné (Windows)

```bash
date "+%Y-%m-%d %H:%M:%S"    # AVANT tout : un run peut être à venir, pas manqué
powershell -NoProfile -Command "\$i=Get-ScheduledTaskInfo -TaskName 'Hermes - Reindex RAG'; \
  Write-Output (\$i.LastRunTime, \$i.LastTaskResult, \$i.NextRunTime)"
tail -3 data/rag/reindex.log ; tail -6 data/rag/logs/indexer.log
```

- `LastRunTime` est mis à jour **aussi par un lancement manuel** : il ne date pas le run planifié. Le
  journal applicatif (une ligne de début horodatée par run) est la source de vérité ; une ligne
  « début d'indexation » sans ligne de résultat = processus mort en cours de route.
- Le chemin du journal se lit dans le script, pas dans l'intuition : le log de la tâche
  (`data/rag/reindex.log`) et celui du moteur (`data/rag/logs/indexer.log`) ne sont pas dans le même
  dossier. Vérifier l'existence avant d'annoncer « log disparu ».
- Un run mort laisse un verrou orphelin, retiré au run suivant (ligne « verrou orphelin retire »).
- Lire `Settings` de la tâche (`WakeToRun`, `StartWhenAvailable`, `MultipleInstances`) et l'heure de
  démarrage de la machine avant d'accuser le planificateur : une machine debout et une tâche `Ready`
  n'expliquent pas un run perdu.

## 4. Verrous résiduels : inertes ou bloquants ?

La détention se teste en ouvrant le fichier en `a+b` puis `msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)` :
un succès signifie verrou LIBRE, un `OSError` qu'il est détenu. Deux conséquences :

- un `.lock` résiduel sans PID lisible (fichier d'un octet, souvent le `\0` écrit par la sonde
  elle-même) est **inerte** — il ne bloque aucune écriture, c'est un résidu à nettoyer, pas une panne ;
- avec `perime = detenu and age > seuil`, un résidu libre n'est jamais signalé comme anomalie.

Nettoyage : sauvegarder les fichiers (dossier scratch horodaté), supprimer, vérifier que le dossier
ne contient plus de `.lock`, puis consigner l'origine habituelle (le harnais de validation).
