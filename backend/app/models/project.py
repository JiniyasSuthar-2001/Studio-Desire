from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.session import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id = Column(Integer, ForeignKey("portfolio_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    subcategory_id = Column(Integer, ForeignKey("portfolio_subcategories.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    subtitle = Column(String(500), nullable=True)
    location = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False, default=2026)
    category = Column(String(100), index=True, nullable=False, default="Residential")  # Residential, Commercial, Hospitality, Office, Retail
    project_type = Column(String(255), nullable=True)          # e.g., Private Residence, High-Rise Penthouse, Luxury Villa
    area = Column(String(100), nullable=True)                  # e.g., 6,400 sq.ft
    description = Column(Text, nullable=False, default="")
    cover_image = Column(String(1000), nullable=False, default="/uploads/projects/placeholder.webp")
    
    # Workflow & Lifecycle Status
    status = Column(String(50), default="PLANNING", index=True)  # ENQUIRY, CONSULTATION, PLANNING, DESIGN, CLIENT_REVIEW, APPROVAL, EXECUTION, COMPLETED, ARCHIVED
    start_date = Column(String(50), nullable=True)
    expected_completion_date = Column(String(50), nullable=True)
    actual_completion_date = Column(String(50), nullable=True)

    # Financial Summary
    budget = Column(Float, default=0.0)
    project_value = Column(Float, default=0.0)
    amount_received = Column(Float, default=0.0)
    amount_pending = Column(Float, default=0.0)

    # Publishing & Presentation
    featured = Column(Boolean, default=False, index=True)
    is_demo = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False, index=True)
    vr_url = Column(String(1000), nullable=True)               # Level 1: Project-wide Central VR
    vr_qr_code = Column(String(1000), nullable=True)          # Central QR code image/data
    show_qr = Column(Boolean, default=True)                    # Project-level QR visibility
    vr_type = Column(String(50), default="external")           # "external" or "hosted"
    vr_build_entry = Column(String(1000), nullable=True)       # Entry HTML relative path for imported build
    grid_span = Column(String(50), default="span-6")           # Editorial CSS grid span
    aspect_ratio = Column(String(50), default="ratio-standard")# Editorial image ratio
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="projects")
    portfolio_category = relationship("PortfolioCategory", back_populates="projects", foreign_keys=[category_id])
    portfolio_subcategory = relationship("PortfolioSubcategory", back_populates="projects", foreign_keys=[subcategory_id])
    media = relationship(
        "ProjectMedia", 
        back_populates="project", 
        cascade="all, delete-orphan",
        order_by="ProjectMedia.sort_order"
    )
    blueprint_drawings = relationship(
        "BlueprintDrawing",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="BlueprintDrawing.sort_order"
    )
    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Task.id"
    )
    milestones = relationship(
        "ProjectMilestone",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMilestone.order"
    )
    materials = relationship(
        "ProjectMaterial",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMaterial.id"
    )
    meetings = relationship(
        "Meeting",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Meeting.date"
    )
    files = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectFile.id"
    )
    payments = relationship(
        "PaymentRecord",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="PaymentRecord.id"
    )


class ProjectMedia(Base):
    __tablename__ = "project_media"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True) # Nullable for unassigned media
    media_type = Column(String(50), nullable=False, default="image")  # "image", "video", "3d", "blueprint", "document", "vr"
    url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    title = Column(String(255), nullable=True)
    caption = Column(String(500), nullable=True)
    alt_text = Column(String(500), nullable=True)
    room_name = Column(String(100), nullable=True, index=True)
    status = Column(String(50), default="published", index=True)  # "draft", "published", "unassigned"
    is_published = Column(Boolean, default=True, index=True)
    sort_order = Column(Integer, default=0, index=True)
    vr_url = Column(String(1000), nullable=True)               # Level 3: Individual project photograph VR destination
    has_vr = Column(Boolean, default=False, index=True)
    show_qr = Column(Boolean, default=False)                   # Optional image-specific QR visibility (off by default)
    vr_type = Column(String(50), default="external")           # "external" or "hosted"
    vr_build_entry = Column(String(1000), nullable=True)       # Entry HTML relative path for imported build
    version = Column(String(50), default="v1")
    uploaded_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="media")
