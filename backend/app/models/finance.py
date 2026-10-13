from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)  # e.g., Advance Token, Stage 1 Milestone, Final Handover
    amount = Column(Float, nullable=False, default=0.0)
    payment_date = Column(String(50), nullable=True, index=True)  # YYYY-MM-DD
    payment_method = Column(String(100), default="Bank Transfer")  # Bank Transfer, Cheque, UPI, Cash, Card
    reference_number = Column(String(100), nullable=True)  # Transaction ID / Cheque No
    status = Column(String(50), default="RECEIVED", index=True)  # PENDING, RECEIVED, OVERDUE, REFUNDED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="payments")
