# 02 — Contrats (le cœur du système)

C'est le document le plus important : il définit les interfaces stables que
toutes les autres couches respectent. Schémas exprimés en Pydantic-like.

## 2.1 Message d'entrée (Dashboard → API)

```python
class ChatRequest:
    session_id: str            # UUID de conversation
    message: str               # texte utilisateur
    modality: "text" | "voice" = "text"
    attachments: list[Attachment] = []
    force_agent: str | None = None   # bypass router (debug/avancé)
```

## 2.2 Enveloppe d'agent (Router → Agent)

```python
class AgentRequest:
    request_id: str
    session_id: str
    intent: str                # intent détecté par le router
    message: str
    context: MemoryContext     # voir 04_MEMORY.md
    permissions: list[str]     # permissions accordées pour cet appel
```

```python
class AgentResponse:
    request_id: str
    agent: str
    status: "ok" | "error" | "queued" | "needs_confirmation"
    content: str               # réponse texte (markdown)
    tool_calls: list[ToolCall] = []   # trace des outils utilisés
    artifacts: list[Artifact] = []    # fichiers, images, etc.
    confirmation: ConfirmationRequest | None = None  # si action sensible
```

## 2.3 Définition d'un Outil (Tool)

Un **outil** est une fonction typée qu'un agent peut appeler. Contrat unique :

```python
class Tool:
    name: str                  # ex: "system.disk_usage"
    description: str           # pour le function-calling LLM
    parameters: JSONSchema     # schéma des arguments
    required_permissions: list[str]
    side_effects: "none" | "read" | "write"   # gouverne la confirmation
    handler: Callable[[dict], ToolResult]
```

```python
class ToolResult:
    ok: bool
    data: dict | None
    error: str | None
```

Règle : un outil avec `side_effects == "write"` sur un système en production
(Unraid) DOIT renvoyer `needs_confirmation` avant exécution.
**Exception (choix utilisateur)** : les commandes domotiques Home Assistant
(allumer/éteindre, consigne de température) s'exécutent directement — la
friction d'une confirmation est incompatible avec l'usage vocal. Garde-fous :
détection d'impératif uniquement (les questions et participes ne déclenchent
rien), plage de température bornée 5-35 °C.

## 2.4 Contrat d'enregistrement d'un Agent

Chaque agent expose un descripteur statique pour que le Router le connaisse :

```python
class AgentSpec:
    name: str                  # "system"
    description: str           # utilisée par le router LLM
    keywords: list[str]        # utilisés par le router à règles
    tools: list[Tool]
    default_permissions: list[str]
```

## 2.5 API HTTP (FastAPI)

| Méthode | Route                  | Rôle                                   |
|---------|------------------------|----------------------------------------|
| POST    | `/api/chat`            | Envoi message, réponse (stream SSE/WS) |
| POST    | `/api/chat/confirm`    | Confirmer une action sensible          |
| GET     | `/api/agents`          | Liste des AgentSpec enregistrés        |
| GET     | `/api/sessions/{id}`   | Historique d'une session               |
| GET     | `/api/health`          | Santé des dépendances (DB, Ollama…)    |

Toutes les routes (sauf `/api/health`) requièrent authentification
(voir `06_SECURITY.md`).
