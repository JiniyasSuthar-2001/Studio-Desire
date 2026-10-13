from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username or studio identifier")
    password: str = Field(..., description="Account password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    must_change_password: bool
    user_id: int


class UserProfileOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=6, description="New secret password (min 6 chars)")


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
