"""Agent Recherche — RAG keyword sur les documents ingérés (mode sans LLM).

Quand Ollama/Kubuntu sera branché :
- Les chunks seront vectorisés (nomic-embed-text).
- La recherche passera en mode cosine similarity (meilleure précision).
- Un LLM synthétisera les chunks en réponse naturelle.

En attendant : on retourne les chunks pertinents avec leur source.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.agents.rag_reply import build_rag_reply
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.docs.search import search


class SearchAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="recherche",
            description="Recherche dans les documents ingérés (fiches produit, notes, docs).",
            keywords=[
                "cherche", "recherche", "trouve", "document", "fiche", "note",
                "doc", "contenu", "information", "source", "référence", "base",
            ],
            default_permissions=["docs:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        results, method = await search(request.message, top_k=5)
        call = ToolCall(
            tool="docs.search",
            args={"query": request.message, "top_k": 5, "method": method},
            result=ToolResult(ok=True, data={"hits": len(results)}),
        )

        if not results:
            return AgentResponse(
                request_id=request.request_id, agent="recherche",
                status=AgentStatus.ok,
                content="Aucun document pertinent trouvé.\n\n"
                        "_Utilise `/api/docs/ingest` pour ajouter des documents._",
                tool_calls=[call],
            )

        content = await build_rag_reply(
            question=request.message, hits=results, method=method,
            empty_title="Résultats de recherche",
        )
        return AgentResponse(
            request_id=request.request_id, agent="recherche",
            status=AgentStatus.ok, content=content, tool_calls=[call],
        )
