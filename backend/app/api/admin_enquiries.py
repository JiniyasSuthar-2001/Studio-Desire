import re
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.core.config import settings
    from app.database.session import get_db
    from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
    from app.models.client import Client
    from app.models.project import Project, ProjectMedia
    from app.models.user import User, UserRole
    from app.schemas.enquiry import (
        EnquiryDetailOut,
        EnquiryListOut,
        EnquiryUpdate,
        ConvertToClientRequest,
        ConvertToProjectRequest,
        EmailSettingsSchema,
        EmailTestSchema
    )
    from app.core.dependencies import get_current_user, require_roles, log_activity, security_bearer
    from app.core.security import decode_access_token
    from app.services.email_service import (
        get_email_settings,
        save_email_settings,
        send_owner_enquiry_notification,
        send_smtp_message
    )
except ImportError:
    from backend.app.core.config import settings
    from backend.app.database.session import get_db
    from backend.app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
    from backend.app.models.client import Client
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.enquiry import (
        EnquiryDetailOut,
        EnquiryListOut,
        EnquiryUpdate,
        ConvertToClientRequest,
        ConvertToProjectRequest,
        EmailSettingsSchema,
        EmailTestSchema
    )
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity, security_bearer
    from backend.app.core.security import decode_access_token
    from backend.app.services.email_service import (
        get_email_settings,
        save_email_settings,
        send_owner_enquiry_notification,
        send_smtp_message
    )

router = APIRouter(prefix="/admin", tags=["Admin Enquiries & Leads Pipeline"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


# ==============================================================================
# ENQUIRY CRUD
# ==============================================================================

@router.get("/enquiries", response_model=List[EnquiryListOut], summary="List all customer project enquiries")
def list_enquiries(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectEnquiry)

    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(ProjectEnquiry.status == status_filter.upper())

    if project_type and project_type.upper() != "ALL":
        query = query.filter(ProjectEnquiry.project_type == project_type)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(ProjectEnquiry.name).like(term) |
            func.lower(ProjectEnquiry.email).like(term) |
            func.lower(ProjectEnquiry.reference_number).like(term) |
            func.lower(ProjectEnquiry.phone).like(term) |
            func.lower(ProjectEnquiry.project_type).like(term)
        )

    enquiries = query.order_by(ProjectEnquiry.created_at.desc()).all()

    results = []
    for enq in enquiries:
        results.append({
            "id": enq.id,
            "reference_number": enq.reference_number,
            "name": enq.name,
            "email": enq.email,
            "phone": enq.phone,
            "project_type": enq.project_type,
            "location": enq.location,
            "budget": enq.budget,
            "timeline": enq.timeline,
            "source": enq.source,
            "status": enq.status,
            "assigned_user": enq.assigned_user,
            "email_sent": enq.email_sent,
            "attachments_count": len(enq.attachments),
            "converted_client_id": enq.converted_client_id,
            "converted_project_id": enq.converted_project_id,
            "created_at": enq.created_at
        })

    return results


@router.get("/enquiries/{enquiry_id}", response_model=EnquiryDetailOut, summary="Get full enquiry dossier and attachments")
def get_enquiry_detail(
    enquiry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enquiry = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail=f"Enquiry #{enquiry_id} not found.")

    # Automatically mark as CONTACTED if newly opened
    if enquiry.status == "NEW":
        enquiry.status = "CONTACTED"
        db.commit()
        db.refresh(enquiry)

    return enquiry


@router.get("/enquiries/{enquiry_id}/attachments/{attachment_id}/download", summary="Securely download an enquiry attachment")
@router.get("/enquiries/{enquiry_id}/attachments/{attachment_id}", summary="Securely view an enquiry attachment")
def download_enquiry_attachment(
    enquiry_id: int,
    attachment_id: int,
    token: Optional[str] = Query(None),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
):
    """
    Protected download endpoint for private enquiry attachments (drawings, floor plans, sketches).
    Requires authenticated user with authorized role.
    Strictly verifies attachment ownership and blocks path traversal.
    """
    # Accept token either via standard Authorization Bearer header or via ?token= query param
    jwt_token = (auth.credentials if auth and auth.credentials else None) or token
    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access private enquiry attachments."
        )

    payload = decode_access_token(jwt_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )

    user_role = (payload.get("role") or "").upper()
    allowed_roles = [
        UserRole.MASTER.value,
        UserRole.OWNER.value,
        UserRole.ADMIN.value,
        UserRole.DESIGNER.value,
        UserRole.PROJECT_MANAGER.value,
        UserRole.EDITOR.value
    ]
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have permission to view private enquiry attachments."
        )

    # Verify attachment exists and strictly belongs to this enquiry (prevents ID manipulation between enquiries)
    attachment = db.query(ProjectEnquiryAttachment).filter(
        ProjectEnquiryAttachment.id == attachment_id,
        ProjectEnquiryAttachment.enquiry_id == enquiry_id
    ).first()

    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found or does not belong to the specified enquiry."
        )

    file_path = Path(attachment.storage_path).resolve()

    # Verify file is strictly confined inside private storage directory
    storage_root = settings.ENQUIRY_ATTACHMENTS_DIR.resolve()
    if not file_path.is_relative_to(storage_root):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Attachment file is outside the authorized storage directory."
        )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found on storage.")

    return FileResponse(
        path=str(file_path),
        filename=attachment.original_filename,
        media_type=attachment.mime_type or "application/octet-stream"
    )



