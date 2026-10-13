from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base

class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(100), nullable=True)
    project_type = Column(String(100), nullable=False)  # Residential, Villa, Apartment, Office, etc.
    location = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    budget_range = Column(String(100), nullable=True)
    status = Column(String(50), default="new")  # "new", "reviewed", "contacted"
    created_at = Column(DateTime, default=datetime.utcnow)
