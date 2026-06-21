import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_api_key
from app.config import settings
from app.contracts import AgentRequest, AgentResponse, AgentStatus, ChatRequest
from app.db import ensure_session, persist_message, persist_routing_log, persist_tool_invocations
from app.health import get_health
from app.memory import memory
import app.pending as pending_store
from app.registry import registry
from app.router import route_smart
from app.routers import agenda as agenda_router
from app.routers import audio as audio_router
from app.routers import backup as backup_router
from app.routers import docs as docs_router
from app.routers import hooks as hooks_router
from app.routers import images as images_router
from app.routers import jobs as jobs_router
from app.routers import media as media_router
from app.routers import memory as memory_router
from app.routers import nextcloud as nextcloud_router
from app.routers import sessions
from app.routers import system as system_router
from app.routers import video as video_router
from app.routers import voice as voice_router
from app.sources import nextcloud as nc_source
from app.sources import sync as nc_sync

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks: list[asyncio.Task] = []
    if settings.nextcloud_sync_enabled and nc_source._configured():
        tasks.append(asyncio.create_task(nc_sync.periodic_loop()))
        logger.info("Boucle de sync Nextcloud démarrée")
    else:
        logger.info("Sync Nextcloud désactivée ou non configurée")
    # Boucle d'agenda (rappels / automatisations)
    from app.automation import runner as agenda_runner
    tasks.append(asyncio.create_task(agenda_runner.loop()))
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()


app = FastAPI(title="JARVIS OS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)

app.include_router(sessions.router)
app.include_router(docs_router.router)
app.include_router(nextcloud_router.router)
app.include_router(images_router.router)
app.include_router(video_router.router)
app.include_router(voice_router.router)
app.include_router(jobs_router.router)
app.include_router(memory_router.router)
app.include_router(agenda_router.router)
app.include_router(media_router.router)
app.include_router(audio_router.router)
app.include_router(system_router.router)
app.include_router(hooks_router.router)
app.include_router(backup_router.router)


@app.get("/api/health", tags=["system"])
async def health():
    return await get_health()


@app.get("/api/agents", tags=["agents"], dependencies=[Depends(require_api_key)])
async def list_agents():
    return [spec.model_dump() for spec in registry.specs()]


@app.post("/api/chat", response_model=AgentResponse, tags=["chat"],
          dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest) -> AgentResponse:
    request_id = str(uuid.uuid4())

    decision = await route_smart(req.message, registry, force_agent=req.force_agent)
    logger.info("route session=%s agent=%s method=%s score=%s",
                req.session_id, decision.agent, decision.method, decision.score)

    agent  = registry.get(decision.agent) or registry.get("echo")
    ctx    = await memory.build_context(req.session_id, req.message)

    agent_req = AgentRequest(
        request_id=request_id,
        session_id=req.session_id,
        intent=decision.agent,
        message=req.message,
        context=ctx,
    )
    response = await agent.handle(agent_req)

    await ensure_session(req.session_id)
    await persist_message(req.session_id, "user", req.message)
    await persist_message(req.session_id, "assistant", response.content, agent=response.agent)
    await persist_routing_log(request_id, req.session_id, decision)
    await persist_tool_invocations(request_id, response)
    await memory.record_turn(req.session_id, "user", req.message)
    await memory.record_turn(req.session_id, "assistant", response.content, agent=response.agent)

    if response.status == AgentStatus.needs_confirmation and response.confirmation:
        pending_store.save(response.confirmation)

    return response


@app.post("/api/chat/confirm", response_model=AgentResponse, tags=["chat"],
          dependencies=[Depends(require_api_key)])
async def confirm_action(request_id: str, confirmed: bool = True) -> AgentResponse:
    """Confirme ou annule une action sensible (needs_confirmation)."""
    if not confirmed:
        pending_store.pop(request_id)
        return AgentResponse(
            request_id=request_id, agent="system",
            content="Action annulée.",
        )

    confirmation = pending_store.pop(request_id)
    if confirmation is None:
        return AgentResponse(
            request_id=request_id, agent="system",
            status=AgentStatus.error,
            content="Action introuvable ou déjà exécutée.",
        )

    # Dispatch vers ha_tools selon le nom de l'outil
    from app.agents import ha_tools
    handler = ha_tools.HANDLERS.get(confirmation.tool)
    if handler is None:
        return AgentResponse(
            request_id=request_id, agent="system",
            status=AgentStatus.error,
            content=f"Outil inconnu : {confirmation.tool}",
        )

    try:
        args = confirmation.args
        if args:
            result = await handler(**args)
        else:
            result = await handler()

        if result.ok:
            return AgentResponse(
                request_id=request_id, agent="system",
                content=f"✓ {confirmation.summary} — action exécutée.",
            )
        return AgentResponse(
            request_id=request_id, agent="system",
            status=AgentStatus.error,
            content=f"Erreur : {result.error}",
        )
    except Exception as e:
        logger.error("confirm_action error: %s", e)
        return AgentResponse(
            request_id=request_id, agent="system",
            status=AgentStatus.error,
            content=f"Erreur inattendue : {e}",
        )


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "JARVIS OS API", "docs": "/docs"}
