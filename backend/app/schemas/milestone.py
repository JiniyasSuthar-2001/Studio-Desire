from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MilestoneBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    order: int = 0


class MilestoneCreate(MilestoneBase):
    project_id: Optional[int] = None


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    order: Optional[int] = None


class MilestoneOut(MilestoneBase):
    id: int
    project_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
