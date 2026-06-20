# 01 — Architecture cible

## Topologie physique

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  UNRAID  (orchestrateur)    │        │  KUBUNTU  (calcul IA, GPU)   │
│                             │        │                              │
│  - FastAPI gateway          │  LAN   │  - Ollama (LLM)              │
│  - Next.js dashboard        │◄──────►│  - ComfyUI (images)          │
│  - PostgreSQL               │  HTTP  │  - Faster-Whisper (STT)      │
│  - Redis                    │        │  - Piper (TTS)               │
│  - Qdrant                   │        │                              │
└─────────────────────────────┘        └──────────────────────────────┘
```

- **Unraid** = chef d'orchestre. Héberge la **webapp** (dashboard Next.js +
  FastAPI), les bases de données, et reste **toujours allumé**. C'est le point
  d'entrée unique : l'utilisateur accède à JARVIS via cette webapp servie par le
  serveur, depuis n'importe quel appareil du réseau.
- **Kubuntu** = nœud de calcul GPU (Ollama, ComfyUI, Whisper, Piper). Peut être
  **éteint** quand inutilisé pour économiser l'énergie.
- Communication : HTTP(S) sur le LAN. Les endpoints GPU (Ollama, ComfyUI, etc.)
  sont configurés par variables d'environnement (`OLLAMA_BASE_URL`, etc.), jamais
  en dur.

## Wake-on-LAN du nœud de calcul

Kubuntu n'a pas besoin de tourner en permanence. Le **Resource Orchestrator**
(voir `08_ORCHESTRATION.md`) gère le réveil avec une règle précise :

**Kubuntu est réveillé si et seulement si la tâche requiert une capacité
`gpu: true` sur la machine `kubuntu`.** Une demande TTS (Piper sur Unraid,
CPU-only) ne réveille pas Kubuntu.

Séquence :
1. L'Orchestrateur résout les capacités requises pour la tâche.
2. Si au moins une capacité est `gpu: true` + `machine: kubuntu`, vérifie la santé.
3. Si injoignable et WoL activé : envoie magic packet → attend le réveil
   (SSE `waking` affiché dans la webapp).
4. Réveil OK → tâche poursuit. Sinon → `503` clair.

Config : `KUBUNTU_WOL_ENABLED`, `KUBUNTU_MAC`, `KUBUNTU_WOL_TIMEOUT`.

## Déploiement

- **Docker Compose** comme cible par défaut (un `compose.yaml` par hôte, ou un
  fichier unique avec profils `unraid` / `kubuntu`).
- Rationale : Unraid gère nativement Docker ; pas besoin de la complexité K8s
  pour un déploiement personnel mono-utilisateur.
- Réversible : si besoin d'échelle plus tard, les conteneurs migrent vers k3s.

## Gestion GPU / VRAM (point critique)

Ollama, ComfyUI et Whisper se disputent le même GPU. Stratégie :

1. **Ollama** garde le modèle de routage/chat chargé (keep-alive).
2. **ComfyUI** et les gros modèles image/STT sont chargés à la demande puis
   déchargés. Un **verrou GPU** (clé Redis `gpu:lock`) sérialise les tâches
   lourdes pour éviter l'OOM VRAM.
3. Le Router refuse/queue une tâche image si une autre tâche GPU lourde tourne
   (retour `202 queued` + position de file).

## Flux d'une requête

```
1. Dashboard envoie {message, session_id} → POST /api/chat
2. FastAPI authentifie, charge le contexte mémoire (Redis court terme + Qdrant long terme)
3. Router classe l'intent → choisit un agent (voir 03_ROUTER.md)
4. Agent exécute, appelle ses outils, peut streamer des tokens
5. Réponse + traces persistées (Postgres), mémoire mise à jour
```
