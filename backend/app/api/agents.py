"""Agent control REST API — real status, pause/resume, manual trigger."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Real agent state — persisted in memory (use Redis in production)
_agent_states: Dict[str, Dict] = {
    "cold_calling":    {"status": "active", "queue": 0, "completed_today": 0, "failed_today": 0},
    "follow_up":       {"status": "active", "queue": 0, "completed_today": 0, "failed_today": 0},
    "demo_scheduling": {"status": "active", "queue": 0, "completed_today": 0, "failed_today": 0},
    "auto_mail":       {"status": "active", "queue": 0, "completed_today": 0, "failed_today": 0},
    "auto_reply":      {"status": "active", "queue": 0, "completed_today": 0, "failed_today": 0},
    "call_answering":  {"status": "active", "queue": 0, "completed_today": 0, "failed_today": 0},
}

_agent_configs: Dict[str, Dict] = {
    agent: {
        "max_cold_call_attempts": 3,
        "cooldown_minutes": 60,
        "follow_up_delay_hours": 24,
        "calling_hours_start": 9,
        "calling_hours_end": 17,
        "auto_reply_confidence_threshold": 0.75,
        "max_task_retries": 3,
    }
    for agent in _agent_states
}


class AgentConfigUpdate(BaseModel):
    max_cold_call_attempts: Optional[int] = None
    cooldown_minutes: Optional[int] = None
    follow_up_delay_hours: Optional[int] = None
    calling_hours_start: Optional[int] = None
    calling_hours_end: Optional[int] = None
    auto_reply_confidence_threshold: Optional[float] = None
    max_task_retries: Optional[int] = None


def increment_completed(agent_type: str):
    if agent_type in _agent_states:
        _agent_states[agent_type]["completed_today"] += 1


def increment_failed(agent_type: str):
    if agent_type in _agent_states:
        _agent_states[agent_type]["failed_today"] += 1


def is_agent_active(agent_type: str) -> bool:
    return _agent_states.get(agent_type, {}).get("status") == "active"


@router.get("")
async def list_agents():
    """List all agents with real status."""
    from app.main import get_orchestrator
    orch = get_orchestrator()
    orch_running = orch is not None and orch._running

    result = []
    for agent_type, state in _agent_states.items():
        result.append({
            "agent_type": agent_type,
            "orchestrator_running": orch_running,
            **state,
        })
    return result


@router.get("/orchestrator/status")
async def orchestrator_status():
    """Check if the orchestrator background loop is running."""
    from app.main import get_orchestrator
    orch = get_orchestrator()
    return {
        "running": orch is not None and orch._running,
        "message": "Orchestrator is running — agents work automatically" if (orch and orch._running)
                   else "Orchestrator is stopped — start it to enable auto mode",
    }


@router.post("/orchestrator/start")
async def start_orchestrator():
    """Start the orchestrator background loop."""
    import asyncio
    from app.main import get_orchestrator
    orch = get_orchestrator()
    if orch and not orch._running:
        asyncio.create_task(orch.run())
        return {"status": "started", "message": "Orchestrator started — agents now work automatically"}
    return {"status": "already_running", "message": "Orchestrator is already running"}


@router.post("/orchestrator/stop")
async def stop_orchestrator():
    """Stop the orchestrator background loop."""
    from app.main import get_orchestrator
    orch = get_orchestrator()
    if orch:
        orch.stop()
        return {"status": "stopped", "message": "Orchestrator stopped"}
    return {"status": "not_running"}


@router.get("/{agent_type}")
async def get_agent(agent_type: str):
    if agent_type not in _agent_states:
        raise HTTPException(404, "Agent not found")
    return {"agent_type": agent_type, **_agent_states[agent_type]}


@router.post("/{agent_type}/pause")
async def pause_agent(agent_type: str):
    if agent_type not in _agent_states:
        raise HTTPException(404, "Agent not found")
    _agent_states[agent_type]["status"] = "paused"
    logger.info("Agent %s paused", agent_type)
    return {"agent_type": agent_type, "status": "paused"}


@router.post("/{agent_type}/resume")
async def resume_agent(agent_type: str):
    if agent_type not in _agent_states:
        raise HTTPException(404, "Agent not found")
    _agent_states[agent_type]["status"] = "active"
    logger.info("Agent %s resumed", agent_type)
    return {"agent_type": agent_type, "status": "active"}


@router.post("/{agent_type}/trigger")
async def trigger_agent_now(agent_type: str):
    """Manually trigger the orchestrator to process all pending leads right now."""
    import asyncio
    from app.main import get_orchestrator
    orch = get_orchestrator()
    if not orch:
        raise HTTPException(503, "Orchestrator not running")
    asyncio.create_task(orch._tick())
    return {"status": "triggered", "message": f"Orchestrator tick triggered — processing all pending leads now"}


@router.get("/{agent_type}/config")
async def get_config(agent_type: str):
    return _agent_configs.get(agent_type, {})


@router.patch("/{agent_type}/config")
async def update_config(agent_type: str, body: AgentConfigUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if agent_type in _agent_configs:
        _agent_configs[agent_type].update(updates)
    return _agent_configs.get(agent_type, {})
