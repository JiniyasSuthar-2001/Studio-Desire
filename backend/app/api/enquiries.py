import os
import re
import uuid
import time
import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, Form, File, UploadFile, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

try:
    from app.core.config import settings
    from app.core.rate_limiter import enforce_enquiry_rate_limit
    from app.database.session import get_db
    from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
    from app.schemas.enquiry import EnquiryCreateResponse
    from app.services.email_service import send_owner_enquiry_notification, send_customer_confirmation
except ImportError:
    from backend.app.core.config import settings
    from backend.app.core.rate_limiter import enforce_enquiry_rate_limit
    from backend.app.database.session import get_db
    from backend.app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
    from backend.app.schemas.enquiry import EnquiryCreateResponse
    from backend.app.services.email_service import send_owner_enquiry_notification, send_customer_confirmation

logger = logging.getLogger("studio_desire.enquiries")
router = APIRouter(prefix="/enquiries", tags=["Public Project Enquiries"])

ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".pdf",
    ".dwg", ".dxf", ".mp4", ".mov", ".zip",
    ".doc", ".docx"
}

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def generate_unique_reference(db: Session) -> str:
    """
    Generates a concurrency-safe, collision-free human-friendly reference ID.
    Format: SD-YYYY-XXXXXX (e.g., SD-2026-A83F1C)
    """
    year = datetime.utcnow().year
    for _ in range(20):
        unique_token = uuid.uuid4().hex[:6].upper()
        candidate_ref = f"SD-{year}-{unique_token}"
        existing = db.query(ProjectEnquiry.id).filter(ProjectEnquiry.reference_number == candidate_ref).first()
        if not existing:
            return candidate_ref
    # Fallback to high-entropy token
    return f"SD-{year}-{uuid.uuid4().hex[:10].upper()}"


def determine_file_type(ext: str, mime: str) -> str:
    ext_lower = ext.lower()
    if ext_lower in [".jpg", ".jpeg", ".png", ".webp"]:
        return "image"
    elif ext_lower == ".pdf":
        return "pdf"
    elif ext_lower in [".mp4", ".mov"]:
        return "video"
    elif ext_lower in [".dwg", ".dxf"]:
        return "drawing"
    return "document"


@router.get("/config", summary="Get public enquiry configuration options")
def get_enquiry_config():
    """Returns available project types, budget tiers, and timeline options."""
    return {
        "project_types": [
            "Residential",
            "Villa",
            "Apartment",
            "Office",
            "Restaurant",
            "Retail",
            "Hospitality",
            "Furniture / Product",
            "Other"
        ],
        "budget_ranges": [
            "₹ 25 Lakhs – 50 Lakhs",
            "₹ 50 Lakhs – 1 Crore",
            "₹ 1 Crore – 2.5 Crores",
            "₹ 2.5 Crores – 5 Crores",
            "Above ₹ 5 Crores",
            "Custom Commission / Under Discussion"
        ],
        "timelines": [
            "Immediate (1 — 3 Months)",
            "3 — 6 Months",
            "6 — 12 Months",
            "Concept Exploration Only"
        ]
    }


