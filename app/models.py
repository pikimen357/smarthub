import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey, DateTime, Enum, Float
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class RoleEnum(str, enum.Enum):
    teacher = "teacher"
    student = "student"


class GroupStatusEnum(str, enum.Enum):
    belum_mulai = "belum_mulai"
    diskusi_ai = "diskusi_ai"
    praktik = "praktik"
    selesai = "selesai"


class TaskTypeEnum(str, enum.Enum):
    alat = "alat"
    bahan = "bahan"
    langkah = "langkah"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    role = Column(Enum(RoleEnum), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    classes = relationship("Class", back_populates="teacher")


class Class(Base):
    __tablename__ = "classes"

    id = Column(String, primary_key=True, default=gen_id)
    teacher_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    problem_description = Column(Text, nullable=True)
    problem_image_url = Column(String, nullable=True)
    problem_image_analysis_json = Column(Text, nullable=True)  # hasil deteksi objek AI
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User", back_populates="classes")
    modules = relationship("Module", back_populates="klass", cascade="all, delete-orphan")
    rubric = relationship("Rubric", back_populates="klass", uselist=False, cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="klass", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id = Column(String, primary_key=True, default=gen_id)
    class_id = Column(String, ForeignKey("classes.id"), nullable=False)
    title = Column(String, nullable=False)
    content_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    klass = relationship("Class", back_populates="modules")


class Rubric(Base):
    __tablename__ = "rubrics"

    id = Column(String, primary_key=True, default=gen_id)
    class_id = Column(String, ForeignKey("classes.id"), unique=True, nullable=False)
    criteria_json = Column(Text, nullable=False)  # JSON string list of {criteria, description, max_score}
    created_at = Column(DateTime, default=datetime.utcnow)

    klass = relationship("Class", back_populates="rubric")


class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=gen_id)
    class_id = Column(String, ForeignKey("classes.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(Enum(GroupStatusEnum), default=GroupStatusEnum.belum_mulai)
    created_at = Column(DateTime, default=datetime.utcnow)

    klass = relationship("Class", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    discussion = relationship("Discussion", back_populates="group", uselist=False, cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="group", cascade="all, delete-orphan")
    submission = relationship("Submission", back_populates="group", uselist=False, cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    student_id = Column(String, ForeignKey("users.id"), nullable=False)

    group = relationship("Group", back_populates="members")
    student = relationship("User")


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, ForeignKey("groups.id"), unique=True, nullable=False)
    chat_history_json = Column(Text, default="[]")  # JSON list of {role, message, timestamp}
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group = relationship("Group", back_populates="discussion")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    type = Column(Enum(TaskTypeEnum), nullable=False)
    item_desc = Column(String, nullable=False)
    order_index = Column(Integer, default=0)
    is_checked = Column(Boolean, default=False)

    group = relationship("Group", back_populates="tasks")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, default=gen_id)
    group_id = Column(String, ForeignKey("groups.id"), unique=True, nullable=False)
    final_image_url = Column(String, nullable=True)
    conclusion_text = Column(Text, nullable=True)
    grade_score = Column(Float, nullable=True)
    feedback_text = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    graded_at = Column(DateTime, nullable=True)

    group = relationship("Group", back_populates="submission")
