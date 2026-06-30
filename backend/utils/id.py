"""ID generation helpers for GATEPREP."""
import uuid


def new_id(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"
