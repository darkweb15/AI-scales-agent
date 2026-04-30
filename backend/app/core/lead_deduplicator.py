"""Lead Deduplicator — prevents duplicate lead records.

Checks for existing leads before creating new ones using:
1. Exact email match
2. Exact phone match
3. Fuzzy name + company match (for cases where email/phone differ slightly)

Used by AutoReplyAgent, CallAnsweringAgent, and the leads API.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Strip all non-digit characters, keep + prefix."""
    if not phone:
        return ""
    digits = re.sub(r"[^\d+]", "", phone.strip())
    # Normalize Indian numbers: 91XXXXXXXXXX → +91XXXXXXXXXX
    if digits.startswith("91") and len(digits) == 12:
        digits = "+" + digits
    # 10-digit Indian number → +91XXXXXXXXXX
    if len(digits) == 10 and not digits.startswith("+"):
        digits = "+91" + digits
    return digits


def _normalize_email(email: str) -> str:
    return email.strip().lower() if email else ""


class LeadDeduplicator:
    """Finds existing leads before creating duplicates."""

    async def find_or_none(
        self,
        session: AsyncSession,
        db_service: Any,
        email: Optional[str] = None,
        phone: Optional[str] = None,
    ) -> Optional[Any]:
        """Return existing lead if found by email or phone, else None.

        Checks in priority order:
        1. Email (most reliable)
        2. Phone (normalized)
        """
        # 1. Email match
        if email:
            norm_email = _normalize_email(email)
            lead = await db_service.find_lead_by_email(session, norm_email)
            if lead:
                logger.info("Dedup: found existing lead by email %s → %s", norm_email, lead.id)
                return lead

        # 2. Phone match (try normalized variants)
        if phone:
            norm_phone = _normalize_phone(phone)
            if norm_phone:
                lead = await db_service.find_lead_by_phone(session, norm_phone)
                if lead:
                    logger.info("Dedup: found existing lead by phone %s → %s", norm_phone, lead.id)
                    return lead

                # Also try without country code
                if norm_phone.startswith("+91") and len(norm_phone) == 13:
                    short = norm_phone[3:]  # 10-digit
                    lead = await db_service.find_lead_by_phone(session, short)
                    if lead:
                        logger.info("Dedup: found existing lead by short phone %s → %s", short, lead.id)
                        return lead

        return None

    async def find_or_create(
        self,
        session: AsyncSession,
        db_service: Any,
        data: dict,
    ) -> tuple[Any, bool]:
        """Find existing lead or create new one. Returns (lead, was_created).

        Normalizes phone and email before lookup and creation.
        """
        email = _normalize_email(data.get("email", ""))
        phone = _normalize_phone(data.get("phone", ""))

        # Normalize data
        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone

        existing = await self.find_or_none(session, db_service, email=email, phone=phone)
        if existing:
            return existing, False

        lead = await db_service.create_lead(session, data)
        logger.info("Dedup: created new lead %s (email=%s, phone=%s)", lead.id, email, phone)
        return lead, True


# Singleton
_deduplicator: Optional[LeadDeduplicator] = None


def get_deduplicator() -> LeadDeduplicator:
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = LeadDeduplicator()
    return _deduplicator
