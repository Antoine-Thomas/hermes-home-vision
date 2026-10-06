# RAPPORT <NOM DU CHANTIER> — ETAPE <N>

<une ligne de contexte : date/heure de la fenetre de mesure, nature de l'etape (lecture seule ou non),
methodes utilisees, chemins des artefacts de mesure>

## Inventaire / mesures

| Composant | Role | Port | Processus | Dependances | Etat | Health check | Dernier succes | Dernier echec |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  | READY / DEGRADED / FAILED / BLOCKED |  | <horodatage + source> | <horodatage + source> |

## Contrats / points de decision

<pour chaque paire de composants qui communiquent : entree attendue, sortie produite, format,
erreurs possibles, etat en cas de defaillance — ou la section equivalente a l'etape>

## Verdict

```
RAPPORT <NOM>  ETAPE <N>
READY:     <composants, avec la preuve qui les rend READY>
DEGRADED:  <composants, avec le chiffre qui degrade>
FAILED:    <composants, avec le fait precis (aucun listener, commande disparue)>
BLOCKED:   <composants dont le role n'est pas demontre>
RISQUES:   1. <risque mesure>
           2. <risque mesure>
MODIFICATIONS: 0
```

## Preuve de non-modification

- Horodatage de derniere modification des fichiers sensibles : <fichier = date, motif d'attribution>
- Fichiers CREES par cette etape (les seuls) : <journal de chantier, lots de mesures>
- Etat des elements interdits (taches a ne pas toucher, donnees de production) : <constat>

## Etape suivante proposee (soumise au GO)

- <sous-etape 1> : <ce qui serait fait, sur quoi, avec quel backup>
- <sous-etape 2> : …

STOP. J'attends ton GO pour l'etape <N+1>.
