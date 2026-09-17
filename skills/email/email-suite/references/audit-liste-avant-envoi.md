# Audit de la liste AVANT d'écrire la campagne

Une campagne ne vaut que ce que vaut sa liste. Faire cet audit **avant** de
rédiger les brouillons : deux fois sur deux, le blocage réel était la liste, pas
le message. Annoncer les chiffres à l'utilisateur avant de produire du contenu.

Ordre d'exécution : 1 → 6. S'arrêter et remonter au user si l'étape 1 ou 2 vide
la liste.

---

## 1. Domaines non délivrables (RFC 2606 / RFC 6761)

Ces TLD et domaines sont **réservés par la norme** et ne peuvent pas recevoir de
courrier. Leur présence signale presque toujours un jeu de test, pas des
contacts réels.

```python
UNDELIVERABLE = ("example.com", "example.org", "example.net", "example.edu",
                 "test", "invalid", "localhost", "domain.com", "email.com")

def non_delivrable(email):
    d = email.rsplit("@", 1)[-1].lower()
    return any(d == x or d.endswith("." + x) for x in UNDELIVERABLE)
```

Cas réel : un dossier de CVs contenait 4 adresses, toutes en `@example.com` —
c'étaient des fixtures générées pour tester un pipeline de recrutement. Le
pipeline d'extraction fonctionnait parfaitement (TXT, PDF, DOCX, PNG via OCR,
noms et secteurs extraits) ; il n'y avait simplement aucun destinataire réel.

**Ne pas filtrer silencieusement.** Écrire les rejets en commentaire dans le
`.txt` de sortie avec le fichier source, pour que l'utilisateur voie la
traçabilité :

```
# --- REJETES (non delivrables, laisses pour tracabilite) ---
# camille.dupont@example.com  # cv_camille_dupont.txt  -> domaine non delivrable
```

## 2. Croisement avec les campagnes précédentes

Avant de déclarer une liste « nouvelle », la croiser avec le `tracking.json` de
chaque campagne passée du même projet (`sent`, `bounced`, `stop`).

```python
deja = set()
for cle in ("sent", "bounced", "stop"):
    for x in tracking.get(cle, []):
        deja.add(x.lower() if isinstance(x, str) else x.get("email", "").lower())
```

Cas réel : les 13 seules adresses exploitables d'un export LinkedIn étaient
**13/13 déjà contactées** trois semaines plus tôt, dans une campagne restée sans
réponse. Sans ce croisement, la « nouvelle » campagne était un doublon intégral.

Le fait de ré-écrire aux mêmes personnes n'est pas interdit — mais c'est une
décision de l'utilisateur, pas un effet de bord. Lui poser la question :
relance assumée (nouvel angle), segmentation, ou exclusion.

## 3. Artefact de concaténation des regex sur du texte libre

`[a-zA-Z0-9._%+-]+@...` appliquée à de la prose colle le mot précédent au local
part quand il n'y a pas d'espace :

```
"...pour les entrepreneursdaniel_antoni@intuit.com"
  -> entrepreneursdaniel_antoni@intuit.com   (faux)
  -> daniel_antoni@intuit.com                (vrai, présent ailleurs)
```

Heuristique de détection : si une adresse plus longue se termine par une adresse
plus courte **du même domaine**, la longue est un artefact.

```python
artefacts = set()
for a in adresses:
    la, da = a.split("@", 1)
    for b in adresses:
        if a != b:
            lb, db = b.split("@", 1)
            if da == db and len(la) > len(lb) and la.endswith(lb):
                artefacts.add(a)
                break
```

Concerne surtout `messages.csv` d'un export LinkedIn, les corps d'emails et les
PDF sans espaces fiables.

## 4. Intention de l'adresse ≠ adresse valide

Une adresse syntaxiquement bonne et jamais contactée peut être hors sujet. Les
adresses extraites de messages entrants sont souvent des **recruteurs** qui ont
écrit pour proposer un poste (`recruitment@`, `developpement@`, contacts RH de
grands groupes). Leur envoyer une offre de prestation est à contre-emploi et
brûle un contact utile autrement.

Signaux à vérifier avant d'inclure : le local part (`recruitment`, `rh`,
`recrutement`), et le contexte d'où l'adresse a été extraite (message entrant
vs. carnet d'adresses).

## 5. Base légale, par segment (France / CNIL)

Ce n'est pas de la théorie : ça change **quel segment est envoyable**.

| Destinataire | Règle | Conséquence |
|---|---|---|
| Adresse **professionnelle**, message lié à l'activité de la structure | Prospection tolérée sans consentement préalable, opt-out obligatoire et visible | Segment B2B envoyable |
| **Particulier** | Consentement préalable requis | Non envoyable sans accord explicite |

Le piège concret : une personne qui a envoyé son **CV** a communiqué son adresse
pour une **candidature**. La réutiliser pour vendre une prestation est un
changement de finalité que la CNIL n'admet pas. Les CVs sont donc une source
légitime pour **recruter**, pas pour **prospecter des particuliers**.

À dire à l'utilisateur, même s'il a déjà écrit « je respecte l'anti-spam » : sa
règle est généralement juste, mais elle ne distingue pas ces deux cas.

## 6. Plafond structurel de l'export LinkedIn

`Connections.csv` ne contient l'email d'une relation que si celle-ci a activé le
partage (`linkedin.com/psettings/privacy/email`). Rendement observé : **13
adresses sur 937 relations (1,4 %)**. C'est écrit en préambule du CSV lui-même.

Ne pas essayer de compenser en pilotant un navigateur sur LinkedIn :

- les coordonnées ne sont visibles que connecté — donc il faudrait les
  identifiants de l'utilisateur, ce qui n'est jamais à faire ;
- automatiser une session connectée est contraire aux CGU (risque de
  restriction du compte de l'utilisateur) ;
- **et ça n'apporterait rien** : les seules adresses accessibles sont
  précisément celles déjà dans l'export.

L'export **est** la réponse complète. Le dire clairement plutôt que de tenter
puis échouer.

Détail de parsing (préambule de 3 lignes, extraction depuis `messages.csv`) :
voir `references/linkedin-export-parsing.md`.

---

## Format de restitution

Après l'audit, donner ces chiffres avant tout brouillon :

```
Retenus ............ N   (dont X particuliers, Y entreprises)
Ecartes :
  domaine non delivrable ...... n1
  deja contactes .............. n2   <- croisement tracking.json
  artefact d'extraction ....... n3
  adresse de l'expediteur ..... n4
  hors cible (recruteurs) ..... n5
```

Si `Retenus` est nul ou négligeable, **le dire immédiatement** et proposer les
sources de remplacement (vrai dossier de CVs, relance de la base existante,
crawl SIRENE pour du B2B — voir `references/sirene-crawl-entreprises.md`).
Produire des brouillons soignés pour une liste vide est du travail perdu.

## Alternative quand la liste est vide

1. Demander le **vrai** dossier de CVs / la vraie source de contacts.
2. Proposer la relance de la base déjà contactée, avec un angle différent et une
   ligne STOP (décision utilisateur, cf. §2).
3. Construire une liste neuve : API SIRENE par code postal + code NAF, puis
   enrichissement email (`references/sirene-crawl-entreprises.md`).
