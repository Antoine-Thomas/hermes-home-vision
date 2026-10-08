# Rappel « certificat-api-wazuh » — echeance et renouvellement

Point a re-verifier a CHAQUE audit de la stack Wazuh. Le certificat de l'API est auto-signe et vit dans le
VOLUME `single-node_wazuh_api_configuration` (`/var/ossec/api/configuration/ssl/`), pas dans un bind-mount
hote : la copie du dossier compose ne le contient pas.

## Mesure de reference — 2026-10-08 (wazuh-docker 4.7.3 single-node)

| Champ | Valeur |
|---|---|
| Fichier | `/var/ossec/api/configuration/ssl/server.crt` (+ `server.key`, 0400 root) |
| Auto-signe | oui — `subject == issuer` |
| Subject / Issuer | `C=US, ST=California, L=San Francisco, O=Wazuh, CN=wazuh.com` |
| SAN | `DNS:localhost` (seul) |
| Validite | 2026-07-19 03:21:04 UTC -> **2027-07-19 03:21:04 UTC** (365 j) |
| Cle / signature | RSA 2048 / sha256WithRSAEncryption |
| Empreinte X509 SHA256 | `E9:6D:A7:FB:03:85:7C:B5:C3:8E:8D:08:BF:37:84:B3:9A:6C:97:AC:20:B5:D1:F3:8B:C2:07:10:6A:CB:CF:35` |
| Serial | `5187C061A08FCED0A16F32423327C856EBF36925` |
| Chaine | simple (1 certificat, 0 intermediaire) ; TLS negocie : TLSv1.2 |
| Exposition | API publiee sur `127.0.0.1:55085` -> **loopback uniquement** (risque contenu) |

**Echeance : renouveler le certificat API Wazuh avant le 2027-06-19** (30 jours avant l'expiration).
La date ci-dessus est une MESURE : la re-mesurer a chaque audit, jamais la recopier de memoire.

## Sondes (lecture seule)

```bash
M=single-node-wazuh.manager-1
docker exec $M openssl x509 -in /var/ossec/api/configuration/ssl/server.crt -noout \
  -subject -issuer -dates -serial -fingerprint -sha256 -ext subjectAltName
echo | openssl s_client -connect 127.0.0.1:55085 -servername localhost -showcerts 2>&1 | grep -c 'BEGIN CERTIFICATE'
docker exec $M sh -c 'M1=$(openssl x509 -in .../server.crt -noout -modulus|openssl sha256); \
  M2=$(openssl rsa -in .../server.key -noout -modulus 2>/dev/null|openssl sha256); [ "$M1" = "$M2" ] && echo paire OK'
```

Pieges de mesure :

- Le `curl` de cet hote est bati sur **Schannel** (`curl -V` -> `libcurl/8.18.0 ... Schannel`) : `curl -vk`
  **n'affiche pas** les lignes `subject:` / `issuer:` / `SSL certificate`. Analyser la chaine avec
  `openssl s_client` (`/usr/bin/openssl`, present sur l'hote ET dans le conteneur manager) avant de
  conclure a un echec de mesure.
- Deux empreintes differentes, a ne pas confondre : le **sha256 du FICHIER** (`sha256sum`) et
  l'**empreinte X509 du certificat** (`openssl x509 -fingerprint -sha256`). C'est la seconde qui se compare
  de bout en bout (fichier servi == certificat presente par le serveur == copie archivee).
- Un certificat auto-signe avec `SAN: DNS:localhost` impose `-servername localhost` (ou un `-k`) cote
  client : un echec de verification n'est pas une panne de l'API.

## Renouvellement (procedure officielle — operation TLS, a ne pas lancer sans fenetre de rollback)

Documentation Wazuh 4.7, « Configuration > SSL certificate » : le certificat est genere par l'API
elle-meme au premier demarrage, et se regenere par

```bash
docker exec -it single-node-wazuh.manager-1 sh -c \
 'cd /var/ossec/api/configuration/ssl && \
  openssl req -newkey rsa:2048 -new -nodes -x509 -days 365 -keyout server.key -out server.crt'
```

puis application par recreation du service (`docker compose up -d --force-recreate wazuh.manager` —
`up -d` seul est un no-op). Controles apres coup : API `200` avec le compte `wazuh-wui`, dashboard `302`,
filebeat `talk to server... OK`, et verification que l'empreinte presente correspond au nouveau fichier.
