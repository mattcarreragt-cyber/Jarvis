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

Kubuntu n'a pas besoin de tourner en permanence. Le chef d'orchestre (Unraid)
le réveille à la demande :

1. Une requête arrive nécessitant le GPU (chat LLM, image, voix).
2. FastAPI vérifie la santé du nœud Kubuntu (`GET {OLLAMA_BASE_URL}/...`).
3. Si injoignable et **WoL activé** (flag de config `KUBUNTU_WOL_ENABLED`),
   envoie un magic packet à `KUBUNTU_MAC` puis attend (polling santé) jusqu'à
   `KUBUNTU_WOL_TIMEOUT`.
4. Réveil OK → la requête poursuit. Sinon → réponse `503` claire (« nœud de
   calcul indisponible »).

- Le WoL est **activable/désactivable** depuis la config (et idéalement
  l'UI). Désactivé → comportement classique (erreur si Kubuntu est éteint).
- L'utilisateur voit un état « réveil en cours… » dans la webapp pendant le WoL.
- Idéalement, mise en veille auto de Kubuntu après une période d'inactivité
  (géré côté Kubuntu, hors périmètre v1).

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
