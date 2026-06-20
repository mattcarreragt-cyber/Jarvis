# 00 — Principes & règles du projet

Version : 2.0 (remplace `01_PROJECT_RULES.md` v1.0)

## Stack technique

| Couche            | Techno                          |
|-------------------|---------------------------------|
| Frontend          | Next.js                         |
| API / Backend     | FastAPI (Python)                |
| Base relationnelle| PostgreSQL                      |
| Cache / file      | Redis                           |
| Vecteurs / mémoire| Qdrant                          |
| LLM local         | Ollama                          |
| TTS               | Piper                           |
| STT               | Faster-Whisper                  |
| Génération image  | ComfyUI                         |

## Règles absolues (reformulées)

La règle v1.0 « Ne jamais casser l'existant » était ambiguë : le repo est vide,
il n'y a pas d'« existant » logiciel. On la précise :

1. **Ne jamais casser les services en production déjà utilisés au quotidien** :
   Unraid (NAS, conteneurs critiques) et Home Assistant. Tout agent qui les
   touche passe par un mode **lecture seule par défaut**, écriture sur action
   explicite et confirmée.
2. **Local-first** : aucune fonctionnalité cœur ne doit dépendre d'un service
   cloud externe pour fonctionner. Le cloud reste optionnel et opt-in.
3. **Contrats avant code** : aucun agent/outil n'est implémenté avant que son
   interface (`docs/02_CONTRACTS.md`) ne soit définie.
4. **Tranches verticales** : on livre un agent fonctionnel de bout en bout
   avant d'en élargir le nombre. Pas de couches à moitié.
5. **Sécurité par défaut** : tout agent a des permissions explicites et
   minimales (voir `docs/06_SECURITY.md`).

## Définition de « fini »

Une étape n'est « finie » que si : code + test automatisé + doc à jour +
critère d'acceptation de `docs/07_BUILD_ORDER.md` vérifié.
