"""Client ComfyUI — génération d'images SDXL (Kubuntu GPU).

Best-effort : si ComfyUI est injoignable (Kubuntu éteint), generate() renvoie None.
Le réveil Wake-on-LAN et le déchargement des LLM (capacité `exclusive`) sont gérés
en amont par app.orchestration.scheduler.dispatch("image").

Flux ComfyUI :
1. POST /prompt {prompt: <workflow>, client_id}   → {prompt_id}
2. polling GET /history/{prompt_id}                → outputs quand terminé
3. l'image est servie par GET /view?filename&subfolder&type — proxifiée par l'API.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid

import httpx

from app.config import settings

logger = logging.getLogger("jarvis.comfyui")


def _base() -> str:
    return settings.comfyui_base_url.rstrip("/")


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{_base()}/system_stats")
            return r.status_code < 500
    except Exception:
        return False


def _build_workflow(prompt: str, negative: str, seed: int) -> dict:
    """Workflow SDXL text→image au format API ComfyUI (graphe de nœuds)."""
    return {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": settings.comfyui_checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": settings.comfyui_width,
                "height": settings.comfyui_height,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["4", 1]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": settings.comfyui_steps,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "jarvis", "images": ["8", 0]},
        },
    }


async def generate(
    prompt: str,
    negative: str = "lowres, blurry, watermark, text, deformed",
    seed: int | None = None,
) -> dict | None:
    """Génère une image. Retourne {filename, subfolder, type, seed} ou None."""
    seed = seed if seed is not None else random.randint(0, 2**31 - 1)
    client_id = str(uuid.uuid4())
    workflow = _build_workflow(prompt, negative, seed)

    try:
        async with httpx.AsyncClient(timeout=settings.comfyui_timeout) as client:
            r = await client.post(
                f"{_base()}/prompt",
                json={"prompt": workflow, "client_id": client_id},
            )
            if r.status_code >= 400:
                logger.warning("ComfyUI /prompt erreur %s : %s", r.status_code, r.text[:300])
                return None
            prompt_id = r.json().get("prompt_id")
            if not prompt_id:
                return None

            # Polling de l'historique
            deadline = asyncio.get_event_loop().time() + settings.comfyui_timeout
            while asyncio.get_event_loop().time() < deadline:
                await asyncio.sleep(1.5)
                h = await client.get(f"{_base()}/history/{prompt_id}")
                if h.status_code != 200:
                    continue
                data = h.json().get(prompt_id)
                if not data:
                    continue
                outputs = data.get("outputs", {})
                for node in outputs.values():
                    images = node.get("images")
                    if images:
                        img = images[0]
                        return {
                            "filename":  img["filename"],
                            "subfolder": img.get("subfolder", ""),
                            "type":      img.get("type", "output"),
                            "seed":      seed,
                        }
            logger.warning("ComfyUI : génération non terminée dans le délai imparti")
            return None
    except Exception as e:
        logger.debug("generate indisponible (Kubuntu éteint ?): %s", e)
        return None


async def fetch_image(filename: str, subfolder: str, type_: str) -> bytes | None:
    """Récupère les octets d'une image générée (proxy depuis ComfyUI)."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{_base()}/view",
                params={"filename": filename, "subfolder": subfolder, "type": type_},
            )
            r.raise_for_status()
            return r.content
    except Exception as e:
        logger.debug("fetch_image échoué: %s", e)
        return None
