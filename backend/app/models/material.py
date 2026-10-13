from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class ProjectMaterial(Base):
    __tablename__ = "project_materials"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)  # Marble, Wood, Fabric, Hardware, Lighting, Flooring, Paint, Sanitary, Other
    supplier = Column(String(255), nullable=True)
    reference = Column(String(100), nullable=True)  # SKU / Catalog Code
    price = Column(Float, default=0.0)
    quantity = Column(String(100), nullable=True)  # e.g., "120 sq.m", "4 pieces"
    notes = Column(Text, nullable=True)
    image_url = Column(String(1000), nullable=True)
    status = Column(String(50), default="PROPOSED", index=True)  # PROPOSED, CLIENT_REVIEW, APPROVED, REJECTED, ORDERED, INSTALLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="materials")
