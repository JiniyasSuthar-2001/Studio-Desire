from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    date = Column(String(50), nullable=False, index=True)  # YYYY-MM-DD
    time = Column(String(50), nullable=True)  # e.g., 14:30 or 2:30 PM
    location = Column(String(255), nullable=True)  # e.g., Studio Desire HQ, Site Visit, Zoom
    meeting_type = Column(String(100), default="Client Consultation", index=True)  # Consultation, Design Review, Site Visit, Material Selection, Budget Review
    notes = Column(Text, nullable=True)
    participants = Column(String(500), nullable=True)  # Comma separated or string list
    status = Column(String(50), default="SCHEDULED", index=True)  # SCHEDULED, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="meetings")
    client = relationship("Client", back_populates="meetings")
