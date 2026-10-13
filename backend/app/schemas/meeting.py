from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MeetingBase(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    time: Optional[str] = None
    location: Optional[str] = "Studio Desire HQ"
    meeting_type: str = "Client Consultation"
    notes: Optional[str] = None
    participants: Optional[str] = None
    status: str = "SCHEDULED"  # SCHEDULED, COMPLETED, CANCELLED


class MeetingCreate(MeetingBase):
    project_id: Optional[int] = None
    client_id: Optional[int] = None


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    meeting_type: Optional[str] = None
    notes: Optional[str] = None
    participants: Optional[str] = None
    status: Optional[str] = None
    project_id: Optional[int] = None
    client_id: Optional[int] = None


class MeetingOut(MeetingBase):
    id: int
    project_id: Optional[int] = None
    client_id: Optional[int] = None
    project_title: Optional[str] = None
    client_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
