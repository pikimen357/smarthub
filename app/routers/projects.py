import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher, require_student
from app.services import gemini_service, maps_service

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


def _resolve_location(latitude, longitude, address):
    """Terima kombinasi lat/lng ATAU address, kembalikan (latitude, longitude, address) final."""
    if latitude is not None and longitude is not None:
        resolved_address = address or maps_service.reverse_geocode(latitude, longitude)
        return latitude, longitude, resolved_address
    elif address:
        geo = maps_service.geocode_address(address)
        return geo["latitude"], geo["longitude"], geo["formatted_address"]
    return None, None, None  # lokasi memang belum diisi, itu boleh


def _to_out(project: models.Project) -> schemas.ProjectOut:
    out = schemas.ProjectOut.model_validate(project)
    if project.latitude is not None and project.longitude is not None:
        out.map_preview_url = maps_service.static_map_url(project.latitude, project.longitude)
    return out


@router.post("/classes/{class_id}/projects", response_model=schemas.ProjectOut)
def create_project(
    class_id: str,
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_class(db, class_id, teacher.id)

    latitude, longitude, address = _resolve_location(payload.latitude, payload.longitude, payload.address)

    project = models.Project(
        class_id=class_id,
        title=payload.title,
        description=payload.description,
        latitude=latitude,
        longitude=longitude,
        address=address,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(project)


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

    return [_to_out(p) for p in query.all()]


@router.get("/projects/{project_id}", response_model=schemas.ProjectOut)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    return _to_out(project)


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

    # Update lokasi hanya kalau salah satu field lokasi dikirim
    if payload.address is not None and payload.latitude is None:
        geo = maps_service.geocode_address(payload.address)
        project.latitude, project.longitude, project.address = (
            geo["latitude"], geo["longitude"], geo["formatted_address"],
        )
    elif payload.latitude is not None and payload.longitude is not None:
        project.latitude, project.longitude = payload.latitude, payload.longitude
        project.address = payload.address or maps_service.reverse_geocode(payload.latitude, payload.longitude)

    db.commit()
    db.refresh(project)
    return _to_out(project)


@router.post("/projects/{project_id}/problem-image")
def upload_problem_image(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    project = _get_owned_project(db, project_id, teacher.id)

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
        "problem_image_url": project.problem_image_url,
        "analysis": json.loads(project.problem_image_analysis_json),
    }


@router.post("/projects/{project_id}/start", response_model=schemas.GroupOut)
def start_project(
    project_id: str,
    db: Session = Depends(get_db),
    student: models.User = Depends(require_student),
):
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