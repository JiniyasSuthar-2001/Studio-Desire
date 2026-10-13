from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.finance import PaymentRecord
    from app.models.project import Project
    from app.models.user import User
    from app.schemas.finance import PaymentCreate, PaymentUpdate, PaymentOut, ProjectFinanceOut, OverallFinanceSummary
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.finance import PaymentRecord
    from backend.app.models.project import Project
    from backend.app.models.user import User
    from backend.app.schemas.finance import PaymentCreate, PaymentUpdate, PaymentOut, ProjectFinanceOut, OverallFinanceSummary
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/finance", tags=["Admin Finance & Payments"])


def recalculate_project_finances(project_id: int, db: Session):
    """
    Recalculates received and pending amounts for a project based on real payment records.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return

    total_received = db.query(func.sum(PaymentRecord.amount)).filter(
        PaymentRecord.project_id == project_id,
        PaymentRecord.status == "RECEIVED"
    ).scalar() or 0.0

    project.amount_received = float(total_received)
    effective_value = project.project_value or project.budget or 0.0
    project.amount_pending = max(0.0, float(effective_value) - float(total_received))
    db.commit()


@router.get("/summary", response_model=OverallFinanceSummary, summary="Get high-level studio financial summary")
def get_finance_summary(
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    total_budget = db.query(func.sum(Project.budget)).scalar() or 0.0
    total_project_value = db.query(func.sum(Project.project_value)).scalar() or 0.0
    total_received = db.query(func.sum(PaymentRecord.amount)).filter(PaymentRecord.status == "RECEIVED").scalar() or 0.0

    effective_total = total_project_value or total_budget
    total_pending = max(0.0, float(effective_total) - float(total_received))

    recent_payments_db = db.query(PaymentRecord).order_by(PaymentRecord.id.desc()).limit(10).all()
    recent_outs = []
    for p in recent_payments_db:
        recent_outs.append(
            PaymentOut(
                id=p.id,
                project_id=p.project_id,
                project_title=p.project.title if p.project else "Unknown Project",
                title=p.title,
                amount=p.amount,
                payment_date=p.payment_date,
                payment_method=p.payment_method or "Bank Transfer",
                reference_number=p.reference_number,
                status=p.status or "RECEIVED",
                notes=p.notes,
                created_at=p.created_at
            )
        )

    return OverallFinanceSummary(
        total_budget=float(total_budget),
        total_project_value=float(total_project_value),
        total_received=float(total_received),
        total_pending=float(total_pending),
        recent_payments=recent_outs
    )


@router.get("/project/{project_id}", response_model=ProjectFinanceOut, summary="Get project finance ledger and payment history")
def get_project_finance(
    project_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    recalculate_project_finances(project.id, db)
    db.refresh(project)

    payments = db.query(PaymentRecord).filter(PaymentRecord.project_id == project_id).order_by(PaymentRecord.id.desc()).all()
    p_outs = []
    for p in payments:
        p_outs.append(
            PaymentOut(
                id=p.id,
                project_id=p.project_id,
                project_title=project.title,
                title=p.title,
                amount=p.amount,
                payment_date=p.payment_date,
                payment_method=p.payment_method,
                reference_number=p.reference_number,
                status=p.status,
                notes=p.notes,
                created_at=p.created_at
            )
        )

    val = project.project_value or project.budget or 0.0
    progress = (project.amount_received / val * 100.0) if val > 0 else 0.0

    return ProjectFinanceOut(
        project_id=project.id,
        project_title=project.title,
        budget=project.budget or 0.0,
        project_value=project.project_value or 0.0,
        amount_received=project.amount_received or 0.0,
        amount_pending=project.amount_pending or 0.0,
        payment_progress_percentage=round(min(100.0, progress), 1),
        payments=p_outs
    )


@router.post("/payments", response_model=PaymentOut, summary="Log a project payment record")
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    payment = PaymentRecord(
        project_id=payload.project_id,
        title=payload.title.strip(),
        amount=payload.amount,
        payment_date=payload.payment_date.strip() if payload.payment_date else None,
        payment_method=payload.payment_method.strip() if payload.payment_method else "Bank Transfer",
        reference_number=payload.reference_number.strip() if payload.reference_number else None,
        status=payload.status.upper(),
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    recalculate_project_finances(project.id, db)

    log_activity(db, current_user, action="Logged Payment", entity_type="finance", entity_id=str(payment.id), details=f"Logged ₹{payment.amount:,.2f} ({payment.title}) for '{project.title}'")

    return PaymentOut(
        id=payment.id,
        project_id=payment.project_id,
        project_title=project.title,
        title=payment.title,
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_method=payment.payment_method,
        reference_number=payment.reference_number,
        status=payment.status,
        notes=payment.notes,
        created_at=payment.created_at
    )


@router.put("/payments/{payment_id}", response_model=PaymentOut, summary="Update an existing payment record")
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    payment = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if payload.title is not None:
        payment.title = payload.title.strip()
    if payload.amount is not None:
        payment.amount = payload.amount
    if payload.payment_date is not None:
        payment.payment_date = payload.payment_date.strip() if payload.payment_date else None
    if payload.payment_method is not None:
        payment.payment_method = payload.payment_method.strip()
    if payload.reference_number is not None:
        payment.reference_number = payload.reference_number.strip() if payload.reference_number else None
    if payload.status is not None:
        payment.status = payload.status.upper()
    if payload.notes is not None:
        payment.notes = payload.notes.strip() if payload.notes else None

    db.commit()
    db.refresh(payment)

    recalculate_project_finances(payment.project_id, db)

    proj = db.query(Project).filter(Project.id == payment.project_id).first()
    proj_title = proj.title if proj else "Unknown"

    log_activity(db, current_user, action="Updated Payment Record", entity_type="finance", entity_id=str(payment.id), details=f"Updated payment #{payment.id} for '{proj_title}'")

    return PaymentOut(
        id=payment.id,
        project_id=payment.project_id,
        project_title=proj_title,
        title=payment.title,
        amount=payment.amount,
        payment_date=payment.payment_date,
        payment_method=payment.payment_method,
        reference_number=payment.reference_number,
        status=payment.status,
        notes=payment.notes,
        created_at=payment.created_at
    )


@router.delete("/payments/{payment_id}", summary="Delete payment record")
def delete_payment(
    payment_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    payment = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    proj_id = payment.project_id
    title = payment.title
    db.delete(payment)
    db.commit()

    recalculate_project_finances(proj_id, db)

    log_activity(db, current_user, action="Deleted Payment Record", entity_type="finance", entity_id=str(payment_id), details=f"Deleted payment '{title}'")

    return {"success": True, "message": f"Payment '{title}' deleted."}
