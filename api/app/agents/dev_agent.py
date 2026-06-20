"""Agent Dev — exécution de code Python/Bash en sandbox Docker.

Pas de GPU requis. Tourne entièrement sur Unraid via le socket Docker.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.agents.dev_tools import SPECS, run_bash, run_python
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall

_PYTHON_PAT = re.compile(
    r"\b(python|script|calcul|calculer|exécute|exécuter|code python|snippet|fonction)\b", re.I
)
_BASH_PAT = re.compile(
    r"\b(bash|shell|commande shell|terminal|sh)\b", re.I
)
_CODE_FENCE = re.compile(r"```(?:python|bash|sh)?\n(.*?)```", re.DOTALL)


class DevAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="dev",
            description="Exécute du code Python ou bash en sandbox Docker isolée (Unraid, pas de GPU).",
            keywords=[
                "python", "script", "calcul", "code", "exécute", "exécuter",
                "bash", "shell", "terminal", "fonction", "snippet", "algorithme",
            ],
            tools=SPECS,
            default_permissions=["dev:execute"],
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        msg = req.message

        # Extraire le code dans un bloc ```…```
        fence = _CODE_FENCE.search(msg)
        code = fence.group(1).strip() if fence else None

        if not code:
            return AgentResponse(
                request_id=req.request_id,
                agent=self.spec.name,
                status=AgentStatus.ok,
                content=(
                    "Pour exécuter du code, entoure-le d'un bloc de code :\n\n"
                    "```python\nprint('hello')\n```\n\n"
                    "ou\n\n"
                    "```bash\necho hello\n```"
                ),
            )

        # Détecter le langage
        use_bash = bool(_BASH_PAT.search(msg)) and not fence
        if fence:
            lang_match = re.match(r"```(python|bash|sh)?", msg[fence.start():])
            lang = lang_match.group(1) if lang_match else "python"
            use_bash = lang in ("bash", "sh")

        if use_bash:
            result = await run_bash(code)
            tool_name = "dev.run_bash"
        else:
            result = await run_python(code)
            tool_name = "dev.run_python"

        tool_call = ToolCall(tool=tool_name, args={"code": code} if not use_bash else {"script": code}, result=result)

        if result.ok:
            output = (result.data or {}).get("output", "").strip() or "(pas de sortie)"
            content = f"```\n{output}\n```"
        else:
            content = f"Erreur d'exécution : {result.error}"

        return AgentResponse(
            request_id=req.request_id,
            agent=self.spec.name,
            status=AgentStatus.ok if result.ok else AgentStatus.error,
            content=content,
            tool_calls=[tool_call],
        )
