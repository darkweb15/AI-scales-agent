"""Orchestrator package — pure LLM-driven agentic sales AI system.

The GraphOrchestrator uses LangGraph + LLM reasoning for all decisions.
Legacy rule-based routing (routing.py, orchestrator.py) is retained for
backward compatibility but is no longer used in production.
"""


def __getattr__(name: str):
    if name == "GraphOrchestrator":
        from .graph_orchestrator import GraphOrchestrator  # noqa: PLC0415
        return GraphOrchestrator
    if name == "Orchestrator":
        from .orchestrator import Orchestrator  # noqa: PLC0415
        return Orchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GraphOrchestrator", "Orchestrator"]
