"""Orchestrator package — central routing engine for the AI Sales Automation System."""

from .routing import evaluate_lead, is_on_cooldown


def __getattr__(name: str):
    if name == "Orchestrator":
        from .orchestrator import Orchestrator  # noqa: PLC0415
        return Orchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Orchestrator", "evaluate_lead", "is_on_cooldown"]
