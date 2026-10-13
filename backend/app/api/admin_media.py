from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.user import User
    from app.models.client import Client
    from app.models.project import Project, ProjectMedia
    from app.schemas.admin import UnifiedMediaItemOut, AssignMediaRequest
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.user import User
    from backend.app.models.client import Client
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.schemas.admin import UnifiedMediaItemOut, AssignMediaRequest
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/media", tags=["Admin Unified Media Library"])


@router.get("", response_model=List[UnifiedMediaItemOut], summary="List media assets with filters")
def list_unified_media(
    media_type: Optional[str] = None,  # image, video, 3d, blueprint, vr, document, unassigned, all
    project_id: Optional[int] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectMedia).outerjoin(Project, ProjectMedia.project_id == Project.id)

    if media_type and media_type.lower() != "all":
        mtype = media_type.lower()
        if mtype == "unassigned":
            query = query.filter((ProjectMedia.project_id == None) | (ProjectMedia.status == "unassigned"))
        elif mtype in ["photo", "photos", "image", "images"]:
            query = query.filter(ProjectMedia.media_type.in_(["image", "photo"]))
        elif mtype in ["video", "videos"]:
            query = query.filter(ProjectMedia.media_type.in_(["video"]))
        elif mtype in ["3d", "3d renders", "render_3d"]:
            query = query.filter(ProjectMedia.media_type.in_(["3d", "render_3d"]))
        elif mtype in ["blueprint", "blueprints"]:
            query = query.filter(ProjectMedia.media_type.in_(["blueprint", "drawing"]))
        elif mtype in ["vr"]:
            query = query.filter(ProjectMedia.media_type.in_(["vr"]))
        elif mtype in ["document", "documents", "files"]:
            query = query.filter(ProjectMedia.media_type.in_(["document", "file", "pdf"]))
        else:
            query = query.filter(func.lower(ProjectMedia.media_type) == mtype)

    if project_id:
        query = query.filter(ProjectMedia.project_id == project_id)

    if q and q.strip():
        search = f"%{q.strip().lower()}%"
        query = query.filter(
            (func.lower(ProjectMedia.caption).like(search)) |
            (func.lower(ProjectMedia.title).like(search)) |
            (func.lower(ProjectMedia.room_name).like(search)) |
            (func.lower(ProjectMedia.url).like(search)) |
            (func.lower(Project.title).like(search))
        )

    items = query.order_by(ProjectMedia.id.desc()).all()
    results = []
    for item in items:
        p_title = item.project.title if item.project else None
        results.append(
            UnifiedMediaItemOut(
                id=item.id,
                project_id=item.project_id,
                project_title=p_title,
                media_type=item.media_type,
                url=item.url,
                thumbnail_url=item.thumbnail_url or item.url,
                title=item.title,
                caption=item.caption,
                alt_text=item.alt_text,
                room_name=item.room_name,
                status=item.status or "published",
                is_published=bool(item.is_published),
                version=item.version or "v1",
                uploaded_by=item.uploaded_by,
                sort_order=item.sort_order or 0,
                vr_url=getattr(item, "vr_url", None),
                has_vr=bool(getattr(item, "has_vr", False) or getattr(item, "vr_url", None)),
                show_qr=bool(getattr(item, "show_qr", False)),
                vr_type=getattr(item, "vr_type", "external") or "external",
                vr_build_entry=getattr(item, "vr_build_entry", None),
                created_at=item.created_at
            )
        )
    return results


