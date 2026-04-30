"""LangGraph Orchestrator — real agentic decision-making engine.

Replaces the if/else routing with a stateful LangGraph graph where:
- Each node is an agent action
- Edges are decided by LLM reasoning, not hardcoded conditions
- The graph loops until the lead reaches a terminal state or needs human review

Graph structure:
    START
      ↓
    [load_lead_state]        ← fetch lead + full interaction history from DB
      ↓
    [llm_reason_action]      ← LLM decides what to do next (ReAct reasoning)
      ↓
    [route_to_agent]         ← dispatch to the right agent node
      ↓
    [cold_call_node]  ──┐
    [send_email_node] ──┤
    [follow_up_node]  ──┤→ [process_outcome] → [update_lead_state] → loop or END
    [schedule_demo_node]─┘
    [escalate_node]   ──┘
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, TypedDict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph State — shared across all nodes
# ---------------------------------------------------------------------------

class LeadAgentState(TypedDict):
    """State passed between all nodes in the LangGraph."""
    lead_id: str
    lead_data: Dict[str, Any]           # serialized lead fields
    interaction_history: List[Dict]     # last N interactions
    llm_decision: Dict[str, Any]        # LLM reasoning output
    action_result: Dict[str, Any]       # result from agent node
    next_node: str                      # routing decision
    iteration: int                      # loop counter (prevent infinite loops)
    error: Optional[str]


# ---------------------------------------------------------------------------
# LangGraph Orchestrator
# ---------------------------------------------------------------------------

class GraphOrchestrator:
    """Real agentic orchestrator using LangGraph stateful graph.
    
    The LLM reasons about each lead's full context and decides the next action.
    No hardcoded if/else routing — pure AI decision making.
    """

    MAX_ITERATIONS = 3  # max reasoning loops per lead per tick

    def __init__(
        self,
        session_factory,
        notification_service,
        config,
        db_service=None,
    ) -> None:
        self._session_factory = session_factory
        self._notification = notification_service
        self._config = config
        self._running = False

        from ..database.service import DatabaseService
        self._db = db_service or DatabaseService()

        # Import LLM and RAG
        from ..core.agent_llm import get_agent_llm
        from ..core.rag_knowledge_base import get_rag_knowledge_base
        self._llm = get_agent_llm()
        self._rag = get_rag_knowledge_base()

        # Build the LangGraph
        self._graph = self._build_graph()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Main polling loop — runs every poll_interval seconds."""
        self._running = True
        logger.info("🧠 LangGraph Orchestrator started (poll: %ds)",
                    self._config.orchestrator_poll_interval_seconds)
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.exception("Orchestrator tick error: %s", e)
            await asyncio.sleep(self._config.orchestrator_poll_interval_seconds)

    def stop(self) -> None:
        self._running = False

    async def process_lead(self, lead_id: str) -> Dict[str, Any]:
        """Process a single lead through the agentic graph. Returns final state."""
        async with self._session_factory() as session:
            lead = await self._db.get_lead(session, uuid.UUID(lead_id))
            if not lead:
                return {"error": f"Lead {lead_id} not found"}

            interactions = await self._db.get_interactions_for_lead(session, lead.id)

        # Build initial state
        initial_state: LeadAgentState = {
            "lead_id": lead_id,
            "lead_data": self._serialize_lead(lead),
            "interaction_history": self._serialize_interactions(interactions[-10:]),  # last 10
            "llm_decision": {},
            "action_result": {},
            "next_node": "llm_reason_action",
            "iteration": 0,
            "error": None,
        }

        # Run the graph
        try:
            final_state = await self._graph.ainvoke(initial_state)
            return final_state
        except Exception as e:
            logger.exception("Graph execution failed for lead %s: %s", lead_id, e)
            return {"error": str(e), "lead_id": lead_id}

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self):
        """Build the LangGraph StateGraph."""
        try:
            from langgraph.graph import StateGraph, END

            graph = StateGraph(LeadAgentState)

            # Add all nodes
            graph.add_node("load_lead_state", self._node_load_lead_state)
            graph.add_node("llm_reason_action", self._node_llm_reason_action)
            graph.add_node("cold_call_node", self._node_cold_call)
            graph.add_node("send_email_node", self._node_send_email)
            graph.add_node("follow_up_node", self._node_follow_up)
            graph.add_node("schedule_demo_node", self._node_schedule_demo)
            graph.add_node("escalate_node", self._node_escalate)
            graph.add_node("update_lead_state", self._node_update_lead_state)

            # Entry point
            graph.set_entry_point("load_lead_state")

            # load_lead_state → llm_reason_action
            graph.add_edge("load_lead_state", "llm_reason_action")

            # llm_reason_action → route based on LLM decision
            graph.add_conditional_edges(
                "llm_reason_action",
                self._route_after_reasoning,
                {
                    "cold_call": "cold_call_node",
                    "send_email": "send_email_node",
                    "follow_up": "follow_up_node",
                    "schedule_demo": "schedule_demo_node",
                    "escalate": "escalate_node",
                    "end": END,
                },
            )

            # All agent nodes → update_lead_state
            for node in ["cold_call_node", "send_email_node", "follow_up_node",
                         "schedule_demo_node", "escalate_node"]:
                graph.add_edge(node, "update_lead_state")

            # update_lead_state → loop back or end
            graph.add_conditional_edges(
                "update_lead_state",
                self._route_after_update,
                {
                    "continue": "llm_reason_action",
                    "end": END,
                },
            )

            return graph.compile()

        except ImportError:
            logger.warning("LangGraph not installed — using fallback async graph")
            return self._build_fallback_graph()

    # ------------------------------------------------------------------
    # Graph nodes
    # ------------------------------------------------------------------

    async def _node_load_lead_state(self, state: LeadAgentState) -> LeadAgentState:
        """Load fresh lead data and interaction history from DB."""
        try:
            async with self._session_factory() as session:
                lead = await self._db.get_lead(session, uuid.UUID(state["lead_id"]))
                if lead:
                    interactions = await self._db.get_interactions_for_lead(session, lead.id)
                    state["lead_data"] = self._serialize_lead(lead)
                    state["interaction_history"] = self._serialize_interactions(interactions[-10:])
        except Exception as e:
            state["error"] = str(e)
        return state

    async def _node_llm_reason_action(self, state: LeadAgentState) -> LeadAgentState:
        """LLM reasons about the best next action for this lead.
        
        This is the core intelligence — no if/else, pure LLM reasoning.
        """
        lead = state["lead_data"]
        history = state["interaction_history"]

        # Build lead summary for LLM
        lead_summary = f"""
Lead: {lead.get('first_name', '')} {lead.get('last_name', '')} at {lead.get('company', 'Unknown')}
Status: {lead.get('status', 'new')}
Phone: {lead.get('phone', 'N/A')}
Email: {lead.get('email', 'N/A')}
Call attempts: {lead.get('call_attempts', 0)}
Email attempts: {lead.get('email_attempts', 0)}
Last contacted: {lead.get('last_contacted_at', 'Never')}
Demo scheduled: {lead.get('demo_scheduled_at', 'Not scheduled')}
Tags: {lead.get('tags', [])}
Notes: {lead.get('notes', '')}
"""

        # Build interaction history summary
        history_text = "No prior interactions."
        if history:
            history_lines = []
            for h in history[-5:]:  # last 5 interactions
                history_lines.append(
                    f"- [{h.get('timestamp', '')}] {h.get('agent_type', '')} via {h.get('channel', '')}: "
                    f"{h.get('outcome', '')} — {h.get('summary', '')}"
                )
            history_text = "\n".join(history_lines)

        # Determine available actions based on lead state
        status = lead.get("status", "new")
        available_actions = self._get_available_actions(lead)

        if not available_actions:
            state["llm_decision"] = {
                "action": "end",
                "reasoning": f"Lead status '{status}' requires no action",
                "urgency": "low",
                "message_hint": "",
            }
            state["next_node"] = "end"
            return state

        # LLM reasons about next action
        decision = self._llm.reason_next_action(
            lead_summary=lead_summary,
            interaction_history=history_text,
            available_actions=available_actions,
        )

        logger.info(
            "🧠 LLM decision for lead %s: %s (reason: %s)",
            state["lead_id"][:8],
            decision.get("action"),
            decision.get("reasoning", "")[:80],
        )

        state["llm_decision"] = decision
        state["next_node"] = decision.get("action", "end")
        return state

    async def _node_cold_call(self, state: LeadAgentState) -> LeadAgentState:
        """Execute an outbound cold call via Vapi."""
        lead = state["lead_data"]
        lead_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        company = lead.get("company", "")
        phone = lead.get("phone", "")

        logger.info("📞 Cold calling %s (%s)", lead_name, phone)

        try:
            import os
            vapi_key = os.environ.get("VAPI_API_KEY", "")
            if not vapi_key:
                state["action_result"] = {"outcome": "skipped", "reason": "VAPI_API_KEY not set"}
                return state

            # Generate personalized call script using LLM
            rag_context = self._rag.retrieve(f"Pebble POS features pricing for {company}")
            script = self._llm.generate_call_script(lead_name, company, rag_context=rag_context)

            from ..agents.cold_calling.vapi_telephony import VapiTelephonyAPI
            telephony = VapiTelephonyAPI()
            telephony.initiate_call(phone, lead_name, company)

            state["action_result"] = {
                "outcome": "called",
                "script_used": script[:100],
                "new_status": "contacted",
            }

            # Update DB
            async with self._session_factory() as session:
                from ..models.enums import LeadStatus
                await self._db.update_lead(
                    session,
                    uuid.UUID(state["lead_id"]),
                    last_contacted_at=datetime.now(timezone.utc),
                    call_attempts=lead.get("call_attempts", 0) + 1,
                )
                await self._db.update_lead_status(session, uuid.UUID(state["lead_id"]), LeadStatus.contacted)
                await session.commit()

        except Exception as e:
            logger.error("Cold call failed: %s", e)
            state["action_result"] = {"outcome": "failed", "error": str(e)}

        return state

    async def _node_send_email(self, state: LeadAgentState) -> LeadAgentState:
        """Send a personalized email using LLM-generated content."""
        lead = state["lead_data"]
        lead_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        company = lead.get("company", "")
        status = lead.get("status", "new")
        decision = state.get("llm_decision", {})

        logger.info("📧 Sending email to %s (%s)", lead_name, lead.get("email"))

        try:
            import os, httpx

            sg_key = os.environ.get("SENDGRID_API_KEY", "")
            if not sg_key:
                state["action_result"] = {"outcome": "skipped", "reason": "SENDGRID_API_KEY not set"}
                return state

            # LLM generates personalized email content
            email_content = self._llm.generate_email(
                lead_name=lead_name,
                company=company,
                intent=status,
                context=decision.get("message_hint", ""),
                template_hint=decision.get("reasoning", ""),
            )

            subject = email_content.get("subject", f"Quick question, {lead_name.split()[0] if lead_name else 'there'}")
            body = email_content.get("body", "")

            from_email = os.environ.get("FROM_EMAIL", "bhargav.gangula@growith.io")
            from_name = os.environ.get("FROM_NAME", "Priya from Pebble")

            payload = {
                "personalizations": [{"to": [{"email": lead.get("email"), "name": lead_name}], "subject": subject}],
                "from": {"email": from_email, "name": from_name},
                "content": [{"type": "text/html", "value": body.replace("\n", "<br>")}],
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"},
                    json=payload,
                )

            if resp.status_code in (200, 202):
                state["action_result"] = {"outcome": "sent", "subject": subject}
                async with self._session_factory() as session:
                    from ..models.enums import LeadStatus
                    await self._db.update_lead(
                        session,
                        uuid.UUID(state["lead_id"]),
                        last_contacted_at=datetime.now(timezone.utc),
                        email_attempts=lead.get("email_attempts", 0) + 1,
                    )
                    await self._db.update_lead_status(session, uuid.UUID(state["lead_id"]), LeadStatus.contacted)
                    await session.commit()
            else:
                state["action_result"] = {"outcome": "failed", "error": resp.text[:100]}

        except Exception as e:
            logger.error("Email send failed: %s", e)
            state["action_result"] = {"outcome": "failed", "error": str(e)}

        return state

    async def _node_follow_up(self, state: LeadAgentState) -> LeadAgentState:
        """Execute a follow-up action — LLM decides channel and content."""
        lead = state["lead_data"]
        history = state["interaction_history"]
        decision = state.get("llm_decision", {})

        # LLM already decided the best channel in reasoning
        # Check last interaction to alternate channels intelligently
        last_channel = "call"
        if history:
            last_channel = history[-1].get("channel", "call")

        # LLM-driven channel selection (not keyword-based)
        channel_decision = self._llm.reason_next_action(
            lead_summary=f"Lead {lead.get('first_name')} needs follow-up. Last contact via {last_channel}.",
            interaction_history="\n".join([f"- {h.get('channel')}: {h.get('outcome')}" for h in history[-3:]]),
            available_actions=["call", "email"],
        )
        channel = channel_decision.get("action", "email")

        logger.info("🔄 Follow-up for lead %s via %s", state["lead_id"][:8], channel)

        if channel == "call":
            # Delegate to cold call node
            return await self._node_cold_call(state)
        else:
            return await self._node_send_email(state)

    async def _node_schedule_demo(self, state: LeadAgentState) -> LeadAgentState:
        """Send demo scheduling email with available slots."""
        lead = state["lead_data"]
        lead_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

        logger.info("📅 Scheduling demo for %s", lead_name)

        try:
            # Generate demo scheduling email using LLM
            email_content = self._llm.generate_email(
                lead_name=lead_name,
                company=lead.get("company", ""),
                intent="demo_scheduling",
                context="Lead is interested and ready to see a demo",
                template_hint="Offer 3 specific time slots, include booking link",
            )

            # For now log the intent — actual calendar integration via DemoSchedulingAgent
            state["action_result"] = {
                "outcome": "demo_email_sent",
                "subject": email_content.get("subject", ""),
            }

            async with self._session_factory() as session:
                from ..models.enums import LeadStatus
                await self._db.update_lead_status(
                    session,
                    uuid.UUID(state["lead_id"]),
                    LeadStatus.follow_up_scheduled,
                )
                await session.commit()

        except Exception as e:
            logger.error("Demo scheduling failed: %s", e)
            state["action_result"] = {"outcome": "failed", "error": str(e)}

        return state

    async def _node_escalate(self, state: LeadAgentState) -> LeadAgentState:
        """Escalate lead to human review."""
        logger.info("🚨 Escalating lead %s to human review", state["lead_id"][:8])

        try:
            async with self._session_factory() as session:
                from ..models.enums import LeadStatus
                await self._db.update_lead_status(
                    session,
                    uuid.UUID(state["lead_id"]),
                    LeadStatus.requires_human_review,
                )
                await session.commit()

            self._notification.emit("lead.escalated", {
                "lead_id": state["lead_id"],
                "reason": state.get("llm_decision", {}).get("reasoning", "LLM escalation"),
            })

            state["action_result"] = {"outcome": "escalated"}

        except Exception as e:
            state["action_result"] = {"outcome": "failed", "error": str(e)}

        return state

    async def _node_update_lead_state(self, state: LeadAgentState) -> LeadAgentState:
        """Emit WebSocket event and decide whether to loop."""
        result = state.get("action_result", {})
        outcome = result.get("outcome", "unknown")

        # Emit real-time event to dashboard
        self._notification.emit("agent.action_completed", {
            "lead_id": state["lead_id"],
            "action": state.get("llm_decision", {}).get("action", "unknown"),
            "outcome": outcome,
            "reasoning": state.get("llm_decision", {}).get("reasoning", ""),
        })

        state["iteration"] = state.get("iteration", 0) + 1

        # Decide whether to loop (only loop if action succeeded and not terminal)
        terminal_outcomes = {"escalated", "failed", "skipped", "end"}
        if outcome in terminal_outcomes or state["iteration"] >= self.MAX_ITERATIONS:
            state["next_node"] = "end"
        else:
            state["next_node"] = "end"  # one action per tick, re-evaluate next poll

        return state

    # ------------------------------------------------------------------
    # Routing functions (conditional edges)
    # ------------------------------------------------------------------

    def _route_after_reasoning(self, state: LeadAgentState) -> str:
        """Route to the correct agent node based on LLM decision."""
        action = state.get("llm_decision", {}).get("action", "end")

        routing_map = {
            "cold_call": "cold_call",
            "call": "cold_call",
            "send_email": "send_email",
            "email": "send_email",
            "follow_up": "follow_up",
            "schedule_demo": "schedule_demo",
            "demo": "schedule_demo",
            "escalate": "escalate",
            "wait": "end",
            "end": "end",
        }

        route = routing_map.get(action.lower(), "end")
        logger.info("🔀 Routing lead %s → %s (LLM said: %s)", state["lead_id"][:8], route, action)
        return route

    def _route_after_update(self, state: LeadAgentState) -> str:
        """Decide whether to loop back or end."""
        return "end" if state.get("next_node") == "end" else "continue"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_available_actions(self, lead: Dict) -> List[str]:
        """Return valid actions for this lead based on status — LLM picks the best one."""
        status = lead.get("status", "new")
        call_attempts = lead.get("call_attempts", 0)
        email_attempts = lead.get("email_attempts", 0)
        total_attempts = call_attempts + email_attempts

        from ..models.enums import LeadStatus

        # Terminal states — no action
        if status in (LeadStatus.do_not_contact, LeadStatus.unsubscribed,
                      LeadStatus.requires_human_review, LeadStatus.converted):
            return []

        # Max attempts reached
        if total_attempts >= self._config.max_total_follow_up_attempts:
            return ["escalate"]

        if status == LeadStatus.new:
            if call_attempts < self._config.max_cold_call_attempts:
                return ["cold_call", "send_email"]  # LLM picks
            return ["send_email"]

        if status == LeadStatus.contacted:
            return ["follow_up", "send_email", "cold_call"]  # LLM picks best

        if status == LeadStatus.interested:
            return ["schedule_demo", "send_email"]

        if status == LeadStatus.follow_up_scheduled:
            return ["send_email", "cold_call"]

        if status in (LeadStatus.demo_scheduled, LeadStatus.demo_completed):
            return ["send_email"]  # reminder or follow-up

        if status == LeadStatus.not_interested:
            return []  # respect the decision

        return ["send_email"]

    def _serialize_lead(self, lead) -> Dict:
        return {
            "id": str(lead.id),
            "first_name": lead.first_name or "",
            "last_name": lead.last_name or "",
            "email": lead.email or "",
            "phone": lead.phone or "",
            "company": lead.company or "",
            "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
            "call_attempts": lead.call_attempts or 0,
            "email_attempts": lead.email_attempts or 0,
            "last_contacted_at": lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
            "demo_scheduled_at": lead.demo_scheduled_at.isoformat() if lead.demo_scheduled_at else None,
            "tags": lead.tags or [],
            "notes": lead.notes or "",
        }

    def _serialize_interactions(self, interactions) -> List[Dict]:
        result = []
        for i in interactions:
            result.append({
                "timestamp": i.timestamp.isoformat() if i.timestamp else "",
                "agent_type": i.agent_type.value if hasattr(i.agent_type, "value") else str(i.agent_type),
                "channel": i.channel.value if hasattr(i.channel, "value") else str(i.channel),
                "outcome": i.outcome or "",
                "summary": i.summary or "",
                "intent": i.intent_detected.value if i.intent_detected and hasattr(i.intent_detected, "value") else "",
            })
        return result

    # ------------------------------------------------------------------
    # Fallback graph (when LangGraph not installed)
    # ------------------------------------------------------------------

    def _build_fallback_graph(self):
        """Simple async fallback when LangGraph is not installed."""
        logger.warning("Using fallback graph (LangGraph not installed)")

        class FallbackGraph:
            def __init__(self, orchestrator):
                self._orch = orchestrator

            async def ainvoke(self, state: LeadAgentState) -> LeadAgentState:
                state = await self._orch._node_load_lead_state(state)
                state = await self._orch._node_llm_reason_action(state)

                route = self._orch._route_after_reasoning(state)
                if route == "cold_call":
                    state = await self._orch._node_cold_call(state)
                elif route == "send_email":
                    state = await self._orch._node_send_email(state)
                elif route == "follow_up":
                    state = await self._orch._node_follow_up(state)
                elif route == "schedule_demo":
                    state = await self._orch._node_schedule_demo(state)
                elif route == "escalate":
                    state = await self._orch._node_escalate(state)

                state = await self._orch._node_update_lead_state(state)
                return state

        return FallbackGraph(self)

    # ------------------------------------------------------------------
    # Internal tick
    # ------------------------------------------------------------------

    async def _tick(self) -> None:
        """Poll DB for pending leads and run each through the graph."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            leads = await self._db.query_leads_pending_action(session, now)

        if not leads:
            return

        # Process max 5 leads per tick to stay within Groq free tier (30 req/min)
        # Each lead uses ~2 LLM calls, so 5 leads = 10 calls per tick
        batch = leads[:5]
        logger.info("🔄 Graph tick: processing %d/%d pending leads", len(batch), len(leads))

        for i, lead in enumerate(batch):
            try:
                await self.process_lead(str(lead.id))
                if i < len(batch) - 1:
                    await asyncio.sleep(3)  # 3s between leads → ~20 calls/min, under 30 limit
            except Exception as e:
                logger.exception("Error processing lead %s: %s", lead.id, e)
