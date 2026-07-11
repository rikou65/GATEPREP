from __future__ import annotations

from typing import Any, Dict, List, Optional


class AnalyticsRepository:
    def __init__(self, db):
        self._db = db

    async def get_latest_attempt_stats(
        self, user_id: str, attempt_collection: str, id_field: str
    ) -> Dict[str, Any]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }},
            {"$group": {
                "_id": None,
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }},
            {"$project": {"_id": 0}},
        ]
        cursor = self._db[attempt_collection].aggregate(pipeline)
        res = await cursor.to_list(1)
        if not res:
            return {"solved": 0, "accuracy": 0.0}
        stats = res[0]
        solved = stats["solved"]
        accuracy = round(stats["correct"] / solved * 100, 1) if solved > 0 else 0.0
        return {"solved": solved, "accuracy": accuracy}

    async def get_subject_breakdown(
        self, user_id: str, attempt_collection: str, item_collection: str, id_field: str
    ) -> Dict[str, Dict[str, Any]]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }},
            {"$lookup": {
                "from": item_collection,
                "localField": "_id",
                "foreignField": id_field,
                "as": "item",
            }},
            {"$unwind": "$item"},
            {"$group": {
                "_id": "$item.subject_id",
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }},
        ]
        rows = await self._db[attempt_collection].aggregate(pipeline).to_list(None)
        return {r["_id"]: {"solved": r["solved"], "correct": r["correct"]} for r in rows if r["_id"]}

    async def get_topic_breakdown(
        self, user_id: str, attempt_collection: str, item_collection: str, id_field: str, subject_id: str
    ) -> Dict[str, Dict[str, Any]]:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {
                "_id": f"${id_field}",
                "is_correct": {"$first": "$is_correct"},
            }},
            {"$lookup": {
                "from": item_collection,
                "localField": "_id",
                "foreignField": id_field,
                "as": "item",
            }},
            {"$unwind": "$item"},
            {"$match": {"item.subject_id": subject_id}},
            {"$group": {
                "_id": "$item.topic_id",
                "solved": {"$sum": 1},
                "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}},
            }},
        ]
        rows = await self._db[attempt_collection].aggregate(pipeline).to_list(None)
        return {r["_id"]: {"solved": r["solved"], "correct": r["correct"]} for r in rows if r["_id"]}

    async def count(self, collection: str, filter_dict: Dict[str, Any]) -> int:
        return await self._db[collection].count_documents(filter_dict)

    async def aggregate(self, collection: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return await self._db[collection].aggregate(pipeline).to_list(None)

    async def find_all(self, collection: str, filter_dict: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> list:
        cursor = self._db[collection].find(filter_dict, projection or {"_id": 0})
        return await cursor.to_list(None)

    async def find_one(self, collection: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return await self._db[collection].find_one(filter_dict, {"_id": 0})

    def aggregate_cursor(self, collection: str, pipeline: List[Dict[str, Any]]) -> Any:
        return self._db[collection].aggregate(pipeline)
