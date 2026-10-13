import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app.database.session import Base


class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    MASTER = "MASTER"
    ADMIN = "ADMIN"
    DESIGNER = "DESIGNER"
    EDITOR = "EDITOR"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    UPLOADER = "UPLOADER"
    VIEWER = "VIEWER"
    OBSERVER = "OBSERVER"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.VIEWER.value, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
