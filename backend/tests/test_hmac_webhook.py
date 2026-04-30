"""Property test for HMAC webhook signature verification.

**Property 12: HMAC Webhook Rejection**
**Validates: Requirements 8.6**

Uses Hypothesis to generate arbitrary payloads with invalid/missing
signatures and asserts all are rejected, while the correctly computed
signature is always accepted.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_lib

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.security import verify_webhook_signature

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_signature(payload: bytes, secret: str) -> str:
    """Compute the correct sha256= signature for a payload."""
    digest = hmac_lib.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Arbitrary binary payloads (non-empty to keep tests meaningful)
payloads = st.binary(min_size=1, max_size=4096)

# Arbitrary secrets (non-empty printable ASCII)
secrets = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=8,
    max_size=64,
)

# Arbitrary hex strings that are NOT the correct digest
hex_chars = st.text(alphabet="0123456789abcdef", min_size=1, max_size=128)


# ---------------------------------------------------------------------------
# Property: valid signature is always accepted
# ---------------------------------------------------------------------------


@given(payload=payloads, secret=secrets)
@settings(max_examples=200)
def test_valid_signature_always_accepted(payload: bytes, secret: str) -> None:
    """For any payload and secret, the correctly computed signature is accepted."""
    sig = _make_valid_signature(payload, secret)
    assert verify_webhook_signature(payload, sig, secret) is True


# ---------------------------------------------------------------------------
# Property: wrong secret is always rejected
# ---------------------------------------------------------------------------


@given(payload=payloads, correct_secret=secrets, wrong_secret=secrets)
@settings(max_examples=200)
def test_wrong_secret_always_rejected(
    payload: bytes, correct_secret: str, wrong_secret: str
) -> None:
    """A signature computed with a different secret must be rejected."""
    if correct_secret == wrong_secret:
        return  # skip degenerate case where secrets happen to match

    sig = _make_valid_signature(payload, correct_secret)
    assert verify_webhook_signature(payload, sig, wrong_secret) is False


# ---------------------------------------------------------------------------
# Property: tampered payload is always rejected
# ---------------------------------------------------------------------------


@given(payload=payloads, secret=secrets, extra_byte=st.integers(min_value=0, max_value=255))
@settings(max_examples=200)
def test_tampered_payload_always_rejected(
    payload: bytes, secret: str, extra_byte: int
) -> None:
    """Appending a byte to the payload invalidates the signature."""
    sig = _make_valid_signature(payload, secret)
    tampered = payload + bytes([extra_byte])
    assert verify_webhook_signature(tampered, sig, secret) is False


# ---------------------------------------------------------------------------
# Property: arbitrary invalid signatures are always rejected
# ---------------------------------------------------------------------------


@given(payload=payloads, secret=secrets, bad_hex=hex_chars)
@settings(max_examples=200)
def test_arbitrary_invalid_signature_rejected(
    payload: bytes, secret: str, bad_hex: str
) -> None:
    """A sha256= header with an arbitrary hex value is rejected unless it
    happens to be the correct digest (astronomically unlikely)."""
    correct_hex = hmac_lib.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    if bad_hex == correct_hex:
        return  # skip the one-in-2^256 collision

    sig = f"sha256={bad_hex}"
    assert verify_webhook_signature(payload, sig, secret) is False


# ---------------------------------------------------------------------------
# Edge-case examples
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "signature_header",
    [
        "",                          # empty string
        "sha256=",                   # missing hex
        "sha256=abc",                # truncated hex
        "md5=abc123",                # wrong prefix
        "abc123",                    # no prefix at all
        "SHA256=abc123",             # wrong case prefix
    ],
)
def test_malformed_signature_headers_rejected(signature_header: str) -> None:
    """Malformed or missing signature headers must always be rejected."""
    payload = b"test payload"
    secret = "supersecret"
    assert verify_webhook_signature(payload, signature_header, secret) is False


def test_empty_secret_rejected() -> None:
    """An empty secret must always be rejected."""
    payload = b"test payload"
    sig = _make_valid_signature(payload, "some_secret")
    assert verify_webhook_signature(payload, sig, "") is False


def test_flipped_bit_rejected() -> None:
    """Flipping a single bit in the signature hex must be rejected."""
    payload = b"hello world"
    secret = "my_secret"
    sig = _make_valid_signature(payload, secret)
    # Flip the last hex character
    prefix, hex_part = sig.split("=", 1)
    flipped_last = hex_part[:-1] + ("0" if hex_part[-1] != "0" else "1")
    tampered_sig = f"{prefix}={flipped_last}"
    assert verify_webhook_signature(payload, tampered_sig, secret) is False


def test_correct_signature_accepted_example() -> None:
    """Concrete example: known payload + secret produces the expected digest."""
    payload = b"{'event': 'email.opened', 'lead_id': '123'}"
    secret = "webhook_secret_key"
    sig = _make_valid_signature(payload, secret)
    assert verify_webhook_signature(payload, sig, secret) is True
