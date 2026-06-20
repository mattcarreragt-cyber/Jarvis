# 04 — Mémoire

Trois horizons de mémoire, trois stockages.

## 4.1 Court terme — Redis

- Contexte de la conversation en cours (N derniers tours).
- Clé : `session:{session_id}:turns`, TTL configurable.
- Sert à reconstituer le contexte immédiat sans requête lourde.

## 4.2 Persistant relationnel — PostgreSQL

Source de vérité structurée et auditable.

```
sessions(id, user_id, created_at, title)
messages(id, session_id, role, content, agent, created_at)
routing_logs(id, request_id, intent, agent, method, score, created_at)
tool_invocations(id, request_id, tool, args, result_ok, created_at)
```

## 4.3 Long terme sémantique — Qdrant

Mémoire rappelable par similarité (faits, préférences, documents).

```
collection "memory":
    vector: embedding(text)      # via Ollama embeddings (ex: nomic-embed-text)
    payload: { text, kind: "fact|preference|doc_chunk",
               source, session_id, created_at }
```

### Construction du `MemoryContext` (injecté dans AgentRequest)

```python
class MemoryContext:
    recent_turns: list[Turn]        # depuis Redis
    relevant_memories: list[str]    # top-k Qdrant sur le message courant
    user_profile: dict              # préférences persistantes (Postgres)
```

## Règles

- Écriture en mémoire long terme = **explicite** (l'agent ou une heuristique
  décide « ça vaut la peine d'être retenu »), pas tout systématiquement.
- Embeddings générés **localement** par Ollama (local-first).
- Toute donnée mémoire est rattachée à un `user_id` (multi-profil futur) et
  purgeable (droit à l'oubli).
