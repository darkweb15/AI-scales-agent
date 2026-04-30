"""HMAC webhook signature verification (Requirement 8.6).

Inbound webhook endpoints must call ``require_valid_webhook_signature`` as a
FastAPI dependency to reject requests with invalid or missing signatures.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status


# ---------------------------------------------------------------------------
# Core verification function (pure — no FastAPI dependency)
# ---------------------------------------------------------------------------


def verify_webhook_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """Return ``True`` iff ``signature_header`` is the valid HMAC-SHA256
    signature for ``payload`` using ``secret``.

    The expected format of ``signature_header`` is ``sha256=<hex_digest>``.
    Comparison is performed with :func:`hmac.compare_digest` to prevent
    timing-based attacks.

    Parameters
    ----------
    payload:
        The raw request body bytes.
    signature_header:
        The value of the ``X-Hub-Signature-256`` (or equivalent) header.
    secret:
        The shared HMAC secret string.

    Returns
    -------
    bool
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    if not signature_header or not secret:
        return False

    # Expect "sha256=<hex>"
    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    provided_hex = signature_header[len(prefix):]

    # Compute expected digest
    expected_hex = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    return hmac.compare_digest(expected_hex, provided_hex)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def require_valid_webhook_signature(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(default=None),
) -> None:
    """FastAPI dependency that raises HTTP 401 for invalid webhook signatures.

    Reads the raw request body and the ``X-Hub-Signature-256`` header, then
    calls :func:`verify_webhook_signature`.  Raises
    :class:`fastapi.HTTPException` with status 401 if the signature is
    missing or invalid.

    Usage::

        @router.post("/webhook/email")
        async def email_webhook(
            _: None = Depends(require_valid_webhook_signature),
        ):
            ...
    """
    from ..core.config import get_config  # local import to avoid circular deps

    body = await request.body()
    config = get_config()

    if not verify_webhook_signature(
        payload=body,
        signature_header=x_hub_signature_256 or "",
        secret=config.hmac_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook signature.",
        )
