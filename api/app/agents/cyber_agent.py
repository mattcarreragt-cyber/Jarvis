"""Agent Cybersécurité — conseiller défensif sur TES hôtes (audit SSH read-only).

Lance des analyses de failles non destructives et propose des correctifs.
L'application des correctifs se fait via une action explicite (panneau / endpoint
de remédiation), jamais automatiquement.
"""

from __future__ import annotations

import re

from app.agents.base import Agent
from app.contracts import AgentRequest, AgentResponse, AgentSpec, AgentStatus, ToolCall, ToolResult
from app.cyber import audit, store

_SEV_ICON = {"critical": "🟥", "high": "🟧", "medium": "🟨", "low": "🟦", "info": "⬜"}
_LIST = re.compile(r"\b(mes\s+(?:machines|h[ôo]tes|serveurs)|liste.*h[ôo]tes)\b", re.I)


class CyberAgent(Agent):
    @property
    def spec(self) -> AgentSpec:
        return AgentSpec(
            name="cyber",
            description="Conseiller cybersécurité : audite tes hôtes (SSH), détecte "
                        "les failles et propose des durcissements. Défensif uniquement.",
            keywords=[
                "sécurité", "securite", "faille", "failles", "vulnérabilité",
                "vulnérabilités", "vulnerabilite", "audit", "audite", "auditer",
                "durcis", "durcir", "pare-feu", "firewall", "cyber", "pentest",
                "sécurise", "sécuriser", "ssh", "hardening",
            ],
            default_permissions=["cyber:audit"],
        )

    async def handle(self, req: AgentRequest) -> AgentResponse:
        msg = req.message

        if _LIST.search(msg):
            hosts = await store.list_hosts()
            if not hosts:
                return self._r(req, "Aucun hôte déclaré. Ajoute-en un dans le panneau "
                                    "Cyber (label, hostname, utilisateur SSH).")
            lines = ["## Hôtes surveillés", ""]
            lines += [f"- **{h['label']}** — `{h['username']}@{h['hostname']}:{h['port']}`" for h in hosts]
            return self._r(req, "\n".join(lines))

        # Identifier l'hôte cible par son label
        hosts = await store.list_hosts()
        target = None
        for h in hosts:
            if re.search(rf"\b{re.escape(h['label'].lower())}\b", msg.lower()):
                target = h
                break

        if target is None:
            labels = ", ".join(h["label"] for h in hosts) or "(aucun)"
            return self._r(req,
                "Pour lancer un audit, précise l'hôte. Hôtes connus : " + labels +
                ".\nEx. « audite unraid ». Ajoute un hôte dans le panneau Cyber si besoin.")

        # Lancer l'audit
        result = await audit.run_audit(target)
        call = ToolCall(tool="cyber.audit", args={"host": target["label"]},
                        result=ToolResult(ok=result.get("ok", False), data=result.get("summary"),
                                          error=result.get("error")))
        if not result.get("ok"):
            return self._r(req, f"Audit impossible sur **{target['label']}** : "
                                f"{result.get('error')}", call, status=AgentStatus.error)

        findings = result["findings"]
        await store.save_findings(target["id"], findings)
        return self._r(req, self._format(target, findings, result["summary"]), call)

    @staticmethod
    def _format(host: dict, findings: list[dict], summary: dict) -> str:
        if not findings:
            return f"✅ Audit de **{host['label']}** terminé — aucun problème détecté."
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        findings = sorted(findings, key=lambda f: order.get(f["severity"], 9))
        head = " · ".join(f"{_SEV_ICON[s]} {summary[s]} {s}" for s in
                          ["critical", "high", "medium", "low", "info"] if summary.get(s))
        lines = [f"## Audit sécurité — {host['label']}", "", head, ""]
        for f in findings:
            lines.append(f"### {_SEV_ICON[f['severity']]} {f['title']}  _({f['severity']})_")
            if f.get("detail"):
                lines.append(f"```\n{f['detail'][:400]}\n```")
            if f.get("recommendation"):
                lines.append(f"→ {f['recommendation']}")
            if f.get("remediation"):
                lines.append(f"Correctif proposé : `{f['remediation']}`")
            lines.append("")
        lines.append("---")
        lines.append("_Les correctifs ne sont **pas** appliqués automatiquement. "
                     "Applique-les depuis le panneau Cyber (bouton) après vérification._")
        return "\n".join(lines)

    @staticmethod
    def _r(req: AgentRequest, content: str, call: ToolCall | None = None,
           status: AgentStatus = AgentStatus.ok) -> AgentResponse:
        return AgentResponse(request_id=req.request_id, agent="cyber", status=status,
                             content=content, tool_calls=[call] if call else [])
