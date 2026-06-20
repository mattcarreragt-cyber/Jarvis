"""Construction de réponse RAG partagée (SearchAgent, NextcloudAgent).

Si le LLM (Ollama/Kubuntu) est disponible → réponse rédigée + liste des sources.
Sinon → extraits bruts (mode keyword), comme avant.
"""

from __future__ import annotations

from app.llm.rag import synthesize


def _clean_source(src: str) -> str:
    return src.split("nextcloud:", 1)[-1]


def _excerpts(hits: list[dict], title: str) -> str:
    lines = [f"## {title} ({len(hits)} extraits)", ""]
    for i, r in enumerate(hits, 1):
        lines.append(f"### [{i}] `{_clean_source(r['source'])}`  _(score: {r['score']})_")
        lines.append(r["text"].strip())
        lines.append("")
    return "\n".join(lines)


def _sources_block(hits: list[dict]) -> str:
    lines = ["", "---", "**Sources :**"]
    for i, r in enumerate(hits, 1):
        lines.append(f"- [{i}] `{_clean_source(r['source'])}`")
    return "\n".join(lines)


async def build_rag_reply(
    question: str,
    hits: list[dict],
    method: str,
    empty_title: str = "Résultats",
) -> str:
    """Réponse synthétisée si LLM dispo, sinon extraits. `method` = semantic|keyword."""
    answer = await synthesize(question, hits)
    if answer:
        return answer + "\n" + _sources_block(hits)

    # Repli : extraits bruts
    body = _excerpts(hits, empty_title)
    note = (
        "_Recherche sémantique (embeddings) — synthèse LLM indisponible (Kubuntu éteint ?)._"
        if method == "semantic"
        else "_Mode keyword — résultats plus précis avec les embeddings + LLM (Kubuntu)._"
    )
    return f"{body}\n---\n{note}"
