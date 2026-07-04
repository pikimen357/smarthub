import json
import os
import random
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher, require_student
from app.services import gemini_service

router = APIRouter(prefix="/classes", tags=["Classes"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _generate_token() -> str:
    prefix = "".join(random.choices(string.ascii_uppercase, k=5))
    suffix = "".join(random.choices(string.digits + string.ascii_uppercase, k=4))
    return f"{prefix}-{suffix}"


@router.post("/", response_model=schemas.ClassOut)
def create_class(
    payload: schemas.ClassCreate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    token = _generate_token()
    while db.query(models.Class).filter(models.Class.token == token).first():
        token = _generate_token()

    new_class = models.Class(teacher_id=teacher.id, name=payload.name, token=token)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


@router.get("/", response_model=list[schemas.ClassOut])
def list_my_classes(
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    return db.query(models.Class).filter(models.Class.teacher_id == teacher.id).all()


@router.get("/{class_id}", response_model=schemas.ClassOut)
def get_class(
    class_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    klass = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    return klass


@router.put("/{class_id}/problem", response_model=schemas.ClassOut)
def update_problem(
    class_id: str,
    payload: schemas.ClassProblemUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    klass = _get_owned_class(db, class_id, teacher.id)
    klass.problem_description = payload.problem_description
    db.commit()
    db.refresh(klass)
    return klass


@router.post("/{class_id}/problem-image")
def upload_problem_image(
    class_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    klass = _get_owned_class(db, class_id, teacher.id)

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = file.file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    analysis = gemini_service.analyze_image(content, file.content_type or "image/jpeg")

    klass.problem_image_url = f"/static/uploads/{filename}"
    klass.problem_image_analysis_json = json.dumps(analysis)
    db.commit()
    db.refresh(klass)

    return {
        "problem_image_url": klass.problem_image_url,
        "analysis": analysis,
    }


@router.get("/{class_id}/problem-image/analysis")
def get_image_analysis(
    class_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    klass = db.query(models.Class).filter(models.Class.id == class_id).first()
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    if not klass.problem_image_analysis_json:
        raise HTTPException(status_code=404, detail="Belum ada analisis gambar untuk kelas ini")
    return json.loads(klass.problem_image_analysis_json)


@router.post("/join", response_model=schemas.GroupOut)
def join_class(
    payload: schemas.ClassJoinRequest,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    """
    Siswa join menggunakan token kelas. Untuk MVP: siswa otomatis dimasukkan
    ke grup pribadi (1 grup = 1 siswa) jika belum tergabung di grup manapun
    pada kelas ini. Guru bisa menggabungkan grup secara manual lewat endpoint groups.
    """
    klass = db.query(models.Class).filter(models.Class.token == payload.token).first()
    if not klass:
        raise HTTPException(status_code=404, detail="Token kelas tidak valid")

    existing_membership = (
        db.query(models.GroupMember)
        .join(models.Group)
        .filter(models.Group.class_id == klass.id, models.GroupMember.student_id == student.id)
        .first()
    )
    if existing_membership:
        return existing_membership.group

    group = models.Group(class_id=klass.id, name=f"Grup {student.name}")
    db.add(group)
    db.commit()
    db.refresh(group)

    member = models.GroupMember(group_id=group.id, student_id=student.id)
    db.add(member)
    db.commit()

    return group


def _get_owned_class(db: Session, class_id: str, teacher_id: str) -> models.Class:
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher_id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")
    return klass
