from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class SiteContent(Base):
    __tablename__ = "site_contents"

    id = Column(Integer, primary_key=True, index=True)
    section = Column(String(100), unique=True, index=True, nullable=False)  # about, contact, planning, footer, settings
    content_json = Column(Text, nullable=False)  # JSON string representation
    updated_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
