import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher
from app.services import gemini_service

router = APIRouter(prefix="/projects/{project_id}/rubric", tags=["Rubric"])


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


def _to_out(rubric: models.Rubric) -> schemas.RubricOut:
    return schemas.RubricOut(
        id=rubric.id,
        project_id=rubric.project_id,
        criteria=json.loads(rubric.criteria_json),
    )


@router.post("/generate", response_model=schemas.RubricOut)
def generate_rubric(
    project_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    project = _get_owned_project(db, project_id, teacher.id)
    modules = db.query(models.Module).filter(models.Module.project_id == project_id).all()
    modules_text = "\n".join(f"- {m.title} ({m.type}): {m.url}" for m in modules)

    criteria = gemini_service.generate_rubric(project.description or "", modules_text)

    rubric = db.query(models.Rubric).filter(models.Rubric.project_id == project_id).first()
    if rubric:
        rubric.criteria_json = json.dumps(criteria)
    else:
        rubric = models.Rubric(project_id=project_id, criteria_json=json.dumps(criteria))
        db.add(rubric)

    db.commit()
    db.refresh(rubric)
    return _to_out(rubric)


@router.get("/", response_model=schemas.RubricOut)
def get_rubric(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rubric = db.query(models.Rubric).filter(models.Rubric.project_id == project_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubrik belum dibuat untuk project ini")
    return _to_out(rubric)


@router.put("/", response_model=schemas.RubricOut)
def update_rubric(
    project_id: str,
    payload: schemas.RubricUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_project(db, project_id, teacher.id)
    rubric = db.query(models.Rubric).filter(models.Rubric.project_id == project_id).first()
    criteria_json = json.dumps([c.model_dump() for c in payload.criteria])

    if rubric:
        rubric.criteria_json = criteria_json
    else:
        rubric = models.Rubric(project_id=project_id, criteria_json=criteria_json)
        db.add(rubric)

    db.commit()
    db.refresh(rubric)
    return _to_out(rubric)