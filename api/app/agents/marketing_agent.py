"""Agent Marketing — assistant IA contenu Xenum.

Lit les fiches produit / docs marketing ingérés, assiste la création de contenu.
V1 : RAG keyword + contexte — sans LLM (génération réelle avec Ollama sur Kubuntu).
V2 (Kubuntu) : LLM synthétise les chunks en texte de pub / caption / post.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.docs.search import keyword_search

# Intentions détectées en langage naturel
_POST_PAT    = re.compile(r"\b(post|publication|caption|légende|texte|rédige|écris|contenu)\b", re.I)
_BRIEF_PAT   = re.compile(r"\b(brief|angle|idée|stratégi|campagne|concept|axe)\b", re.I)
_PRODUIT_PAT = re.compile(r"\b(produit|fiche|caractéristique|feature|bénéfice|avantage)\b", re.I)


class MarketingAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="marketing",
            description="Assistant marketing Xenum : contenu, publications, fiches produit, "
                        "stratégie. Utilise les documents ingérés comme source de vérité.",
            keywords=[
                "xenum", "marketing", "publication", "post", "contenu", "rédige",
                "caption", "accroche", "campagne", "pub", "publicité", "texte",
                "produit", "fiche", "brief", "stratégie", "audience", "canal",
                "instagram", "linkedin", "facebook", "réseau", "social",
            ],
            default_permissions=["docs:read"],
        )

    async def handle(self, request: AgentRequest) -> AgentResponse:
        msg = request.message

        # Recherche dans les docs Xenum ingérés (tags=xenum ou tous si pas de tag)
        results = await keyword_search(msg, top_k=4, tags_filter=["xenum"])
        if not results:
            # Fallback sans filtre tag
            results = await keyword_search(msg, top_k=4)

        call = ToolCall(
            tool="docs.keyword_search",
            args={"query": msg, "top_k": 4},
            result=ToolResult(ok=True, data={"hits": len(results)}),
        )

        is_post   = bool(_POST_PAT.search(msg))
        is_brief  = bool(_BRIEF_PAT.search(msg))
        is_produit = bool(_PRODUIT_PAT.search(msg))

        context_block = self._format_context(results)

        if is_post:
            content = self._assist_post(msg, context_block)
        elif is_brief:
            content = self._assist_brief(msg, context_block)
        elif is_produit:
            content = self._assist_produit(msg, context_block)
        else:
            content = self._assist_generic(msg, context_block)

        return AgentResponse(
            request_id=request.request_id, agent="marketing",
            status=AgentStatus.ok,
            content=content,
            tool_calls=[call],
        )

    @staticmethod
    def _format_context(results: list[dict]) -> str:
        if not results:
            return "_Aucun document Xenum ingéré pour l'instant._\n" \
                   "_Ajoute des fiches produit via `/api/docs/ingest` (tag : `xenum`)._"
        lines = ["**Extraits pertinents de ta base de documents :**", ""]
        for r in results:
            lines.append(f"> [{r['source']}] {r['text'][:300].strip()}…")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _assist_post(msg: str, ctx: str) -> str:
        return f"""## Assistant rédaction — publication Xenum

{ctx}

---
**Ce que je peux faire maintenant (mode keyword) :**
- Te fournir le contexte produit extrait de tes docs ci-dessus.
- Te suggérer une structure : accroche → corps → CTA.

**Ce qui sera disponible avec Ollama/Kubuntu :**
- Rédaction complète du post dans ton style.
- Déclinaisons par canal (Instagram, LinkedIn, Facebook).
- Variations A/B d'accroche.

💡 **Structure suggérée pour un post Xenum :**
```
[ACCROCHE] — problème ou bénéfice frappant (1 ligne)
[CORPS]    — contexte, preuve, différenciateur (2-3 lignes)
[CTA]      — action claire (1 ligne)
[HASHTAGS] — 5-8 tags pertinents
```
"""

    @staticmethod
    def _assist_brief(msg: str, ctx: str) -> str:
        return f"""## Assistant brief créatif — Xenum

{ctx}

---
**Axes stratégiques à explorer** _(basés sur tes docs)_ :

1. **Différenciateur produit** — qu'est-ce qui rend Xenum unique parmi les extraits ?
2. **Douleur client** — quel problème le produit résout-il concrètement ?
3. **Preuve sociale** — résultats, chiffres, témoignages disponibles dans les docs.
4. **Ton** — à définir : expert / accessible / premium / engagé ?

_Génération LLM complète disponible avec Kubuntu (Ollama)._
"""

    @staticmethod
    def _assist_produit(msg: str, ctx: str) -> str:
        return f"""## Informations produit Xenum

{ctx}

---
_Ces extraits proviennent de tes documents ingérés. Ajoute d'autres fiches produit
via `POST /api/docs/ingest` avec le tag `xenum` pour enrichir la base._
"""

    @staticmethod
    def _assist_generic(msg: str, ctx: str) -> str:
        return f"""## Assistant Marketing Xenum

{ctx}

---
Je peux t'aider sur :
- **Publications** — structure et rédaction de posts (LinkedIn, Instagram, Facebook)
- **Fiches produit** — extraire et synthétiser les infos de tes docs
- **Brief créatif** — angles et axes de campagne
- **Images de pub** — génération via ComfyUI _(disponible avec Kubuntu)_

Précise ta demande pour que je t'assiste au mieux.
"""
