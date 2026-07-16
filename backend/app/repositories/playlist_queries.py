from __future__ import annotations

from typing import Any, Dict, Optional


def playlist_summary_pipeline(
    user_id: str, subject_id: Optional[str] = None
) -> list[Dict[str, Any]]:
    match_q: Dict[str, Any] = {"user_id": user_id}
    if subject_id:
        match_q["subject_id"] = subject_id

    return [
        {"$match": match_q},
        {"$sort": {"created_at": -1}},
        {
            "$lookup": {
                "from": "videos",
                "localField": "playlist_id",
                "foreignField": "playlist_id",
                "as": "vids",
            }
        },
        {
            "$lookup": {
                "from": "video_progress",
                "let": {"uid": user_id, "vid_ids": "$vids.video_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$user_id", "$$uid"]},
                                    {"$in": ["$video_id", "$$vid_ids"]},
                                ]
                            }
                        }
                    }
                ],
                "as": "prog",
            }
        },
    ]
