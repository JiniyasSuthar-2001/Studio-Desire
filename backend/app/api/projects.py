from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

try:
    from app.database.session import get_db
    from app.models.project import Project, ProjectMedia
    from app.models.category import PortfolioCategory
    from app.schemas.project import (
        ProjectSummaryOut,
        ProjectDetailOut,
        ProjectListResponse,
        MediaOut
    )
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.models.category import PortfolioCategory
    from backend.app.schemas.project import (
        ProjectSummaryOut,
        ProjectDetailOut,
        ProjectListResponse,
        MediaOut
    )

router = APIRouter(prefix="/projects", tags=["Projects Public Archive"])


@router.get("", response_model=ProjectListResponse, summary="List all published architectural projects")
def get_projects(
    category: Optional[str] = Query(None, description="Filter by category (e.g., Residential, Hospitality, Office)"),
    category_id: Optional[int] = Query(None, description="Filter by authoritative category ID"),
    media_type: Optional[str] = Query(None, description="Filter by media type ('video', 'image', or 'photos')"),
    featured: Optional[bool] = Query(None, description="Filter only featured projects"),
    db: Session = Depends(get_db)
):
    # PUBLIC API: STRICTLY enforce is_published == True
    query = db.query(Project).filter(Project.is_published == True)

    # Authoritative Category ID Filter
    if category_id:
        query = query.filter(Project.category_id == category_id)
    # Category Slug or Name Filter
    elif category and category.upper() != "ALL":
        clean_cat = category.strip().lower()
        matched_cat = db.query(PortfolioCategory).filter(
            or_(
                func.lower(PortfolioCategory.slug) == clean_cat,
                func.lower(PortfolioCategory.name) == clean_cat
            )
        ).first()
        if matched_cat:
            query = query.filter(
                or_(
                    Project.category_id == matched_cat.id,
                    func.lower(Project.category) == matched_cat.name.lower()
                )
            )
        else:
            query = query.filter(func.lower(Project.category) == clean_cat)

    # Featured Filter
    if featured is not None:
        query = query.filter(Project.featured == featured)

    # Media Type Filter
    if media_type:
        clean_media = media_type.lower()
        if clean_media in ["video", "videos"]:
            query = query.join(Project.media).filter(ProjectMedia.media_type == "video", ProjectMedia.is_published == True).distinct()
        elif clean_media in ["image", "photos", "photo"]:
            query = query.join(Project.media).filter(ProjectMedia.media_type.in_(["image", "photo"]), ProjectMedia.is_published == True).distinct()

    projects = query.order_by(Project.featured.desc(), Project.id.desc()).all()

    summaries = []
    for p in projects:
        pub_media = [m for m in p.media if getattr(m, 'is_published', True)]
        has_vid = any(m.media_type == "video" for m in pub_media)
        summary = ProjectSummaryOut(
            id=p.id,
            title=p.title,
            slug=p.slug,
            subtitle=p.subtitle,
            location=p.location,
            year=p.year,
            category=p.category,
            category_id=p.category_id,
            subcategory_id=p.subcategory_id,
            project_type=p.project_type,
            area=p.area,
            description=p.description,
            cover_image=p.cover_image,
            featured=p.featured,
            is_demo=p.is_demo,
            grid_span=p.grid_span or "span-6",
            aspect_ratio=p.aspect_ratio or "ratio-standard",
            created_at=p.created_at,
            updated_at=p.updated_at,
            has_video=has_vid,
            media_count=len(pub_media)
        )
        summaries.append(summary)

    return ProjectListResponse(total=len(summaries), projects=summaries)


