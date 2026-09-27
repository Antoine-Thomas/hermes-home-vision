---
name: windows-driver-integrity
description: "Use when auditing Windows drivers or enabling HVCI."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, drivers, hvci, deviceguard, pnputil]
    category: devops
---

# Windows Driver Integrity (HVCI / magasin de pilotes)

Auditer le magasin de pilotes Windows, statuer sur la compatibilite HVCI, et activer l'Integrite de la
memoire sans casser un peripherique.

## When to use

- Activer HVCI / « Isolation du noyau » / « Integrite de la memoire », ou comprendre ce qui la bloque.
- Inventorier les pilotes d'un poste : quels paquets non-Microsoft, lesquels sont `Legacy`.
- Savoir si un paquet de pilotes est encore utilise AVANT de le retirer.
- Identifier un peripherique qui n'est plus branche (USB, manette, adaptateur) a partir de son seul
  historique d'installation.
- Ne pas utiliser pour installer/tuner un GPU ou WSL2 (`windows-ops`), ni pour l'audit d'espace disque
  (`disk-space-reclamation`).

## Regle 1 — lire l'etat par le BON namespace WMI

`Win32_DeviceGuard` vit dans `root\Microsoft\Windows\DeviceGuard`, **jamais** dans `root\cimv2`. Dans le
namespace par defaut la classe repond **toutes proprietes vides sans lever d'erreur** : le resultat
ressemble a « rien n'est configure » alors que la donnee existe. Un `0` obtenu au mauvais namespace
n'est pas une mesure.

```powershell
Get-CimInstance -Namespace 'root\Microsoft\Windows\DeviceGuard' -ClassName Win32_DeviceGuard
```

Lecture : `VirtualizationBasedSecurityStatus` (2 = VBS en cours), `SecurityServicesConfigured` /
`SecurityServicesRunning` (2 = HVCI, 1 = Credential Guard). Registre :
`HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity\Enabled`
et `...\Control\CI\Config\VulnerableDriverBlocklistEnable`.

**HVCI depend de VBS.** Sur un poste ou VBS ne tourne que grace a l'hyperviseur Hyper-V (Docker/WSL2),
couper Hyper-V eteint HVCI quel que soit `Enabled`. Le verifier (`Win32_ComputerSystem.HypervisorPresent`)
et le dire a l'utilisateur : c'est une dependance, pas une option.

## Regle 2 — les candidats HVCI se filtrent sur `Attributs: Legacy`

`pnputil /enum-drivers` rend un bloc par paquet. `Attributs: Universal` ne bloque pas HVCI ;
`Attributs: Legacy` designe les paquets non declaratifs — c'est la liste a examiner. Lancer `pnputil`
**via PowerShell** : en bash MSYS ses options `/enum-drivers` sont exposees a la traduction de chemin.

`Legacy` n'est **pas** une preuve d'incompatibilite : les paquets Microsoft d'infrastructure (cdrom,
prnms00x) le portent aussi. Ordre de suspicion a annoncer : tiers anciens d'abord, puis MediaTek/Intel,
puis Microsoft d'infrastructure. Ne pas presenter les huit paquets comme « incompatibles » — presenter
la liste et l'ordre, et dire ce qui n'est pas etabli.

## Regle 3 — ne retirer un paquet qu'apres avoir prouve qu'il est fantome

Quatre verifications **concordantes** (aucune ne suffit seule) :

1. `Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.InfName -eq 'oemNN.inf' }` rend **vide** ;
2. cle de service `HKLM\SYSTEM\CurrentControlSet\Services\<nom du pilote>` **absente** ;
3. aucun peripherique de la classe declaree, **fantomes compris** (`Get-PnpDevice -PresentOnly:$false`) ;
4. arborescence `C:\Windows\System32\DriverStore\FileRepository\<pkg>.inf_*` inspectee.

Exporter AVANT de supprimer (`pnputil /export-driver oemNN.inf <dossier>`), et prouver l'export en le
comparant a une copie anterieure (`diff -r` + egalite des tailles fichier par fichier). `/force` est
**ignore** avec `/uninstall` : ne pas compter dessus.

## Regle 4 — identifier le materiel par l'historique, jamais par une table de PID

Un peripherique debranche ne laisse aucune entree Enum. Deux sources :
`HKLM\SYSTEM\CurrentControlSet\Enum\USB` (cles `VID_xxxx&PID_yyyy`) et `C:\Windows\INF\setupapi.dev*.log`,
ou la ligne `inf: {Configure Driver: <nom convivial>}` **nomme l'appareil**.

Beaucoup de PID Microsoft appartiennent a des webcams ou des claviers : ne nommer un peripherique
qu'avec sa description, jamais depuis une table de PID meme fournie par l'utilisateur. Et une trace du
paquet dans `setupapi` peut venir d'un simple `pnputil /export-driver *` (section
`[Copy Driver Package]`, champ `cmd:`) — ce n'est **pas** une preuve d'installation sur un appareil.

## Regle 5 — activer HVCI : ecrire proprement, verifier deux fois, ne pas redemarrer

```bash
reg add "HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity" \
  /v Enabled /t REG_DWORD /d 1 /f
```

Ecrire via **PowerShell** (options `/v /t /d /f` exposees a la traduction MSYS) et verifier par **deux
lectures independantes** : `reg query` puis `Get-ItemProperty`.

**Signal avant redemarrage** : `SecurityServicesConfigured` passe de `0` a **`2`** (avec
`SecurityServicesRunning` encore vide) = configure et accepte, en attente du reboot. Un refus de
Windows se verrait ici — c'est la preuve a donner avant de redemarrer.

Quand l'utilisateur annonce qu'il redemarrera lui-meme : livrer la commande passee + la valeur relue, et
**s'arreter** (ne jamais redemarrer a sa place). Et ne pas chercher la liste des pilotes incompatibles
dans le registre : elle est calculee a la volee par l'app Securite Windows, il faut la faire copier par
l'utilisateur.

## Regle 6 — repondre a « est-ce que je perds X ? »

La question n'est pas « ce paquet est-il compatible ? » mais « une dependance reelle existe-t-elle ? ».
Avant de recommander l'activation : nommer l'appareil par l'historique (Regle 4), puis **verifier si
Windows fournit deja un pilote inbox moderne pour cette famille de materiel** — s'il existe, le paquet
ancien n'est pas necessaire et l'activation ne coute rien. Ne conclure a la compatibilite que sur le
pilote reellement charge : un pilote inbox signe et versionne avec Windows est compatible HVCI, un
paquet de 2009 marque `Legacy` ne l'est pas.

## Rapport attendu

Etat **AVANT / APRES** pour chaque composant, la reponse directe a la question posee (oui/non), et une
section anomalies — y compris les ecarts entre ce que l'utilisateur annoncait et ce qui a ete mesure.
Dire ce qui n'a pas pu etre etabli plutot que de proposer une cause plausible.

## References

- `references/hvci-driver-store.md` — commandes detaillees : inventaire et parsing du magasin,
  preuves de paquet fantome, lecture de `setupapi.dev*.log`, controle avant/apres redemarrage.
