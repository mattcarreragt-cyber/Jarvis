"""Tests de (dé)sérialisation des contrats — critère de 'fini' étape 2."""

from app.contracts import (
    AgentRequest,
    AgentResponse,
    AgentSpec,
    AgentStatus,
    ChatRequest,
    ConfirmationRequest,
    MemoryContext,
    Modality,
    SideEffect,
    ToolCall,
    ToolResult,
    ToolSpec,
    Turn,
)


def test_chat_request_defaults():
    req = ChatRequest(session_id="s1", message="hello")
    assert req.modality == Modality.text
    assert req.attachments == []
    assert req.force_agent is None


def test_chat_request_roundtrip():
    req = ChatRequest(session_id="s1", message="hi", modality="voice")
    dumped = req.model_dump()
    assert dumped["modality"] == "voice"
    assert ChatRequest.model_validate(dumped) == req


def test_tool_spec_side_effects_default():
    tool = ToolSpec(name="system.cpu_usage", description="CPU load")
    assert tool.side_effects == SideEffect.none
    assert tool.required_permissions == []


def test_agent_spec_with_tools():
    spec = AgentSpec(
        name="system",
        description="Machine locale",
        keywords=["cpu", "ram", "disque"],
        tools=[
            ToolSpec(
                name="system.disk_usage",
                description="Espace disque",
                side_effects="read",
                required_permissions=["system:read"],
            )
        ],
        default_permissions=["system:read"],
    )
    dumped = spec.model_dump()
    assert AgentSpec.model_validate(dumped) == spec
    assert spec.tools[0].side_effects == SideEffect.read


def test_agent_request_defaults():
    req = AgentRequest(
        request_id="r1", session_id="s1", intent="system", message="état machine"
    )
    assert isinstance(req.context, MemoryContext)
    assert req.context.recent_turns == []
    assert req.hint is None


def test_agent_response_with_tool_calls():
    resp = AgentResponse(
        request_id="r1",
        agent="system",
        status="ok",
        content="CPU 12%",
        tool_calls=[
            ToolCall(
                tool="system.cpu_usage",
                args={},
                result=ToolResult(ok=True, data={"percent": 12}),
            )
        ],
    )
    dumped = resp.model_dump()
    assert AgentResponse.model_validate(dumped) == resp
    assert resp.tool_calls[0].result.ok is True


def test_agent_response_needs_confirmation():
    resp = AgentResponse(
        request_id="r1",
        agent="unraid",
        status=AgentStatus.needs_confirmation,
        confirmation=ConfirmationRequest(
            request_id="r1",
            tool="unraid.restart_container",
            args={"name": "plex"},
            summary="Redémarrer le conteneur plex",
        ),
    )
    assert resp.status == AgentStatus.needs_confirmation
    assert resp.confirmation.tool == "unraid.restart_container"


def test_memory_context_roundtrip():
    ctx = MemoryContext(
        recent_turns=[Turn(role="user", content="salut")],
        relevant_memories=["préfère le français"],
        user_profile={"lang": "fr"},
    )
    assert MemoryContext.model_validate(ctx.model_dump()) == ctx
