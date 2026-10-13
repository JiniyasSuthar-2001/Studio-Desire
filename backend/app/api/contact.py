import re
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

try:
    from app.core.rate_limiter import enforce_enquiry_rate_limit
    from app.database.session import get_db
    from app.models.contact import ContactInquiry
    from app.models.enquiry import ProjectEnquiry
    from app.schemas.contact import ContactInquiryCreate, ContactInquiryResponse
    from app.services.email_service import send_owner_enquiry_notification, send_customer_confirmation
except ImportError:
    from backend.app.core.rate_limiter import enforce_enquiry_rate_limit
    from backend.app.database.session import get_db
    from backend.app.models.contact import ContactInquiry
    from backend.app.models.enquiry import ProjectEnquiry
    from backend.app.schemas.contact import ContactInquiryCreate, ContactInquiryResponse
    from backend.app.services.email_service import send_owner_enquiry_notification, send_customer_confirmation

logger = logging.getLogger("studio_desire.contact")
router = APIRouter(prefix="/contact", tags=["Contact Inquiries"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def generate_unique_reference(db: Session) -> str:
    """
    Generates a concurrency-safe, collision-free human-friendly reference ID.
    Format: SD-YYYY-XXXXXX
    """
    year = datetime.utcnow().year
    for _ in range(20):
        unique_token = uuid.uuid4().hex[:6].upper()
        candidate_ref = f"SD-{year}-{unique_token}"
        existing = db.query(ProjectEnquiry.id).filter(ProjectEnquiry.reference_number == candidate_ref).first()
        if not existing:
            return candidate_ref
    return f"SD-{year}-{uuid.uuid4().hex[:10].upper()}"


@router.post(
    "",
    response_model=ContactInquiryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_enquiry_rate_limit)],
    summary="Submit a project or consultation enquiry to Studio Desire"
)
def submit_contact_inquiry(
    inquiry_in: ContactInquiryCreate,
    db: Session = Depends(get_db)
):
    clean_name = inquiry_in.name.strip()
    clean_email = inquiry_in.email.strip().lower()
    clean_phone = inquiry_in.phone.strip() if inquiry_in.phone else ""
    clean_type = inquiry_in.project_type.strip()
    clean_location = inquiry_in.location.strip()[:255] if inquiry_in.location and inquiry_in.location.strip() else None
    clean_budget = inquiry_in.budget_range.strip()[:100] if inquiry_in.budget_range and inquiry_in.budget_range.strip() else None
    clean_msg = inquiry_in.message.strip()

    # Input Validation
    if not clean_name or len(clean_name) > 150:
        raise HTTPException(status_code=400, detail="Name is required and must be under 150 characters.")
    if not clean_email or len(clean_email) > 255 or not EMAIL_REGEX.match(clean_email):
        raise HTTPException(status_code=400, detail="A valid email address is required (under 255 characters).")
    if not clean_type or len(clean_type) > 100:
        raise HTTPException(status_code=400, detail="Project type is required and must be under 100 characters.")
    if not clean_msg or len(clean_msg) < 5 or len(clean_msg) > 5000:
        raise HTTPException(status_code=400, detail="Message is required (between 5 and 5,000 characters).")

    ref_number = generate_unique_reference(db)

    # Unified ProjectEnquiry record
    unified_enquiry = ProjectEnquiry(
        reference_number=ref_number,
        name=clean_name,
        email=clean_email,
        phone=clean_phone or "Not provided",
        project_type=clean_type,
        location=clean_location,
        budget=clean_budget,
        timeline=None,
        message=clean_msg,
        source="contact",
        status="NEW"
    )

    try:
        db.add(unified_enquiry)
        db.flush()
    except IntegrityError:
        db.rollback()
        unified_enquiry.reference_number = generate_unique_reference(db)
        db.add(unified_enquiry)
        db.flush()

    # Legacy contact inquiry record for backwards compatibility
    legacy_inquiry = ContactInquiry(
        name=clean_name,
        email=clean_email,
        phone=clean_phone,
        project_type=clean_type,
        location=clean_location,
        message=clean_msg,
        budget_range=clean_budget,
        status="new"
    )
    db.add(legacy_inquiry)
    db.commit()
    db.refresh(unified_enquiry)

    # Attempt Email Notification & Customer Confirmation
    try:
        success, err = send_owner_enquiry_notification(unified_enquiry)
        if success:
            unified_enquiry.email_sent = True
            unified_enquiry.email_error = None
        else:
            unified_enquiry.email_sent = False
            unified_enquiry.email_error = err
        send_customer_confirmation(unified_enquiry)
        db.commit()
    except Exception as email_err:
        logger.error(f"Contact email notification error: {email_err}")
        unified_enquiry.email_sent = False
        unified_enquiry.email_error = str(email_err)
        db.commit()

    return ContactInquiryResponse(
        success=True,
        message=f"Thank you for sharing your project. Your enquiry {unified_enquiry.reference_number} has been received.",
        inquiry_id=unified_enquiry.id,
        created_at=unified_enquiry.created_at
    )
