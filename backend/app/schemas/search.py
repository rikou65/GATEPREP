from __future__ import annotations

from typing import Any, Dict, Optional

from app.schemas.common import OutModel


class SearchResultOut(OutModel):
    type: str
    id: str
    title: str
    subtitle: str = ""
    url: str
    excerpt: str = ""
    badge: Optional[str] = None
    metadata: Dict[str, Any] = {}
