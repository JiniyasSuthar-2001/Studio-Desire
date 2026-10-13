from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class ProjectEnquiry(Base):
    """
    Represents a public project enquiry submitted by a client/visitor
    through the Planning page or Contact page.
    """
    __tablename__ = "project_enquiries"

    id = Column(Integer, primary_key=True, index=True)
    reference_number = Column(String(50), unique=True, index=True, nullable=False) # e.g., ENQ-0001
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(100), nullable=False)
    project_type = Column(String(100), nullable=False, index=True) # Residential, Villa, Apartment, Office, etc.
    location = Column(String(255), nullable=True)
    budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    source = Column(String(50), default="planning") # "planning" or "contact"
    
    # Statuses: NEW, CONTACTED, CONSULTATION, PROPOSAL, NEGOTIATION, WON, LOST, ARCHIVED
    status = Column(String(50), default="NEW", index=True)
    assigned_user = Column(String(100), nullable=True)
    internal_notes = Column(Text, nullable=True)
    
    # Email notification tracking
    email_sent = Column(Boolean, default=False)
    email_error = Column(Text, nullable=True)
    
    # Conversion tracking
    converted_client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    converted_project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Attachments (rough sketches, drawings, PDFs, images)
    attachments = relationship(
        "ProjectEnquiryAttachment",
        back_populates="enquiry",
        cascade="all, delete-orphan",
        order_by="ProjectEnquiryAttachment.id"
    )


class ProjectEnquiryAttachment(Base):
    """
    Uploaded rough designs, reference drawings, photographs, and documents
    belonging to an enquiry submission.
    """
    __tablename__ = "project_enquiry_attachments"

    id = Column(Integer, primary_key=True, index=True)
    enquiry_id = Column(Integer, ForeignKey("project_enquiries.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # image, pdf, video, drawing, document
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    storage_path = Column(String(500), nullable=False)
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    enquiry = relationship("ProjectEnquiry", back_populates="attachments")
