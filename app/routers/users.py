from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import require_teacher  # ganti dari get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/teachers", response_model=list[schemas.UserOut])
def list_teachers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher),
):
    return db.query(models.User).filter(models.User.role == models.RoleEnum.teacher).all()


@router.get("/students", response_model=list[schemas.UserOut])
def list_students(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_teacher),
):
    return db.query(models.User).filter(models.User.role == models.RoleEnum.student).all()