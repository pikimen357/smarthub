from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_teacher
from app.services import maps_service

router = APIRouter(tags=["Quest Map"])


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


def _to_out(quest: models.Quest) -> schemas.QuestOut:
    out = schemas.QuestOut.model_validate(quest)
    out.map_preview_url = maps_service.static_map_url(quest.latitude, quest.longitude)
    return out


@router.post("/projects/{project_id}/quests", response_model=schemas.QuestOut)
def create_quest(
    project_id: str,
    payload: schemas.QuestCreate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    _get_owned_project(db, project_id, teacher.id)

    if payload.latitude is not None and payload.longitude is not None:
        latitude, longitude = payload.latitude, payload.longitude
        address = payload.address or maps_service.reverse_geocode(latitude, longitude)
    elif payload.address:
        geo = maps_service.geocode_address(payload.address)
        latitude, longitude, address = geo["latitude"], geo["longitude"], geo["formatted_address"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Isi salah satu: (latitude & longitude) atau address",
        )

    quest = models.Quest(
        project_id=project_id,
        module_id=payload.module_id,
        title=payload.title,
        description=payload.description,
        latitude=latitude,
        longitude=longitude,
        address=address,
    )
    db.add(quest)
    db.commit()
    db.refresh(quest)
    return _to_out(quest)


@router.get("/projects/{project_id}/quests", response_model=list[schemas.QuestOut])
def list_quests(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Menampilkan semua pin/quest untuk ditampilkan di Quest Map (guru & siswa)."""
    quests = db.query(models.Quest).filter(models.Quest.project_id == project_id).all()
    return [_to_out(q) for q in quests]


@router.get("/quests/{quest_id}", response_model=schemas.QuestOut)
def get_quest(
    quest_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest tidak ditemukan")
    return _to_out(quest)


@router.put("/quests/{quest_id}", response_model=schemas.QuestOut)
def update_quest(
    quest_id: str,
    payload: schemas.QuestUpdate,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest tidak ditemukan")
    _get_owned_project(db, quest.project_id, teacher.id)  # pastikan quest milik project guru ini

    if payload.title is not None:
        quest.title = payload.title
    if payload.description is not None:
        quest.description = payload.description
    if payload.module_id is not None:
        quest.module_id = payload.module_id

    if payload.address and payload.latitude is None:
        geo = maps_service.geocode_address(payload.address)
        quest.latitude, quest.longitude, quest.address = (
            geo["latitude"], geo["longitude"], geo["formatted_address"],
        )
    elif payload.latitude is not None and payload.longitude is not None:
        quest.latitude, quest.longitude = payload.latitude, payload.longitude
        quest.address = payload.address or maps_service.reverse_geocode(payload.latitude, payload.longitude)

    db.commit()
    db.refresh(quest)
    return _to_out(quest)


@router.delete("/quests/{quest_id}")
def delete_quest(
    quest_id: str,
    db: Session = Depends(get_db),
    teacher: models.User = Depends(require_teacher),
):
    quest = db.query(models.Quest).filter(models.Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest tidak ditemukan")
    _get_owned_project(db, quest.project_id, teacher.id)

    db.delete(quest)
    db.commit()
    return {"detail": "Quest berhasil dihapus"}