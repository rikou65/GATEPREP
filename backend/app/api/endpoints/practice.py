from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_current_user
from app.api.responses import err, ok
from app.core.ids import new_id
from app.repositories.mistakes import MistakeRepository
from app.repositories.pyqs import PYQRepository, PYQAttemptRepository
from app.repositories.questions import QuestionRepository, QuestionAttemptRepository, QuestionNoteRepository
from app.schemas.practice import (
    AttemptIn,
    FlagIn,
    MistakeIn,
    NotesIn,
    PYQIn,
    QuestionIn,
    QuestionPatch,
)
from app.services.practice import (
    MistakeService,
    PYQAttemptService,
    PYQService,
    QuestionAttemptService,
    QuestionFlagService,
    QuestionNoteService,
    QuestionService,
)

router = APIRouter()


def _q_services(request: Request):
    db = request.app.state.db
    q_repo = QuestionRepository(db)
    att_repo = QuestionAttemptRepository(db)
    note_repo = QuestionNoteRepository(db)
    return (
        QuestionService(q_repo),
        QuestionAttemptService(q_repo, att_repo),
        QuestionNoteService(note_repo),
        QuestionFlagService(q_repo),
    )


def _pyq_services(request: Request):
    db = request.app.state.db
    pyq_repo = PYQRepository(db)
    att_repo = PYQAttemptRepository(db)
    return PYQService(pyq_repo), PYQAttemptService(pyq_repo, att_repo)


def _mistake_service(request: Request):
    return MistakeService(MistakeRepository(request.app.state.db))


@router.get("/questions")
async def list_questions(
    request: Request,
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    question_type: Optional[str] = None,
    attempted: Optional[str] = None,
    result: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user=Depends(get_current_user),
):
    svc, _, _, _ = _q_services(request)
    result_data = await svc.list_questions(
        user["user_id"], subject_id, topic_id, question_type,
        attempted, result, flag, limit, skip,
    )
    return ok(result_data)


