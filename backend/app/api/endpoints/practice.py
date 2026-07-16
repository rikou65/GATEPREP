from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.providers import (
    get_mistake_service,
    get_pyq_attempt_service,
    get_pyq_service,
    get_question_attempt_service,
    get_question_flag_service,
    get_question_note_service,
    get_question_service,
)
from app.api.responses import err, ok
from app.core.ids import new_id
from app.schemas.auth import CurrentUser
from app.schemas.common import DeletedOut, Envelope, FlagsOut, SavedOut
from app.schemas.practice import (
    AttemptIn,
    AttemptResultOut,
    FlagIn,
    MistakeIn,
    NotesIn,
    PracticeListOut,
    PYQIn,
    QuestionIn,
    QuestionNotesOut,
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


@router.get("/questions", response_model=Envelope[PracticeListOut])
async def list_questions(
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    question_type: Optional[str] = None,
    attempted: Optional[str] = None,
    result: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
    svc: QuestionService = Depends(get_question_service),
):
    result_data = await svc.list_questions(
        user.user_id,
        subject_id,
        topic_id,
        question_type,
        attempted,
        result,
        flag,
        limit,
        skip,
    )
    return ok(result_data)


@router.get("/questions/{question_id}", response_model=Envelope[dict])
async def get_question(
    question_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: QuestionService = Depends(get_question_service),
):
    q = await svc.get_question(question_id, user.user_id)
    if q is None:
        return err("not_found", "Question not found", 404)
    return ok(q)


@router.post("/questions/{question_id}/attempt", response_model=Envelope[AttemptResultOut])
async def attempt_question(
    question_id: str,
    body: AttemptIn,
    user: CurrentUser = Depends(get_current_user),
    att_svc: QuestionAttemptService = Depends(get_question_attempt_service),
):
    result_data = await att_svc.attempt(
        question_id, user.user_id, body.selected_answer, body.time_taken,
    )
    if result_data is None:
        return err("not_found", "Question not found", 404)
    return ok(result_data)


@router.get("/questions/{question_id}/attempts", response_model=Envelope[List[dict]])
async def question_attempts(
    question_id: str,
    user: CurrentUser = Depends(get_current_user),
    att_svc: QuestionAttemptService = Depends(get_question_attempt_service),
):
    return ok(await att_svc.list_attempts(question_id, user.user_id))


@router.get("/questions/{question_id}/notes", response_model=Envelope[QuestionNotesOut])
async def get_question_notes(
    question_id: str,
    user: CurrentUser = Depends(get_current_user),
    note_svc: QuestionNoteService = Depends(get_question_note_service),
):
    return ok(await note_svc.get(question_id, user.user_id))


@router.post("/questions/{question_id}/notes", response_model=Envelope[SavedOut])
async def save_question_notes(
    question_id: str,
    body: NotesIn,
    user: CurrentUser = Depends(get_current_user),
    note_svc: QuestionNoteService = Depends(get_question_note_service),
):
    await note_svc.save(question_id, user.user_id, body.note_content)
    return ok({"saved": True})


@router.post("/questions", response_model=Envelope[dict])
async def create_question(
    body: QuestionIn,
    user: CurrentUser = Depends(get_current_user),
    svc: QuestionService = Depends(get_question_service),
):
    doc = await svc.create_question(new_id("q"), user.user_id, body)
    return ok(doc)


@router.put("/questions/{question_id}", response_model=Envelope[dict])
async def update_question(
    question_id: str,
    body: QuestionPatch,
    user: CurrentUser = Depends(get_current_user),
    svc: QuestionService = Depends(get_question_service),
):
    updates = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k == "correct_answer"
    }
    result = await svc.update_question(user.user_id, question_id, updates)
    if result is None:
        return err("not_found", "Question not found", 404)
    if isinstance(result, dict) and "error" in result:
        return err("nothing_to_update", "No fields supplied", 400)
    return ok(result)


@router.delete("/questions/{question_id}", response_model=Envelope[DeletedOut])
async def delete_question(
    question_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: QuestionService = Depends(get_question_service),
):
    deleted = await svc.delete_question(user.user_id, question_id)
    if deleted == 0:
        return err("not_found", "Question not found", 404)
    return ok({"deleted": deleted})


@router.get("/pyqs", response_model=Envelope[PracticeListOut])
async def list_pyqs(
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    year: Optional[int] = None,
    attempted: Optional[str] = None,
    result: Optional[str] = None,
    flag: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    user: CurrentUser = Depends(get_current_user),
    svc: PYQService = Depends(get_pyq_service),
):
    result_data = await svc.list_pyqs(
        user.user_id, subject_id, topic_id, year,
        attempted, result, flag, limit, skip,
    )
    return ok(result_data)


@router.post("/pyqs", response_model=Envelope[dict])
async def create_pyq(
    body: PYQIn,
    user: CurrentUser = Depends(get_current_user),
    svc: PYQService = Depends(get_pyq_service),
):
    doc = await svc.create_pyq(new_id("pyq"), user.user_id, body)
    return ok(doc)


