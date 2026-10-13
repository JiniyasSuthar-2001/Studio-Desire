import io
import os
import zipfile
import shutil
import time
from pathlib import Path
try:
    import qrcode
    import qrcode.image.svg
except ImportError:
    qrcode = None
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File, Form, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

import urllib.parse
from app.database.session import get_db
from app.models.project import Project, ProjectMedia
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.user import User
from app.core.dependencies import get_current_user, require_roles, log_activity
from app.core.config import settings

router = APIRouter(prefix="/admin/vr", tags=["Admin VR & QR Engine"])

ALLOWED_QR_SCHEMES = {"http", "https"}
MAX_QR_URL_LENGTH = 2048
MAX_VR_PACKAGE_SIZE = 100 * 1024 * 1024  # 100 MB max package size
DISALLOWED_PACKAGE_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".py", ".php", ".pl", ".cgi",
    ".msi", ".dll", ".so", ".bin", ".vbs", ".ps1", ".jar"
}


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


class SetProjectVRRequest(BaseModel):
    project_id: int
    vr_url: Optional[str] = None
    vr_type: Optional[str] = "external"
    show_qr: Optional[bool] = True


class SetRoomVRRequest(BaseModel):
    space_id: int
    vr_url: Optional[str] = None
    vr_type: Optional[str] = "external"
    show_qr: Optional[bool] = True


class SetRenderVRRequest(BaseModel):
    media_id: int
    vr_url: Optional[str] = None
    vr_type: Optional[str] = "external"
    show_qr: Optional[bool] = False
    is_project_media: Optional[bool] = False


@router.get("/qr", summary="Generate clean dynamic QR code SVG/PNG for any URL")
def generate_qr_code(
    request: Request,
    url: str = Query(..., description="Target VR URL to encode in QR"),
    format: str = Query("svg", description="Format: 'svg' or 'png'")
):
    """
    Generates an architectural high-contrast QR code vector (SVG) or PNG on the fly.
    Does not invent or cache dummy QR codes.
    """
    clean_url = validate_qr_url(url, request)

    if qrcode is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR generation service unavailable. Ensure 'qrcode' Python package is installed."
        )

    if format.lower() == "png":
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
        )
        qr.add_data(clean_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#121212", back_color="#FAFAFA")
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/png")
    else:
        # SVG format
        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
            image_factory=factory
        )
        qr.add_data(clean_url)
        qr.make(fit=True)
        svg_img = qr.make_image()
        buf = io.BytesIO()
        svg_img.save(buf)
        buf.seek(0)
        return Response(content=buf.getvalue(), media_type="image/svg+xml")