@router.get("/questions/{question_id}")
async def get_question(
    question_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    svc, _, _, _ = _q_services(request)
    q = await svc.get_question(question_id, user["user_id"])
    if q is None:
        return err("not_found", "Question not found", 404)
    return ok(q)


@router.post("/questions/{question_id}/attempt")
async def attempt_question(
    question_id: str,
    body: AttemptIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, att_svc, _, _ = _q_services(request)
    result_data = await att_svc.attempt(
        question_id, user["user_id"], body.selected_answer, body.time_taken,
    )
    if result_data is None:
        return err("not_found", "Question not found", 404)
    return ok(result_data)


@router.get("/questions/{question_id}/attempts")
async def question_attempts(
    question_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, att_svc, _, _ = _q_services(request)
    return ok(await att_svc.list_attempts(question_id, user["user_id"]))


@router.get("/questions/{question_id}/notes")
async def get_question_notes(
    question_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, note_svc, _ = _q_services(request)
    return ok(await note_svc.get(question_id, user["user_id"]))


@router.post("/questions/{question_id}/notes")
async def save_question_notes(
    question_id: str,
    body: NotesIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, note_svc, _ = _q_services(request)
    await note_svc.save(question_id, user["user_id"], body.note_content)
    return ok({"saved": True})


@router.post("/questions")
async def create_question(
    body: QuestionIn,
    request: Request,
    user=Depends(get_current_user),
):
    svc, _, _, _ = _q_services(request)
    doc = await svc.create_question(new_id("q"), user["user_id"], body)
    return ok(doc)


@router.put("/questions/{question_id}")
async def update_question(
    question_id: str,
    body: QuestionPatch,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    repo = QuestionRepository(db)
    updates = {
        k: v for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k == "correct_answer"
    }
    if not updates:
        return err("nothing_to_update", "No fields supplied", 400)
    from app.core.time import iso, now_utc
    updates["updated_at"] = iso(now_utc())
    matched = await repo.update(question_id, user["user_id"], updates)
    if matched == 0:
        return err("not_found", "Question not found", 404)
    doc = await repo.find_by_id(question_id, user["user_id"])
    return ok(doc)


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    q_repo = QuestionRepository(db)
    deleted = await q_repo.delete(question_id, user["user_id"])
    if deleted == 0:
        return err("not_found", "Question not found", 404)
    from app.repositories.questions import QuestionAttemptRepository, QuestionNoteRepository
    await QuestionAttemptRepository(db).delete_all(user["user_id"], question_id)
    await QuestionNoteRepository(db).delete_all(user["user_id"], question_id)
    await q_repo.delete_flags(user["user_id"], question_id)
    from app.repositories.mistakes import MistakeRepository
    await MistakeRepository(db).delete_all_for_question(user["user_id"], question_id)
    return ok({"deleted": 1})


@router.get("/pyqs")
async def list_pyqs(
    request: Request,
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    year: Optional[int] = None,
    attempted: Optional[str] = None,
    result: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user=Depends(get_current_user),
):
    svc, _ = _pyq_services(request)
    result_data = await svc.list_pyqs(
        user["user_id"], subject_id, topic_id, year,
        attempted, result, flag, limit, skip,
    )
    return ok(result_data)


@router.post("/pyqs")
async def create_pyq(
    body: PYQIn,
    request: Request,
    user=Depends(get_current_user),
):
    svc, _ = _pyq_services(request)
    doc = await svc.create_pyq(new_id("pyq"), user["user_id"], body)
    return ok(doc)


@router.put("/pyqs/{pyq_id}")
async def update_pyq(
    pyq_id: str,
    body: QuestionPatch,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    repo = PYQRepository(db)
    updates = {
        k: v for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k == "correct_answer"
    }
    if not updates:
        return err("nothing_to_update", "No fields supplied", 400)
    from app.core.time import iso, now_utc
    updates["updated_at"] = iso(now_utc())
    matched = await repo.update(pyq_id, user["user_id"], updates)
    if matched == 0:
        return err("not_found", "PYQ not found", 404)
    doc = await repo.find_by_id(pyq_id, user["user_id"])
    return ok(doc)


@router.delete("/pyqs/{pyq_id}")
async def delete_pyq(
    pyq_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    pyq_repo = PYQRepository(db)
    deleted = await pyq_repo.delete(pyq_id, user["user_id"])
    if deleted == 0:
        return err("not_found", "PYQ not found", 404)
    await PYQAttemptRepository(db).delete_all(user["user_id"], pyq_id)
    await pyq_repo.delete_flags(user["user_id"], pyq_id)
    return ok({"deleted": 1})


@router.post("/questions/{question_id}/flag")
async def flag_question(
    question_id: str,
    body: FlagIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, flag_svc = _q_services(request)
    error = await flag_svc.add(question_id, user["user_id"], body.flag_type)
    if error:
        return err("invalid_flag", error, 400)
    return ok({"flags": await flag_svc.list(question_id, user["user_id"])})


@router.delete("/questions/{question_id}/flag/{flag_type}")
async def unflag_question(
    question_id: str,
    flag_type: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, _, _, flag_svc = _q_services(request)
    error = await flag_svc.remove(question_id, user["user_id"], flag_type)
    if error:
        return err("invalid_flag", error, 400)
    return ok({"flags": await flag_svc.list(question_id, user["user_id"])})


@router.post("/pyqs/{pyq_id}/flag")
async def flag_pyq(
    pyq_id: str,
    body: FlagIn,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    pyq_repo = PYQRepository(db)
    svc, _ = _pyq_services(request)
    if body.flag_type not in {"review", "important"}:
        return err("invalid_flag", f"flag_type must be one of {{'important', 'review'}}", 400)
    p = await pyq_repo.find_by_id(pyq_id, user["user_id"])
    if p is None:
        return err("not_found", "PYQ not found", 404)
    from app.core.time import iso, now_utc
    now = iso(now_utc())
    await pyq_repo.add_flag({
        "user_id": user["user_id"], "pyq_id": pyq_id,
        "flag_type": body.flag_type, "created_at": now, "updated_at": now,
    })
    return ok({"flags": await pyq_repo.get_flags(user["user_id"], pyq_id)})


@router.delete("/pyqs/{pyq_id}/flag/{flag_type}")
async def unflag_pyq(
    pyq_id: str,
    flag_type: str,
    request: Request,
    user=Depends(get_current_user),
):
    db = request.app.state.db
    pyq_repo = PYQRepository(db)
    if flag_type not in {"review", "important"}:
        return err("invalid_flag", f"flag_type must be one of {{'important', 'review'}}", 400)
    await pyq_repo.remove_flag(user["user_id"], pyq_id, flag_type)
    return ok({"flags": await pyq_repo.get_flags(user["user_id"], pyq_id)})


@router.post("/pyqs/{pyq_id}/attempt")
async def attempt_pyq(
    pyq_id: str,
    body: AttemptIn,
    request: Request,
    user=Depends(get_current_user),
):
    _, att_svc = _pyq_services(request)
    result_data = await att_svc.attempt(
        pyq_id, user["user_id"], body.selected_answer, body.time_taken,
    )
    if result_data is None:
        return err("not_found", "PYQ not found", 404)
    return ok(result_data)


@router.get("/pyqs/{pyq_id}/attempts")
async def pyq_attempts_list(
    pyq_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    _, att_svc = _pyq_services(request)
    return ok(await att_svc.list_attempts(pyq_id, user["user_id"]))


@router.get("/mistakes")
async def list_mistakes(
    request: Request,
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    mistake_type: Optional[str] = None,
    user=Depends(get_current_user),
):
    svc = _mistake_service(request)
    return ok(await svc.list_mistakes(
        user["user_id"], subject_id, topic_id, mistake_type,
    ))


@router.post("/mistakes")
async def create_mistake(
    body: MistakeIn,
    request: Request,
    user=Depends(get_current_user),
):
    svc = _mistake_service(request)
    doc = await svc.create_mistake(
        user["user_id"], body.question_id, body.mistake_type, body.note or "",
    )
    if doc is None:
        return err("not_found", "Question not found", 404)
    return ok(doc)


@router.delete("/mistakes/{mistake_id}")
async def delete_mistake(
    mistake_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    svc = _mistake_service(request)
    deleted = await svc.delete_mistake(mistake_id, user["user_id"])
    return ok({"deleted": deleted})
