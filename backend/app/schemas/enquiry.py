from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class EnquiryAttachmentOut(BaseModel):
    id: int
    original_filename: str
    filename: str
    file_type: str
    mime_type: str
    file_size: int
    url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnquiryDetailOut(BaseModel):
    id: int
    reference_number: str
    name: str
    email: str
    phone: str
    project_type: str
    location: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    message: str
    source: str
    status: str
    assigned_user: Optional[str] = None
    internal_notes: Optional[str] = None
    email_sent: bool
    email_error: Optional[str] = None
    converted_client_id: Optional[int] = None
    converted_project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    attachments: List[EnquiryAttachmentOut] = []

    model_config = ConfigDict(from_attributes=True)


class EnquiryListOut(BaseModel):
    id: int
    reference_number: str
    name: str
    email: str
    phone: str
    project_type: str
    location: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    source: str
    status: str
    assigned_user: Optional[str] = None
    email_sent: bool
    attachments_count: int = 0
    converted_client_id: Optional[int] = None
    converted_project_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnquiryUpdate(BaseModel):
    status: Optional[str] = None
    assigned_user: Optional[str] = None
    internal_notes: Optional[str] = None
    project_type: Optional[str] = None


class ConvertToClientRequest(BaseModel):
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ConvertToProjectRequest(BaseModel):
    title: str
    client_id: Optional[int] = None
    category: str = "Residential"
    project_type: Optional[str] = "Private Residence"
    location: Optional[str] = None
    year: int = 2026
    budget: float = 0.0
    status: str = "CONSULTATION"


class EnquiryCreateResponse(BaseModel):
    success: bool
    reference_number: str
    message: str
    enquiry_id: int


class EmailSettingsSchema(BaseModel):
    sender_name: str = "Studio Desire"
    sender_email: str = "studiodesire01@gmail.com"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    security: str = "TLS"  # TLS, SSL, None
    smtp_username: str = ""
    smtp_password: Optional[str] = None
    recipients: List[str] = ["studiodesire01@gmail.com"]
    send_customer_confirmation: bool = True


class EmailTestSchema(BaseModel):
    recipient: Optional[str] = None
