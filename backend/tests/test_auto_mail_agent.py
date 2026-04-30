"""Unit and property tests for AutoMailAgent.

Tests cover Requirements 5.1–5.8 including:
- Email personalization completeness (Property 5)
- Unsubscribe suppression (Property 10)
- Retry logic with exponential backoff
- Webhook handlers for open/click/unsubscribe events
"""

import uuid
from datetime import datetime, timedelta

import pytest
from hypothesis import given, strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.auto_mail import (
    AutoMailAgent,
    EmailResult,
    StubEmailProvider,
    StubLLMService,
)
from backend.app.database.service import DatabaseService
from backend.app.models.email_template import EmailTemplate
from backend.app.models.enums import AgentType, LeadStatus
from backend.app.models.lead import Lead


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_service():
    """Return a DatabaseService instance."""
    return DatabaseService()


@pytest.fixture
def email_provider():
    """Return a StubEmailProvider instance."""
    return StubEmailProvider()


@pytest.fixture
def llm_service():
    """Return a StubLLMService instance."""
    return StubLLMService()


@pytest.fixture
def agent(db_service, email_provider, llm_service):
    """Return an AutoMailAgent instance with stub dependencies."""
    return AutoMailAgent(
        db_service=db_service,
        email_provider=email_provider,
        llm_service=llm_service,
        max_retries=3,
    )


@pytest.fixture
def sample_lead():
    """Return a sample Lead instance."""
    return Lead(
        id=uuid.uuid4(),
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        company="Acme Corp",
        status=LeadStatus.new,
        source="website",
        call_attempts=0,
        email_attempts=0,
    )


@pytest.fixture
def sample_template():
    """Return a sample EmailTemplate instance."""
    return EmailTemplate(
        id=uuid.uuid4(),
        name="intro_email",
        subject_template="Hello {first_name}!",
        body_template="Hi {first_name} {last_name},\n\nWe noticed you work at {company}. Let's connect!\n\nBest,\nSales Team",
        agent_type=AgentType.auto_mail,
        stage=LeadStatus.new,
        variables=["first_name", "last_name", "company"],
    )


# ============================================================================
# Unit Tests
# ============================================================================


def test_personalize_content_replaces_all_placeholders(agent, sample_lead, sample_template):
    """Test that personalize_content replaces all {variable} placeholders."""
    result = agent.personalize_content(sample_lead, sample_template)

    assert "{first_name}" not in result
    assert "{last_name}" not in result
    assert "{company}" not in result
    assert "John" in result
    assert "Doe" in result
    assert "Acme Corp" in result


def test_personalize_content_handles_missing_fields(agent, sample_template):
    """Test that personalize_content handles leads with missing fields."""
    lead = Lead(
        id=uuid.uuid4(),
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        company=None,  # Missing company
        status=LeadStatus.new,
        call_attempts=0,
        email_attempts=0,
    )

    result = agent.personalize_content(lead, sample_template)

    assert "{first_name}" not in result
    assert "{last_name}" not in result
    assert "{company}" not in result
    assert "Jane" in result
    assert "Smith" in result


@pytest.mark.asyncio
async def test_send_email_suppresses_unsubscribed_leads(
    agent, sample_lead, sample_template, db_service
):
    """Test that send_email suppresses emails to unsubscribed leads (Req 5.8)."""
    from backend.app.database.base import Base, engine

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create unsubscribed lead
        lead = await db_service.create_lead(
            session,
            {
                "first_name": "Unsubscribed",
                "last_name": "User",
                "email": "unsubscribed@example.com",
                "status": LeadStatus.unsubscribed,
                "call_attempts": 0,
                "email_attempts": 0,
            },
        )
        await session.commit()

        # Attempt to send email
        result = await agent.send_email(session, lead, sample_template)

        assert result.outcome == "suppressed"
        assert result.email_id is None

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_send_email_logs_interaction(agent, sample_lead, sample_template, db_service):
    """Test that send_email logs to InteractionLog (Req 5.3)."""
    from backend.app.database.base import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create lead
        lead = await db_service.create_lead(
            session,
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "status": LeadStatus.new,
                "call_attempts": 0,
                "email_attempts": 0,
            },
        )
        await session.commit()

        # Send email
        result = await agent.send_email(session, lead, sample_template)
        await session.commit()

        assert result.outcome == "sent"
        assert result.email_id is not None

        # Verify interaction log
        interactions = await db_service.get_interactions_for_lead(session, lead.id)
        assert len(interactions) == 1
        assert interactions[0].agent_type == AgentType.auto_mail
        assert interactions[0].outcome == "sent"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_send_email_retries_on_failure(agent, sample_lead, sample_template, db_service):
    """Test that send_email retries with exponential backoff on failure (Req 5.7)."""
    from backend.app.database.base import Base, engine

    # Create failing email provider
    failing_provider = StubEmailProvider(fail=True)
    agent_with_failing_provider = AutoMailAgent(
        db_service=db_service,
        email_provider=failing_provider,
        llm_service=StubLLMService(),
        max_retries=3,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create lead
        lead = await db_service.create_lead(
            session,
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "status": LeadStatus.new,
                "call_attempts": 0,
                "email_attempts": 0,
            },
        )
        await session.commit()

        # Send email (should fail after retries)
        result = await agent_with_failing_provider.send_email(session, lead, sample_template)

        assert result.outcome == "failed"
        assert result.error is not None

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_schedule_email_creates_scheduled_send(
    agent, sample_lead, sample_template, db_service
):
    """Test that schedule_email creates a deferred send."""
    from backend.app.database.base import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create lead
        lead = await db_service.create_lead(
            session,
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "status": LeadStatus.new,
                "call_attempts": 0,
                "email_attempts": 0,
            },
        )
        await session.commit()

        # Schedule email
        send_at = datetime.utcnow() + timedelta(hours=24)
        result = await agent.schedule_email(session, lead, sample_template, send_at)
        await session.commit()

        assert result.outcome == "scheduled"
        assert result.email_id is not None

        # Verify scheduled email in provider
        assert len(agent.email_provider.scheduled) == 1
        assert agent.email_provider.scheduled[0]["to"] == lead.email

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_schedule_email_suppresses_unsubscribed(
    agent, sample_lead, sample_template, db_service
):
    """Test that schedule_email suppresses unsubscribed leads."""
    from backend.app.database.base import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create unsubscribed lead
        lead = await db_service.create_lead(
            session,
            {
                "first_name": "Unsubscribed",
                "last_name": "User",
                "email": "unsubscribed@example.com",
                "status": LeadStatus.unsubscribed,
                "call_attempts": 0,
                "email_attempts": 0,
            },
        )
        await session.commit()

        # Attempt to schedule email
        send_at = datetime.utcnow() + timedelta(hours=24)
        result = await agent.schedule_email(session, lead, sample_template, send_at)

        assert result.outcome == "suppressed"
        assert len(agent.email_provider.scheduled) == 0

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_handle_unsubscribe_webhook_updates_status(agent, sample_lead, db_service):
    """Test that handle_unsubscribe_webhook updates lead status (Req 5.6)."""
    from backend.app.database.base import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Create lead
        lead = await db_service.create_lead(
            session,
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "status": LeadStatus.contacted,
                "call_attempts": 0,
                "email_attempts": 0,
            },
        )
        await session.commit()

        # Handle unsubscribe webhook
        await agent.handle_unsubscribe_webhook(session, lead.id, lead.email)
        await session.commit()

        # Verify status updated
        updated_lead = await db_service.get_lead(session, lead.id)
        assert updated_lead.status == LeadStatus.unsubscribed

        # Verify interaction log
        interactions = await db_service.get_interactions_for_lead(session, lead.id)
        assert len(interactions) == 1
        assert interactions[0].outcome == "unsubscribed"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ============================================================================