@router.put("/pyqs/{pyq_id}", response_model=Envelope[dict])
async def update_pyq(
    pyq_id: str,
    body: QuestionPatch,
    user: CurrentUser = Depends(get_current_user),
    svc: PYQService = Depends(get_pyq_service),
):
    updates = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k == "correct_answer"
    }
    result = await svc.update_pyq(user.user_id, pyq_id, updates)
    if result is None:
        return err("not_found", "PYQ not found", 404)
    if isinstance(result, dict) and "error" in result:
        return err("nothing_to_update", "No fields supplied", 400)
    return ok(result)


@router.delete("/pyqs/{pyq_id}", response_model=Envelope[DeletedOut])
async def delete_pyq(
    pyq_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: PYQService = Depends(get_pyq_service),
):
    deleted = await svc.delete_pyq(user.user_id, pyq_id)
    if deleted == 0:
        return err("not_found", "PYQ not found", 404)
    return ok({"deleted": deleted})


@router.post("/questions/{question_id}/flag", response_model=Envelope[FlagsOut])
async def flag_question(
    question_id: str,
    body: FlagIn,
    user: CurrentUser = Depends(get_current_user),
    flag_svc: QuestionFlagService = Depends(get_question_flag_service),
):
    error = await flag_svc.add(question_id, user.user_id, body.flag_type)
    if error:
        return err("invalid_flag", error, 400)
    return ok({"flags": await flag_svc.list(question_id, user.user_id)})


@router.delete("/questions/{question_id}/flag/{flag_type}", response_model=Envelope[FlagsOut])
async def unflag_question(
    question_id: str,
    flag_type: str,
    user: CurrentUser = Depends(get_current_user),
    flag_svc: QuestionFlagService = Depends(get_question_flag_service),
):
    error = await flag_svc.remove(question_id, user.user_id, flag_type)
    if error:
        return err("invalid_flag", error, 400)
    return ok({"flags": await flag_svc.list(question_id, user.user_id)})


@router.post("/pyqs/{pyq_id}/flag", response_model=Envelope[FlagsOut])
async def flag_pyq(
    pyq_id: str,
    body: FlagIn,
    user: CurrentUser = Depends(get_current_user),
    svc: PYQService = Depends(get_pyq_service),
):
    error = await svc.add_flag(user.user_id, pyq_id, body.flag_type)
    if error:
        return err("invalid_flag", error, 400)
    return ok({"flags": await svc.list_flags(user.user_id, pyq_id)})


@router.delete("/pyqs/{pyq_id}/flag/{flag_type}", response_model=Envelope[FlagsOut])
async def unflag_pyq(
    pyq_id: str,
    flag_type: str,
    user: CurrentUser = Depends(get_current_user),
    svc: PYQService = Depends(get_pyq_service),
):
    error = await svc.remove_flag(user.user_id, pyq_id, flag_type)
    if error:
        return err("invalid_flag", error, 400)
    return ok({"flags": await svc.list_flags(user.user_id, pyq_id)})


@router.post("/pyqs/{pyq_id}/attempt", response_model=Envelope[AttemptResultOut])
async def attempt_pyq(
    pyq_id: str,
    body: AttemptIn,
    user: CurrentUser = Depends(get_current_user),
    att_svc: PYQAttemptService = Depends(get_pyq_attempt_service),
):
    result_data = await att_svc.attempt(
        pyq_id, user.user_id, body.selected_answer, body.time_taken,
    )
    if result_data is None:
        return err("not_found", "PYQ not found", 404)
    return ok(result_data)


@router.get("/pyqs/{pyq_id}/attempts", response_model=Envelope[List[dict]])
async def pyq_attempts_list(
    pyq_id: str,
    user: CurrentUser = Depends(get_current_user),
    att_svc: PYQAttemptService = Depends(get_pyq_attempt_service),
):
    return ok(await att_svc.list_attempts(pyq_id, user.user_id))


@router.get("/mistakes", response_model=Envelope[List[dict]])
async def list_mistakes(
    subject_id: Optional[str] = None,
    topic_id: Optional[str] = None,
    mistake_type: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    svc: MistakeService = Depends(get_mistake_service),
):
    return ok(
        await svc.list_mistakes(user.user_id, subject_id, topic_id, mistake_type)
    )


@router.post("/mistakes", response_model=Envelope[dict])
async def create_mistake(
    body: MistakeIn,
    user: CurrentUser = Depends(get_current_user),
    svc: MistakeService = Depends(get_mistake_service),
):
    doc = await svc.create_mistake(
        user.user_id, body.question_id, body.mistake_type, body.note or "",
    )
    if doc is None:
        return err("not_found", "Question not found", 404)
    return ok(doc)


@router.delete("/mistakes/{mistake_id}", response_model=Envelope[DeletedOut])
async def delete_mistake(
    mistake_id: str,
    user: CurrentUser = Depends(get_current_user),
    svc: MistakeService = Depends(get_mistake_service),
):
    deleted = await svc.delete_mistake(mistake_id, user.user_id)
    return ok({"deleted": deleted})
