import os
import re
import time
import uuid
import shutil
import mimetypes
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session

try:
    from app.core.config import settings
    from app.database.session import get_db
    from app.models.project import Project, ProjectMedia
    from app.models.visualization import VisualizationSpace, VisualizationMedia
    from app.models.blueprint import BlueprintDrawing
    from app.models.user import User
    from app.schemas.admin import (
        BulkUploadItem,
        BulkUploadCommitRequest,
        AssignMediaRequest
    )
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.core.config import settings
    from backend.app.database.session import get_db
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.models.visualization import VisualizationSpace, VisualizationMedia
    from backend.app.models.blueprint import BlueprintDrawing
    from backend.app.models.user import User
    from backend.app.schemas.admin import (
        BulkUploadItem,
        BulkUploadCommitRequest,
        AssignMediaRequest
    )
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

logger = logging.getLogger("studio_desire.upload")
router = APIRouter(prefix="/admin/upload", tags=["Admin Upload & Media Library"])

# Canonical media uploads folder from settings
UPLOADS_DIR = settings.UPLOADS_DIR
CMS_UPLOADS = (UPLOADS_DIR / "cms").resolve()
CMS_UPLOADS.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif",
    ".pdf", ".mp4", ".mov", ".webm", ".dwg", ".dxf"
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".php", ".py",
    ".js", ".html", ".htm", ".vbs", ".dll", ".phtml", ".phar", ".asp", ".aspx"
}


def sanitize_filename(filename: str) -> str:
    """
    Strips directory separators, null bytes, drive letters, and traversal characters.
    """
    if not filename:
        return "unnamed_upload"
    # Strip null bytes
    cleaned = filename.replace("\x00", "")
    # Use Path.name to strip leading directory paths / drive letters
    cleaned = Path(cleaned).name
    # Remove traversal sequences and dangerous characters
    cleaned = re.sub(r'[\/\\:]', '', cleaned)
    cleaned = re.sub(r'^\.+', '', cleaned)  # no leading dots
    if not cleaned:
        return "unnamed_upload"
    return cleaned


def detect_content_type(filename: str, relative_path: str = "") -> str:
    lower_path = (relative_path + "/" + filename).lower()
    lower_name = filename.lower()

    if any(k in lower_path for k in ["3d", "render", "corona", "max"]):
        return "3d"
    if any(k in lower_path for k in ["blueprint", "drawing", "plan", "cad", "section", "elevation"]):
        return "blueprint"
    if any(lower_name.endswith(ext) for ext in [".mp4", ".mov", ".webm", ".avi", ".mkv"]):
        return "video"
    if any(lower_name.endswith(ext) for ext in [".pdf", ".dwg", ".dxf"]):
        return "document"
    if any(lower_name.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".avif"]):
        return "image"
    return "document"


