from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class VisualizationSpace(Base):
    """
    Represents a 3D rendered spatial room / architectural volume in Studio Desire's visualization archive.
    """
    __tablename__ = "visualization_spaces"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    project_name = Column(String(255), nullable=False)
    room = Column(String(100), nullable=False, index=True)  # Living Room, Kitchen, Bedroom, Bathroom, Exterior, Dining, Other
    category = Column(String(100), nullable=False, index=True, default="Residential")
    year = Column(Integer, default=2026)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    version = Column(String(50), default="v1")
    status = Column(String(50), default="APPROVED", index=True)  # DRAFT, INTERNAL_REVIEW, CLIENT_REVIEW, APPROVED, REJECTED, ARCHIVED
    software = Column(String(255), default="Corona Renderer · 3ds Max · Unreal Engine VR")
    cover_image = Column(String(1000), nullable=False)
    vr_url = Column(String(1000), nullable=True)
    has_vr = Column(Boolean, default=False, index=True)
    show_qr = Column(Boolean, default=True)                    # Room-level QR visibility
    vr_type = Column(String(50), default="external")           # "external" or "hosted"
    vr_build_entry = Column(String(1000), nullable=True)       # Entry HTML relative path for imported build
    is_published = Column(Boolean, default=True, index=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Secondary perspectives & detail renders belonging to this space
    media = relationship(
        "VisualizationMedia",
        back_populates="space",
        cascade="all, delete-orphan",
        order_by="VisualizationMedia.sort_order"
    )


class VisualizationMedia(Base):
    """
    Secondary 3D perspectives, elevation angles, dusk studies, and detail renders for a room.
    """
    __tablename__ = "visualization_media"

    id = Column(Integer, primary_key=True, index=True)
    space_id = Column(Integer, ForeignKey("visualization_spaces.id", ondelete="CASCADE"), nullable=False)
    url = Column(String(1000), nullable=False)
    caption = Column(String(500), nullable=True)
    angle = Column(String(100), nullable=True)  # e.g., Wide Perspective, Detail Angle, Dusk Lighting
    vr_url = Column(String(1000), nullable=True) # Level 3: Individual render VR
    has_vr = Column(Boolean, default=False)
    show_qr = Column(Boolean, default=False)     # Optional render-level QR visibility
    vr_type = Column(String(50), default="external")
    vr_build_entry = Column(String(1000), nullable=True)
    sort_order = Column(Integer, default=0)

    space = relationship("VisualizationSpace", back_populates="media")
