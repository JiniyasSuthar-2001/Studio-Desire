from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MaterialBase(BaseModel):
    name: str
    category: str
    supplier: Optional[str] = None
    reference: Optional[str] = None
    price: float = 0.0
    quantity: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: str = "PROPOSED"  # PROPOSED, CLIENT_REVIEW, APPROVED, REJECTED, ORDERED, INSTALLED


class MaterialCreate(MaterialBase):
    project_id: int


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    supplier: Optional[str] = None
    reference: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[str] = None
    notes: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


class MaterialOut(MaterialBase):
    id: int
    project_id: int
    project_title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
