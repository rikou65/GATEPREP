from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from shared import db, err, get_current_user, ok

router = APIRouter()


async def _get_latest_attempt_stats(uid: str, collection: str, id_field: str, filter_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get solved count and accuracy based on latest attempts per item."""
    match = {"user_id": uid}
    if filter_dict:
        # If we have a filter (like subject_id), we need to lookup the item first or filter by ID list
        # To keep it efficient, we assume the items are already filtered if IDs are provided
        pass

    pipeline = [
        {"$match": match},
        {"$sort": {"attempted_at": -1}},
        {"$group": {
            "_id": f"${id_field}",
            "is_correct": {"$first": "$is_correct"}
        }},
        {"$group": {
            "_id": None,
            "solved": {"$sum": 1},
            "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}
        }},
        {"$project": {"_id": 0}}
    ]
    cursor = db[collection].aggregate(pipeline)
    res = await cursor.to_list(1)
    if not res:
        return {"solved": 0, "accuracy": 0.0}
    
    stats = res[0]
    solved = stats["solved"]
    accuracy = round(stats["correct"] / solved * 100, 1) if solved > 0 else 0.0
    return {"solved": solved, "accuracy": accuracy}


async def _get_subject_breakdown(uid: str, attempt_coll: str, item_coll: str, id_field: str) -> Dict[str, Dict[str, Any]]:
    """Get solved and correct counts grouped by subject_id."""
    pipeline = [
        {"$match": {"user_id": uid}},
        {"$sort": {"attempted_at": -1}},
        {"$group": {
            "_id": f"${id_field}",
            "is_correct": {"$first": "$is_correct"}
        }},
        {"$lookup": {
            "from": item_coll,
            "localField": "_id",
            "foreignField": id_field,
            "as": "item"
        }},
        {"$unwind": "$item"},
        {"$group": {
            "_id": "$item.subject_id",
            "solved": {"$sum": 1},
            "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}
        }}
    ]
    cursor = db[attempt_coll].aggregate(pipeline)
    rows = await cursor.to_list(None)
    return {r["_id"]: {"solved": r["solved"], "correct": r["correct"]} for r in rows if r["_id"]}


async def _get_topic_breakdown(uid: str, attempt_coll: str, item_coll: str, id_field: str, subject_id: str) -> Dict[str, Dict[str, Any]]:
    """Get solved and correct counts grouped by topic_id for a specific subject."""
    pipeline = [
        {"$match": {"user_id": uid}},
        {"$sort": {"attempted_at": -1}},
        {"$group": {
            "_id": f"${id_field}",
            "is_correct": {"$first": "$is_correct"}
        }},
        {"$lookup": {
            "from": item_coll,
            "localField": "_id",
            "foreignField": id_field,
            "as": "item"
        }},
        {"$unwind": "$item"},
        {"$match": {"item.subject_id": subject_id}},
        {"$group": {
            "_id": "$item.topic_id",
            "solved": {"$sum": 1},
            "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}
        }}
    ]
    cursor = db[attempt_coll].aggregate(pipeline)
    rows = await cursor.to_list(None)
    return {r["_id"]: {"solved": r["solved"], "correct": r["correct"]} for r in rows if r["_id"]}


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)) -> Dict[str, Any]:
    uid = user["user_id"]
    
    # 1. Summary Stats
    q_stats = await _get_latest_attempt_stats(uid, "question_attempts", "question_id")
    p_stats = await _get_latest_attempt_stats(uid, "pyq_attempts", "pyq_id")
    
    counts = {
        "playlists": await db.playlists.count_documents({"user_id": uid}),
        "videos_done": await db.video_progress.count_documents({"user_id": uid, "completed": True}),
        "mistakes": await db.mistakes.count_documents({"user_id": uid}),
        "resources": await db.resources.count_documents({"user_id": uid}),
    }
    
    summary = {
        "questions_solved": q_stats["solved"],
        "pyqs_solved": p_stats["solved"],
        "videos_completed": counts["videos_done"],
        "total_playlists": counts["playlists"],
        "question_accuracy": q_stats["accuracy"],
        "pyq_accuracy": p_stats["accuracy"],
        "total_mistakes": counts["mistakes"],
        "resources_uploaded": counts["resources"],
    }

    # 2. Subject Overview
    subjects = await db.subjects.find({}, {"_id": 0}).sort("order", 1).to_list(100)
    
    # Batch get totals per subject for this user
    q_totals = {r["_id"]: r["count"] async for r in db.questions.aggregate([
        {"$match": {"user_id": uid}},
        {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}}
    ])}
    p_totals = {r["_id"]: r["count"] async for r in db.pyqs.aggregate([
        {"$match": {"user_id": uid}},
        {"$group": {"_id": "$subject_id", "count": {"$sum": 1}}}
    ])}
    
    # Batch get user progress per subject
    q_progress = await _get_subject_breakdown(uid, "question_attempts", "questions", "question_id")
    p_progress = await _get_subject_breakdown(uid, "pyq_attempts", "pyqs", "pyq_id")
    
    overview = []
    for s in subjects:
        sid = s["subject_id"]
        
        # QB Stats
        qb_t = q_totals.get(sid, 0)
        qb_p = q_progress.get(sid, {"solved": 0, "correct": 0})
        qb_acc = round(qb_p["correct"] / qb_p["solved"] * 100, 1) if qb_p["solved"] > 0 else 0.0
        
        # PYQ Stats
        pyq_t = p_totals.get(sid, 0)
        pyq_p = p_progress.get(sid, {"solved": 0, "correct": 0})
        pyq_acc = round(pyq_p["correct"] / pyq_p["solved"] * 100, 1) if pyq_p["solved"] > 0 else 0.0
        
        overview.append({
            "subject": s,
            "qb": {"total": qb_t, "solved": qb_p["solved"], "remaining": qb_t - qb_p["solved"], "accuracy": qb_acc},
            "pyq": {"total": pyq_t, "solved": pyq_p["solved"], "remaining": pyq_t - pyq_p["solved"], "accuracy": pyq_acc}
        })

    # 3. Recent Activity (optimized & enriched)
    qa_pipeline = [
        {"$match": {"user_id": uid}},
        {"$sort": {"attempted_at": -1}},
        {"$limit": 10},
        {"$lookup": {
            "from": "questions",
            "localField": "question_id",
            "foreignField": "question_id",
            "as": "q"
        }},
        {"$unwind": {"path": "$q", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "subjects",
            "localField": "q.subject_id",
            "foreignField": "subject_id",
            "as": "subj"
        }},
        {"$lookup": {
            "from": "topics",
            "localField": "q.topic_id",
            "foreignField": "topic_id",
            "as": "top"
        }},
        {"$project": {
            "_id": 0,
            "attempt_id": 1, "question_id": 1, "is_correct": 1, "time_taken": 1, "attempted_at": 1,
            "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
            "topic_name": {"$arrayElemAt": ["$top.name", 0]},
            "question_type": "$q.question_type"
        }}
    ]
    pa_pipeline = [
        {"$match": {"user_id": uid}},
        {"$sort": {"attempted_at": -1}},
        {"$limit": 10},
        {"$lookup": {
            "from": "pyqs",
            "localField": "pyq_id",
            "foreignField": "pyq_id",
            "as": "q"
        }},
        {"$unwind": {"path": "$q", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {
            "from": "subjects",
            "localField": "q.subject_id",
            "foreignField": "subject_id",
            "as": "subj"
        }},
        {"$lookup": {
            "from": "topics",
            "localField": "q.topic_id",
            "foreignField": "topic_id",
            "as": "top"
        }},
        {"$project": {
            "_id": 0,
            "attempt_id": 1, "pyq_id": 1, "is_correct": 1, "time_taken": 1, "attempted_at": 1,
            "subject_name": {"$arrayElemAt": ["$subj.name", 0]},
            "topic_name": {"$arrayElemAt": ["$top.name", 0]},
            "question_type": "$q.question_type",
            "year": "$q.year"
        }}
    ]

    qa_recent = await db.question_attempts.aggregate(qa_pipeline).to_list(10)
    pa_recent = await db.pyq_attempts.aggregate(pa_pipeline).to_list(10)

    merged = [{"type": "question", **a} for a in qa_recent] + [{"type": "pyq", **a} for a in pa_recent]
    recent = sorted(merged, key=lambda x: x["attempted_at"], reverse=True)[:10]

    return ok({"summary": summary, "subjects": overview, "recent_activity": recent})


@router.get("/analytics/subject/{subject_id}")
async def subject_analytics(subject_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    uid = user["user_id"]
    topics = await db.topics.find({"subject_id": subject_id}, {"_id": 0}).sort("order", 1).to_list(200)
    
    # Batch totals per topic
    q_totals = {r["_id"]: r["count"] async for r in db.questions.aggregate([
        {"$match": {"subject_id": subject_id, "user_id": uid}},
        {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}}
    ])}
    p_totals = {r["_id"]: r["count"] async for r in db.pyqs.aggregate([
        {"$match": {"subject_id": subject_id, "user_id": uid}},
        {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}}
    ])}
    
    # Batch progress per topic
    q_progress = await _get_topic_breakdown(uid, "question_attempts", "questions", "question_id", subject_id)
    p_progress = await _get_topic_breakdown(uid, "pyq_attempts", "pyqs", "pyq_id", subject_id)
    
    # Batch extra counts
    qids_by_topic = {}
    async for q in db.questions.find({"subject_id": subject_id}, {"question_id": 1, "topic_id": 1}):
        qids_by_topic.setdefault(q["topic_id"], []).append(q["question_id"])
        
    # Notes count per topic
    notes_count = {}
    for tid, qids in qids_by_topic.items():
        notes_count[tid] = await db.question_notes.count_documents({"user_id": uid, "question_id": {"$in": qids}})
        
    # Mistakes count per topic
    mistakes_count = {r["_id"]: r["count"] async for r in db.mistakes.aggregate([
        {"$match": {"user_id": uid, "subject_id": subject_id}},
        {"$group": {"_id": "$topic_id", "count": {"$sum": 1}}}
    ])}
    
    rows = []
    for t in topics:
        tid = t["topic_id"]
        
        qb_t = q_totals.get(tid, 0)
        qb_p = q_progress.get(tid, {"solved": 0, "correct": 0})
        qb_acc = round(qb_p["correct"] / qb_p["solved"] * 100, 1) if qb_p["solved"] > 0 else 0.0
        
        pyq_t = p_totals.get(tid, 0)
        pyq_p = p_progress.get(tid, {"solved": 0, "correct": 0})
        pyq_acc = round(pyq_p["correct"] / pyq_p["solved"] * 100, 1) if pyq_p["solved"] > 0 else 0.0
        
        rows.append({
            "topic": t,
            "qb": {"total": qb_t, "solved": qb_p["solved"], "remaining": qb_t - qb_p["solved"], "accuracy": qb_acc},
            "pyq": {"total": pyq_t, "solved": pyq_p["solved"], "remaining": pyq_t - pyq_p["solved"], "accuracy": pyq_acc},
            "notes_count": notes_count.get(tid, 0),
            "mistakes_count": mistakes_count.get(tid, 0)
        })
    
    return ok(rows)


@router.get("/analytics/topic/{topic_id}")
async def topic_analytics(topic_id: str, user=Depends(get_current_user)) -> Dict[str, Any]:
    uid = user["user_id"]
    t = await db.topics.find_one({"topic_id": topic_id}, {"_id": 0})
    if not t:
        return err("not_found", "Topic not found", 404)
    
    sid = t["subject_id"]
    
    # Total counts for this topic
    qb_t = await db.questions.count_documents({"topic_id": topic_id, "user_id": uid})
    pyq_t = await db.pyqs.count_documents({"topic_id": topic_id, "user_id": uid})
    
    # Progress for this topic (we can reuse _get_topic_breakdown or just use a simpler one)
    # Using a simpler one for a single topic
    async def _single_topic_stats(coll, id_f, item_coll):
        p = [
            {"$match": {"user_id": uid}},
            {"$sort": {"attempted_at": -1}},
            {"$group": {"_id": f"${id_f}", "is_correct": {"$first": "$is_correct"}}},
            {"$lookup": {"from": item_coll, "localField": "_id", "foreignField": id_f, "as": "i"}},
            {"$unwind": "$i"},
            {"$match": {"i.topic_id": topic_id}},
            {"$group": {"_id": None, "solved": {"$sum": 1}, "correct": {"$sum": {"$cond": ["$is_correct", 1, 0]}}}}
        ]
        res = await db[coll].aggregate(p).to_list(1)
        if not res: return {"solved": 0, "correct": 0}
        return {"solved": res[0]["solved"], "correct": res[0]["correct"]}

    qb_p = await _single_topic_stats("question_attempts", "question_id", "questions")
    pyq_p = await _single_topic_stats("pyq_attempts", "pyq_id", "pyqs")
    
    qb_acc = round(qb_p["correct"] / qb_p["solved"] * 100, 1) if qb_p["solved"] > 0 else 0.0
    pyq_acc = round(pyq_p["correct"] / pyq_p["solved"] * 100, 1) if pyq_p["solved"] > 0 else 0.0
    
    qids = [q["question_id"] async for q in db.questions.find({"topic_id": topic_id}, {"question_id": 1})]
    notes = await db.question_notes.count_documents({"user_id": uid, "question_id": {"$in": qids}})
    mis = await db.mistakes.count_documents({"user_id": uid, "topic_id": topic_id})
    
    return ok({
        "topic": t,
        "qb": {"total": qb_t, "solved": qb_p["solved"], "remaining": qb_t - qb_p["solved"], "accuracy": qb_acc},
        "pyq": {"total": pyq_t, "solved": pyq_p["solved"], "remaining": pyq_t - pyq_p["solved"], "accuracy": pyq_acc},
        "notes_count": notes,
        "mistakes_count": mis
    })
