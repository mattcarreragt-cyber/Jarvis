# 05 — Catalogue des agents

7 agents prévus. **On ne les construit pas tous d'un coup** : la tranche
verticale de référence est l'**Agent System** (périmètre clair, peu de
dépendances, testable). Les autres suivent une fois l'architecture prouvée.

> Note : « Xenum » et « Marketing » du bootstrap d'origine ne sont **pas deux
> agents** mais une seule thématique → fusionnés dans l'**Agent Marketing**.

| Agent          | Domaine        | Side-effects max | Dépendances        | Priorité |
|----------------|----------------|------------------|--------------------|----------|
| **System**     | Machine locale | read (write opt) | OS, psutil         | **1**    |
| Unraid         | NAS/conteneurs | write (confirmé) | API Unraid         | 2        |
| Recherche      | RAG / web      | read             | Qdrant, web        | 3        |
| Dev            | Code / scripts | write (sandbox)  | conteneur isolé    | 4        |
| Home Assistant | Domotique      | write (confirmé) | API HA             | 5        |
| Image          | Génération img | write (fichiers) | ComfyUI            | 6        |
| Marketing      | Contenu Xenum  | read + génération| Qdrant, LLM, Image | 7        |

## Agent Marketing (assistant IA marketing Xenum) — spec

Assistant de création de contenu marketing pour **Xenum**. L'utilisateur est
créateur de contenu (textes de publications, images de pub, réflexions/stratégie).

Capacités :

- **RAG sur documents marketing existants** : fiches produit, brand guidelines,
  contenus passés sont ingérés dans Qdrant (collection dédiée `marketing`) et
  servent de contexte/source de vérité. C'est le différenciateur clé.
- **Génération de textes** : posts, captions, accroches, déclinaisons par canal,
  toujours ancrés sur les docs ingérés (ton, produit, positionnement).
- **Génération d'images de pub** : délègue à l'**Agent Image** (ComfyUI) — ne
  réimplémente pas la génération, l'appelle comme outil.
- **Réflexion / brainstorming** : angles, idées de campagne, analyse.

Outils : `marketing.ingest_doc` (read fichier → embeddings), `marketing.search_docs`
(RAG), `marketing.draft` (génération texte), délégation `image.generate`.

`side_effects` : `read` (docs) + génération de fichiers (drafts/images). Aucune
publication automatique — l'utilisateur valide et publie lui-même (pas de
`net:out` vers les réseaux sociaux en v1).

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
