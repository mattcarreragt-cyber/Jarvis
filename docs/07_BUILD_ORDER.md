# 07 — Ordre de construction (corrigé)

## Problème de l'ordre d'origine

L'ordre v1 (`Infra → Dashboard → Voice → Memory → Router → Agents …`) plaçait
**Voice et Memory avant le Router**. Or la voix n'a aucune valeur tant qu'il n'y
a pas de router + agent derrière. On corrige pour avancer **verticalement** :
livrer un agent fonctionnel de bout en bout le plus tôt possible.

## Ordre corrigé

| # | Étape                     | Contenu                                                        | Critère de « fini » |
|---|---------------------------|----------------------------------------------------------------|---------------------|
| 1 | **Infra**                 | docker-compose : Postgres, Redis, Qdrant, FastAPI, Ollama      | `GET /api/health` répond OK pour chaque dépendance |
| 2 | **Contrats**              | Implémentation des modèles de `02_CONTRACTS.md`                | Schémas Pydantic + tests de (dé)sérialisation |
| 3 | **Router (squelette)**    | Router à règles + agent « echo » bidon                         | Un message route vers echo et revient |
| 4 | **Agent System** ⭐        | Tranche verticale complète (voir `05_AGENTS.md`)               | « état de la machine ? » → résumé tracé en base |
| 5 | **Mémoire**               | Redis court terme + Qdrant long terme + MemoryContext          | Contexte injecté dans l'agent, rappel sémantique OK |
| 6 | **Dashboard**             | Next.js : chat, historique, santé                              | Conversation fluide bout en bout via l'UI |
| 7 | **Router LLM (fallback)** | Branche le function-calling Ollama (hybride complet)           | Cas ambigu routé correctement, repli si timeout |
| 8 | **Agents métier**         | Unraid, Recherche, Dev (sandbox), HA — un par un               | Chaque agent passe son critère + sécurité |
| 9 | **Voice**                 | Whisper (STT) + Piper (TTS) branchés sur le chat existant      | Aller-retour vocal complet |
| 10| **Images**                | ComfyUI + verrou GPU                                           | Génération d'image avec gestion VRAM |
| 11| **App Generator / OS**    | Couche de génération d'applications, finition « OS »           | À spécifier après retour d'usage |

## Principe transverse

À chaque étape : **code + test + doc + critère vérifié** = fini (cf. `00_PRINCIPLES.md`).
On n'élargit jamais le nombre d'agents tant que la tranche verticale (#4) n'est
pas verte.
