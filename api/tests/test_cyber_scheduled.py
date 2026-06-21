"""Tests audit cyber planifié (baisse de score) + parsing agenda cyber/hebdo."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.agents.agenda_agent import AgendaAgent
from app.contracts import AgentRequest
from app.cyber import scheduled


def _audit_result(score):
    return {"ok": True, "findings": [], "score": score, "grade": "B" if score >= 75 else "D",
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}}


async def test_scheduled_alert_on_score_drop():
    host = {"id": "h1", "label": "unraid"}
    with patch("app.cyber.scheduled.store.list_hosts", new=AsyncMock(return_value=[host])), \
         patch("app.cyber.scheduled.store.score_history", new=AsyncMock(return_value=[{"score": 90, "grade": "A"}])), \
         patch("app.cyber.scheduled.audit.run_audit", new=AsyncMock(return_value=_audit_result(70))), \
         patch("app.cyber.scheduled.store.save_findings", new=AsyncMock()), \
         patch("app.cyber.scheduled.store.save_score", new=AsyncMock()):
        out = await scheduled.run_and_alert("unraid")
    assert "BAISSE 90→70" in out
    assert "unraid" in out


async def test_scheduled_no_alert_when_stable():
    host = {"id": "h1", "label": "unraid"}
    with patch("app.cyber.scheduled.store.list_hosts", new=AsyncMock(return_value=[host])), \
         patch("app.cyber.scheduled.store.score_history", new=AsyncMock(return_value=[{"score": 70}])), \
         patch("app.cyber.scheduled.audit.run_audit", new=AsyncMock(return_value=_audit_result(80))), \
         patch("app.cyber.scheduled.store.save_findings", new=AsyncMock()), \
         patch("app.cyber.scheduled.store.save_score", new=AsyncMock()):
        out = await scheduled.run_and_alert("tous")
    assert "BAISSE" not in out
    assert "80/100" in out


async def test_scheduled_unknown_host():
    with patch("app.cyber.scheduled.store.list_hosts", new=AsyncMock(return_value=[])):
        out = await scheduled.run_and_alert("inconnu")
    assert "introuvable" in out


# ─── Parsing agenda : type cyber + hebdomadaire ──────────────────────────────

async def _capture(msg):
    with patch("app.agents.agenda_agent.store.add_task",
               new=AsyncMock(return_value="tid")) as add:
        await AgendaAgent().handle(AgentRequest(
            request_id="a1", session_id="s1", intent="agenda", message=msg))
    return add.call_args.kwargs if add.call_args else None


async def test_agenda_creates_cyber_task():
    kw = await _capture("chaque jour à 8h, audite unraid")
    assert kw["kind"] == "cyber"
    assert kw["schedule_kind"] == "daily"
    assert "unraid" in kw["payload"].lower()


async def test_agenda_weekly_schedule():
    kw = await _capture("chaque lundi à 9h, audite tous mes hôtes")
    assert kw["kind"] == "cyber"
    assert kw["schedule_kind"] == "interval"
    assert kw["interval_sec"] == 7 * 24 * 3600


def test_next_weekday_anchors_correctly():
    # mercredi 2026-06-17 10:00 UTC, prochaine occurrence lundi (wd=0) 09:00
    now = datetime(2026, 6, 17, 10, 0, tzinfo=timezone.utc)  # weekday()==2 (mercredi)
    nxt = AgendaAgent._next_weekday(now, 0, "09:00")
    assert nxt.weekday() == 0
    assert nxt.hour == 9
    assert nxt > now
