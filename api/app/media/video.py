"""Génération de vidéo via ComfyUI/AnimateDiff (Kubuntu GPU).

Asynchrone : la génération prend plusieurs minutes. On soumet un job (submit),
puis on interroge son état (status) ; l'agent renvoie un job_id et le dashboard
poll jusqu'à la vidéo finale.

Workflow paramétrable : un template JSON (config/comfyui_video_workflow.json)
contient des tokens __PROMPT__, __NEG__, __FRAMES__, __FPS__ remplacés ici.
Remplace le template par ton propre export API ComfyUI si tes nœuds diffèrent.

Best-effort : ComfyUI injoignable → submit/status renvoient un état d'erreur.
Le réveil WoL et le déchargement des modèles GPU concurrents (capacité exclusive)
sont gérés en amont par scheduler.dispatch("video").
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from pathlib import Path

import httpx

from app.config import settings
from app.media.comfyui import _base

logger = logging.getLogger("jarvis.video")

_TOKENS_INT = {"__FRAMES__", "__FPS__"}


def _resolve_template_path(path: str | None = None) -> Path | None:
    rel = path or settings.video_workflow_path
    candidates = [
        rel,
        f"/app/{rel}",
        str(Path(__file__).resolve().parent.parent.parent.parent / rel),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return None


def _substitute(node: object, prompt: str, negative: str, frames: int, fps: int) -> object:
    """Remplace récursivement les tokens dans le template."""
    if isinstance(node, dict):
        return {k: _substitute(v, prompt, negative, frames, fps) for k, v in node.items()}
    if isinstance(node, list):
        return [_substitute(v, prompt, negative, frames, fps) for v in node]
    if isinstance(node, str):
        if node == "__PROMPT__":
            return prompt
        if node == "__NEG__":
            return negative
        if node == "__FRAMES__":
            return frames
        if node == "__FPS__":
            return fps
    return node


def build_workflow(prompt: str, negative: str, frames: int, fps: int, seed: int,
                   workflow_path: str | None = None) -> dict | None:
    path = _resolve_template_path(workflow_path)
    if path is None:
        logger.error("Template vidéo introuvable : %s", settings.video_workflow_path)
        return None
    try:
        template = json.loads(path.read_text())
    except Exception as e:
        logger.error("Template vidéo illisible : %s", e)
        return None

    template.pop("_comment", None)
    wf = _substitute(template, prompt, negative, frames, fps)
    # Injecte le seed dans le premier KSampler trouvé
    for node in wf.values():
        if isinstance(node, dict) and node.get("class_type") == "KSampler":
            node.setdefault("inputs", {})["seed"] = seed
    return wf


async def submit(prompt: str, seconds: int, negative: str = "", seed: int | None = None,
                 base_url: str | None = None, workflow_path: str | None = None) -> dict:
    """Soumet un job vidéo. Retourne {ok, job_id?, frames?, error?}."""
    seconds = max(2, min(seconds, settings.video_max_seconds))
    fps = settings.video_fps
    frames = min(seconds * fps, settings.video_max_frames)
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    negative = negative or "lowres, blurry, watermark, text, deformed, flickering"

    wf = build_workflow(prompt, negative, frames, fps, seed, workflow_path)
    if wf is None:
        return {"ok": False, "error": "Template de workflow vidéo manquant ou invalide"}

    client_id = str(uuid.uuid4())
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{_base(base_url)}/prompt",
                                  json={"prompt": wf, "client_id": client_id})
            if r.status_code >= 400:
                logger.warning("ComfyUI /prompt vidéo erreur %s : %s", r.status_code, r.text[:300])
                return {"ok": False, "error": f"ComfyUI a refusé le workflow ({r.status_code})"}
            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                return {"ok": False, "error": "Pas de prompt_id retourné"}
            return {"ok": True, "job_id": prompt_id, "frames": frames,
                    "seconds": seconds, "seed": seed}
    except Exception as e:
        logger.debug("submit vidéo indisponible (Kubuntu éteint ?): %s", e)
        return {"ok": False, "error": "ComfyUI/Kubuntu injoignable"}


async def status(job_id: str, base_url: str | None = None) -> dict:
    """État d'un job. Retourne {state: running|done|error, media?}.

    media = {filename, subfolder, type} quand la vidéo est prête.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            h = await client.get(f"{_base(base_url)}/history/{job_id}")
            if h.status_code != 200:
                return {"state": "running"}
            data = h.json().get(job_id)
            if not data:
                # Soit encore en file, soit terminé sans entrée → on regarde la queue
                return {"state": "running"}

            outputs = data.get("outputs", {})
            for node in outputs.values():
                media = node.get("gifs") or node.get("videos") or node.get("images")
                if media:
                    m = media[0]
                    return {"state": "done", "media": {
                        "filename":  m["filename"],
                        "subfolder": m.get("subfolder", ""),
                        "type":      m.get("type", "output"),
                    }}

            # Terminé mais pas de média → erreur d'exécution
            status_info = data.get("status", {})
            if status_info.get("status_str") == "error":
                return {"state": "error", "error": "Échec d'exécution du workflow"}
            return {"state": "running"}
    except Exception as e:
        logger.debug("status vidéo: %s", e)
        return {"state": "running"}


async def fetch_video(filename: str, subfolder: str, type_: str,
                      base_url: str | None = None) -> bytes | None:
    """Récupère les octets de la vidéo générée (proxy depuis ComfyUI)."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(f"{_base(base_url)}/view",
                                 params={"filename": filename, "subfolder": subfolder, "type": type_})
            r.raise_for_status()
            return r.content
    except Exception as e:
        logger.debug("fetch_video échoué: %s", e)
        return None