@router.put("/{media_id}", response_model=UnifiedMediaItemOut, summary="Update media metadata")
def update_media_item(
    media_id: int,
    payload: dict,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "EDITOR"])),
    db: Session = Depends(get_db)
):
    media = db.query(ProjectMedia).filter(ProjectMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found")

    allowed_fields = [
        "title", "caption", "alt_text", "room_name", "sort_order",
        "is_published", "status", "version", "project_id", "media_type",
        "vr_url", "has_vr", "show_qr", "vr_type", "vr_build_entry"
    ]
    for key, val in payload.items():
        if key in allowed_fields:
            if key == "vr_url":
                cleaned = val.strip() if (isinstance(val, str) and val.strip()) else None
                setattr(media, "vr_url", cleaned)
                setattr(media, "has_vr", bool(cleaned))
            else:
                setattr(media, key, val)

    db.commit()
    db.refresh(media)

    log_activity(db, current_user, action="Updated Media", entity_type="media", entity_id=str(media.id), details=f"Media #{media.id} updated")

    p_title = media.project.title if media.project else None
    return UnifiedMediaItemOut(
        id=media.id,
        project_id=media.project_id,
        project_title=p_title,
        media_type=media.media_type,
        url=media.url,
        thumbnail_url=media.thumbnail_url or media.url,
        title=media.title,
        caption=media.caption,
        alt_text=media.alt_text,
        room_name=media.room_name,
        status=media.status or "published",
        is_published=bool(media.is_published),
        version=media.version or "v1",
        uploaded_by=media.uploaded_by,
        sort_order=media.sort_order or 0,
        vr_url=getattr(media, "vr_url", None),
        has_vr=bool(getattr(media, "has_vr", False) or getattr(media, "vr_url", None)),
        show_qr=bool(getattr(media, "show_qr", False)),
        vr_type=getattr(media, "vr_type", "external") or "external",
        vr_build_entry=getattr(media, "vr_build_entry", None),
        created_at=media.created_at
    )


@router.post("/batch-assign", summary="Assign multiple media items to a project")
def batch_assign_media(
    payload: AssignMediaRequest,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "EDITOR"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Target project not found")

    items = db.query(ProjectMedia).filter(ProjectMedia.id.in_(payload.media_ids)).all()
    for item in items:
        item.project_id = project.id
        item.status = "published" if payload.publish_now else "draft"
        item.is_published = payload.publish_now
        if payload.media_type:
            item.media_type = payload.media_type
        if payload.room_name:
            item.room_name = payload.room_name

    db.commit()

    log_activity(db, current_user, action="Batch Assigned Media", entity_type="media", entity_id=str(project.id), details=f"Assigned {len(items)} media files to '{project.title}'")

    return {"success": True, "count": len(items), "project_id": project.id, "project_title": project.title}


@router.delete("/{media_id}", summary="Delete media record")
def delete_media_item(
    media_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    media = db.query(ProjectMedia).filter(ProjectMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media item not found")

    db.delete(media)
    db.commit()

    log_activity(db, current_user, action="Deleted Media", entity_type="media", entity_id=str(media_id), details=f"Deleted media #{media_id}")

    return {"success": True, "message": f"Media #{media_id} deleted."}


@router.get("/audit", summary="Audit all database media records against disk storage")
def audit_media_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from pathlib import Path
    try:
        from app.core.config import settings
        from app.models.visualization import VisualizationSpace, VisualizationMedia
        from app.models.blueprint import BlueprintDrawing
    except ImportError:
        from backend.app.core.config import settings
        from backend.app.models.visualization import VisualizationSpace, VisualizationMedia
        from backend.app.models.blueprint import BlueprintDrawing

    uploads_root = settings.UPLOADS_DIR

    results = {
        "uploads_root": str(uploads_root),
        "uploads_root_exists": uploads_root.exists(),
        "total_records_checked": 0,
        "valid_local_files": 0,
        "valid_external_urls": 0,
        "missing_local_files": [],
        "invalid_urls": []
    }

    def check_url(model_name: str, record_id: int, field_name: str, url: Optional[str]):
        if not url:
            return
        results["total_records_checked"] += 1
        clean_url = url.strip()

        if clean_url.startswith("http://") or clean_url.startswith("https://") or clean_url.startswith("data:"):
            results["valid_external_urls"] += 1
            return

        # Check local /uploads path
        if clean_url.startswith("/uploads/"):
            rel_path = clean_url[len("/uploads/"):]
            local_file = (uploads_root / rel_path).resolve()
            if local_file.exists() and local_file.is_file():
                results["valid_local_files"] += 1
            else:
                results["missing_local_files"].append({
                    "model": model_name,
                    "id": record_id,
                    "field": field_name,
                    "url": clean_url,
                    "expected_path": str(local_file)
                })
        else:
            results["invalid_urls"].append({
                "model": model_name,
                "id": record_id,
                "field": field_name,
                "url": clean_url
            })

    # 1. ProjectMedia
    for pm in db.query(ProjectMedia).all():
        check_url("ProjectMedia", pm.id, "url", pm.url)
        if pm.thumbnail_url and pm.thumbnail_url != pm.url:
            check_url("ProjectMedia", pm.id, "thumbnail_url", pm.thumbnail_url)

    # 2. Project cover_image
    for p in db.query(Project).all():
        check_url("Project", p.id, "cover_image", p.cover_image)

    # 3. VisualizationSpace cover_image
    for vs in db.query(VisualizationSpace).all():
        check_url("VisualizationSpace", vs.id, "cover_image", vs.cover_image)

    # 4. VisualizationMedia url
    for vm in db.query(VisualizationMedia).all():
        check_url("VisualizationMedia", vm.id, "url", vm.url)

    # 5. BlueprintDrawing
    for bp in db.query(BlueprintDrawing).all():
        check_url("BlueprintDrawing", bp.id, "file_url", bp.file_url)
        if bp.thumbnail_url:
            check_url("BlueprintDrawing", bp.id, "thumbnail_url", bp.thumbnail_url)

    return results


@router.post("/repair-missing", summary="Safely repair known missing image references with fallbacks")
def repair_missing_media(
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    from pathlib import Path
    try:
        from app.core.config import settings
        from app.models.visualization import VisualizationSpace, VisualizationMedia
        from app.models.blueprint import BlueprintDrawing
    except ImportError:
        from backend.app.core.config import settings
        from backend.app.models.visualization import VisualizationSpace, VisualizationMedia
        from backend.app.models.blueprint import BlueprintDrawing

    uploads_root = settings.UPLOADS_DIR
    placeholder = "/uploads/projects/placeholder.webp"
    repaired = []

    def is_missing_local(url: Optional[str]) -> bool:
        if not url:
            return False
        clean = url.strip()
        if clean.startswith("/uploads/"):
            rel_path = clean[len("/uploads/"):]
            local_file = (uploads_root / rel_path).resolve()
            return not (local_file.exists() and local_file.is_file())
        return False

    # 1. Project cover images
    for p in db.query(Project).all():
        if is_missing_local(p.cover_image):
            old_val = p.cover_image
            p.cover_image = placeholder
            repaired.append({"model": "Project", "id": p.id, "field": "cover_image", "old": old_val, "new": p.cover_image})

    # 2. VisualizationSpace cover images
    for vs in db.query(VisualizationSpace).all():
        if is_missing_local(vs.cover_image):
            old_val = vs.cover_image
            vs.cover_image = placeholder
            repaired.append({"model": "VisualizationSpace", "id": vs.id, "field": "cover_image", "old": old_val, "new": vs.cover_image})

    # 3. BlueprintDrawing
    for bp in db.query(BlueprintDrawing).all():
        if is_missing_local(bp.file_url):
            old_val = bp.file_url
            bp.file_url = placeholder
            repaired.append({"model": "BlueprintDrawing", "id": bp.id, "field": "file_url", "old": old_val, "new": bp.file_url})
        if bp.thumbnail_url and is_missing_local(bp.thumbnail_url):
            old_val = bp.thumbnail_url
            bp.thumbnail_url = placeholder
            repaired.append({"model": "BlueprintDrawing", "id": bp.id, "field": "thumbnail_url", "old": old_val, "new": bp.thumbnail_url})

    # 4. ProjectMedia
    for pm in db.query(ProjectMedia).all():
        if is_missing_local(pm.url):
            old_val = pm.url
            pm.url = placeholder
            repaired.append({"model": "ProjectMedia", "id": pm.id, "field": "url", "old": old_val, "new": pm.url})
        if pm.thumbnail_url and is_missing_local(pm.thumbnail_url):
            old_val = pm.thumbnail_url
            pm.thumbnail_url = placeholder
            repaired.append({"model": "ProjectMedia", "id": pm.id, "field": "thumbnail_url", "old": old_val, "new": pm.thumbnail_url})

    if repaired:
        db.commit()

    return {"success": True, "repaired_count": len(repaired), "repaired_items": repaired}

