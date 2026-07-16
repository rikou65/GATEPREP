"""At-rest encryption for stored OAuth tokens (Drive + YouTube).

When ``TOKEN_ENCRYPTION_KEY`` is configured (a 32-byte base64-url Fernet key),
secret fields are encrypted on write and decrypted on read at the repository
boundary. When the key is absent, values pass through unchanged so the app
remains functional in local development. This matches the graceful-degrade
pattern used for Supabase config.
"""

from __future__ import annotations

from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.logging import logger

_fernet: Optional[Fernet] = None


def configure_token_encryption_key(key: str) -> None:
    """Initialise the Fernet cipher from ``TOKEN_ENCRYPTION_KEY``.

    A bad or empty key disables encryption (with a warning when non-empty but
    invalid) so startup never crashes solely because of a misconfigured key.
    """
    global _fernet
    if not key:
        _fernet = None
        return
    try:
        _fernet = Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as exc:
        logger.warning(
            f"Invalid TOKEN_ENCRYPTION_KEY, token encryption disabled: {exc}"
        )
        _fernet = None


def is_encryption_enabled() -> bool:
    return _fernet is not None


def encrypt_secret(value: Optional[str]) -> Optional[str]:
    """Encrypt a secret string for storage. Passes through when disabled."""
    if value is None or _fernet is None:
        return value
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: Optional[str]) -> Optional[str]:
    """Decrypt a secret string read from storage.

    Passes through ``None`` and, when disabled, any value. When enabled but
    the value is not a valid Fernet token (i.e. legacy plaintext written
    before encryption was turned on), the original value is returned so
    existing tokens keep working until they are next refreshed.
    """
    if value is None or _fernet is None:
        return value
    try:
        return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value
