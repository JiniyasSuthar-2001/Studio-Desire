from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class BlueprintDrawing(Base):
    __tablename__ = "blueprint_drawings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    project_name = Column(String(255), nullable=False)
    project_slug = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    
    # Blueprint Categories: Floor Plan, Furniture Layout, Electrical, Plumbing, Ceiling, Lighting, Flooring, Elevation, Section, Detail Drawing, Other
    drawing_type = Column(String(100), nullable=False, index=True, default="Floor Plan")
    room_area = Column(String(100), nullable=True)  # e.g., Master Bedroom, Living Pavilion, Culinary Studio
    drawing_number = Column(String(100), nullable=True)  # e.g., SD-HB-WD-04
    
    # Versioning: v1, v2, v3 CURRENT or R0, R1, R2
    revision = Column(String(50), nullable=True, default="v1")
    version = Column(String(50), nullable=True, default="v1")
    status = Column(String(50), default="APPROVED", index=True)  # DRAFT, INTERNAL_REVIEW, CLIENT_REVIEW, APPROVED, ARCHIVED
    
    date = Column(String(50), nullable=True)
    scale = Column(String(50), nullable=True)  # e.g., 1:20 @ A2, 1:50 @ A1, NTS
    sheet_size = Column(String(20), nullable=True)  # e.g., A1, A2, A3
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    uploaded_by = Column(String(100), nullable=True)
    
    thumbnail_url = Column(String(1000), nullable=False)
    file_url = Column(String(1000), nullable=False)
    file_type = Column(String(20), nullable=False, default="image")  # "image" or "pdf"
    sort_order = Column(Integer, default=0, index=True)
    is_demo = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to parent Project
    project = relationship("Project", back_populates="blueprint_drawings", foreign_keys=[project_id])
