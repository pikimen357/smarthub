import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher, require_student
from app.services import gemini_service

router = APIRouter(tags=["Projects (Tugas)"])

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_owned_class(db: Session, class_id: str, teacher_id: str) -> models.Class:
    klass = (
        db.query(models.Class)
        .filter(models.Class.id == class_id, models.Class.teacher_id == teacher_id)
        .first()
    )
    if not klass:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan atau bukan milik Anda")
    return klass


def _get_owned_project(db: Session, project_id: str, teacher_id: str) -> models.Project:
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    _get_owned_class(db, project.class_id, teacher_id)
    return project


def _require_enrolled(db: Session, class_id: str, student_id: str):
    enrolled = (
        db.query(models.ClassEnrollment)
        .filter(models.ClassEnrollment.class_id == class_id, models.ClassEnrollment.student_id == student_id)
        .first()
    )
    if not enrolled:
        raise HTTPException(status_code=403, detail="Anda belum join kelas ini")


@router.post("/classes/{class_id}/projects", response_model=schemas.ProjectOut)
def create_project(
    class_id: str,
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_class(db, class_id, teacher.id)
    project = models.Project(
        class_id=class_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/classes/{class_id}/projects", response_model=list[schemas.ProjectOut])
def list_projects(
    class_id: str,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Guru lihat semua (draft+published, kecuali archived); siswa hanya lihat yang published."""
    query = db.query(models.Project).filter(models.Project.class_id == class_id)

    if current_user.role == models.RoleEnum.student:
        _require_enrolled(db, class_id, current_user.id)
        query = query.filter(models.Project.status == models.ProjectStatusEnum.published)
    else:
        if not include_archived:
            query = query.filter(models.Project.status != models.ProjectStatusEnum.archived)

    return query.all()


@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    return project


@router.put("/projects/{project_id}", response_model=schemas.ProjectOut)
def update_project(
    project_id: str,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    project = _get_owned_project(db, project_id, teacher.id)

    if payload.title is not None:
        project.title = payload.title
    if payload.description is not None:
        project.description = payload.description
    if payload.status is not None:
        if payload.status not in ("draft", "published", "archived"):
            raise HTTPException(status_code=400, detail="status harus 'draft', 'published', atau 'archived'")
        project.status = payload.status

    db.commit()
    db.refresh(project)
    return project


@router.post("/projects/{project_id}/problem-image")
def upload_problem_image(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    project = _get_owned_project(db, project_id, teacher.id)

    # Hapus file gambar lama (kalau ada) sebelum simpan yang baru
    if project.problem_image_url:
        old_filepath = project.problem_image_url.replace("/static/", "app/static/", 1)
        if os.path.exists(old_filepath):
            os.remove(old_filepath)

    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = file.file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    analysis = gemini_service.analyze_image(content, file.content_type or "image/jpeg")

    project.problem_image_url = f"/static/uploads/{filename}"
    project.problem_image_analysis_json = json.dumps(analysis)
    db.commit()

    return {"problem_image_url": project.problem_image_url, "analysis": analysis}


@router.get("/projects/{project_id}/problem-image/analysis")
def get_image_analysis(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project or not project.problem_image_analysis_json:
        raise HTTPException(status_code=404, detail="Belum ada analisis gambar untuk project ini")

    return {
        "problem_image_url": project.problem_image_url,   # <-- tambahan ini
        "analysis": json.loads(project.problem_image_analysis_json),
    }


@router.post("/projects/{project_id}/start", response_model=schemas.GroupOut)
def start_project(
    project_id: str,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
    """Siswa 'mulai' sebuah project/tugas -> dibuatkan Group (kalau belum ada)."""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    if project.status != models.ProjectStatusEnum.published:
        raise HTTPException(status_code=400, detail="Project belum dipublish oleh guru")

    _require_enrolled(db, project.class_id, student.id)

    existing_membership = (
        db.query(models.GroupMember)
        .join(models.Group)
        .filter(models.Group.project_id == project_id, models.GroupMember.student_id == student.id)
        .first()
    )
    if existing_membership:
        return existing_membership.group

    group = models.Group(project_id=project_id, name=f"Grup {student.name}")
    db.add(group)
    db.commit()
    db.refresh(group)

    member = models.GroupMember(group_id=group.id, student_id=student.id)
    db.add(member)
    db.commit()

    return group