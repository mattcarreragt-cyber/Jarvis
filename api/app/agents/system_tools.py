"""Outils de l'agent System — métriques de la machine locale.

Tous en lecture seule (side_effects <= read) pour la v1. Voir docs/05_AGENTS.md.
"""

from __future__ import annotations

import psutil

from app.contracts import SideEffect, ToolResult, ToolSpec


def cpu_usage() -> ToolResult:
    per_core = psutil.cpu_percent(interval=0.3, percpu=True)
    return ToolResult(
        ok=True,
        data={
            "percent": psutil.cpu_percent(interval=0.0),
            "per_core": per_core,
            "cores": psutil.cpu_count(logical=True),
        },
    )


def memory_usage() -> ToolResult:
    vm = psutil.virtual_memory()
    return ToolResult(
        ok=True,
        data={
            "total_gb": round(vm.total / 1e9, 2),
            "used_gb": round(vm.used / 1e9, 2),
            "available_gb": round(vm.available / 1e9, 2),
            "percent": vm.percent,
        },
    )


def disk_usage() -> ToolResult:
    parts = []
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
        except (PermissionError, OSError):
            continue
        parts.append(
            {
                "mount": p.mountpoint,
                "total_gb": round(u.total / 1e9, 2),
                "used_gb": round(u.used / 1e9, 2),
                "percent": u.percent,
            }
        )
    return ToolResult(ok=True, data={"partitions": parts})


def uptime() -> ToolResult:
    import time

    boot = psutil.boot_time()
    seconds = int(time.time() - boot)
    load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)
    return ToolResult(
        ok=True,
        data={
            "uptime_seconds": seconds,
            "uptime_hours": round(seconds / 3600, 1),
            "load_avg": list(load),
        },
    )


def top_processes(limit: int = 5) -> ToolResult:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        procs.append(p.info)
    procs.sort(key=lambda x: (x.get("cpu_percent") or 0), reverse=True)
    return ToolResult(ok=True, data={"processes": procs[:limit]})


# Handlers indexés par nom d'outil
HANDLERS = {
    "system.cpu_usage": cpu_usage,
    "system.memory_usage": memory_usage,
    "system.disk_usage": disk_usage,
    "system.uptime": uptime,
    "system.top_processes": top_processes,
}

# Descripteurs statiques (exposés au Router via l'AgentSpec)
SPECS = [
    ToolSpec(name="system.cpu_usage", description="Charge CPU instantanée + par cœur",
             required_permissions=["system:read"], side_effects=SideEffect.none),
    ToolSpec(name="system.memory_usage", description="RAM utilisée / disponible",
             required_permissions=["system:read"], side_effects=SideEffect.none),
    ToolSpec(name="system.disk_usage", description="Espace disque par montage",
             required_permissions=["system:read"], side_effects=SideEffect.read),
    ToolSpec(name="system.uptime", description="Uptime + load average",
             required_permissions=["system:read"], side_effects=SideEffect.none),
    ToolSpec(name="system.top_processes", description="Top processus par CPU/RAM",
             required_permissions=["system:read"], side_effects=SideEffect.read),
]
