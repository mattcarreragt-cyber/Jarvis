"""Agent Nextcloud — RAG keyword sur les fichiers synchronisés depuis Nextcloud.

Filtre la recherche sur tags=["nextcloud"]. Même chemin de migration que SearchAgent :
embeddings + synthèse LLM quand Kubuntu sera branché.
"""

from __future__ import annotations

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.docs.search import keyword_search


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
        results = await keyword_search(request.message, top_k=6, tags_filter=["nextcloud"])
        call = ToolCall(
            tool="nextcloud.keyword_search",
            args={"query": request.message, "top_k": 6},
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

        lines = [f"## Nextcloud — {len(results)} extraits pertinents", ""]
        for i, r in enumerate(results, 1):
            # source = "nextcloud:/chemin" → on affiche le chemin propre
            src = r["source"].split("nextcloud:", 1)[-1]
            lines.append(f"### [{i}] `{src}`  _(score: {r['score']})_")
            lines.append(r["text"].strip())
            lines.append("")

        lines.append("---")
        lines.append("_Mode keyword — l'analyse en langage naturel arrivera avec "
                     "les embeddings + LLM sur Kubuntu._")

        return AgentResponse(
            request_id=request.request_id, agent="nextcloud",
            status=AgentStatus.ok,
            content="\n".join(lines),
            tool_calls=[call],
        )
