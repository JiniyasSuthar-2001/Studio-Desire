import urllib.parse
import io
import os
try:
    import qrcode
    import qrcode.image.svg
except ImportError:
    qrcode = None
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.project import Project
from app.models.blueprint import BlueprintDrawing
from app.schemas.visualization import (
    VisualizationSpaceSummaryOut,
    VisualizationSpaceDetailOut,
    VisualizationProjectArchiveOut,
    VisualizationListResponse
)

router = APIRouter(prefix="/visualizations", tags=["3D Visual Exploration"])

ALLOWED_QR_SCHEMES = {"http", "https"}
MAX_QR_URL_LENGTH = 2048


def validate_qr_url(url: str, request: Optional[Request] = None) -> str:
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid VR URL is required to generate a QR code."
        )
    
    clean_url = url.strip()

    # If it's a relative path (e.g. self-hosted build), resolve with base URL
    if clean_url.startswith("/"):
        base = os.getenv("PUBLIC_SITE_URL")
        if not base and request:
            base = str(request.base_url).rstrip("/")
        if not base:
            base = "http://localhost:8000"
        clean_url = f"{base.rstrip('/')}{clean_url}"

    if len(clean_url) > MAX_QR_URL_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL exceeds maximum allowed length of {MAX_QR_URL_LENGTH} characters."
        )

    # Disallow control characters
    if any(ord(c) < 32 or ord(c) == 127 for c in clean_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL contains invalid control characters."
        )

    try:
        parsed = urllib.parse.urlparse(clean_url)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed URL provided."
        )

    if not parsed.scheme or parsed.scheme.lower() not in ALLOWED_QR_SCHEMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTTP and HTTPS URLs are permitted for QR code generation."
        )

    if not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must include a valid domain/host."
        )

    return clean_url


@router.get("/qr", summary="Generate dynamic vector SVG QR code for any configured VR URL")
def generate_dynamic_qr(
    request: Request,
    url: str = Query(..., description="The real target VR URL to encode")
):
    """
    Generates a crisp architectural SVG QR code for any real configured VR URL.
    Strictly validates URL scheme (only http/https) and blocks dangerous schemes.
    """
    clean_url = validate_qr_url(url, request)

    if qrcode is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR generation service unavailable. Ensure 'qrcode' Python package is installed."
        )

    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=factory
    )
    qr.add_data(clean_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#141413", back_color="transparent")

    stream = io.BytesIO()
    img.save(stream)
    svg_content = stream.getvalue()

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400"
        }
    )

@router.get("/projects-archive", response_model=List[VisualizationProjectArchiveOut], summary="List projects with their multi-room 3D visualizations and central VR")
def get_projects_visualization_archive(
    project_slug: Optional[str] = Query(None, description="Optional filter by specific project slug"),
    db: Session = Depends(get_db)
):
    # Fetch published projects
    proj_query = db.query(Project).filter(Project.is_published == True)
    if isinstance(project_slug, str) and project_slug.strip():
        proj_query = proj_query.filter(Project.slug == project_slug.strip())
    
    projects = proj_query.order_by(Project.featured.desc(), Project.year.desc(), Project.id.asc()).all()

    # Also fetch all published spaces
    all_spaces = db.query(VisualizationSpace).filter(VisualizationSpace.is_published == True).order_by(
        VisualizationSpace.sort_order.asc(),
        VisualizationSpace.id.asc()
    ).all()

    # Map spaces to projects
    project_spaces_map = {}
    for space in all_spaces:
        key = space.project_id
        if not key:
            matching_p = next((p for p in projects if p.title.lower() == space.project_name.lower() or p.slug.lower() in space.slug.lower()), None)
            if matching_p:
                key = matching_p.id

        if key:
            if key not in project_spaces_map:
                project_spaces_map[key] = []
            project_spaces_map[key].append(space)

    results = []
    for p in projects:
        rooms = project_spaces_map.get(p.id, [])
        if rooms or (p.vr_url and p.vr_url.strip()):
            has_central = bool(p.vr_url and p.vr_url.strip())
            results.append({
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "subtitle": p.subtitle,
                "location": p.location,
                "year": p.year,
                "category": p.category,
                "description": p.description,
                "cover_image": p.cover_image,
                "vr_url": p.vr_url if has_central else None,
                "has_central_vr": has_central,
                "rooms": rooms
            })

    return results


@router.get("", response_model=VisualizationListResponse, summary="List all 3D rendered spaces with optional category filter")
def get_visualizations(
    category: Optional[str] = Query(None, description="Filter by room category (e.g. Living Room, Bedroom, Kitchen & Dining)"),
    db: Session = Depends(get_db)
):
    query = db.query(VisualizationSpace).filter(VisualizationSpace.is_published == True)

    if category and category.upper() != "ALL":
        query = query.filter(func.lower(VisualizationSpace.category) == category.lower())

    spaces = query.order_by(VisualizationSpace.sort_order.asc(), VisualizationSpace.id.asc()).all()
    return {
        "total": len(spaces),
        "spaces": spaces
    }

@router.get("/categories", response_model=List[str], summary="Get distinct room categories in the 3D archive")
def get_categories(db: Session = Depends(get_db)):
    distinct_categories = db.query(VisualizationSpace.category).filter(VisualizationSpace.is_published == True).distinct().all()
    cats = [c[0].upper() for c in distinct_categories if c[0]]
    all_cats = ["ALL"]
    for c in sorted(cats):
        if c not in all_cats:
            all_cats.append(c)
    return all_cats

@router.get("/{slug_or_id}", response_model=VisualizationSpaceDetailOut, summary="Get full room visualization dossier by slug or ID")
def get_visualization_detail(slug_or_id: str, db: Session = Depends(get_db)):
    space = None
    if slug_or_id.isdigit():
        space = db.query(VisualizationSpace).filter(VisualizationSpace.id == int(slug_or_id), VisualizationSpace.is_published == True).first()
    
    if not space:
        space = db.query(VisualizationSpace).filter(VisualizationSpace.slug == slug_or_id, VisualizationSpace.is_published == True).first()

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"3D visualization space '{slug_or_id}' was not found in the studio archive."
        )

    return space

@router.get("/{slug_or_id}/qr", summary="Generate dynamic vector SVG QR code for the room's VR URL")
def get_vr_qr_code(slug_or_id: str, db: Session = Depends(get_db)):
    space = None
    if slug_or_id.isdigit():
        space = db.query(VisualizationSpace).filter(VisualizationSpace.id == int(slug_or_id), VisualizationSpace.is_published == True).first()
    
    if not space:
        space = db.query(VisualizationSpace).filter(VisualizationSpace.slug == slug_or_id, VisualizationSpace.is_published == True).first()

    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not space.has_vr or not space.vr_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This space does not have an active VR experience configured yet."
        )

    clean_vr_url = validate_qr_url(space.vr_url)

    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=factory
    )
    qr.add_data(clean_vr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#141413", back_color="transparent")
    
    stream = io.BytesIO()
    img.save(stream)
    svg_content = stream.getvalue()

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=86400"
        }
    )
