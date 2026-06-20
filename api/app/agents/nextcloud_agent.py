"""Agent Nextcloud — RAG keyword sur les fichiers synchronisés depuis Nextcloud.

Filtre la recherche sur tags=["nextcloud"]. Même chemin de migration que SearchAgent :
embeddings + synthèse LLM quand Kubuntu sera branché.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.agents.rag_reply import build_rag_reply
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.docs.search import search


class NextcloudAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="nextcloud",
            description="Recherche et analyse dans les fichiers Nextcloud synchronisés "
                        "(documents, tableurs, présentations, PDF, images).",
            keywords=[
                "nextcloud", "cloud", "mes fichiers", "mes documents",
                "drive", "nuage", "fichier", "dossier",
            ],
            default_permissions=["docs:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        results, method = await search(request.message, top_k=6, tags_filter=["nextcloud"])
        call = ToolCall(
            tool="nextcloud.search",
            args={"query": request.message, "top_k": 6, "method": method},
            result=ToolResult(ok=True, data={"hits": len(results)}),
        )

        if not results:
            return AgentResponse(
                request_id=request.request_id, agent="nextcloud",
                status=AgentStatus.ok,
                content="Aucun fichier Nextcloud pertinent trouvé.\n\n"
                        "_Vérifie que la sync est configurée et lancée "
                        "(`POST /api/nextcloud/sync`)._",
                tool_calls=[call],
            )

        content = await build_rag_reply(
            question=request.message, hits=results, method=method,
            empty_title="Nextcloud — extraits pertinents",
        )
        return AgentResponse(
            request_id=request.request_id, agent="nextcloud",
            status=AgentStatus.ok, content=content, tool_calls=[call],
        )
