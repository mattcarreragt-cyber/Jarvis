import logging
import uuid

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_api_key
from app.contracts import AgentRequest, AgentResponse, ChatRequest
from app.db import ensure_session, persist_message, persist_routing_log, persist_tool_invocations
from app.health import get_health
from app.memory import memory
from app.registry import registry
from app.router import route
from app.routers import sessions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")

app = FastAPI(title="JARVIS OS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)

app.include_router(sessions.router)


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

    decision = route(req.message, registry, force_agent=req.force_agent)
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

    return response


@app.post("/api/chat/confirm", response_model=AgentResponse, tags=["chat"],
          dependencies=[Depends(require_api_key)])
async def confirm_action(request_id: str, confirmed: bool = True) -> AgentResponse:
    """Confirme ou annule une action sensible (needs_confirmation)."""
    if not confirmed:
        return AgentResponse(
            request_id=request_id, agent="system",
            content="Action annulée.",
        )
    # L'exécution réelle sera branchée quand les agents write seront implémentés.
    return AgentResponse(
        request_id=request_id, agent="system",
        content="Action confirmée. (Exécution disponible en v2)",
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "JARVIS OS API", "docs": "/docs"}