@router.get("/featured", response_model=ProjectDetailOut, summary="Retrieve the top featured published project")
def get_featured_project(db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.is_published == True, Project.featured == True).first()
    if not project:
        project = db.query(Project).filter(Project.is_published == True).order_by(Project.id.desc()).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No published projects found in the archive"
        )
    pub_media = [m for m in project.media if getattr(m, 'is_published', True)]
    media_out_list = [
        MediaOut(
            id=m.id,
            project_id=m.project_id or project.id,
            media_type=m.media_type,
            url=m.url,
            thumbnail_url=m.thumbnail_url or m.url,
            caption=m.caption,
            alt_text=m.alt_text,
            sort_order=m.sort_order or 0,
            vr_url=getattr(m, "vr_url", None),
            has_vr=bool(getattr(m, "has_vr", False) or getattr(m, "vr_url", None)),
            show_qr=bool(getattr(m, "show_qr", False)),
            vr_type=getattr(m, "vr_type", "external") or "external",
            vr_build_entry=getattr(m, "vr_build_entry", None)
        )
        for m in pub_media
    ]
    return ProjectDetailOut(
        id=project.id,
        title=project.title,
        slug=project.slug,
        subtitle=project.subtitle,
        location=project.location,
        year=project.year,
        category=project.category,
        category_id=project.category_id,
        subcategory_id=project.subcategory_id,
        project_type=project.project_type,
        area=project.area,
        description=project.description,
        cover_image=project.cover_image,
        featured=project.featured,
        is_demo=project.is_demo,
        is_published=project.is_published,
        vr_url=project.vr_url,
        vr_qr_code=project.vr_qr_code,
        show_qr=getattr(project, "show_qr", True) if getattr(project, "show_qr", True) is not None else True,
        vr_type=getattr(project, "vr_type", "external") or "external",
        vr_build_entry=getattr(project, "vr_build_entry", None),
        grid_span=project.grid_span or "span-6",
        aspect_ratio=project.aspect_ratio or "ratio-standard",
        created_at=project.created_at,
        updated_at=project.updated_at,
        media=media_out_list
    )


@router.get("/categories", response_model=List[str], summary="Get list of available published project categories")
def get_categories(db: Session = Depends(get_db)):
    results = db.query(Project.category).filter(Project.is_published == True).distinct().all()
    categories = ["ALL"] + [r[0] for r in results if r[0]]
    return categories


@router.get("/{slug_or_id}", response_model=ProjectDetailOut, summary="Retrieve a full published project architectural dossier")
def get_project_by_slug(slug_or_id: str, db: Session = Depends(get_db)):
    project = None
    if slug_or_id.isdigit():
        project = db.query(Project).filter(Project.id == int(slug_or_id), Project.is_published == True).first()
    
    if not project:
        project = db.query(Project).filter(Project.slug == slug_or_id.lower(), Project.is_published == True).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Published project '{slug_or_id}' was not found in the Studio Desire archive"
        )
    
    pub_media = [m for m in project.media if getattr(m, 'is_published', True)]
    media_out_list = [
        MediaOut(
            id=m.id,
            project_id=m.project_id or project.id,
            media_type=m.media_type,
            url=m.url,
            thumbnail_url=m.thumbnail_url or m.url,
            caption=m.caption,
            alt_text=m.alt_text,
            sort_order=m.sort_order or 0,
            vr_url=getattr(m, "vr_url", None),
            has_vr=bool(getattr(m, "has_vr", False) or getattr(m, "vr_url", None)),
            show_qr=bool(getattr(m, "show_qr", False)),
            vr_type=getattr(m, "vr_type", "external") or "external",
            vr_build_entry=getattr(m, "vr_build_entry", None)
        )
        for m in pub_media
    ]
    return ProjectDetailOut(
        id=project.id,
        title=project.title,
        slug=project.slug,
        subtitle=project.subtitle,
        location=project.location,
        year=project.year,
        category=project.category,
        category_id=project.category_id,
        subcategory_id=project.subcategory_id,
        project_type=project.project_type,
        area=project.area,
        description=project.description,
        cover_image=project.cover_image,
        featured=project.featured,
        is_demo=project.is_demo,
        is_published=project.is_published,
        vr_url=project.vr_url,
        vr_qr_code=project.vr_qr_code,
        show_qr=getattr(project, "show_qr", True) if getattr(project, "show_qr", True) is not None else True,
        vr_type=getattr(project, "vr_type", "external") or "external",
        vr_build_entry=getattr(project, "vr_build_entry", None),
        grid_span=project.grid_span or "span-6",
        aspect_ratio=project.aspect_ratio or "ratio-standard",
        created_at=project.created_at,
        updated_at=project.updated_at,
        media=media_out_list
    )
