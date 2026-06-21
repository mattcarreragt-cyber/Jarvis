"""Agent Chat généraliste — conversation libre via Ollama (Kubuntu GPU).

C'est l'agent par défaut du router (fallback). Contrairement aux chemins de fond
(sync, RAG), c'est ICI qu'on accepte de réveiller Kubuntu : l'utilisateur demande
explicitement une réponse conversationnelle.

Flux :
1. resolve_chat_hint(message) → "fast" | "deep" (mots-clés stratégie/analyse/code…)
2. scheduler.dispatch("chat.<hint>") → vérifie/réveille Kubuntu, renvoie le modèle
3. ollama.chat(messages) avec contexte mémoire (tours récents + souvenirs)
4. Si Kubuntu indisponible → message clair (pas d'échec silencieux)
"""

from __future__ import annotations

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.llm.ollama import chat
from app.llm.persona import assistant_system
from app.orchestration.scheduler import dispatch, resolve_chat_hint


class ChatAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="chat",
            description="Conversation généraliste : questions ouvertes, raisonnement, "
                        "rédaction, code. Agent par défaut quand aucun agent spécialisé "
                        "ne correspond.",
            keywords=[],  # agent par défaut : ne concourt pas au scoring keyword
            default_permissions=["chat:use"],
        )

    def _build_messages(self, req: AgentRequest) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": assistant_system()}]

        ctx = req.context
        if ctx.relevant_memories:
            mem = "\n".join(f"- {m}" for m in ctx.relevant_memories)
            messages.append({
                "role": "system",
                "content": f"Éléments mémorisés pertinents :\n{mem}",
            })
        # Tours récents (court terme) — ordre chronologique
        for turn in ctx.recent_turns:
            role = "assistant" if turn.role == "assistant" else "user"
            messages.append({"role": role, "content": turn.content})

        messages.append({"role": "user", "content": req.message})
        return messages

    async def handle(self, req: AgentRequest) -> AgentResponse:
        hint = req.hint or resolve_chat_hint(req.message)
        capability = f"chat.{hint}"

        disp = await dispatch(capability)
        if not disp.get("ok"):
            return AgentResponse(
                request_id=req.request_id, agent="chat",
                status=AgentStatus.error,
                content=(
                    "Le nœud de calcul (Kubuntu) est indisponible, je ne peux pas "
                    "générer de réponse conversationnelle pour le moment.\n\n"
                    f"_{disp.get('error', 'GPU hors ligne')}._"
                ),
                tool_calls=[ToolCall(
                    tool="orchestration.dispatch", args={"capability": capability},
                    result=ToolResult(ok=False, error=disp.get("error")),
                )],
            )

        model = disp.get("model")
        answer = await chat(self._build_messages(req), model=model,
                            base_url=disp.get("base_url"))
        call = ToolCall(
            tool="llm.chat",
            args={"capability": capability, "model": model,
                  "machine": disp.get("machine")},
            result=ToolResult(ok=answer is not None,
                              error=None if answer else "Réponse vide / LLM injoignable"),
        )

        if not answer:
            return AgentResponse(
                request_id=req.request_id, agent="chat",
                status=AgentStatus.error,
                content="Kubuntu est joignable mais le modèle n'a pas répondu. "
                        "Vérifie qu'Ollama a bien le modèle requis.",
                tool_calls=[call],
            )

        return AgentResponse(
            request_id=req.request_id, agent="chat",
            status=AgentStatus.ok, content=answer, tool_calls=[call],
        )
