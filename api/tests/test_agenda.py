"""Tests Agenda — parsing, planification, runner (mocks, sans Postgres)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.agents.agenda_agent import AgendaAgent
from app.automation import runner, store
from app.contracts import AgentRequest
from app.registry import registry
from app.router import route


def _req(msg):
    return AgentRequest(request_id="a1", session_id="s1", intent="agenda", message=msg)


# ─── compute_next_run ────────────────────────────────────────────────────────

def test_compute_next_run_interval():
    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    nxt = store.compute_next_run("interval", None, 3600, base)
    assert nxt == base + timedelta(hours=1)


def test_compute_next_run_daily_future_today():
    base = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
    nxt = store.compute_next_run("daily", "08:00", None, base)
    assert nxt.hour == 8 and nxt.day == 1


def test_compute_next_run_daily_rolls_tomorrow():
    base = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    nxt = store.compute_next_run("daily", "08:00", None, base)
    assert nxt.day == 2


# ─── Parsing agent ───────────────────────────────────────────────────────────

async def _capture(msg):
    with patch("app.agents.agenda_agent.store.add_task",
               new=AsyncMock(return_value="tid")) as add:
        resp = await AgendaAgent().handle(_req(msg))
    return resp, (add.call_args.kwargs if add.call_args else None)


async def test_parse_reminder_at_time():
    resp, kw = await _capture("rappelle-moi d'appeler Paul à 14h30")
    assert kw["schedule_kind"] == "once"
    assert kw["time_of_day"] == "14:30"
    assert kw["kind"] == "reminder"
    assert "appeler paul" in kw["payload"].lower()


async def test_parse_delay():
    resp, kw = await _capture("dans 20 minutes, sortir le plat")
    assert kw["schedule_kind"] == "once"
    assert "sortir le plat" in kw["payload"].lower()


async def test_parse_daily_prompt():
    resp, kw = await _capture("chaque jour à 8h, résume mes nouveaux fichiers")
    assert kw["schedule_kind"] == "daily"
    assert kw["time_of_day"] == "08:00"
    assert kw["kind"] == "prompt"          # « résume » = commande


async def test_parse_interval_prompt():
    resp, kw = await _capture("toutes les 2 heures, vérifie l'espace disque")
    assert kw["schedule_kind"] == "interval"
    assert kw["interval_sec"] == 7200
    assert kw["kind"] == "prompt"


async def test_help_when_no_schedule():
    with patch("app.agents.agenda_agent.store.add_task", new=AsyncMock()):
        resp = await AgendaAgent().handle(_req("rappelle-moi un truc"))
    assert "rappelle-moi" in resp.content.lower()


async def test_list_and_clear():
    with patch("app.agents.agenda_agent.store.list_tasks", new=AsyncMock(return_value=[])):
        r = await AgendaAgent().handle(_req("mes rappels"))
    assert "Aucun rappel" in r.content
    with patch("app.agents.agenda_agent.store.clear_tasks", new=AsyncMock(return_value=2)):
        r = await AgendaAgent().handle(_req("annule tout"))
    assert "2" in r.content


def test_router_agenda_keywords():
    for p in ["rappelle-moi d'appeler Paul à 14h", "planifie une tâche", "chaque jour à 8h résume"]:
        assert route(p, registry).agent == "agenda", p


# ─── Runner ──────────────────────────────────────────────────────────────────

async def test_runner_executes_reminder():
    due = [{"id": "1", "label": "x", "kind": "reminder", "payload": "boire de l'eau",
            "schedule_kind": "once", "time_of_day": None, "interval_sec": None}]
    with patch("app.automation.runner.store.due_tasks", new=AsyncMock(return_value=due)), \
         patch("app.automation.runner.store.add_notification", new=AsyncMock()) as notif, \
         patch("app.automation.runner.store.mark_ran", new=AsyncMock()) as mark:
        n = await runner.tick()
    assert n == 1
    assert "boire de l'eau" in notif.call_args.args[0]
    mark.assert_awaited_once()


async def test_runner_executes_prompt():
    due = [{"id": "2", "label": "x", "kind": "prompt", "payload": "cpu et ram",
            "schedule_kind": "interval", "time_of_day": None, "interval_sec": 60}]
    with patch("app.automation.runner.store.due_tasks", new=AsyncMock(return_value=due)), \
         patch("app.automation.runner.store.add_notification", new=AsyncMock()) as notif, \
         patch("app.automation.runner.store.mark_ran", new=AsyncMock()):
        await runner.tick()
    # le résultat de l'agent (system) est inclus dans la notif
    assert "cpu et ram" in notif.call_args.args[0].lower()
