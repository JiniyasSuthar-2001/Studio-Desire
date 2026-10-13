from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProjectFileBase(BaseModel):
    name: str
    category: str = "Other"
    file_url: str
    file_type: Optional[str] = "pdf"
    file_size: int = 0
    uploaded_by: Optional[str] = None
    notes: Optional[str] = None


class ProjectFileCreate(ProjectFileBase):
    project_id: int


class ProjectFileOut(ProjectFileBase):
    id: int
    project_id: int
    project_title: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
