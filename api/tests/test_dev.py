"""Tests Agent Dev — sans Docker live (mocks)."""

from unittest.mock import AsyncMock, patch

from app.agents.dev_agent import DevAgent
from app.contracts import AgentRequest, AgentStatus, ToolResult
from app.registry import registry
from app.router import route


async def test_dev_agent_no_code_block():
    agent = DevAgent()
    resp = await agent.handle(AgentRequest(
        request_id="d1", session_id="s1",
        intent="dev", message="exécute du python stp",
    ))
    assert resp.status == AgentStatus.ok
    assert "bloc de code" in resp.content


async def test_dev_agent_python_ok():
    fake = ToolResult(ok=True, data={"output": "42\n"})
    with patch("app.agents.dev_agent.run_python", new=AsyncMock(return_value=fake)) as mock_py, \
         patch("app.agents.dev_agent.run_bash", new=AsyncMock()) as mock_bash:
        agent = DevAgent()
        resp = await agent.handle(AgentRequest(
            request_id="d2", session_id="s1", intent="dev",
            message="exécute ```python\nprint(6*7)\n```",
        ))
    assert resp.status == AgentStatus.ok
    assert "42" in resp.content
    mock_py.assert_awaited_once()
    mock_bash.assert_not_awaited()


async def test_dev_agent_bash_routing():
    fake = ToolResult(ok=True, data={"output": "hello\n"})
    with patch("app.agents.dev_agent.run_bash", new=AsyncMock(return_value=fake)) as mock_bash, \
         patch("app.agents.dev_agent.run_python", new=AsyncMock()) as mock_py:
        agent = DevAgent()
        resp = await agent.handle(AgentRequest(
            request_id="d3", session_id="s1", intent="dev",
            message="lance ```bash\necho hello\n```",
        ))
    assert "hello" in resp.content
    mock_bash.assert_awaited_once()
    mock_py.assert_not_awaited()


async def test_dev_agent_error():
    fake = ToolResult(ok=False, error="SyntaxError")
    with patch("app.agents.dev_agent.run_python", new=AsyncMock(return_value=fake)):
        agent = DevAgent()
        resp = await agent.handle(AgentRequest(
            request_id="d4", session_id="s1", intent="dev",
            message="```python\nprint(\n```",
        ))
    assert resp.status == AgentStatus.error
    assert "SyntaxError" in resp.content


def test_router_dev_keywords():
    for phrase in ["exécute ce code python", "lance un script bash", "écris un algorithme"]:
        d = route(phrase, registry)
        assert d.agent == "dev", f"'{phrase}' → {d.agent}"
