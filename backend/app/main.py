"""FastAPI application entry point."""
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import leads, agents, bookings, analytics, notifications, websocket, test_call
from app.api import business_data, call_webhook, campaigns, voice_webhook

logger = logging.getLogger(__name__)

app = FastAPI(title="SalesAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leads.router,         prefix="/api/leads",         tags=["leads"])
app.include_router(agents.router,        prefix="/api/agents",        tags=["agents"])
app.include_router(bookings.router,      prefix="/api/bookings",      tags=["bookings"])
app.include_router(analytics.router,     prefix="/api/analytics",     tags=["analytics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(websocket.router,     prefix="/ws",                tags=["websocket"])
app.include_router(test_call.router,     prefix="/api",               tags=["test"])
app.include_router(business_data.router, prefix="/api/business",      tags=["business"])
app.include_router(call_webhook.router,  prefix="/api",               tags=["webhook"])
app.include_router(campaigns.router,     prefix="/api/campaigns",     tags=["campaigns"])
app.include_router(voice_webhook.router, prefix="/api",               tags=["voice"])

# Global orchestrator instance — accessible from agents API
_orchestrator = None


def get_orchestrator():
    return _orchestrator


@app.on_event("startup")
async def startup():
    """Initialize DB, seed test data, and start the LangGraph Orchestrator."""
    global _orchestrator

    from app.database.base import init_db
    await init_db()
    await seed_test_lead()

    # Initialize RAG knowledge base in background
    try:
        from app.core.rag_knowledge_base import get_rag_knowledge_base
        rag = get_rag_knowledge_base()
        logger.info("✅ RAG knowledge base initialized")
    except Exception as e:
        logger.warning("⚠️  RAG init failed (non-fatal): %s", e)

    # Start the LangGraph Orchestrator
    try:
        from app.database.base import async_session_factory
        from app.core.config import get_config
        from app.core.notification import NotificationService
        from app.orchestrator.graph_orchestrator import GraphOrchestrator

        config = get_config()
        notification = NotificationService()

        _orchestrator = GraphOrchestrator(
            session_factory=async_session_factory,
            notification_service=notification,
            config=config,
        )

        # Run orchestrator in background
        asyncio.create_task(_orchestrator.run())
        logger.info("✅ LangGraph Orchestrator started — real AI reasoning active")
        logger.info("   → LLM: Groq llama-3.3-70b (primary) / OpenAI GPT-4o-mini (fallback)")
        logger.info("   → RAG: ChromaDB with Pebble product knowledge")

    except Exception as e:
        logger.warning("⚠️  LangGraph Orchestrator failed to start: %s", e)
        logger.warning("    Falling back to legacy orchestrator...")
        try:
            from app.database.base import async_session_factory
            from app.core.config import get_config
            from app.core.notification import NotificationService
            from app.orchestrator.orchestrator import Orchestrator

            config = get_config()
            notification = NotificationService()
            task_queue = _build_task_queue()

            _orchestrator = Orchestrator(
                session_factory=async_session_factory,
                task_queue=task_queue,
                notification_service=notification,
                config=config,
            )
            asyncio.create_task(_orchestrator.run())
            logger.info("✅ Legacy orchestrator started as fallback")
        except Exception as e2:
            logger.warning("⚠️  All orchestrators failed: %s", e2)


@app.on_event("shutdown")
async def shutdown():
    """Stop the orchestrator gracefully."""
    global _orchestrator
    if _orchestrator:
        _orchestrator.stop()
        logger.info("Orchestrator stopped")


def _build_task_queue():
    """Build a TaskQueue — uses stub (direct execution) since Redis is optional."""
    logger.info("ℹ️  Using direct task execution (no Redis required)")
    return _StubTaskQueue()


class _StubTaskQueue:
    """Stub TaskQueue that executes agent tasks directly (no Redis needed)."""

    def enqueue(self, agent_type, action, lead_id, payload, priority=5, eta=None):
        import uuid
        task_id = str(uuid.uuid4())
        # Fire-and-forget: run the agent action in background
        asyncio.create_task(
            _execute_agent_action(agent_type, action, lead_id, payload)
        )
        logger.info("StubQueue: dispatched %s/%s for lead %s", agent_type, action, lead_id)
        return task_id

    def cancel(self, task_id):
        return True

    def get_queue_depth(self, agent_type):
        return 0


async def _execute_agent_action(agent_type, action, lead_id, payload):
    """Execute an agent action directly (used when Redis/Celery not available)."""
    import uuid
    from app.database.base import async_session_factory
    from app.database.service import DatabaseService
    from app.models.enums import AgentType

    db = DatabaseService()

    try:
        async with async_session_factory() as session:
            lead = await db.get_lead(session, lead_id if isinstance(lead_id, uuid.UUID) else uuid.UUID(str(lead_id)))
            if not lead:
                return

            if agent_type == AgentType.cold_calling and action == "call":
                await _run_cold_call(lead, session, db)

            elif agent_type == AgentType.auto_mail and action == "send_intro_email":
                await _run_auto_mail(lead, session, db, "intro")

            elif agent_type == AgentType.follow_up and action == "follow_up":
                await _run_follow_up(lead, session, db)

            await session.commit()

    except Exception as e:
        logger.error("Agent action failed (%s/%s): %s", agent_type, action, e)


async def _run_cold_call(lead, session, db):
    """Execute a cold call via Vapi."""
    import os
    from app.models.enums import LeadStatus
    from datetime import datetime, timezone

    vapi_key = os.environ.get("VAPI_API_KEY", "")
    if not vapi_key:
        logger.warning("Cold call skipped — VAPI_API_KEY not set")
        return

    try:
        from app.agents.cold_calling.vapi_telephony import VapiTelephonyAPI
        telephony = VapiTelephonyAPI()
        lead_name = f"{lead.first_name} {lead.last_name}".strip()
        company = lead.company or ""

        logger.info("🤖 Auto-calling lead %s (%s)", lead_name, lead.phone)
        telephony.initiate_call(lead.phone or "", lead_name, company)

        # Update lead
        await db.update_lead(session, lead.id,
            last_contacted_at=datetime.now(timezone.utc),
            call_attempts=lead.call_attempts + 1,
        )
        await db.update_lead_status(session, lead.id, LeadStatus.contacted)
        logger.info("✅ Auto-call placed for %s", lead_name)

    except Exception as e:
        logger.error("Cold call failed for lead %s: %s", lead.id, e)


async def _run_auto_mail(lead, session, db, template: str = "intro"):
    """Send an automated email via SendGrid."""
    import os, httpx
    from app.models.enums import LeadStatus
    from datetime import datetime, timezone

    sg_key = os.environ.get("SENDGRID_API_KEY", "")
    if not sg_key:
        logger.warning("Auto mail skipped — SENDGRID_API_KEY not set")
        return

    lead_name = f"{lead.first_name} {lead.last_name}".strip()
    first_name = lead.first_name or "there"

    payload = {
        "personalizations": [{"to": [{"email": lead.email, "name": lead_name}],
                               "subject": f"Quick question about your POS, {first_name}"}],
        "from": {"email": os.environ.get("FROM_EMAIL", "bhargav.gangula@growith.io"),
                 "name": os.environ.get("FROM_NAME", "Priya from Pebble")},
        "content": [{"type": "text/html", "value": f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <p>Hey {first_name},</p>
  <p>I'm Priya from Pebble — we help restaurants and retail stores with their POS, online ordering, loyalty, and AI, all from one platform.</p>
  <p>Quick question: are you happy with your current setup, or is there something you wish it did better?</p>
  <p>Would love to show you a quick 15-min demo — no commitment at all.</p>
  <p><a href="https://pebble.prod.xenvoice.com/book-a-demo" style="background:#6366f1;color:white;padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:bold;">Book a Free Demo →</a></p>
  <p>Priya<br><span style="color:#9ca3af;font-size:12px;">Pebble | customercare@pebbletab.com</span></p>
</div>"""}],
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code in (200, 202):
                await db.update_lead(session, lead.id,
                    last_contacted_at=datetime.now(timezone.utc),
                    email_attempts=lead.email_attempts + 1,
                )
                await db.update_lead_status(session, lead.id, LeadStatus.contacted)
                logger.info("✅ Auto email sent to %s", lead.email)
    except Exception as e:
        logger.error("Auto mail failed for %s: %s", lead.email, e)


async def _run_follow_up(lead, session, db):
    """Follow up via email (default channel)."""
    await _run_auto_mail(lead, session, db, template="follow_up")


async def seed_test_lead():
    """Add a test lead with your number if it doesn't exist."""
    from app.database.base import async_session_factory
    from app.database.service import DatabaseService
    from app.models.enums import LeadStatus

    db = DatabaseService()
    async with async_session_factory() as session:
        try:
            existing = await db.find_lead_by_phone(session, "+919876543210")
            if existing is None:
                await db.create_lead(session, {
                    "first_name": "Test",
                    "last_name": "Lead",
                    "email": "test@salesai.com",
                    "phone": "+919876543210",
                    "company": "SalesAI Test",
                    "status": LeadStatus.new,
                    "source": "manual",
                    "call_attempts": 0,
                    "email_attempts": 0,
                    "notes": "Test lead for AI calling",
                    "tags": ["test", "demo"],
                })
                await session.commit()
                print("✅ Test lead seeded!")
            else:
                print("✅ Test lead already exists")
        except Exception as e:
            print(f"⚠️  Seed skipped: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "orchestrator": "running" if _orchestrator and _orchestrator._running else "stopped"}
