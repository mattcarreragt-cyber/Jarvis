# 08 — Orchestration des ressources

Le Router d'agent (`03_ROUTER.md`) répond à « quel agent ? ».
Ce document répond à « quelle machine, quel modèle, dans quel ordre ? ».

Ces deux couches sont **séparées** — le Router d'agent ne sait rien des
machines, l'orchestrateur ne sait rien des intents.

## Architecture des deux couches de routage

```
Message utilisateur
      │
      ▼
┌─────────────┐    intent + agent
│ Router      │──────────────────────────────► Agent
│ (intent)    │
└─────────────┘

Agent demande des outils (chat, stt, image…)
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Resource Orchestrator                              │
│                                                     │
│  1. Résoudre capacités requises → Capability Registry│
│  2. Sélectionner modèle selon politique              │
│  3. Vérifier disponibilité machine                  │
│  4. Réveiller Kubuntu via WoL (si et seulement si   │
│     au moins une capacité GPU=oui)                  │
│  5. Gérer le gpu:lock (file Redis)                  │
└─────────────────────────────────────────────────────┘
      │
      ▼
Backend (Ollama / ComfyUI / Whisper / Piper)
```

---

## Capability Registry

Registre déclaratif : mappe **capacité → (machine, backend, modèle, GPU)**.
Configuré dans `config/capabilities.yaml`, chargé au démarrage, rechargeable
à chaud sans restart.

```yaml
capabilities:

  chat.fast:
    machine: kubuntu
    backend: ollama
    model: llama3.1:8b          # rapide, contexte court
    gpu: true

  chat.deep:
    machine: kubuntu
    backend: ollama
    model: llama3.1:70b         # raisonnement, longue réflexion
    gpu: true

  embeddings:
    machine: kubuntu
    backend: ollama
    model: nomic-embed-text
    gpu: true                   # léger, mais sur Kubuntu

  stt:
    machine: kubuntu
    backend: faster-whisper
    model: large-v3
    gpu: true

  tts:
    machine: unraid             # Piper est CPU-only, Kubuntu pas nécessaire
    backend: piper
    model: fr_FR-upmc-medium
    gpu: false

  image:
    machine: kubuntu
    backend: comfyui
    model: sdxl                 # ou flux selon la demande
    gpu: true
```

**Règle WoL** : Kubuntu est réveillé si et seulement si la tâche contient
au moins une capacité avec `gpu: true` ET `machine: kubuntu`.
Une demande TTS pure reste sur Unraid — Kubuntu n'est pas réveillé.

---

## Politique de sélection de modèle

Quand un agent demande `chat`, le Scheduler choisit la capacité selon :

| Condition                                        | Capacité choisie |
|--------------------------------------------------|-----------------|
| Reformulation, résumé court, réponse rapide      | `chat.fast`     |
| Raisonnement, analyse, stratégie, code complexe  | `chat.deep`     |
| Génération marketing (réflexion / brainstorming) | `chat.deep`     |
| Génération marketing (caption / post court)      | `chat.fast`     |
| Embeddings mémoire                               | `embeddings`    |

L'agent peut **surcharger** la politique via `hint: fast|deep` dans son
`AgentRequest`. Le Scheduler accepte le hint mais peut le refuser si la
ressource est indisponible (fallback sur le niveau inférieur).

---

## Scheduler — comportement

```python
class Scheduler:

    def dispatch(capability: str, hint: str | None, payload: dict) -> TaskHandle:

        cap = registry.resolve(capability, hint)   # choisit fast/deep selon hint + policy

        if cap.machine == "kubuntu":
            ensure_kubuntu_alive()                 # vérifie santé ; WoL si besoin

        if cap.gpu:
            acquire_gpu_lock(cap.backend)          # verrou Redis sérialisé

        return execute(cap, payload)

    def ensure_kubuntu_alive():
        if health_check(KUBUNTU_URL):
            return                                 # déjà réveillé
        if not WOL_ENABLED:
            raise ServiceUnavailable("Kubuntu est éteint (WoL désactivé)")
        send_magic_packet(KUBUNTU_MAC)
        wait_for_health(KUBUNTU_URL, timeout=KUBUNTU_WOL_TIMEOUT)
        # pendant l'attente : SSE "réveil en cours…" envoyé au dashboard
```

### États exposés au dashboard (SSE)

| État                   | Signification                                  |
|------------------------|------------------------------------------------|
| `computing`            | Kubuntu répond, tâche en cours                 |
| `waking`               | Magic packet envoyé, attente réveil            |
| `queued:{position}`    | gpu:lock occupé, position dans la file         |
| `unavailable`          | Kubuntu injoignable, WoL désactivé ou timeout  |

---

## Résumé des variables d'environnement ajoutées

```
KUBUNTU_URL          URL de santé du nœud Kubuntu (ex: http://kubuntu:11434)
KUBUNTU_MAC          Adresse MAC pour le magic packet WoL
KUBUNTU_WOL_ENABLED  true | false
KUBUNTU_WOL_TIMEOUT  secondes max pour attendre le réveil (ex: 60)
OLLAMA_BASE_URL      URL Ollama sur Kubuntu
COMFYUI_BASE_URL     URL ComfyUI sur Kubuntu
WHISPER_BASE_URL     URL Faster-Whisper sur Kubuntu
PIPER_BASE_URL       URL Piper sur Unraid
```
