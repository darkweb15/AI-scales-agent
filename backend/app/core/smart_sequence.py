"""Smart Sequence Engine — Email first, then call openers.

Flow:
1. Send Pebble intro email to all leads
2. Wait 24-48 hours
3. Who opened? → Call them FIRST (warm leads, 3x conversion)
4. Who didn't open? → Call them too (cold outreach)
5. Who answered + interested? → Book demo automatically
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)

# Pebble email template
PEBBLE_EMAIL_SUBJECT = "Quick question about {business_name}'s operations"

PEBBLE_EMAIL_HTML = """
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">

<p>Hi {first_name},</p>

<p>I noticed <strong>{business_name}</strong> and wanted to reach out quickly.</p>

<p>We work with restaurants and retail stores to help them:</p>
<ul>
  <li>✅ <strong>Never miss a call</strong> — AI answers every phone call, takes orders automatically</li>
  <li>✅ <strong>Stop paying 30% to DoorDash</strong> — let customers order directly from you</li>
  <li>✅ <strong>Bring customers back</strong> — automated loyalty + marketing campaigns</li>
  <li>✅ <strong>One platform</strong> — POS, ordering, loyalty, reviews, and AI all in one</li>
</ul>

<p>Most of our customers see results in the first 30 days — more orders, fewer missed calls, and customers coming back more often.</p>

<p>Would a quick 15-minute demo make sense? No commitment — just to see if it's a fit for {business_name}.</p>

<p>
  <a href="https://pebble.prod.xenvoice.com/book-a-demo" 
     style="background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">
    Book a Free Demo →
  </a>
</p>

<p>Or just reply to this email and I'll set something up.</p>

<p>Best,<br>
<strong>Priya</strong><br>
Sales Team, Pebble<br>
📞 (469)-310-7731<br>
🌐 <a href="https://pebble.prod.xenvoice.com">pebble.prod.xenvoice.com</a>
</p>

<p style="font-size: 11px; color: #999; margin-top: 30px;">
  You're receiving this because your business was identified as a potential fit for Pebble POS. 
  <a href="mailto:customercare@pebbletab.com?subject=Unsubscribe">Unsubscribe</a>
</p>

</body>
</html>
"""


class SmartSequenceEngine:
    """Orchestrates the email → call sequence for maximum conversion."""

    def __init__(self) -> None:
        from app.agents.auto_mail.sendgrid_provider import SendGridProvider
        self._email = SendGridProvider()

    def send_intro_email(self, lead: dict) -> dict:
        """Send personalized Pebble intro email to a lead."""
        first_name = lead.get("first_name", "there")
        business_name = lead.get("company") or lead.get("name") or "your business"
        to_email = lead.get("email", "")

        if not to_email or "business.com" in to_email:
            # Skip placeholder emails
            return {"success": False, "reason": "no_real_email"}

        subject = PEBBLE_EMAIL_SUBJECT.format(business_name=business_name)
        body = PEBBLE_EMAIL_HTML.format(
            first_name=first_name,
            business_name=business_name,
        )

        email_id = str(uuid.uuid4())
        result = self._email.send(
            to=to_email,
            subject=subject,
            body=body,
            email_id=email_id,
        )

        return {
            "success": result.success,
            "email_id": email_id,
            "to": to_email,
            "error": result.error,
        }

    def get_email_template_preview(self, business_name: str = "Your Restaurant") -> str:
        """Return a preview of the email template."""
        return PEBBLE_EMAIL_HTML.format(
            first_name="Owner",
            business_name=business_name,
        )