@router.post("/project-vr", summary="Set Level 1 Project-Wide Central VR URL")
def set_project_vr(
    payload: SetProjectVRRequest,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cleaned_url = payload.vr_url.strip() if payload.vr_url else None
    project.vr_url = cleaned_url
    if payload.vr_type:
        project.vr_type = payload.vr_type
    if payload.show_qr is not None:
        project.show_qr = payload.show_qr
    db.commit()

    action = "Updated" if project.vr_url else "Removed"
    log_activity(db, current_user, action=f"{action} Central VR", entity_type="project", entity_id=str(project.id), details=f"{action} central VR URL for '{project.title}'")

    return {
        "success": True,
        "project_id": project.id,
        "vr_url": project.vr_url,
        "has_vr": bool(project.vr_url),
        "vr_type": project.vr_type or "external",
        "show_qr": bool(project.show_qr),
        "qr_api_url": f"/api/admin/vr/qr?url={urllib.parse.quote(project.vr_url)}" if project.vr_url else None
    }


@router.post("/room-vr", summary="Set Level 2 Room-Specific VR URL")
def set_room_vr(
    payload: SetRoomVRRequest,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    space = db.query(VisualizationSpace).filter(VisualizationSpace.id == payload.space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Visualization space not found")

    cleaned_url = payload.vr_url.strip() if payload.vr_url else None
    space.vr_url = cleaned_url
    space.has_vr = bool(cleaned_url)
    if payload.vr_type:
        space.vr_type = payload.vr_type
    if payload.show_qr is not None:
        space.show_qr = payload.show_qr
    db.commit()

    action = "Updated" if space.vr_url else "Removed"
    log_activity(db, current_user, action=f"{action} Room VR", entity_type="visualization", entity_id=str(space.id), details=f"{action} VR URL for room '{space.room}'")

    return {
        "success": True,
        "space_id": space.id,
        "room": space.room,
        "vr_url": space.vr_url,
        "has_vr": space.has_vr,
        "vr_type": getattr(space, "vr_type", "external") or "external",
        "show_qr": getattr(space, "show_qr", True),
        "qr_api_url": f"/api/admin/vr/qr?url={urllib.parse.quote(space.vr_url)}" if space.vr_url else None
    }


@router.post("/render-vr", summary="Set Level 3 Individual 3D Render VR URL")
def set_render_vr(
    payload: SetRenderVRRequest,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    cleaned_url = payload.vr_url.strip() if payload.vr_url else None

    if payload.is_project_media:
        p_media = db.query(ProjectMedia).filter(ProjectMedia.id == payload.media_id).first()
        if not p_media:
            raise HTTPException(status_code=404, detail="Project media item not found")
        p_media.vr_url = cleaned_url
        p_media.has_vr = bool(cleaned_url)
        if payload.vr_type:
            p_media.vr_type = payload.vr_type
        if payload.show_qr is not None:
            p_media.show_qr = payload.show_qr
        db.commit()

        action = "Updated" if p_media.vr_url else "Removed"
        log_activity(db, current_user, action=f"{action} Project Photo VR", entity_type="media", entity_id=str(p_media.id), details=f"{action} VR for photo #{p_media.id}")

        return {
            "success": True,
            "media_id": p_media.id,
            "is_project_media": True,
            "vr_url": p_media.vr_url,
            "has_vr": p_media.has_vr,
            "show_qr": bool(p_media.show_qr),
            "vr_type": p_media.vr_type or "external",
            "qr_api_url": f"/api/admin/vr/qr?url={urllib.parse.quote(p_media.vr_url)}" if p_media.vr_url else None
        }

    # Otherwise visualization media
    media = db.query(VisualizationMedia).filter(VisualizationMedia.id == payload.media_id).first()
    if not media:
        # Check ProjectMedia fallback
        p_media = db.query(ProjectMedia).filter(ProjectMedia.id == payload.media_id).first()
        if p_media:
            p_media.vr_url = cleaned_url
            p_media.has_vr = bool(cleaned_url)
            if payload.vr_type:
                p_media.vr_type = payload.vr_type
            if payload.show_qr is not None:
                p_media.show_qr = payload.show_qr
            db.commit()
            return {
                "success": True,
                "media_id": p_media.id,
                "is_project_media": True,
                "vr_url": p_media.vr_url,
                "has_vr": p_media.has_vr,
                "show_qr": bool(p_media.show_qr),
                "vr_type": p_media.vr_type or "external",
                "qr_api_url": f"/api/admin/vr/qr?url={urllib.parse.quote(p_media.vr_url)}" if p_media.vr_url else None
            }
        raise HTTPException(status_code=404, detail="Visualization render not found")

    media.vr_url = cleaned_url
    media.has_vr = bool(cleaned_url)
    if payload.vr_type:
        media.vr_type = payload.vr_type
    if payload.show_qr is not None:
        media.show_qr = payload.show_qr
    db.commit()

    action = "Updated" if media.vr_url else "Removed"
    log_activity(db, current_user, action=f"{action} Render VR", entity_type="visualization", entity_id=str(media.id), details=f"{action} VR for render #{media.id}")

    return {
        "success": True,
        "media_id": media.id,
        "vr_url": media.vr_url,
        "has_vr": media.has_vr,
        "show_qr": getattr(media, "show_qr", False),
        "vr_type": getattr(media, "vr_type", "external") or "external",
        "qr_api_url": f"/api/admin/vr/qr?url={urllib.parse.quote(media.vr_url)}" if media.vr_url else None
    }


@router.post("/upload-build", summary="Mode B: Import complete self-hosted VR experience (ZIP package)")
async def upload_vr_build(
    file: UploadFile = File(..., description="ZIP archive containing static WebXR/WebGL/360 VR experience"),
    scope: str = Form(..., description="'project', 'room', or 'render'"),
    target_id: int = Form(..., description="ID of project, room, or render media"),
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    """
    Mode B VR Import:
    - Validates zip package
    - Prevents directory traversal & unsafe executables
    - Extracts into dedicated non-executable static directory
    - Finds index.html entry point and saves URL in database
    """
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid archive format. Only .zip packages containing an index.html entry point are supported."
        )

    # Validate target exists
    clean_scope = scope.lower().strip()
    target_obj = None
    if clean_scope == "project":
        target_obj = db.query(Project).filter(Project.id == target_id).first()
        if not target_obj:
            raise HTTPException(status_code=404, detail=f"Project #{target_id} not found")
    elif clean_scope == "room":
        target_obj = db.query(VisualizationSpace).filter(VisualizationSpace.id == target_id).first()
        if not target_obj:
            raise HTTPException(status_code=404, detail=f"Visualization room #{target_id} not found")
    elif clean_scope == "render":
        target_obj = db.query(ProjectMedia).filter(ProjectMedia.id == target_id).first()
        if not target_obj:
            target_obj = db.query(VisualizationMedia).filter(VisualizationMedia.id == target_id).first()
        if not target_obj:
            raise HTTPException(status_code=404, detail=f"Render #{target_id} not found")
    else:
        raise HTTPException(status_code=400, detail="Invalid scope. Must be 'project', 'room', or 'render'.")

    # Read zip bytes and check size
    content = await file.read()
    if len(content) > MAX_VR_PACKAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"VR package exceeds maximum allowed size of {MAX_VR_PACKAGE_SIZE // (1024 * 1024)} MB."
        )

    try:
        archive_stream = io.BytesIO(content)
        with zipfile.ZipFile(archive_stream, 'r') as zf:
            # 1. Inspect all entries for security
            entry_names = zf.namelist()
            for entry in entry_names:
                # Disallow absolute paths and directory traversal
                if entry.startswith("/") or entry.startswith("\\") or ".." in entry:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Archive contains unsafe paths with directory traversal."
                    )
                # Disallow dangerous executable extensions
                ext = Path(entry).suffix.lower()
                if ext in DISALLOWED_PACKAGE_EXTENSIONS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Archive contains unsupported executable file '{entry}'. Only static HTML/JS/CSS/WebXR assets are permitted."
                    )
                # Check for symlinks
                info = zf.getinfo(entry)
                if (info.external_attr >> 16) & 0o120000 == 0o120000:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Archive contains symbolic links which are not permitted."
                    )

            # Determine extraction directory
            base_uploads = settings.UPLOADS_DIR / "vr_builds"
            build_folder_name = f"{clean_scope}_{target_id}_{int(time.time())}"
            target_extract_dir = base_uploads / build_folder_name
            target_extract_dir.mkdir(parents=True, exist_ok=True)

            # Extract archive
            zf.extractall(target_extract_dir)

            # 2. Locate entry file (index.html)
            entry_file = None
            if (target_extract_dir / "index.html").exists():
                entry_file = "index.html"
            else:
                # Search one level deep
                for child in target_extract_dir.iterdir():
                    if child.is_dir() and (child / "index.html").exists():
                        entry_file = f"{child.name}/index.html"
                        break

            if not entry_file:
                # Cleanup extracted directory
                shutil.rmtree(target_extract_dir, ignore_errors=True)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Imported VR package does not contain an 'index.html' entry point."
                )

            relative_entry_url = f"/uploads/vr_builds/{build_folder_name}/{entry_file}"

            # 3. Update database record
            target_obj.vr_url = relative_entry_url
            target_obj.vr_type = "hosted"
            target_obj.vr_build_entry = relative_entry_url
            target_obj.show_qr = True
            if hasattr(target_obj, "has_vr"):
                target_obj.has_vr = True

            db.commit()
            log_activity(
                db, current_user,
                action="Imported VR Build",
                entity_type=clean_scope,
                entity_id=str(target_id),
                details=f"Imported self-hosted VR build '{file.filename}' -> {relative_entry_url}"
            )

            return {
                "success": True,
                "scope": clean_scope,
                "target_id": target_id,
                "vr_url": relative_entry_url,
                "vr_type": "hosted",
                "entry_point": relative_entry_url,
                "qr_api_url": f"/api/admin/vr/qr?url={urllib.parse.quote(relative_entry_url)}"
            }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Corrupted or invalid ZIP file.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract VR package: {str(e)}")


