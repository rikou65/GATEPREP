import os
from typing import Dict


BASE_URL: str = os.environ.get(
    "VITE_BACKEND_URL", "http://localhost:8001"
).rstrip("/")
API: str = f"{BASE_URL}/api"


def json_session_headers(session_token: str) -> Dict[str, str]:
    return {
        "Cookie": f"session_token={session_token}",
        "Content-Type": "application/json",
    }
