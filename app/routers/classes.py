import random
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher, require_student

router = APIRouter(prefix="/classes", tags=["Classes"])


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

    new_class = models.Class(teacher_id=teacher.id,
                             name=payload.name,
                             schedule=payload.schedule,
                             description=payload.description,
                             token=token)
    db.add(new_class)
    db.commit()
    db.refresh(new_class)
    return new_class


@router.get("/", response_model=list[schemas.ClassOut])
def list_my_classes(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    query = db.query(models.Class).filter(models.Class.teacher_id == teacher.id)
    if not include_archived:
        query = query.filter(models.Class.is_archived == False)
    return query.all()


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


@router.post("/join")
def join_class(
    payload: schemas.ClassJoinRequest,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    klass = db.query(models.Class).filter(models.Class.token == payload.token).first()
    if not klass:
        raise HTTPException(status_code=404, detail="Token kelas tidak valid")
    if klass.is_archived:
        raise HTTPException(status_code=400, detail="Kelas ini sudah diarsipkan dan tidak menerima siswa baru")

    existing = (
        db.query(models.ClassEnrollment)
        .filter(models.ClassEnrollment.class_id == klass.id, models.ClassEnrollment.student_id == student.id)
        .first()
    )
    if existing:
        return {"detail": "Anda sudah tergabung di kelas ini", "class_id": klass.id, "class_name": klass.name}

    enrollment = models.ClassEnrollment(class_id=klass.id, student_id=student.id)
    db.add(enrollment)
    db.commit()

    return {"detail": "Berhasil join kelas", "class_id": klass.id, "class_name": klass.name}


@router.get("/{class_id}/students")
def list_class_students(
    class_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    """Untuk statistik 'Total Siswa' di dashboard guru."""
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher.id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")

    enrollments = db.query(models.ClassEnrollment).filter(models.ClassEnrollment.class_id == class_id).all()
    return [
        {"student_id": e.student.id, "name": e.student.name, "email": e.student.email, "joined_at": e.joined_at}
        for e in enrollments
    ]

@router.put("/{class_id}", response_model=schemas.ClassOut)
def update_class(
    class_id: str,
    payload: schemas.ClassUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher.id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")

    if payload.name is not None:
        klass.name = payload.name
    if payload.schedule is not None:
        klass.schedule = payload.schedule
    if payload.description is not None:
        klass.description = payload.description

    db.commit()
    db.refresh(klass)
    return klass


@router.delete("/{class_id}")
def archive_class(
    class_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    """Soft delete: kelas diarsipkan, data tidak benar-benar dihapus dari database."""
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher.id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")

    klass.is_archived = True
    db.commit()
    return {"detail": "Kelas berhasil diarsipkan (soft delete)"}


@router.post("/{class_id}/restore", response_model=schemas.ClassOut)
def restore_class(
    class_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    """Mengembalikan kelas yang sudah diarsipkan."""
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher.id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")

    klass.is_archived = False
    db.commit()
    db.refresh(klass)
    return klass