# 06 — Sécurité & permissions

Un OS qui pilote Unraid + Home Assistant + génère du code a une surface
d'attaque réelle. La sécurité est cadrée dès la spec.

## Authentification

- Service mono-utilisateur au départ, mais **jamais ouvert sans auth**.
- API protégée par token (JWT ou clé d'API en header), même sur le LAN.
- Le dashboard s'authentifie ; les routes (sauf `/api/health`) exigent un token valide.

## Modèle de permissions

- Chaque `Tool` déclare `required_permissions`.
- Chaque `AgentSpec` a des `default_permissions` minimales.
- Le Router n'accorde à un `AgentRequest` que les permissions nécessaires
  (principe du moindre privilège).

Permissions de base (exemples) : `system:read`, `system:write`,
`unraid:read`, `unraid:write`, `ha:read`, `ha:write`, `dev:exec`, `net:out`.

## Actions sensibles → confirmation obligatoire

Tout outil `side_effects == "write"` ciblant un système en production renvoie
`needs_confirmation` (voir `02_CONTRACTS.md`). L'exécution réelle n'a lieu
qu'après `POST /api/chat/confirm`. Cela matérialise la règle « ne jamais casser
l'existant ».

**Exception — Home Assistant** (choix utilisateur) : les commandes domotiques
s'exécutent directement, sans confirmation, pour rester utilisables à la voix.
Garde-fous côté agent : seuls les impératifs déclenchent une action (les
questions « est-il éteint ? » et les participes « allumée » sont ignorés),
et les consignes de température sont bornées à 5-35 °C.

## Sandboxing de l'Agent Dev

L'agent Dev (qui exécute du code/scripts) tourne dans un **conteneur isolé**,
sans accès réseau par défaut, montage en lecture seule sauf répertoire de
travail dédié, et limites CPU/mémoire. Aucune exécution sur l'hôte.

## Réseau sortant

`net:out` est une permission explicite. Les agents local-first (System) ne
l'ont pas. Seuls Recherche (web) et opt-ins l'obtiennent.

## Secrets

- Aucun secret en dur dans le repo. Variables d'environnement / fichier `.env`
  non commité (+ `.env.example` documenté).
- Tokens d'API (Unraid, HA) stockés côté serveur, jamais exposés au frontend.

## Audit

`routing_logs` + `tool_invocations` (Postgres) donnent une piste d'audit
complète : qui a demandé quoi, quel agent, quels outils, quel résultat.