@router.patch("/enquiries/{enquiry_id}", response_model=EnquiryDetailOut, summary="Update enquiry status, notes, or assigned user")
def update_enquiry(
    enquiry_id: int,
    payload: EnquiryUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER", "EDITOR"])),
    db: Session = Depends(get_db)
):
    enquiry = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail=f"Enquiry #{enquiry_id} not found.")

    if payload.status:
        enquiry.status = payload.status.upper()
    if payload.assigned_user is not None:
        enquiry.assigned_user = payload.assigned_user
    if payload.internal_notes is not None:
        enquiry.internal_notes = payload.internal_notes
    if payload.project_type:
        enquiry.project_type = payload.project_type

    db.commit()
    db.refresh(enquiry)

    log_activity(
        db, current_user,
        action="Updated Enquiry",
        entity_type="enquiry",
        entity_id=str(enquiry.id),
        details=f"Updated status to {enquiry.status} for {enquiry.reference_number}"
    )

    return enquiry


@router.delete("/enquiries/{enquiry_id}", summary="Permanently delete an enquiry")
def delete_enquiry(
    enquiry_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    enquiry = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found.")

    ref = enquiry.reference_number
    db.delete(enquiry)
    db.commit()

    log_activity(
        db, current_user,
        action="Deleted Enquiry",
        entity_type="enquiry",
        entity_id=str(enquiry_id),
        details=f"Permanently deleted enquiry {ref}"
    )

    return {"success": True, "message": f"Enquiry {ref} has been removed."}


# ==============================================================================
# CONVERSION PIPELINES (ENQUIRY -> CLIENT, ENQUIRY -> PROJECT)
# ==============================================================================

@router.post("/enquiries/{enquiry_id}/convert-to-client", summary="Convert an enquiry into a Client record")
def convert_enquiry_to_client(
    enquiry_id: int,
    payload: ConvertToClientRequest = None,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    enquiry = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found.")

    # Check if already converted
    if enquiry.converted_client_id:
        existing_client = db.query(Client).filter(Client.id == enquiry.converted_client_id).first()
        if existing_client:
            return {
                "success": True,
                "message": f"Enquiry was already converted to Client '{existing_client.name}'.",
                "client_id": existing_client.id,
                "client_name": existing_client.name
            }

    # Check if a client with this email already exists
    client = db.query(Client).filter(Client.email == enquiry.email).first()
    if not client:
        company_val = payload.company if payload and payload.company else None
        address_val = payload.address if payload and payload.address else enquiry.location
        notes_val = payload.notes if payload and payload.notes else f"Converted from Enquiry {enquiry.reference_number}: {enquiry.message}"
        client = Client(
            name=enquiry.name,
            company=company_val,
            email=enquiry.email,
            phone=enquiry.phone,
            address=address_val,
            notes=notes_val
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    enquiry.converted_client_id = client.id
    if enquiry.status == "NEW":
        enquiry.status = "CONSULTATION"
    db.commit()

    log_activity(
        db, current_user,
        action="Converted Enquiry to Client",
        entity_type="client",
        entity_id=str(client.id),
        details=f"Converted {enquiry.reference_number} ({enquiry.name}) into Client '{client.name}'"
    )

    return {
        "success": True,
        "message": f"Successfully converted enquiry to Client '{client.name}'.",
        "client_id": client.id,
        "client_name": client.name
    }


@router.post("/enquiries/{enquiry_id}/convert-to-project", summary="Convert an enquiry into an active draft Project")
def convert_enquiry_to_project(
    enquiry_id: int,
    payload: Optional[ConvertToProjectRequest] = None,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER", "DESIGNER"])),
    db: Session = Depends(get_db)
):
    enquiry = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found.")

    # Ensure client exists
    client_id = payload.client_id if payload and payload.client_id else enquiry.converted_client_id
    if not client_id:
        # Create client automatically
        client = db.query(Client).filter(Client.email == enquiry.email).first()
        if not client:
            client = Client(
                name=enquiry.name,
                email=enquiry.email,
                phone=enquiry.phone,
                address=enquiry.location,
                notes=f"Created via project conversion from {enquiry.reference_number}"
            )
            db.add(client)
            db.commit()
            db.refresh(client)
        client_id = client.id
        enquiry.converted_client_id = client.id

    # Title & slug
    proj_title = payload.title if payload and payload.title else f"{enquiry.name} — {enquiry.project_type}"
    base_slug = slugify(proj_title)
    unique_slug = base_slug
    counter = 1
    while db.query(Project).filter(Project.slug == unique_slug).first():
        unique_slug = f"{base_slug}-{counter}"
        counter += 1

    # Default cover image
    cover_image = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=85"
    image_attachments = [a for a in enquiry.attachments if a.file_type == "image"]
    if image_attachments:
        cover_image = image_attachments[0].url

    cat = payload.category if payload and payload.category else "Residential"
    p_type = payload.project_type if payload and payload.project_type else enquiry.project_type
    p_status = payload.status if payload and payload.status else "CONSULTATION"
    p_budget = payload.budget if payload and payload.budget else 0.0

    new_project = Project(
        title=proj_title,
        slug=unique_slug,
        client_id=client_id,
        subtitle=f"Commission via Enquiry {enquiry.reference_number}",
        location=enquiry.location or "Ahmedabad, Gujarat",
        year=datetime.utcnow().year,
        category=cat,
        project_type=p_type,
        area="To be determined",
        description=enquiry.message,
        cover_image=cover_image,
        status=p_status,
        budget=p_budget,
        project_value=p_budget,
        amount_received=0.0,
        amount_pending=p_budget,
        featured=False,
        is_demo=False,
        is_published=False  # DRAFT
    )
    db.add(new_project)
    db.flush()

    # Link compatible attachments into ProjectMedia
    for idx, att in enumerate(enquiry.attachments):
        m_type = "image"
        if att.file_type in ["image", "video", "blueprint", "document"]:
            m_type = att.file_type
        
        media_item = ProjectMedia(
            project_id=new_project.id,
            media_type=m_type,
            url=att.url,
            thumbnail_url=att.url if m_type == "image" else None,
            caption=f"Client Reference: {att.original_filename}",
            alt_text=att.original_filename,
            sort_order=idx + 1,
            status="draft",
            is_published=False
        )
        db.add(media_item)

    # Update enquiry tracking
    enquiry.status = "WON"
    enquiry.converted_project_id = new_project.id
    db.commit()

    log_activity(
        db, current_user,
        action="Converted Enquiry to Project",
        entity_type="project",
        entity_id=str(new_project.id),
        details=f"Converted {enquiry.reference_number} into project '{new_project.title}'"
    )

    return {
        "success": True,
        "message": f"Successfully created project '{new_project.title}' from {enquiry.reference_number}.",
        "project_id": new_project.id,
        "project_slug": new_project.slug,
        "project_title": new_project.title,
        "client_id": client_id
    }


# ==============================================================================
# EMAIL RETRY & SMTP SETTINGS
# ==============================================================================

@router.post("/enquiries/{enquiry_id}/retry-email", summary="Retry sending email notification for an enquiry")
def retry_enquiry_email(
    enquiry_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    enquiry = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found.")

    success, err = send_owner_enquiry_notification(enquiry)
    if success:
        enquiry.email_sent = True
        enquiry.email_error = None
        db.commit()
        return {"success": True, "message": f"Email notification for {enquiry.reference_number} was sent successfully."}
    else:
        enquiry.email_sent = False
        enquiry.email_error = err
        db.commit()
        raise HTTPException(status_code=500, detail=f"Email delivery failed: {err}")


@router.get("/email/settings", summary="Get SMTP configuration (password masked)")
def get_admin_email_settings(
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    cfg = get_email_settings()
    has_pwd = bool(cfg.get("smtp_password"))
    masked_cfg = dict(cfg)
    masked_cfg["smtp_password"] = "••••••••" if has_pwd else ""
    masked_cfg["has_password"] = has_pwd
    return masked_cfg


@router.put("/email/settings", summary="Update SMTP email configuration")
def update_admin_email_settings(
    payload: EmailSettingsSchema,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    data = payload.model_dump()
    save_email_settings(data, updated_by=current_user.username)
    log_activity(
        db, current_user,
        action="Updated Email Settings",
        entity_type="settings",
        entity_id="email",
        details="Updated SMTP email server configuration"
    )
    return {"success": True, "message": "Email settings updated successfully."}


@router.post("/email/test", summary="Send a test email to verify SMTP configuration")
def test_email_configuration(
    payload: EmailTestSchema,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    cfg = get_email_settings()
    recipient = payload.recipient or (cfg.get("recipients", [])[0] if cfg.get("recipients") else cfg.get("sender_email"))
    if not recipient:
        raise HTTPException(status_code=400, detail="No recipient specified and no default recipient configured.")

    subject = "Studio Desire — SMTP Connection Test"
    text_content = f"This is a test notification from the Studio Desire Owner System sent on {datetime.utcnow().strftime('%d %b %Y %H:%M UTC')}."
    html_content = f"""<div style="font-family: sans-serif; padding: 20px; background: #faf9f7; color: #141413;">
        <h2 style="font-family: Georgia, serif; text-transform: uppercase; margin-bottom: 8px;">Studio Desire</h2>
        <p style="font-size: 14px; color: #22c55e; font-weight: bold;">✔ SMTP Connection Successful</p>
        <p style="font-size: 14px; color: #555;">Your Studio Desire email configuration is working and ready to dispatch project enquiry notifications.</p>
    </div>"""

    success, err = send_smtp_message([recipient], subject, text_content, html_content)
    if success:
        return {"success": True, "message": f"Test email sent successfully to {recipient}."}
    else:
        raise HTTPException(status_code=500, detail=f"SMTP test failed: {err}")
