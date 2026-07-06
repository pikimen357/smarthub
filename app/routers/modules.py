from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher

router = APIRouter(prefix="/projects/{project_id}/modules", tags=["Modules"])


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


@router.post("/", response_model=schemas.ModuleOut)
def create_module(
    project_id: str,
    payload: schemas.ModuleCreate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_project(db, project_id, teacher.id)
    module = models.Module(project_id=project_id, title=payload.title, content_text=payload.content_text)
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


@router.get("/", response_model=list[schemas.ModuleOut])
def list_modules(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Module).filter(models.Module.project_id == project_id).all()


@router.get("/{module_id}", response_model=schemas.ModuleOut)
def get_module(
    project_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    module = (
        db.query(models.Module)
        .filter(models.Module.id == module_id, models.Module.project_id == project_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Modul tidak ditemukan")
    return module


@router.put("/{module_id}", response_model=schemas.ModuleOut)
def update_module(
    project_id: str,
    module_id: str,
    payload: schemas.ModuleUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_project(db, project_id, teacher.id)
    module = (
        db.query(models.Module)
        .filter(models.Module.id == module_id, models.Module.project_id == project_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Modul tidak ditemukan")

    if payload.title is not None:
        module.title = payload.title
    if payload.content_text is not None:
        module.content_text = payload.content_text

    db.commit()
    db.refresh(module)
    return module


@router.delete("/{module_id}")
def delete_module(
    project_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_project(db, project_id, teacher.id)
    module = (
        db.query(models.Module)
        .filter(models.Module.id == module_id, models.Module.project_id == project_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Modul tidak ditemukan")

    db.delete(module)
    db.commit()
    return {"detail": "Modul berhasil dihapus"}