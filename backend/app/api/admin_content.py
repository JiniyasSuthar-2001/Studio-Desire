import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from app.database.session import get_db
    from app.models.content import SiteContent
    from app.models.user import User, UserRole
    from app.schemas.admin import ContentSectionUpdate
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.content import SiteContent
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.admin import ContentSectionUpdate
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(tags=["Website Content CMS"])

# Strict public content allow-list
# Only sections intentionally designed to be public may be accessible through public endpoints.
ALLOWED_PUBLIC_SECTIONS = {
    "about",
    "contact",
    "slideshow",
    "categories",
    "hero",
    "philosophy",
    "services",
}

# Sensitive sections requiring Master / Admin authority
SENSITIVE_ADMIN_SECTIONS = {
    "email_settings",
    "smtp_settings",
    "system_settings",
    "auth_settings",
    "security_settings",
}

DEFAULT_SECTIONS = {
    "about": {
        "tagline": "Architectural Integrity · Tactile Atmospheres",
        "intro_heading": "Studio Desire is a dedicated interior architecture practice founded in Ahmedabad.",
        "intro_paragraph": "We conceive interior environments as composed spatial atmospheres. Our methodology centers on honest materiality—quarried stone, textured plaster, brushed metal, and calibrated timber—orchestrated with daylight and rigorous detailing.",
        "philosophy": "Our design ethos is quiet, restrained, and deeply architectural. Every joinery junction, shadow gap, and material transition is intentional.",
        "founded_year": 2024,
        "location": "Ahmedabad, Gujarat, India",
        "email": "studiodesire01@gmail.com",
        "principals": [
            {"name": "Zenith Suthar", "role": "Principal Architect & Interior Designer", "phone": "+91 75 75 87 72 25"},
            {"name": "Chetna Bhati", "role": "Design Director & Spatial Strategist", "phone": "+91 87 80 37 04 08"}
        ],
        "approach_points": [
            {"title": "Material Authenticity", "description": "Natural stone, honest timbers, and tactile metals that age with dignity."},
            {"title": "Atmospheric Illumination", "description": "Concealed light channels and soft ambient washes creating depth and calm."},
            {"title": "Architectural Millwork", "description": "Bespoke flush cabinetry and custom detail transitions calibrated to millimeter precision."}
        ]
    },
    "contact": {
        "email": "studiodesire01@gmail.com",
        "phone": "+91 75 75 87 72 25 / +91 87 80 37 04 08",
        "address": "Studio Desire Architecture & Interiors, Ahmedabad, Gujarat, India",
        "hours": "Monday — Saturday: 09:30 — 19:00 IST",
        "enquiry_text": "We welcome residential, hospitality, and corporate interior commissions. Please provide project location, area, and estimated schedule.",
        "instagram": "https://instagram.com/studio_desire",
        "linkedin": "https://linkedin.com/company/studiodesire"
    },
    "slideshow": {
        "auto_play": True,
        "interval_seconds": 5,
        "slides": []
    },
    "categories": {
        "items": [
            {"id": "residential", "name": "Residential", "order": 1, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "office", "name": "Office", "order": 2, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "retail", "name": "Retail", "order": 3, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "apartment", "name": "Apartment", "order": 4, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "cafe", "name": "Café", "order": 5, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "villa", "name": "Villa", "order": 6, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "restaurant", "name": "Restaurant", "order": 7, "is_default": True, "is_active": True, "cover_image": ""},
            {"id": "others", "name": "Others", "order": 8, "is_default": True, "is_active": True, "cover_image": ""}
        ]
    }
}


@router.get("/content/{section}", summary="Public endpoint to read website section content")
def get_public_content(section: str, db: Session = Depends(get_db)):
    """
    Public content accessor strictly protected by ALLOWED_PUBLIC_SECTIONS allow-list.
    Sensitive, administrative, and internal sections are never accessible through this endpoint.
    """
    clean_sec = section.lower().strip()

    if clean_sec not in ALLOWED_PUBLIC_SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content section '{clean_sec}' not found or not publicly accessible."
        )

    record = db.query(SiteContent).filter(SiteContent.section == clean_sec).first()
    if record:
        try:
            return json.loads(record.content_json)
        except Exception:
            return record.content_json

    # Fallback to default schema if not customized yet
    if clean_sec in DEFAULT_SECTIONS:
        return DEFAULT_SECTIONS[clean_sec]

    return {}


@router.get("/admin/content/{section}", summary="Admin endpoint to read editable section content")
def get_admin_content(
    section: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clean_sec = section.lower().strip()

    # Enforce role restrictions on sensitive sections
    if clean_sec in SENSITIVE_ADMIN_SECTIONS:
        user_role = (current_user.role or "").upper()
        if user_role not in [UserRole.MASTER.value, UserRole.OWNER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Master or Admin authorization required to access sensitive system settings."
            )

    record = db.query(SiteContent).filter(SiteContent.section == clean_sec).first()
    if record:
        try:
            content_val = json.loads(record.content_json)
            # Mask passwords if returning email settings
            if clean_sec in ["email_settings", "smtp_settings"] and isinstance(content_val, dict):
                if content_val.get("smtp_password"):
                    content_val["smtp_password"] = "••••••••"
                    content_val["has_password"] = True
        except Exception:
            content_val = record.content_json
        return {
            "section": clean_sec,
            "content": content_val,
            "updated_by": record.updated_by,
            "updated_at": record.updated_at
        }

    default_val = DEFAULT_SECTIONS.get(clean_sec, {})
    return {
        "section": clean_sec,
        "content": default_val,
        "updated_by": "System Default",
        "updated_at": None
    }


@router.put("/admin/content/{section}", summary="Admin endpoint to save customized section content")
def update_admin_content(
    section: str,
    payload: ContentSectionUpdate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    clean_sec = section.lower().strip()
    user_role = (current_user.role or "").upper()

    # SENSITIVE SECTIONS: EDITORS, UPLOADERS, OBSERVERS ARE FORBIDDEN
    if clean_sec in SENSITIVE_ADMIN_SECTIONS:
        if user_role not in [UserRole.MASTER.value, UserRole.OWNER.value, UserRole.ADMIN.value]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User with role '{user_role}' cannot modify sensitive settings ('{clean_sec}')."
            )

    # Validate JSON
    try:
        parsed = json.loads(payload.content_json)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON content: {str(e)}")

    record = db.query(SiteContent).filter(SiteContent.section == clean_sec).first()
    if not record:
        record = SiteContent(
            section=clean_sec,
            content_json=payload.content_json,
            updated_by=current_user.username
        )
        db.add(record)
    else:
        record.content_json = payload.content_json
        record.updated_by = current_user.username

    db.commit()

    log_activity(
        db, current_user,
        action="Updated Website Content",
        entity_type="content",
        entity_id=clean_sec,
        details=f"Edited '{clean_sec}' section"
    )

    return {
        "success": True,
        "section": clean_sec,
        "message": f"Section '{clean_sec}' updated successfully."
    }
