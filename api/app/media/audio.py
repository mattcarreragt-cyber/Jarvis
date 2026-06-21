"""Génération audio / musique via ComfyUI (Stable Audio) — Kubuntu GPU.

Synchrone (génération courte) : submit + polling de l'historique, comme l'image.
Workflow paramétrable (tokens __PROMPT__, __NEG__, __SECONDS__).

Best-effort : ComfyUI injoignable → None. Le réveil WoL et le déchargement des
LLM (capacité exclusive) sont gérés par scheduler.dispatch("audio").
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import uuid
from pathlib import Path

import httpx

from app.config import settings
from app.media.comfyui import _base

logger = logging.getLogger("jarvis.audio")


def _resolve_template(path: str | None) -> Path | None:
    rel = path or settings.audio_workflow_path
    for c in (rel, f"/app/{rel}",
              str(Path(__file__).resolve().parent.parent.parent.parent / rel)):
        if c and Path(c).is_file():
            return Path(c)
    return None


def _apply_tokens(node: object, tokens: dict) -> object:
    if isinstance(node, dict):
        return {k: _apply_tokens(v, tokens) for k, v in node.items()}
    if isinstance(node, list):
        return [_apply_tokens(v, tokens) for v in node]
    if isinstance(node, str) and node in tokens:
        return tokens[node]
    return node


def build_workflow(prompt: str, negative: str, seconds: int, seed: int,
                   workflow_path: str | None = None) -> dict | None:
    path = _resolve_template(workflow_path)
    if path is None:
        logger.error("Template audio introuvable : %s", workflow_path or settings.audio_workflow_path)
        return None
    try:
        template = json.loads(path.read_text())
    except Exception as e:
        logger.error("Template audio illisible : %s", e)
        return None
    template.pop("_comment", None)
    wf = _apply_tokens(template, {
        "__PROMPT__": prompt, "__NEG__": negative, "__SECONDS__": seconds,
    })
    for node in wf.values():
        if isinstance(node, dict) and node.get("class_type") == "KSampler":
            node.setdefault("inputs", {})["seed"] = seed
    return wf


async def generate(prompt: str, seconds: int, negative: str = "",
                   seed: int | None = None, base_url: str | None = None,
                   workflow_path: str | None = None) -> dict | None:
    """Génère un clip audio. Retourne {filename, subfolder, type, seed} ou None."""
    seconds = max(2, min(seconds, settings.audio_max_seconds))
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    negative = negative or "low quality, noise"
    wf = build_workflow(prompt, negative, seconds, seed, workflow_path)
    if wf is None:
        return None

    base = _base(base_url)
    client_id = str(uuid.uuid4())
    try:
        async with httpx.AsyncClient(timeout=settings.audio_timeout) as client:
            r = await client.post(f"{base}/prompt", json={"prompt": wf, "client_id": client_id})
            if r.status_code >= 400:
                logger.warning("ComfyUI /prompt audio erreur %s : %s", r.status_code, r.text[:300])
                return None
            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                return None

            deadline = asyncio.get_event_loop().time() + settings.audio_timeout
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(1.5)
                h = await client.get(f"{base}/history/{prompt_id}")
                if h.status_code != 200:
                    continue
                data = h.json().get(prompt_id)
                if not data:
                    continue
                for node in data.get("outputs", {}).values():
                    audio = node.get("audio")
                    if audio:
                        a = audio[0]
                        return {"filename": a["filename"], "subfolder": a.get("subfolder", ""),
                                "type": a.get("type", "output"), "seed": seed}
            logger.warning("ComfyUI : génération audio non terminée dans le délai")
            return None
    except Exception as e:
        logger.debug("generate audio indisponible (Kubuntu éteint ?): %s", e)
        return None


async def fetch_audio(filename: str, subfolder: str, type_: str,
                      base_url: str | None = None) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{_base(base_url)}/view",
                                 params={"filename": filename, "subfolder": subfolder, "type": type_})
            r.raise_for_status()
            return r.content
    except Exception as e:
        logger.debug("fetch_audio échoué: %s", e)
        return None
