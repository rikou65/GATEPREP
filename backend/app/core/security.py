"""Security helpers.

Password auth is delegated to Supabase. These functions intentionally fail if
used so no future code accidentally accepts plaintext passwords locally.

Session-token hashing is handled locally so session tokens are never stored
in plaintext in ``user_sessions`` (a DB read alone cannot hijack a session).
"""

from __future__ import annotations

import hashlib
import hmac

_session_secret: str = ""


def configure_session_secret(secret: str) -> None:
    """Set the HMAC key used by :func:`hash_session_token`.

    Called once at startup from the app lifespan. Falls back to a fixed
    string when unset so the app still boots, but production deployments
    should always provide ``JWT_SECRET``.
    """
    global _session_secret
    _session_secret = secret or ""


def hash_session_token(token: str) -> str:
    """Return the HMAC-SHA256 digest of a session token for storage/lookup.

    Using HMAC (rather than plain SHA-256) means a database dump alone is
    not enough to forge a valid token-hash — the attacker also needs the
    server secret.
    """
    key = (_session_secret or "gateprep-session-fallback").encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    raise NotImplementedError("Local password verification is not supported")


def hash_password(password: str) -> str:
    raise NotImplementedError("Local password hashing is not supported")
