# JARVIS OS

OS IA personnel **local-first** : tout le calcul (LLM, voix, images, embeddings) tourne
sur ton infra, sans dépendance cloud obligatoire.

## Vue d'ensemble

```
Dashboard (Next.js)
      │  HTTP/WS
      ▼
  FastAPI (API Gateway)
      │
      ▼
   Router  ──►  Agents  ──►  Outils (tools)
      │            │
      ▼            ▼
  Mémoire      LLM / Voix / Images
 (Postgres,    (Ollama, Piper,
  Redis,        Whisper, ComfyUI)
  Qdrant)
```

- **Unraid** = orchestrateur (services, stockage, conteneurs).
- **Kubuntu** = nœud de calcul IA (GPU : Ollama, ComfyUI, Whisper).

## Documentation

La spec vit dans [`docs/`](docs/). Lire dans l'ordre :

1. [`00_PRINCIPLES.md`](docs/00_PRINCIPLES.md) — règles du projet, ce qui est cassable ou non.
2. [`01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) — topologie, déploiement, GPU.
3. [`02_CONTRACTS.md`](docs/02_CONTRACTS.md) — contrats Router / Agent / Outil / API. **Le cœur.**
4. [`03_ROUTER.md`](docs/03_ROUTER.md) — stratégie de routage hybride.
5. [`04_MEMORY.md`](docs/04_MEMORY.md) — modèle de données mémoire.
6. [`05_AGENTS.md`](docs/05_AGENTS.md) — catalogue des agents et périmètres.
7. [`06_SECURITY.md`](docs/06_SECURITY.md) — auth, permissions, sandboxing.
8. [`07_BUILD_ORDER.md`](docs/07_BUILD_ORDER.md) — ordre de construction corrigé + critères de « fini ».
9. [`08_ORCHESTRATION.md`](docs/08_ORCHESTRATION.md) — Capability Registry, Scheduler, sélection de modèle, WoL.

## État

Phase actuelle : **spécification**. Aucun code applicatif n'est encore écrit.
Première tranche verticale planifiée : **Agent System** (voir build order).