@router.post("/bulk", summary="Multi-file and folder upload staging")
async def bulk_upload(
    files: List[UploadFile] = File(...),
    project_id: Optional[int] = Form(None),
    relative_paths: Optional[str] = Form(""),
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR", "UPLOADER"])),
    db: Session = Depends(get_db)
):
    """
    Accepts bulk files with strict server-side validation:
    - Path traversal prevention
    - File extension and size limits
    - Cryptographically safe random filename generation
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for upload.")

    paths_list = [p.strip() for p in (relative_paths or "").split("\n") if p.strip()]
    created_items = []
    written_files: List[Path] = []

    # Verify project if passed
    target_project = None
    if project_id and project_id > 0:
        target_project = db.query(Project).filter(Project.id == project_id).first()
        if not target_project:
            raise HTTPException(status_code=404, detail="Target project not found.")

    max_bytes = settings.MAX_UPLOAD_SIZE_BYTES

    try:
        for idx, file in enumerate(files):
            raw_filename = file.filename or ""
            safe_orig_name = sanitize_filename(raw_filename)
            rel_path = paths_list[idx] if idx < len(paths_list) else raw_filename

            # Validate extension
            ext = Path(safe_orig_name).suffix.lower()
            if not ext or ext not in ALLOWED_EXTENSIONS or ext in DANGEROUS_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported or prohibited file format '{ext}' for file '{safe_orig_name}'. Permitted formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )

            content_type = detect_content_type(safe_orig_name, rel_path)

            # Detect potential room name from folder path
            detected_room = None
            path_parts = [sanitize_filename(p) for p in rel_path.replace("\\", "/").split("/") if p]
            if len(path_parts) > 1:
                for part in path_parts[:-1]:
                    low = part.lower()
                    if low not in ["photos", "videos", "3d", "blueprint", "blueprints", "docs", "documents", "renders", ".."]:
                        detected_room = part.strip()
                        break

            # Cryptographically safe unique server-side filename
            unique_token = uuid.uuid4().hex[:12]
            timestamp = int(time.time())
            safe_stem = re.sub(r'[^a-zA-Z0-9_-]', '_', Path(safe_orig_name).stem)[:32]
            dest_filename = f"media_{timestamp}_{unique_token}_{safe_stem}{ext}"

            dest_path = (CMS_UPLOADS / dest_filename).resolve()

            # Verify confinement inside upload directory (path traversal check)
            if not dest_path.is_relative_to(CMS_UPLOADS):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid upload destination path detected."
                )

            # Stream save with strict size enforcement
            bytes_written = 0
            with open(dest_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        buffer.close()
                        if dest_path.exists():
                            dest_path.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File '{safe_orig_name}' exceeds maximum allowed upload size ({max_bytes // (1024*1024)} MB)."
                        )
                    buffer.write(chunk)

            written_files.append(dest_path)
            web_url = f"/uploads/cms/{dest_filename}"

            # Insert staged ProjectMedia item
            caption_text = safe_stem.replace("_", " ").title() if safe_stem else "Uploaded Asset"
            media_entry = ProjectMedia(
                project_id=target_project.id if target_project else None,
                media_type=content_type,
                url=web_url,
                thumbnail_url=web_url,
                caption=caption_text,
                room_name=detected_room,
                status="draft" if target_project else "unassigned",
                is_published=False,
                sort_order=idx + 1
            )
            db.add(media_entry)
            db.flush()

            created_items.append({
                "id": media_entry.id,
                "url": web_url,
                "thumbnail_url": web_url,
                "filename": safe_orig_name,
                "detected_type": content_type,
                "project_id": target_project.id if target_project else None,
                "room_name": detected_room,
                "drawing_type": "Floor Plan" if content_type == "blueprint" else None,
                "caption": media_entry.caption,
                "sort_order": idx + 1,
                "status": media_entry.status
            })

        db.commit()

    except HTTPException:
        db.rollback()
        for fpath in written_files:
            if fpath.exists():
                try:
                    fpath.unlink()
                except Exception:
                    pass
        raise

    except Exception as exc:
        db.rollback()
        for fpath in written_files:
            if fpath.exists():
                try:
                    fpath.unlink()
                except Exception:
                    pass
        logger.exception(f"Bulk upload failed unexpectedly: {exc}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while saving uploaded files."
        )

    p_name = target_project.title if target_project else "Unassigned"
    log_activity(
        db, current_user,
        action="Uploaded Files",
        entity_type="media",
        details=f"Uploaded {len(files)} files to '{p_name}'"
    )

    return {
        "success": True,
        "total_uploaded": len(files),
        "project_id": target_project.id if target_project else None,
        "items": created_items
    }


@router.post("/commit", summary="Commit and save/publish reviewed upload batch")
def commit_upload_review(
    payload: BulkUploadCommitRequest,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    """
    Applies review screen modifications (project, room, drawing type, ordering)
    and either saves as Draft or Publishes directly to the project and public views.
    """
    committed_count = 0
    for item in payload.items:
        media_entry = db.query(ProjectMedia).filter(ProjectMedia.id == item.id).first()
        if not media_entry:
            continue

        media_entry.project_id = item.project_id
        media_entry.media_type = item.detected_type
        media_entry.room_name = item.room_name
        media_entry.caption = item.caption
        media_entry.sort_order = item.sort_order
        media_entry.is_published = payload.publish_now
        media_entry.status = "published" if payload.publish_now else "draft"

        # If detected as 3D render and room exists or provided, ensure 3D space exists
        if item.detected_type == "3d" and item.room_name and item.project_id:
            project = db.query(Project).filter(Project.id == item.project_id).first()
            if project:
                clean_room = re.sub(r'[^a-zA-Z0-9-]', '', item.room_name.lower().replace(' ', '-'))
                space_slug = f"{project.slug}-{clean_room}"
                space = db.query(VisualizationSpace).filter(VisualizationSpace.slug == space_slug).first()
                if not space:
                    space = VisualizationSpace(
                        title=f"{item.room_name}",
                        slug=space_slug,
                        project_id=project.id,
                        project_name=project.title,
                        room=item.room_name,
                        category="Residential",
                        cover_image=item.url,
                        is_published=payload.publish_now
                    )
                    db.add(space)
                    db.flush()

                # Add visualization media if not already linked
                vis_media = VisualizationMedia(
                    space_id=space.id,
                    url=item.url,
                    caption=item.caption or item.room_name,
                    sort_order=item.sort_order
                )
                db.add(vis_media)

        # If detected as blueprint drawing, add to BlueprintDrawing table
        if item.detected_type == "blueprint" and item.project_id:
            project = db.query(Project).filter(Project.id == item.project_id).first()
            if project:
                bp_slug = f"{project.slug}-dwg-{item.id}"
                existing_bp = db.query(BlueprintDrawing).filter(BlueprintDrawing.slug == bp_slug).first()
                if not existing_bp:
                    bp_drawing = BlueprintDrawing(
                        project_id=project.id,
                        project_name=project.title,
                        project_slug=project.slug,
                        title=item.caption or f"{item.drawing_type or 'Plan'} Drawing",
                        slug=bp_slug,
                        drawing_type=item.drawing_type or "Floor Plan",
                        room_area=item.room_name or "General",
                        drawing_number=f"SD-{project.slug[:3].upper()}-{item.id:02d}",
                        thumbnail_url=item.thumbnail_url or item.url,
                        file_url=item.url,
                        file_type="image",
                        is_demo=False,
                        is_published=payload.publish_now,
                        sort_order=item.sort_order
                    )
                    db.add(bp_drawing)

        committed_count += 1

    db.commit()

    action_label = "Published" if payload.publish_now else "Saved as Draft"
    log_activity(
        db, current_user,
        action=f"Bulk Upload {action_label}",
        entity_type="media",
        details=f"{action_label} {committed_count} items"
    )

    return {
        "success": True,
        "committed_count": committed_count,
        "is_published": payload.publish_now,
        "message": f"Successfully {action_label.lower()} {committed_count} items."
    }


@router.get("/media", summary="List media library assets with category & unassigned filter")
def list_media(
    media_type: Optional[str] = Query(None, description="all, image, video, 3d, blueprint, document, unassigned"),
    project_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectMedia)

    if media_type:
        clean_type = media_type.lower()
        if clean_type == "unassigned":
            query = query.filter((ProjectMedia.project_id == None) | (ProjectMedia.status == "unassigned"))
        elif clean_type in ["image", "photos", "photo"]:
            query = query.filter(ProjectMedia.media_type == "image")
        elif clean_type in ["video", "videos"]:
            query = query.filter(ProjectMedia.media_type == "video")
        elif clean_type == "3d":
            query = query.filter(ProjectMedia.media_type == "3d")
        elif clean_type in ["blueprint", "blueprints"]:
            query = query.filter(ProjectMedia.media_type == "blueprint")
        elif clean_type in ["document", "documents", "docs"]:
            query = query.filter(ProjectMedia.media_type == "document")

    if project_id:
        query = query.filter(ProjectMedia.project_id == project_id)

    if status_filter:
        query = query.filter(ProjectMedia.status == status_filter)

    items = query.order_by(ProjectMedia.id.desc()).all()

    projects_map = {p.id: p.title for p in db.query(Project.id, Project.title).all()}

    results = []
    for m in items:
        results.append({
            "id": m.id,
            "project_id": m.project_id,
            "project_name": projects_map.get(m.project_id, "Unassigned") if m.project_id else "Unassigned",
            "media_type": m.media_type,
            "url": m.url,
            "thumbnail_url": m.thumbnail_url or m.url,
            "caption": m.caption,
            "alt_text": m.alt_text,
            "room_name": m.room_name,
            "status": m.status or ("published" if m.is_published else "draft"),
            "is_published": bool(m.is_published),
            "sort_order": m.sort_order,
            "created_at": m.created_at
        })

    return {
        "total": len(results),
        "items": results
    }


@router.post("/assign", summary="Assign unassigned media items to a project")
def assign_unassigned_media(
    payload: AssignMediaRequest,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR", "UPLOADER"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Target project not found")

    updated_count = 0
    for m_id in payload.media_ids:
        media_entry = db.query(ProjectMedia).filter(ProjectMedia.id == m_id).first()
        if not media_entry:
            continue

        media_entry.project_id = project.id
        if payload.media_type:
            media_entry.media_type = payload.media_type
        if payload.room_name:
            media_entry.room_name = payload.room_name
        if payload.publish_now:
            media_entry.is_published = True
            media_entry.status = "published"
        else:
            media_entry.status = "draft"
        updated_count += 1

    db.commit()

    log_activity(
        db, current_user,
        action="Assigned Media",
        entity_type="project",
        entity_id=str(project.id),
        details=f"Assigned {updated_count} media items to '{project.title}'"
    )

    return {
        "success": True,
        "message": f"Successfully assigned {updated_count} items to '{project.title}'",
        "project_id": project.id
    }


@router.delete("/media/{media_id}", summary="Delete a media item")
def delete_media(
    media_id: int,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    media_entry = db.query(ProjectMedia).filter(ProjectMedia.id == media_id).first()
    if not media_entry:
        raise HTTPException(status_code=404, detail="Media item not found")

    db.delete(media_entry)
    db.commit()

    log_activity(
        db, current_user,
        action="Deleted Media",
        entity_type="media",
        entity_id=str(media_id),
        details="Deleted media entry"
    )

    return {"success": True, "message": "Media item deleted"}
