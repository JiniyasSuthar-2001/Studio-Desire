import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.project import Project
from app.models.user import User
from app.core.dependencies import get_current_user, require_roles, log_activity
from app.schemas.visualization import (
    VisualizationSpaceDetailOut,
    VisualizationSpaceCreate,
    VisualizationSpaceUpdate,
    VisualizationMediaOut,
    VisualizationMediaCreate,
    VisualizationMediaUpdate,
)

router = APIRouter(prefix="/admin/visualizations", tags=["Admin 3D Visualizations & Spaces"])


def generate_unique_slug(db: Session, title: str, space_id: Optional[int] = None) -> str:
    base_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not base_slug:
        base_slug = "spatial-volume"
    
    candidate = base_slug
    counter = 1
    while True:
        query = db.query(VisualizationSpace).filter(VisualizationSpace.slug == candidate)
        if space_id:
            query = query.filter(VisualizationSpace.id != space_id)
        if not query.first():
            return candidate
        counter += 1
        candidate = f"{base_slug}-{counter}"


@router.get("", response_model=List[VisualizationSpaceDetailOut], summary="List all visualization spaces for Owner CRM")
def list_admin_visualizations(
    room: Optional[str] = Query(None, description="Optional room category filter"),
    q: Optional[str] = Query(None, description="Search query"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(VisualizationSpace)
    if room and room.strip() and room.strip() != "ALL":
        query = query.filter(func.lower(VisualizationSpace.room) == room.strip().lower())
    
    if q and q.strip():
        search = f"%{q.strip().lower()}%"
        query = query.filter(
            (func.lower(VisualizationSpace.title).like(search)) |
            (func.lower(VisualizationSpace.project_name).like(search)) |
            (func.lower(VisualizationSpace.location).like(search))
        )
    
    return query.order_by(VisualizationSpace.sort_order.asc(), VisualizationSpace.id.desc()).all()


@router.get("/{space_id}", response_model=VisualizationSpaceDetailOut, summary="Get single visualization space details")
def get_admin_visualization(
    space_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    space = db.query(VisualizationSpace).filter(VisualizationSpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Visualization space not found")
    return space


@router.post("", response_model=VisualizationSpaceDetailOut, status_code=status.HTTP_201_CREATED, summary="Create a new visualization space")
def create_visualization_space(
    payload: VisualizationSpaceCreate,
    current_user: User = Depends(require_roles(["MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    # Resolve linked project name
    project_name = payload.project_name or ""
    if payload.project_id:
        proj = db.query(Project).filter(Project.id == payload.project_id).first()
        if proj:
            project_name = proj.title
    
    if not project_name:
        project_name = payload.title

    slug = payload.slug.strip().lower() if payload.slug and payload.slug.strip() else generate_unique_slug(db, payload.title)
    # Check slug collision
    existing = db.query(VisualizationSpace).filter(VisualizationSpace.slug == slug).first()
    if existing:
        slug = generate_unique_slug(db, slug)

    has_vr = bool(payload.vr_url and payload.vr_url.strip())

    space = VisualizationSpace(
        title=payload.title.strip(),
        slug=slug,
        project_id=payload.project_id,
        project_name=project_name,
        room=payload.room.strip(),
        category=payload.category.strip(),
        year=payload.year,
        location=payload.location.strip() if payload.location else None,
        description=payload.description.strip() if payload.description else None,
        software=payload.software.strip() if payload.software else "Corona Renderer · 3ds Max · Unreal Engine VR",
        cover_image=payload.cover_image.strip(),
        vr_url=payload.vr_url.strip() if payload.vr_url and payload.vr_url.strip() else None,
        has_vr=has_vr,
        show_qr=payload.show_qr,
        vr_type=payload.vr_type or "external",
        is_published=payload.is_published,
        sort_order=payload.sort_order
    )

    db.add(space)
    db.commit()
    db.refresh(space)

    log_activity(
        db, current_user,
        action="Created 3D Visualization",
        entity_type="visualization",
        entity_id=str(space.id),
        details=f"Created spatial room '{space.title}' ({space.room}) under '{space.project_name}'"
    )

    return space


@router.put("/{space_id}", response_model=VisualizationSpaceDetailOut, summary="Update an existing visualization space")
def update_visualization_space(
    space_id: int,
    payload: VisualizationSpaceUpdate,
    current_user: User = Depends(require_roles(["MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    space = db.query(VisualizationSpace).filter(VisualizationSpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Visualization space not found")

    if payload.title is not None:
        space.title = payload.title.strip()
    if payload.slug is not None and payload.slug.strip():
        new_slug = payload.slug.strip().lower()
        if new_slug != space.slug:
            existing = db.query(VisualizationSpace).filter(VisualizationSpace.slug == new_slug, VisualizationSpace.id != space.id).first()
            if existing:
                raise HTTPException(status_code=400, detail="Slug already taken by another space")
            space.slug = new_slug
    if payload.project_id is not None:
        space.project_id = payload.project_id
        if payload.project_id:
            proj = db.query(Project).filter(Project.id == payload.project_id).first()
            if proj:
                space.project_name = proj.title
    if payload.project_name is not None:
        space.project_name = payload.project_name.strip()
    if payload.room is not None:
        space.room = payload.room.strip()
    if payload.category is not None:
        space.category = payload.category.strip()
    if payload.year is not None:
        space.year = payload.year
    if payload.location is not None:
        space.location = payload.location.strip()
    if payload.description is not None:
        space.description = payload.description.strip()
    if payload.software is not None:
        space.software = payload.software.strip()
    if payload.cover_image is not None and payload.cover_image.strip():
        space.cover_image = payload.cover_image.strip()
    if payload.vr_url is not None:
        clean_vr = payload.vr_url.strip() if payload.vr_url.strip() else None
        space.vr_url = clean_vr
        space.has_vr = bool(clean_vr)
    if payload.show_qr is not None:
        space.show_qr = payload.show_qr
    if payload.vr_type is not None:
        space.vr_type = payload.vr_type
    if payload.is_published is not None:
        space.is_published = payload.is_published
    if payload.sort_order is not None:
        space.sort_order = payload.sort_order

    db.commit()
    db.refresh(space)

    log_activity(
        db, current_user,
        action="Updated 3D Visualization",
        entity_type="visualization",
        entity_id=str(space.id),
        details=f"Updated spatial room '{space.title}' ({space.room})"
    )

    return space


@router.delete("/{space_id}", summary="Delete a visualization space and its render records")
def delete_visualization_space(
    space_id: int,
    current_user: User = Depends(require_roles(["MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    space = db.query(VisualizationSpace).filter(VisualizationSpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Visualization space not found")

    title = space.title
    db.delete(space)
    db.commit()

    log_activity(
        db, current_user,
        action="Deleted 3D Visualization",
        entity_type="visualization",
        entity_id=str(space_id),
        details=f"Deleted spatial volume '{title}' (space #{space_id})"
    )

    return {"success": True, "message": f"Visualization space '{title}' successfully deleted"}


@router.post("/{space_id}/media", response_model=VisualizationMediaOut, status_code=status.HTTP_201_CREATED, summary="Add supporting 3D perspective to space")
def add_visualization_media(
    space_id: int,
    payload: VisualizationMediaCreate,
    current_user: User = Depends(require_roles(["MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    space = db.query(VisualizationSpace).filter(VisualizationSpace.id == space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Visualization space not found")

    has_vr = bool(payload.vr_url and payload.vr_url.strip())
    media = VisualizationMedia(
        space_id=space.id,
        url=payload.url.strip(),
        caption=payload.caption.strip() if payload.caption else None,
        angle=payload.angle.strip() if payload.angle else None,
        sort_order=payload.sort_order,
        vr_url=payload.vr_url.strip() if payload.vr_url and payload.vr_url.strip() else None,
        has_vr=has_vr,
        show_qr=payload.show_qr,
        vr_type=payload.vr_type or "external"
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    log_activity(
        db, current_user,
        action="Added 3D Perspective",
        entity_type="visualization_media",
        entity_id=str(media.id),
        details=f"Added render '{payload.caption or 'Perspective'}' to space #{space.id}"
    )

    return media


@router.put("/media/{media_id}", response_model=VisualizationMediaOut, summary="Update supporting 3D perspective metadata")
def update_visualization_media(
    media_id: int,
    payload: VisualizationMediaUpdate,
    current_user: User = Depends(require_roles(["MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    media = db.query(VisualizationMedia).filter(VisualizationMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Visualization media render not found")

    if payload.caption is not None:
        media.caption = payload.caption.strip()
    if payload.angle is not None:
        media.angle = payload.angle.strip()
    if payload.sort_order is not None:
        media.sort_order = payload.sort_order
    if payload.vr_url is not None:
        clean_vr = payload.vr_url.strip() if payload.vr_url.strip() else None
        media.vr_url = clean_vr
        media.has_vr = bool(clean_vr)
    if payload.show_qr is not None:
        media.show_qr = payload.show_qr
    if payload.vr_type is not None:
        media.vr_type = payload.vr_type

    db.commit()
    db.refresh(media)

    log_activity(
        db, current_user,
        action="Updated 3D Perspective",
        entity_type="visualization_media",
        entity_id=str(media.id),
        details=f"Updated render #{media.id} in space #{media.space_id}"
    )

    return media


@router.delete("/media/{media_id}", summary="Remove supporting 3D perspective from space")
def delete_visualization_media(
    media_id: int,
    current_user: User = Depends(require_roles(["MASTER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    media = db.query(VisualizationMedia).filter(VisualizationMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Visualization media render not found")

    space_id = media.space_id
    db.delete(media)
    db.commit()

    log_activity(
        db, current_user,
        action="Removed 3D Perspective",
        entity_type="visualization_media",
        entity_id=str(media_id),
        details=f"Removed render #{media_id} from space #{space_id}"
    )

    return {"success": True, "message": f"Render #{media_id} removed"}
