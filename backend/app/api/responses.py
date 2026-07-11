from __future__ import annotations

from typing import Any, Dict

from fastapi.responses import JSONResponse


def ok(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data}


def err(code: str, message: str, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"success": False, "error": {"code": code, "message": message}},
    )
