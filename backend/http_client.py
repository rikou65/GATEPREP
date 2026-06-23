import asyncio
from typing import Any, Dict, Optional

import httpx


DEFAULT_TIMEOUT = 15.0


async def async_get(url: str, params: Optional[Dict[str, Any]] = None,
                    headers: Optional[Dict[str, str]] = None,
                    timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Perform an async GET with simple retry on network errors / 5xx."""
    backoff = 0.5
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, params=params, headers=headers)
            if resp.status_code >= 500 and attempt < 2:
                await asyncio.sleep(backoff * (attempt + 1))
                continue
            return resp
        except httpx.RequestError:
            if attempt == 2:
                raise
            await asyncio.sleep(backoff * (attempt + 1))


async def async_post(url: str, params: Optional[Dict[str, Any]] = None,
                     data: Optional[Any] = None, json: Optional[Any] = None,
                     headers: Optional[Dict[str, str]] = None,
                     timeout: float = DEFAULT_TIMEOUT) -> httpx.Response:
    """Perform an async POST with simple retry on network errors / 5xx."""
    backoff = 0.5
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, params=params, data=data, json=json, headers=headers)
            if resp.status_code >= 500 and attempt < 2:
                await asyncio.sleep(backoff * (attempt + 1))
                continue
            return resp
        except httpx.RequestError:
            if attempt == 2:
                raise
            await asyncio.sleep(backoff * (attempt + 1))
