from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher

router = APIRouter(tags=["Groups"])


def _get_owned_project(db: Session, project_id: str, teacher_id: str) -> models.Project:
    project = (
        db.query(models.Project)
        .join(models.Class)
        .filter(models.Project.id == project_id, models.Class.teacher_id == teacher_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan atau bukan milik Anda")
    return project


@router.get("/projects/{project_id}/groups", response_model=list[schemas.GroupOut])
def list_groups(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Group).filter(models.Group.project_id == project_id).all()


@router.get("/projects/{project_id}/dashboard")
def project_dashboard(
    project_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    """Progres semua grup dalam project (Belum Mulai, Diskusi AI, Praktik, Selesai)."""
    _get_owned_project(db, project_id, teacher.id)
    groups = db.query(models.Group).filter(models.Group.project_id == project_id).all()

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
    return {"project_id": project_id, "groups": result}


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