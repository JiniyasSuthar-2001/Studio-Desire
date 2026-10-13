from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    username = Column(String(100), nullable=False, index=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100), nullable=True, index=True)  # project, media, visualization, blueprint, content, user
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
