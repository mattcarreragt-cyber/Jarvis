"""Agent Recherche — RAG keyword sur les documents ingérés (mode sans LLM).

Quand Ollama/Kubuntu sera branché :
- Les chunks seront vectorisés (nomic-embed-text).
- La recherche passera en mode cosine similarity (meilleure précision).
- Un LLM synthétisera les chunks en réponse naturelle.

En attendant : on retourne les chunks pertinents avec leur source.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.docs.search import keyword_search


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
        results = await keyword_search(request.message, top_k=5)
        call = ToolCall(
            tool="docs.keyword_search",
            args={"query": request.message, "top_k": 5},
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

        lines = [f"## Résultats de recherche ({len(results)} extraits)", ""]
        for i, r in enumerate(results, 1):
            lines.append(f"### [{i}] `{r['source']}`  _(score: {r['score']})_")
            lines.append(r["text"].strip())
            lines.append("")

        lines.append("---")
        lines.append("_Mode keyword — les résultats seront plus précis avec les embeddings Ollama (Kubuntu)._")

        return AgentResponse(
            request_id=request.request_id, agent="recherche",
            status=AgentStatus.ok,
            content="\n".join(lines),
            tool_calls=[call],
        )
