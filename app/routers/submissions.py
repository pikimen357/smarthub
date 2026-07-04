import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import require_student, require_teacher, get_current_user

router = APIRouter(tags=["Submissions"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_group_for_student(db: Session, group_id: str, student_id: str) -> models.Group:
    membership = (
        db.query(models.GroupMember)
        .filter(models.GroupMember.group_id == group_id, models.GroupMember.student_id == student_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Anda bukan anggota grup ini")
    return membership.group


@router.post("/groups/{group_id}/submission", response_model=schemas.SubmissionOut)
def submit_final_report(
    group_id: str,
    conclusion_text: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    group = _get_group_for_student(db, group_id, student.id)

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file.file.read())

    submission = db.query(models.Submission).filter(models.Submission.group_id == group_id).first()
    if not submission:
        submission = models.Submission(group_id=group_id)
        db.add(submission)

    submission.final_image_url = f"/static/uploads/{filename}"
    submission.conclusion_text = conclusion_text
    submission.submitted_at = datetime.utcnow()

    group.status = models.GroupStatusEnum.selesai

    db.commit()
    db.refresh(submission)
    return submission


@router.get("/groups/{group_id}/submission", response_model=schemas.SubmissionOut)
def get_submission(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    submission = db.query(models.Submission).filter(models.Submission.group_id == group_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Belum ada laporan untuk grup ini")
    return submission


@router.post("/submissions/{submission_id}/grade", response_model=schemas.SubmissionOut)
def grade_submission(
    submission_id: str,
    payload: schemas.GradeRequest,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    submission = db.query(models.Submission).filter(models.Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission tidak ditemukan")

    submission.grade_score = payload.grade_score
    submission.feedback_text = payload.feedback_text
    submission.graded_at = datetime.utcnow()

    db.commit()
    db.refresh(submission)
    return submission
