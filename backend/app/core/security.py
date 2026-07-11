from __future__ import annotations

"""Security helpers.

Password auth is delegated to Supabase. These functions intentionally fail if
used so no future code accidentally accepts plaintext passwords locally.
"""


def verify_password(plain: str, hashed: str) -> bool:
    raise NotImplementedError("Local password verification is not supported")


def hash_password(password: str) -> str:
    raise NotImplementedError("Local password hashing is not supported")
