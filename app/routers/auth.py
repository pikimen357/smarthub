from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=schemas.UserOut)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if payload.role not in ("teacher", "student"):
        raise HTTPException(status_code=400, detail="role harus 'teacher' atau 'student'")

    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    user = models.User(
        role=payload.role,
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Menggunakan form-urlencoded (username, password) agar kompatibel dengan
    OAuth2PasswordBearer/Swagger UI. Field 'username' diisi dengan email.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password salah")

    access_token = create_access_token(data={"sub": user.id, "role": user.role.value})
    return schemas.TokenResponse(
        access_token=access_token,
        role=user.role.value,
        user_id=user.id,
        name=user.name,
    )
