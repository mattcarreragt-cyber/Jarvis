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

- **Unraid** héberge les services stateless/légers + les bases de données.
- **Kubuntu** héberge tout ce qui consomme du GPU.
- Communication : HTTP(S) sur le LAN. Les endpoints GPU (Ollama, ComfyUI, etc.)
  sont configurés par variables d'environnement (`OLLAMA_BASE_URL`, etc.), jamais
  en dur.

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
