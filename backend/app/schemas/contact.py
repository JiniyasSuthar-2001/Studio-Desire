from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class ContactInquiryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Client or inquirer full name")
    email: EmailStr = Field(..., description="Valid email address for contact")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    project_type: str = Field(..., min_length=2, max_length=100, description="Type of project or product enquiry")
    location: Optional[str] = Field(None, max_length=255, description="Project geographical location")
    message: str = Field(..., min_length=5, max_length=5000, description="Enquiry details and brief")
    budget_range: Optional[str] = Field(None, max_length=100, description="Optional anticipated investment range")

class ContactInquiryResponse(BaseModel):
    success: bool = True
    message: str
    inquiry_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
