from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class ProjectFile(Base):
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Other", index=True)  # Contracts, Quotations, Invoices, Blueprints, 3D, Photos, Videos, Material Documents, Other
    file_url = Column(String(1000), nullable=False)
    file_type = Column(String(50), nullable=True)  # pdf, docx, dwg, xlsx, zip, image, etc.
    file_size = Column(Integer, default=0)  # bytes
    uploaded_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="files")
