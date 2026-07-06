import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import require_student, get_current_user
from app.services import gemini_service

router = APIRouter(prefix="/groups/{group_id}/discussion", tags=["Discussion (AI Teman Diskusi)"])


def _get_group_for_student(db: Session, group_id: str, student_id: str) -> models.Group:
    membership = (
        db.query(models.GroupMember)
        .filter(models.GroupMember.group_id == group_id, models.GroupMember.student_id == student_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Anda bukan anggota grup ini")
    return membership.group


def _get_or_create_discussion(db: Session, group_id: str) -> models.Discussion:
    discussion = db.query(models.Discussion).filter(models.Discussion.group_id == group_id).first()
    if not discussion:
        discussion = models.Discussion(group_id=group_id, chat_history_json="[]")
        db.add(discussion)
        db.commit()
        db.refresh(discussion)
    return discussion


@router.get("/", response_model=schemas.DiscussionOut)
def get_discussion(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    discussion = _get_or_create_discussion(db, group_id)
    return schemas.DiscussionOut(
        group_id=group_id, chat_history=json.loads(discussion.chat_history_json)
    )


@router.post("/message", response_model=schemas.DiscussionOut)
def send_message(
    group_id: str,
    payload: schemas.ChatMessageIn,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    group = _get_group_for_student(db, group_id, student.id)
    project = db.query(models.Project).filter(models.Project.id == group.project_id).first()
    modules = db.query(models.Module).filter(models.Module.project_id == group.project_id).all()
    modules_text = "\n".join(f"- {m.title}: {m.content_text or ''}" for m in modules)

    discussion = _get_or_create_discussion(db, group_id)
    history = json.loads(discussion.chat_history_json)

    history.append({"role": "student", "message": payload.message, "timestamp": datetime.utcnow().isoformat()})

    ai_reply = gemini_service.socratic_chat(
        problem_description=project.description or "",
        modules_text=modules_text,
        chat_history=history,
        student_message=payload.message,
    )
    history.append({"role": "ai", "message": ai_reply, "timestamp": datetime.utcnow().isoformat()})

    discussion.chat_history_json = json.dumps(history)

    if group.status == models.GroupStatusEnum.belum_mulai:
        group.status = models.GroupStatusEnum.diskusi_ai

    db.commit()

    return schemas.DiscussionOut(group_id=group_id, chat_history=history)