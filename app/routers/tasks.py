import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import require_student, get_current_user
from app.services import gemini_service

router = APIRouter(tags=["Tasks (Checklist)"])


def _get_group_for_student(db: Session, group_id: str, student_id: str) -> models.Group:
    membership = (
        db.query(models.GroupMember)
        .filter(models.GroupMember.group_id == group_id, models.GroupMember.student_id == student_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Anda bukan anggota grup ini")
    return membership.group


@router.post("/groups/{group_id}/checklist/generate", response_model=list[schemas.TaskOut])
def generate_checklist(
    group_id: str,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    group = _get_group_for_student(db, group_id, student.id)
    klass = db.query(models.Class).filter(models.Class.id == group.class_id).first()
    discussion = db.query(models.Discussion).filter(models.Discussion.group_id == group_id).first()

    if not discussion or json.loads(discussion.chat_history_json) == []:
        raise HTTPException(
            status_code=400, detail="Belum ada riwayat diskusi AI untuk grup ini, silakan diskusi dulu"
        )

    chat_history = json.loads(discussion.chat_history_json)
    result = gemini_service.generate_checklist(klass.problem_description or "", chat_history)

    # Hapus checklist lama (kalau generate ulang) lalu buat yang baru
    db.query(models.Task).filter(models.Task.group_id == group_id).delete()

    order = 0
    new_tasks = []
    for item in result.get("alat", []):
        new_tasks.append(models.Task(group_id=group_id, type=models.TaskTypeEnum.alat, item_desc=item, order_index=order))
        order += 1
    for item in result.get("bahan", []):
        new_tasks.append(models.Task(group_id=group_id, type=models.TaskTypeEnum.bahan, item_desc=item, order_index=order))
        order += 1
    for item in result.get("langkah_kerja", []):
        new_tasks.append(models.Task(group_id=group_id, type=models.TaskTypeEnum.langkah, item_desc=item, order_index=order))
        order += 1

    db.add_all(new_tasks)
    group.status = models.GroupStatusEnum.praktik
    db.commit()

    for t in new_tasks:
        db.refresh(t)
    return new_tasks


@router.get("/groups/{group_id}/tasks", response_model=list[schemas.TaskOut])
def list_tasks(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Task)
        .filter(models.Task.group_id == group_id)
        .order_by(models.Task.order_index)
        .all()
    )


@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def toggle_task(
    task_id: str,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan")

    # pastikan siswa adalah anggota grup terkait
    _get_group_for_student(db, task.group_id, student.id)

    task.is_checked = payload.is_checked
    db.commit()
    db.refresh(task)
    return task
