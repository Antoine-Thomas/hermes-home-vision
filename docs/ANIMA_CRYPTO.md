# ANIMA 0.2 — Spécification du module Crypto (document de conception)

> Statut : **spécification uniquement**. Aucune implémentation, aucune clé,
> aucun accès réseau blockchain. Ce document fixe la cible pour un futur module.

## 1. Objectif

Ajouter à ANIMA une capacité de veille on-chain : collecter des événements
blockchain (transactions, événements de contrats, prix/volumes) et les
transformer en alertes et en connaissances indexées, sans jamais exposer de clé
privée à l'agent Hermes.

## 2. Architecture cible

```
┌─────────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
│ Collecte    │ → │ Normalisation│ → │ Stockage    │ → │ Indexation   │
│ on-chain    │   │ + filtrage   │   │ base dédiée │   │ + alertes    │
│ (RPC/API)   │   │ (événements) │   │ (crypto.db) │   │ (seuils)     │
└─────────────┘   └──────────────┘   └─────────────┘   └──────────────┘
```

- **Collecte** : poll RPC / API REST / WebSocket, en lecture seule (aucune
  transaction signée, aucune écriture).
- **Normalisation** : schéma unique (chaîne, bloc, tx, adresse, méthode,
  valeur, horodatage), filtrage par contrats/adresses d'intérêt.
- **Stockage** : base dédiée `crypto.db` (SQLite), distincte de `state.db`.
- **Indexation** : agrégats par période (volumes, fréquences) + index de
  recherche pour la couche mémoire (niveau 3 RAG).
- **Alertes** : seuils sur les agrégats → canal existant (anti-spam Telegram
  de la supervision).

## 3. Points d'entrée

- **RPC publics** : nœuds RPC (HTTP/WebSocket) pour lire blocs, transactions,
  logs. Aucune clé requise en lecture.
- **APIs d'indexeurs** : APIs REST tierces (équivalents Etherscan/équivalents
  d'indexeurs) pour les requêtes historiques et les prix.
- **Testnets** : un testnet est le point d'entrée de développement (Sepolia ou
  équivalent selon la chaîne cible), avant tout réseau principal.

## 4. Sécurité (contraintes dures)

- **Clés hors de portée de l'agent** : l'agent Hermes ne détient AUCUNE clé
  privée. Une clé API d'indexeur (lecture seule) est le seul secret autorisé,
  stocké dans `.env` (jamais affiché, jamais journalisé).
- **Lecture seule** : le module ne signe, n'envoie et ne diffuse aucune
  transaction. Toute écriture est hors périmètre.
- **ACL** : le module n'est accessible qu'en local (127.0.0.1), comme le RAG et
  SiYuan ; aucun port exposé hors machine.
- **Rotation** : une clé API d'indexeur compromise est révocable et rotative en
  un point unique (le `.env`), sans redéploiement du module.

## 5. Intégration dans ANIMA

- **Nouveau composant supervisé** `crypto` : sonde de santé (dernier bloc vu,
  retard de collecte, taille de la base), seuils dans `SEUILS`.
- **Nouveau job cron** : collecte périodique (cadence à définir), dédié au
  profil `veille` ou à un profil dédié.
- **Base dédiée** `crypto.db` : jamais mélangée à `state.db`.
- **Couche mémoire** : les agrégats et alertes alimentent le RAG (niveau 3)
  pour que le bot puisse répondre sur l'état on-chain.

## 6. Plan par étapes

1. **Analyse** : choisir la chaîne cible et l'indexeur, définir le schéma
   d'événements, les seuils d'alerte (validation utilisateur).
2. **Prototype** : collecte lecture seule sur testnet, stockage `crypto.db`,
   sonde de santé, sans intégration RAG.
3. **Tests** : jeux de données testnet, alertes simulées, test de rotation de
   clé, non-régression de la supervision existante.
4. **Mise en production** (après GO) : bascule vers le réseau principal,
   activation du job cron, indexation RAG, alertes réelles.

## 7. Hors périmètre (explicitement)

Signature de transactions, détention de fonds, envoi d'ordres, bridge, et tout
accès en écriture à une chaîne. Le module est un observateur, pas un acteur.
