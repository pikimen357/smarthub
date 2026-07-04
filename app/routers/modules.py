from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher

router = APIRouter(prefix="/classes/{class_id}/modules", tags=["Modules"])


def _get_owned_class(db: Session, class_id: str, teacher_id: str) -> models.Class:
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher_id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")
    return klass


@router.post("/", response_model=schemas.ModuleOut)
def create_module(
    class_id: str,
    payload: schemas.ModuleCreate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_class(db, class_id, teacher.id)
    module = models.Module(class_id=class_id, title=payload.title, content_text=payload.content_text)
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


@router.get("/", response_model=list[schemas.ModuleOut])
def list_modules(
    class_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Module).filter(models.Module.class_id == class_id).all()


@router.get("/{module_id}", response_model=schemas.ModuleOut)
def get_module(
    class_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    module = (
        db.query(models.Module)
        .filter(models.Module.id == module_id, models.Module.class_id == class_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Modul tidak ditemukan")
    return module


@router.put("/{module_id}", response_model=schemas.ModuleOut)
def update_module(
    class_id: str,
    module_id: str,
    payload: schemas.ModuleUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_class(db, class_id, teacher.id)
    module = (
        db.query(models.Module)
        .filter(models.Module.id == module_id, models.Module.class_id == class_id)
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
    class_id: str,
    module_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_class(db, class_id, teacher.id)
    module = (
        db.query(models.Module)
        .filter(models.Module.id == module_id, models.Module.class_id == class_id)
        .first()
    )
    if not module:
        raise HTTPException(status_code=404, detail="Modul tidak ditemukan")

    db.delete(module)
    db.commit()
    return {"detail": "Modul berhasil dihapus"}
