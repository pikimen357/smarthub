from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, EmailStr


# ---------- Auth ----------
class RegisterRequest(BaseModel):
    role: str  # "teacher" | "student"
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    name: str


# ---------- User ----------
class UserOut(BaseModel):
    id: str
    role: str
    name: str
    email: str
    phone: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Class ----------
class ClassCreate(BaseModel):
    name: str


class ClassOut(BaseModel):
    id: str
    name: str
    token: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClassJoinRequest(BaseModel):
    token: str


# ---------- Project (Tugas/Studi Kasus) ----------
class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None  # "draft" | "published"


class ProjectOut(BaseModel):
    id: str
    class_id: str
    title: str
    description: Optional[str]
    problem_image_url: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Module ----------
class ModuleCreate(BaseModel):
    title: str
    content_text: Optional[str] = None


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    content_text: Optional[str] = None


class ModuleOut(BaseModel):
    id: str
    project_id: str
    title: str
    content_text: Optional[str]

    class Config:
        from_attributes = True


# ---------- Rubric ----------
class RubricCriteria(BaseModel):
    criteria: str
    description: str
    max_score: int = 100


class RubricUpdate(BaseModel):
    criteria: List[RubricCriteria]


class RubricOut(BaseModel):
    id: str
    project_id: str
    criteria: List[RubricCriteria]

    class Config:
        from_attributes = True


# ---------- Group ----------
class GroupCreate(BaseModel):
    name: str
    student_ids: List[str] = []


class GroupOut(BaseModel):
    id: str
    project_id: str
    name: str
    status: str

    class Config:
        from_attributes = True


# ---------- Discussion ----------
class ChatMessageIn(BaseModel):
    message: str


class ChatMessageOut(BaseModel):
    role: str
    message: str
    timestamp: datetime


class DiscussionOut(BaseModel):
    group_id: str
    chat_history: List[ChatMessageOut]


# ---------- Task / Checklist ----------
class TaskOut(BaseModel):
    id: str
    group_id: str
    type: str
    item_desc: str
    is_checked: bool

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    is_checked: bool


# ---------- Submission ----------
class SubmissionCreate(BaseModel):
    conclusion_text: str


class SubmissionOut(BaseModel):
    id: str
    group_id: str
    final_image_url: Optional[str]
    conclusion_text: Optional[str]
    grade_score: Optional[float]
    feedback_text: Optional[str]

    class Config:
        from_attributes = True


class GradeRequest(BaseModel):
    grade_score: float
    feedback_text: Optional[str] = None


# ---------- AI ----------
class ImageAnalysisResult(BaseModel):
    objects: List[dict]
    total_count: int
    marked_image_url: Optional[str] = None


# ---------- Quest Map ----------
class QuestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    module_id: Optional[str] = None
    # Isi salah satu: latitude+longitude (pin manual di map), ATAU address (akan di-geocode otomatis)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class QuestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    module_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None


class QuestOut(BaseModel):
    id: str
    project_id: str
    module_id: Optional[str]
    title: str
    description: Optional[str]
    image_url: Optional[str]
    latitude: float
    longitude: float
    address: Optional[str]
    map_preview_url: Optional[str] = None  # URL Static Map (di-generate saat response)

    class Config:
        from_attributes = True