# Property-Based Tests
# ============================================================================


# Strategy for generating Lead-like objects
lead_strategy = st.builds(
    Lead,
    id=st.just(uuid.uuid4()),
    first_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))),
    last_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll"))),
    email=st.emails(),
    phone=st.one_of(st.none(), st.text(min_size=10, max_size=15, alphabet="0123456789+")),
    company=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    status=st.sampled_from(list(LeadStatus)),
    source=st.one_of(st.none(), st.just("website")),
    call_attempts=st.integers(min_value=0, max_value=10),
    email_attempts=st.integers(min_value=0, max_value=10),
)


# Strategy for generating EmailTemplate-like objects
template_strategy = st.builds(
    EmailTemplate,
    id=st.just(uuid.uuid4()),
    name=st.text(min_size=1, max_size=50),
    subject_template=st.text(min_size=1, max_size=100),
    body_template=st.text(min_size=10, max_size=500).map(
        lambda t: f"Hi {{first_name}} {{last_name}},\n\n{t}\n\nFrom {{company}}"
    ),
    agent_type=st.just(AgentType.auto_mail),
    stage=st.one_of(st.none(), st.sampled_from(list(LeadStatus))),
    variables=st.just(["first_name", "last_name", "company", "email"]),
)


@given(lead=lead_strategy, template=template_strategy)
def test_property_5_email_personalization_completeness(lead, template):
    """**Validates: Requirements 5.1, 5.2**

    Property 5: Email Personalization Completeness

    For any valid Lead and EmailTemplate, personalize_content must:
    1. Return a non-empty string
    2. Contain no unresolved {variable} placeholders
    """
    agent = AutoMailAgent(
        db_service=DatabaseService(),
        email_provider=StubEmailProvider(),
        llm_service=StubLLMService(),
    )

    result = agent.personalize_content(lead, template)

    # Assert non-empty
    assert len(result) > 0, "Personalized content must be non-empty"

    # Assert no unresolved placeholders
    import re
    unresolved = re.findall(r'\{(\w+)\}', result)
    assert len(unresolved) == 0, f"Found unresolved placeholders: {unresolved}"


@given(lead=lead_strategy.filter(lambda l: l.status == LeadStatus.unsubscribed), template=template_strategy)
@pytest.mark.asyncio
async def test_property_10_unsubscribe_suppression(lead, template):
    """**Validates: Requirements 5.8, 8.3**

    Property 10: Unsubscribe Suppression

    For any lead with status=unsubscribed and any template,
    send_email must never dispatch (returns outcome='suppressed').
    """
    from backend.app.database.base import Base, engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    db_service = DatabaseService()
    email_provider = StubEmailProvider()
    agent = AutoMailAgent(
        db_service=db_service,
        email_provider=email_provider,
        llm_service=StubLLMService(),
    )

    async with AsyncSession(engine) as session:
        # Create the lead in the database
        created_lead = await db_service.create_lead(
            session,
            {
                "first_name": lead.first_name,
                "last_name": lead.last_name,
                "email": lead.email,
                "phone": lead.phone,
                "company": lead.company,
                "status": LeadStatus.unsubscribed,
                "source": lead.source,
                "call_attempts": lead.call_attempts,
                "email_attempts": lead.email_attempts,
            },
        )
        await session.commit()

        # Attempt to send email
        result = await agent.send_email(session, created_lead, template)

        # Assert suppressed
        assert result.outcome == "suppressed", "Email to unsubscribed lead must be suppressed"
        assert len(email_provider.sent) == 0, "No email should be dispatched to unsubscribed lead"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