@router.get("/all", summary="Get comprehensive list of all VR experiences across 3 levels")
def get_all_vr_experiences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns unified list of:
    - Level 1: Project-wide VR
    - Level 2: Room VR
    - Level 3: Individual 3D Render & Photo VR
    """
    # Level 1
    projects = db.query(Project).all()
    project_vr_list = []
    for p in projects:
        project_vr_list.append({
            "level": 1,
            "level_name": "Project-Wide Central VR",
            "project_id": p.id,
            "project_name": p.title,
            "target_name": p.title,
            "vr_url": p.vr_url,
            "has_vr": bool(p.vr_url),
            "vr_type": getattr(p, "vr_type", "external") or "external",
            "show_qr": getattr(p, "show_qr", True) if getattr(p, "show_qr", True) is not None else True,
            "vr_build_entry": getattr(p, "vr_build_entry", None),
            "cover_image": p.cover_image
        })

    # Level 2
    spaces = db.query(VisualizationSpace).all()
    room_vr_list = []
    for s in spaces:
        room_vr_list.append({
            "level": 2,
            "level_name": "Room VR",
            "space_id": s.id,
            "project_name": s.project_name,
            "room_name": s.room,
            "target_name": f"{s.project_name} — {s.room}",
            "vr_url": s.vr_url,
            "has_vr": bool(s.vr_url),
            "vr_type": getattr(s, "vr_type", "external") or "external",
            "show_qr": getattr(s, "show_qr", True) if getattr(s, "show_qr", True) is not None else True,
            "vr_build_entry": getattr(s, "vr_build_entry", None),
            "cover_image": s.cover_image
        })

    # Level 3: Visualization Media + Project Media
    render_vr_list = []
    
    # Visualization Media (Include ALL renders so owners can configure their first VR URL)
    renders = db.query(VisualizationMedia).all()
    for r in renders:
        space_name = r.space.title if r.space else (r.space.room if r.space else f"Room #{r.space_id}")
        project_name = r.space.project_name if r.space else "Architectural Space"
        target_name = f"{space_name} — {r.caption or r.angle or f'Perspective #{r.id}'}"
        render_vr_list.append({
            "level": 3,
            "level_name": "Individual Render VR",
            "media_id": r.id,
            "space_id": r.space_id,
            "project_name": project_name,
            "space_name": space_name,
            "caption": r.caption,
            "angle": r.angle,
            "target_name": target_name,
            "vr_url": r.vr_url,
            "has_vr": bool(r.vr_url),
            "vr_type": getattr(r, "vr_type", "external") or "external",
            "show_qr": getattr(r, "show_qr", False) if getattr(r, "show_qr", False) is not None else False,
            "vr_build_entry": getattr(r, "vr_build_entry", None),
            "is_project_media": False,
            "cover_image": r.url
        })

    # Project Media (Include project images)
    p_media = db.query(ProjectMedia).filter(ProjectMedia.media_type == "image").all()
    for pm in p_media:
        p_title = pm.project.title if pm.project else "Project Photo"
        target_name = f"{p_title} — {pm.caption or pm.title or f'Photo #{pm.id}'}"
        render_vr_list.append({
            "level": 3,
            "level_name": "Project Photograph VR",
            "media_id": pm.id,
            "project_id": pm.project_id,
            "project_name": p_title,
            "caption": pm.caption or pm.title,
            "target_name": target_name,
            "vr_url": pm.vr_url,
            "has_vr": bool(pm.vr_url),
            "vr_type": getattr(pm, "vr_type", "external") or "external",
            "show_qr": getattr(pm, "show_qr", False) if getattr(pm, "show_qr", False) is not None else False,
            "vr_build_entry": getattr(pm, "vr_build_entry", None),
            "is_project_media": True,
            "cover_image": pm.url
        })

    return {
        "level1_projects": project_vr_list,
        "level2_rooms": room_vr_list,
        "level3_renders": render_vr_list
    }
