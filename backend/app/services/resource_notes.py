from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.repositories.resources import ResourceNoteRepository, ResourceRepository


def normalize_pages(raw) -> List[Dict[str, Any]]:
    seen: Dict[int, str] = {}
    for item in raw or []:
        try:
            if isinstance(item, dict):
                page = int(item.get("page", 0))
                label = str(item.get("label", "") or "")
            else:
                page = int(item)
                label = ""
        except (ValueError, TypeError):
            continue
        if page <= 0:
            continue
        if page in seen and not label:
            continue
        seen[page] = label
    return [{"page": page, "label": seen[page]} for page in sorted(seen.keys())]


def resource_notes_view(doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not doc:
        return {"content": "", "important_pages": []}
    return {
        "content": doc.get("content", "") or "",
        "important_pages": normalize_pages(doc.get("important_pages")),
        "updated_at": doc.get("updated_at"),
    }


class ResourceNotesService:
    def __init__(
        self,
        res_repo: ResourceRepository,
        note_repo: ResourceNoteRepository,
    ):
        self._res_repo = res_repo
        self._note_repo = note_repo

    async def get_notes(
        self, resource_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        doc = await self._note_repo.find(resource_id, user_id)
        return resource_notes_view(doc)

    async def save_notes(
        self,
        resource_id: str,
        user_id: str,
        content: Optional[str],
        important_pages: Optional[list],
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        data = {}
        if content is not None:
            data["content"] = content
        if important_pages is not None:
            data["important_pages"] = normalize_pages(important_pages)
        await self._note_repo.upsert(resource_id, user_id, data)
        doc = await self._note_repo.find(resource_id, user_id)
        return resource_notes_view(doc)

    async def toggle_page(
        self, user_id: str, resource_id: str, page: int, label: str = ""
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        existing = await self._note_repo.find(resource_id, user_id) or {}
        current = {
            item["page"]: item["label"]
            for item in normalize_pages(existing.get("important_pages"))
        }
        if page in current:
            current.pop(page, None)
            action = "removed"
        else:
            current[page] = (label or "")[:200]
            action = "added"
        new_pages = [
            {"page": page_number, "label": current[page_number]}
            for page_number in sorted(current.keys())
        ]
        await self._note_repo.upsert(
            resource_id,
            user_id,
            {"important_pages": new_pages, "content": existing.get("content", "")},
        )
        return {"important_pages": new_pages, "action": action, "page": page}

    async def set_page_label(
        self, user_id: str, resource_id: str, page: int, label: str
    ) -> Optional[Dict[str, Any]]:
        res = await self._res_repo.find_by_id(resource_id, user_id)
        if not res:
            return None
        existing = await self._note_repo.find(resource_id, user_id) or {}
        current = {
            item["page"]: item["label"]
            for item in normalize_pages(existing.get("important_pages"))
        }
        if page not in current:
            return {"error": "not_flagged"}
        current[page] = (label or "")[:200]
        new_pages = [
            {"page": page_number, "label": current[page_number]}
            for page_number in sorted(current.keys())
        ]
        await self._note_repo.upsert(
            resource_id,
            user_id,
            {"important_pages": new_pages},
        )
        return {
            "important_pages": new_pages,
            "page": page,
            "label": current[page],
        }
