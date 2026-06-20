import logging
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.contracts import AgentRequest, AgentResponse, ChatRequest
from app.health import get_health
from app.memory import memory
from app.registry import registry
from app.router import route

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis")

app = FastAPI(title="JARVIS OS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restreindre en prod
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
async def health():
    return await get_health()


@app.get("/api/agents", tags=["agents"])
async def list_agents():
    return [spec.model_dump() for spec in registry.specs()]


@app.post("/api/chat", response_model=AgentResponse, tags=["chat"])
async def chat(req: ChatRequest) -> AgentResponse:
    request_id = str(uuid.uuid4())

    decision = route(req.message, registry, force_agent=req.force_agent)
    logger.info(
        "route session=%s agent=%s method=%s score=%s",
        req.session_id, decision.agent, decision.method, decision.score,
    )

    agent = registry.get(decision.agent) or registry.get("echo")

    context = await memory.build_context(req.session_id, req.message)

    agent_req = AgentRequest(
        request_id=request_id,
        session_id=req.session_id,
        intent=decision.agent,
        message=req.message,
        context=context,
    )
    response = await agent.handle(agent_req)

    # Persiste les tours en mémoire court terme (tolérant aux pannes).
    await memory.record_turn(req.session_id, "user", req.message)
    await memory.record_turn(
        req.session_id, "assistant", response.content, agent=response.agent
    )
    return response


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "JARVIS OS API", "docs": "/docs"}
