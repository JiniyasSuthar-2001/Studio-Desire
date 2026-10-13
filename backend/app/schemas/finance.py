from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class PaymentBase(BaseModel):
    title: str
    amount: float
    payment_date: Optional[str] = None
    payment_method: str = "Bank Transfer"
    reference_number: Optional[str] = None
    status: str = "RECEIVED"  # PENDING, RECEIVED, OVERDUE, REFUNDED
    notes: Optional[str] = None


class PaymentCreate(PaymentBase):
    project_id: int


class PaymentUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    payment_date: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class PaymentOut(PaymentBase):
    id: int
    project_id: int
    project_title: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectFinanceOut(BaseModel):
    project_id: int
    project_title: str
    budget: float
    project_value: float
    amount_received: float
    amount_pending: float
    payment_progress_percentage: float
    payments: List[PaymentOut] = []

    class Config:
        from_attributes = True


class OverallFinanceSummary(BaseModel):
    total_budget: float
    total_project_value: float
    total_received: float
    total_pending: float
    recent_payments: List[PaymentOut] = []
