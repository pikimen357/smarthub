import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher
from app.services import gemini_service

router = APIRouter(prefix="/classes/{class_id}/rubric", tags=["Rubric"])


def _get_owned_class(db: Session, class_id: str, teacher_id: str) -> models.Class:
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher_id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")
    return klass


def _to_out(rubric: models.Rubric) -> schemas.RubricOut:
    return schemas.RubricOut(
        id=rubric.id,
        class_id=rubric.class_id,
        criteria=json.loads(rubric.criteria_json),
    )


@router.post("/generate", response_model=schemas.RubricOut)
def generate_rubric(
    class_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    klass = _get_owned_class(db, class_id, teacher.id)
    modules = db.query(models.Module).filter(models.Module.class_id == class_id).all()
    modules_text = "\n".join(f"- {m.title}: {m.content_text or ''}" for m in modules)

    criteria = gemini_service.generate_rubric(klass.problem_description or "", modules_text)

    rubric = db.query(models.Rubric).filter(models.Rubric.class_id == class_id).first()
    if rubric:
        rubric.criteria_json = json.dumps(criteria)
    else:
        rubric = models.Rubric(class_id=class_id, criteria_json=json.dumps(criteria))
        db.add(rubric)

    db.commit()
    db.refresh(rubric)
    return _to_out(rubric)


@router.get("/", response_model=schemas.RubricOut)
def get_rubric(
    class_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rubric = db.query(models.Rubric).filter(models.Rubric.class_id == class_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubrik belum dibuat untuk kelas ini")
    return _to_out(rubric)


@router.put("/", response_model=schemas.RubricOut)
def update_rubric(
    class_id: str,
    payload: schemas.RubricUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_class(db, class_id, teacher.id)
    rubric = db.query(models.Rubric).filter(models.Rubric.class_id == class_id).first()
    criteria_json = json.dumps([c.model_dump() for c in payload.criteria])

    if rubric:
        rubric.criteria_json = criteria_json
    else:
        rubric = models.Rubric(class_id=class_id, criteria_json=criteria_json)
        db.add(rubric)

    db.commit()
    db.refresh(rubric)
    return _to_out(rubric)
