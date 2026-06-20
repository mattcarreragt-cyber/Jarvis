# 05 — Catalogue des agents

8 agents prévus. **On ne les construit pas tous d'un coup** : la tranche
verticale de référence est l'**Agent System** (périmètre clair, peu de
dépendances, testable). Les autres suivent une fois l'architecture prouvée.

| Agent          | Domaine        | Side-effects max | Dépendances        | Priorité |
|----------------|----------------|------------------|--------------------|----------|
| **System**     | Machine locale | read (write opt) | OS, psutil         | **1**    |
| Unraid         | NAS/conteneurs | write (confirmé) | API Unraid         | 2        |
| Recherche      | RAG / web      | read             | Qdrant, web        | 3        |
| Dev            | Code / scripts | write (sandbox)  | conteneur isolé    | 4        |
| Home Assistant | Domotique      | write (confirmé) | API HA             | 5        |
| Image          | Génération img | write (fichiers) | ComfyUI            | 6        |
| Marketing      | Contenu        | read             | LLM, Recherche     | 7        |
| Xenum          | (à définir)    | ?                | ?                  | 8        |

> ⚠️ **Xenum** et **Marketing** ont un périmètre flou dans le bootstrap d'origine.
> À définir précisément avant implémentation — sinon risque de demi-agents.

## Agent System (tranche de référence) — spec détaillée

`AgentSpec.name = "system"`

Outils (tous `side_effects` ≤ `read` pour la v1) :

| Outil                  | Description                        | Side-effect |
|------------------------|------------------------------------|-------------|
| `system.cpu_usage`     | Charge CPU instantanée + par cœur  | none        |
| `system.memory_usage`  | RAM utilisée/dispo                 | none        |
| `system.disk_usage`    | Espace disque par montage          | read        |
| `system.uptime`        | Uptime + load average              | none        |
| `system.top_processes` | Top N processus par CPU/RAM        | read        |

Critère d'acceptation : « Quel est l'état de la machine ? » → le Router route
vers `system`, l'agent appelle les outils pertinents et renvoie un résumé
markdown lisible, le tout tracé en base.

Les outils `write` (kill process, etc.) sont **hors v1** et exigeront
`needs_confirmation`.