@router.post(
    "",
    response_model=EnquiryCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_enquiry_rate_limit)],
    summary="Submit a new public project enquiry with optional rough design uploads"
)
async def submit_enquiry(
    name: str = Form(..., description="Customer full name"),
    email: str = Form(..., description="Customer email address"),
    phone: str = Form(..., description="Customer telephone number"),
    project_type: str = Form(..., description="Project type"),
    message: str = Form(..., description="Project brief or message"),
    location: Optional[str] = Form(None),
    budget: Optional[str] = Form(None),
    timeline: Optional[str] = Form(None),
    source: str = Form("contact", description="'contact' or 'inquiry'"),
    files: Optional[List[UploadFile]] = File(None, description="Optional rough designs, sketches, floor plans"),
    db: Session = Depends(get_db)
):
    # Strict Input Validation & Length Limits
    clean_name = name.strip()
    clean_email = email.strip().lower()
    clean_phone = phone.strip()
    clean_type = project_type.strip()
    clean_message = message.strip()

    if not clean_name or len(clean_name) > 150:
        raise HTTPException(status_code=400, detail="Name is required and must be under 150 characters.")
    if not clean_email or len(clean_email) > 255 or not EMAIL_REGEX.match(clean_email):
        raise HTTPException(status_code=400, detail="A valid email address is required (under 255 characters).")
    if not clean_phone or len(clean_phone) > 50:
        raise HTTPException(status_code=400, detail="Phone number is required and must be under 50 characters.")
    if not clean_type or len(clean_type) > 100:
        raise HTTPException(status_code=400, detail="Project type is required and must be under 100 characters.")
    if not clean_message or len(clean_message) < 5 or len(clean_message) > 5000:
        raise HTTPException(status_code=400, detail="Project brief or message is required (between 5 and 5,000 characters).")

    clean_location = location.strip()[:255] if location and location.strip() else None
    clean_budget = budget.strip()[:100] if budget and budget.strip() else None
    clean_timeline = timeline.strip()[:100] if timeline and timeline.strip() else None
    clean_source = source.strip().lower()[:50] if source else "planning"

    # Concurrency-safe unique reference generation
    ref_number = generate_unique_reference(db)

    enquiry = ProjectEnquiry(
        reference_number=ref_number,
        name=clean_name,
        email=clean_email,
        phone=clean_phone,
        project_type=clean_type,
        location=clean_location,
        budget=clean_budget,
        timeline=clean_timeline,
        message=clean_message,
        source=clean_source,
        status="NEW"
    )

    try:
        db.add(enquiry)
        db.flush()
    except IntegrityError:
        db.rollback()
        # Retry with fresh reference number
        enquiry.reference_number = generate_unique_reference(db)
        db.add(enquiry)
        db.flush()

    # Handle private attachments storage
    storage_dir = settings.ENQUIRY_ATTACHMENTS_DIR
    storage_dir.mkdir(parents=True, exist_ok=True)
    max_file_size = settings.MAX_UPLOAD_SIZE_BYTES
    saved_attachment_paths: List[Path] = []

    if files:
        for file in files:
            if not file.filename:
                continue

            raw_name = file.filename
            # Sanitize filename
            clean_orig_name = Path(raw_name).name.replace("\x00", "").replace("/", "").replace("\\", "")
            ext = Path(clean_orig_name).suffix.lower()

            if not ext or ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
                # Cleanup written files
                for sp in saved_attachment_paths:
                    if sp.exists():
                        sp.unlink()
                raise HTTPException(
                    status_code=400,
                    detail=f"File format '{ext}' is not permitted for attachments. Permitted formats: {', '.join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS))}"
                )

            # Private unique server-side storage filename
            safe_unique_name = f"enq_{enquiry.id}_{int(time.time())}_{uuid.uuid4().hex[:10]}{ext}"
            target_path = (storage_dir / safe_unique_name).resolve()

            # Path traversal check
            if not target_path.is_relative_to(storage_dir):
                for sp in saved_attachment_paths:
                    if sp.exists():
                        sp.unlink()
                raise HTTPException(status_code=400, detail="Invalid attachment storage path.")

            bytes_written = 0
            with open(target_path, "wb") as f_out:
                while chunk := await file.read(1024 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > max_file_size:
                        f_out.close()
                        if target_path.exists():
                            target_path.unlink()
                        for sp in saved_attachment_paths:
                            if sp.exists():
                                sp.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Attachment '{clean_orig_name}' exceeds maximum allowed size of {max_file_size // (1024*1024)} MB."
                        )
                    f_out.write(chunk)

            saved_attachment_paths.append(target_path)
            file_type = determine_file_type(ext, file.content_type or "")

            attachment = ProjectEnquiryAttachment(
                enquiry_id=enquiry.id,
                original_filename=clean_orig_name,
                filename=safe_unique_name,
                file_type=file_type,
                mime_type=file.content_type or "application/octet-stream",
                file_size=bytes_written,
                storage_path=str(target_path),
                url=f"/api/admin/enquiries/{enquiry.id}/attachments/placeholder"
            )
            db.add(attachment)
            db.flush()

            # Update URL with exact attachment ID
            attachment.url = f"/api/admin/enquiries/{enquiry.id}/attachments/{attachment.id}/download"

    db.commit()
    db.refresh(enquiry)

    # Attempt Email Notification & Customer Confirmation
    try:
        success, err = send_owner_enquiry_notification(enquiry)
        if success:
            enquiry.email_sent = True
            enquiry.email_error = None
        else:
            enquiry.email_sent = False
            enquiry.email_error = err

        # Send confirmation to client
        send_customer_confirmation(enquiry)
        db.commit()
    except Exception as email_err:
        logger.error(f"Enquiry notification failed: {email_err}")
        enquiry.email_sent = False
        enquiry.email_error = str(email_err)
        db.commit()

    return EnquiryCreateResponse(
        success=True,
        reference_number=enquiry.reference_number,
        message="Thank you for sharing your project with Studio Desire. Your project enquiry has been successfully received.",
        enquiry_id=enquiry.id
    )
