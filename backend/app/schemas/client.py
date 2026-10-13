from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ClientBase(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ProjectShortOut(BaseModel):
    id: int
    title: str
    slug: str
    category: str
    status: str
    is_published: bool
    cover_image: Optional[str] = None

    class Config:
        from_attributes = True


class ClientOut(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    project_count: int = 0

    class Config:
        from_attributes = True


class ClientDetailOut(ClientOut):
    projects: List[ProjectShortOut] = []

    class Config:
        from_attributes = True
