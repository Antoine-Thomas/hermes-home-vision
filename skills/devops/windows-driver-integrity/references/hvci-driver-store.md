# Magasin de pilotes et HVCI — commandes detaillees

## Inventaire du magasin

```bash
powershell -NoProfile -Command "& pnputil.exe /enum-drivers" > <fichier>
```

Chaque paquet est un bloc de lignes, blocs separes par une ligne vide. Champs : `Nom publie`
(`oemNN.inf`), `Nom d'origine` (`<pkg>.inf`), `Nom du fournisseur`, `Nom de la classe`, `GUID de la
classe`, `Version du pilote`, `Nom du signataire`, `Attributs` (`Universal` / `Legacy`), `Version WHCP`.

- **La sortie locale est en OEM/cp850.** Un parseur qui cherche un libelle accentue
  (`Nom publiÚ`, `Nom dÆorigine`) rate silencieusement et rend des champs vides : filtrer sur des
  fragments **sans accent** (`publi`, `origine`, `fournisseur`) ou rechercher la ligne contenant
  `Legacy` et remonter de ~10 lignes.
- Compter les paquets (`grep -c -i -E 'oem[0-9]+\.inf'`) avant/apres pour prouver une suppression.

## Preuves qu'un paquet est fantome

```powershell
# 1. aucun peripherique ne l'utilise
Get-CimInstance Win32_PnPSignedDriver | Where-Object { $_.InfName -eq 'oem49.inf' } |
  Select-Object DeviceName,InfName,DriverVersion,DriverProviderName

# 2. pas de cle de service (ex. HKLM:\SYSTEM\CurrentControlSet\Services\xusb21)
# 3. pas de peripherique de la classe, fantomes compris
Get-PnpDevice -PresentOnly:$false | Where-Object { $_.Class -eq 'XnaComposite' }
#    + la classe est-elle declaree ? HKLM:\SYSTEM\CurrentControlSet\Control\Class\{GUID}
```

## Pourquoi un paquet est la : lire setupapi

`C:\Windows\INF\setupapi.dev.log` et les `setupapi.dev.<horodatage>.log` archives. Chercher le nom du
`<pkg>.inf` : sa ligne apparait dans une section `[Copy Driver Package - ...]` avec le champ `cmd:` qui
l'a produite. Exemple de conclusion valide : le paquet n'apparait QUE dans un
`pnputil.exe /export-driver * <dossier>` (sauvegarde de pilotes) → il n'a jamais ete lie a un appareil.

Pour le materiel : compter `VID_xxxx&PID_yyyy` par fichier de log et lire les lignes
`inf: {Configure Driver: <nom>}` / `Device Description` — c'est le nom commercial de l'appareil.

## Export et suppression

```bash
mkdir -p <dossier>
powershell -NoProfile -Command "& pnputil.exe /export-driver oem49.inf 'C:\...\<dossier>'"
powershell -NoProfile -Command "& pnputil.exe /delete-driver oem49.inf /uninstall"
```

- L'export depose les fichiers dans le dossier cible, avec un sous-dossier `x64\` : faire un
  `find <dossier> -type f` avant de conclure a l'echec (le `.sys` n'est pas a la racine).
- `pnputil` repond « Ignorer /force lorsqu'il est utilise avec /uninstall » : `/force` est sans effet ici.
- Verifier les trois effets : plus de trace dans `/enum-drivers`, compteur -1, dossier
  `DriverStore\FileRepository\<pkg>.inf_*` disparu.

## Etat HVCI : lecture et ecriture

```powershell
Get-CimInstance -Namespace 'root\Microsoft\Windows\DeviceGuard' -ClassName Win32_DeviceGuard |
  Select-Object SecurityServicesConfigured,SecurityServicesRunning,VirtualizationBasedSecurityStatus
reg add 'HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity' /v Enabled /t REG_DWORD /d 1 /f
reg query 'HKLM\SYSTEM\CurrentControlSet\Control\DeviceGuard\Scenarios\HypervisorEnforcedCodeIntegrity' /v Enabled
```

| Valeur | Signification |
|---|---|
| `SecurityServicesRunning` contient 2 | HVCI actif |
| `SecurityServicesConfigured` = 2, `Running` vide | configure, **reboot requis** (etat attendu juste apres l'ecriture) |
| `VirtualizationBasedSecurityStatus` = 2 | VBS en cours (prerequis satisfait) |

Indicateurs de redemarrage a verifier si l'on se demande si autre chose attend un reboot :
`WindowsUpdate\Auto Update\RebootRequired` et `Component Based Servicing\RebootPending`.
`PendingFileRenameOperations` non vide n'est **pas** un indicateur exploitable (bruit habituel).

## Si HVCI ne demarre pas apres redemarrage

1. Re-verifier les trois champs ci-dessus : un `Running` vide apres reboot = un pilote incompatible a
   ete retenu au boot.
2. La liste des pilotes incompatibles est affichee par l'app **Securite Windows** (Isolation du noyau).
   Elle est calculee a la volee : **il n'existe pas de liste enregistree** a lire depuis un terminal,
   ni dans `HKLM\SYSTEM\CurrentControlSet\Control\CI\*`, ni dans le journal DeviceGuard. Demander a
   l'utilisateur de copier la liste (nom + version), puis traiter paquet par paquet dans l'ordre de
   suspicion (tiers anciens d'abord).
3. Pour chaque candidat : soit il est fantome → le retirer (voir plus haut), soit il est utilise par un
   peripherique → choisir entre le remplacer, le mettre a jour, ou renoncer a HVCI. Annoncer le choix,
   ne pas decider seul quand un materiel en service est en jeu.
