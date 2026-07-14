from __future__ import annotations

from pydantic import BaseModel, Field


class ApproveSpecificRequest(BaseModel):
    staging_id: str = Field(min_length=1, max_length=50)