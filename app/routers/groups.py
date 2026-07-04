from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher

router = APIRouter(tags=["Groups"])


def _get_owned_class(db: Session, class_id: str, teacher_id: str) -> models.Class:
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher_id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")
    return klass


@router.get("/classes/{class_id}/groups", response_model=list[schemas.GroupOut])
def list_groups(
    class_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Group).filter(models.Group.class_id == class_id).all()


@router.get("/classes/{class_id}/dashboard")
def class_dashboard(
    class_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    """Progres semua grup dalam kelas (Belum Mulai, Diskusi AI, Praktik, Selesai)."""
    _get_owned_class(db, class_id, teacher.id)
    groups = db.query(models.Group).filter(models.Group.class_id == class_id).all()

    result = []
    for g in groups:
        result.append(
            {
                "group_id": g.id,
                "group_name": g.name,
                "status": g.status.value if hasattr(g.status, "value") else g.status,
                "member_count": len(g.members),
                "has_submission": g.submission is not None,
            }
        )
    return {"class_id": class_id, "groups": result}


@router.get("/groups/{group_id}", response_model=schemas.GroupOut)
def get_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Grup tidak ditemukan")
    return group
