import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

try:
    from app.database.session import get_db
    from app.models.category import PortfolioCategory, PortfolioSubcategory
    from app.models.project import Project
    from app.models.user import User, UserRole
    from app.schemas.category import (
        PortfolioCategoryCreate,
        PortfolioCategoryUpdate,
        PortfolioCategoryOut,
        PortfolioSubcategoryCreate,
        PortfolioSubcategoryUpdate,
        PortfolioSubcategoryOut,
        CategoryReorderPayload,
        CategoryReassignPayload,
        FeaturedProjectSummary,
        EligibleProjectItemOut,
        SetFeaturedProjectPayload,
    )
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.category import PortfolioCategory, PortfolioSubcategory
    from backend.app.models.project import Project
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.category import (
        PortfolioCategoryCreate,
        PortfolioCategoryUpdate,
        PortfolioCategoryOut,
        PortfolioSubcategoryCreate,
        PortfolioSubcategoryUpdate,
        PortfolioSubcategoryOut,
        CategoryReorderPayload,
        CategoryReassignPayload,
        FeaturedProjectSummary,
        EligibleProjectItemOut,
        SetFeaturedProjectPayload,
    )
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(tags=["Portfolio Categories"])


def slugify(text: str) -> str:
    """Generate clean URL-safe slug from title/name."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", clean)


def build_category_out(cat: PortfolioCategory, db: Session, is_admin: bool = False) -> PortfolioCategoryOut:
    """Helper to assemble full Category output schema with project counts, subcategories, and featured project."""
    # Count assigned projects (both via FK and legacy name match)
    proj_query = db.query(Project).filter(
        or_(
            Project.category_id == cat.id,
            func.lower(Project.category) == cat.name.lower()
        )
    )
    total_projects = proj_query.count()
    published_projects = proj_query.filter(Project.is_published == True).count()
    unpublished_projects = total_projects - published_projects

    featured_summary = None
    featured_proj_id = cat.featured_project_id
    if cat.featured_project_id:
        proj = db.query(Project).filter(Project.id == cat.featured_project_id).first()
        if proj:
            is_valid_membership = (proj.category_id == cat.id) or (
                proj.category and proj.category.strip().lower() == cat.name.strip().lower()
            )
            if is_valid_membership and proj.is_published:
                featured_summary = FeaturedProjectSummary(
                    id=proj.id,
                    title=proj.title,
                    slug=proj.slug,
                    subtitle=proj.subtitle,
                    location=proj.location,
                    year=proj.year,
                    category=proj.category,
                    cover_image=proj.cover_image,
                    is_published=proj.is_published
                )
            elif is_admin:
                featured_summary = FeaturedProjectSummary(
                    id=proj.id,
                    title=proj.title,
                    slug=proj.slug,
                    subtitle=proj.subtitle,
                    location=proj.location,
                    year=proj.year,
                    category=proj.category,
                    cover_image=proj.cover_image,
                    is_published=proj.is_published
                )
            else:
                # In public mode, do not expose unpublished or mismatched representative
                featured_summary = None
                featured_proj_id = None
        else:
            if not is_admin:
                featured_proj_id = None

    subs_out = [
        PortfolioSubcategoryOut(
            id=s.id,
            category_id=s.category_id,
            name=s.name,
            slug=s.slug,
            display_order=s.display_order,
            is_active=s.is_active,
            created_at=s.created_at
        )
        for s in (cat.subcategories or [])
    ]

    return PortfolioCategoryOut(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        description=cat.description,
        display_order=cat.display_order or 1,
        is_active=cat.is_active if cat.is_active is not None else True,
        is_default=cat.is_default if cat.is_default is not None else False,
        cover_image=cat.cover_image,
        puzzle_size=cat.puzzle_size or "small",
        featured_project_id=featured_proj_id,
        featured_project=featured_summary,
        subcategories=subs_out,
        total_projects=total_projects,
        published_projects=published_projects,
        unpublished_projects=unpublished_projects,
        total_projects_count=total_projects,
        published_projects_count=published_projects,
        unpublished_projects_count=unpublished_projects,
        created_at=cat.created_at,
        updated_at=cat.updated_at
    )


# ============================================================================
# 1. PUBLIC CATEGORIES ENDPOINT
# ============================================================================

@router.get("/categories", response_model=List[PortfolioCategoryOut], summary="List active portfolio categories (Public)")
def get_public_categories(db: Session = Depends(get_db)):
    """
    Public endpoint returning active portfolio categories with their subcategories
    and published project counts.
    """
    categories = (
        db.query(PortfolioCategory)
        .filter(PortfolioCategory.is_active == True)
        .order_by(PortfolioCategory.display_order.asc(), PortfolioCategory.id.asc())
        .all()
    )
    return [build_category_out(c, db, is_admin=False) for c in categories]


# ============================================================================
# 2. ADMIN CATEGORIES MANAGEMENT
# ============================================================================

@router.get("/admin/categories", response_model=List[PortfolioCategoryOut], summary="List all portfolio categories for admin management")
def list_admin_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Admin endpoint returning all categories (active and inactive) with complete project counts.
    """
    categories = (
        db.query(PortfolioCategory)
        .order_by(PortfolioCategory.display_order.asc(), PortfolioCategory.id.asc())
        .all()
    )
    return [build_category_out(c, db, is_admin=True) for c in categories]


@router.get("/admin/categories/{category_id}", response_model=PortfolioCategoryOut, summary="Get single category details")
def get_category_detail(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return build_category_out(cat, db, is_admin=True)


@router.post("/admin/categories", response_model=PortfolioCategoryOut, summary="Create a new portfolio category")
def create_category(
    payload: PortfolioCategoryCreate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Category name cannot be empty")

    clean_slug = (payload.slug.strip() if payload.slug else slugify(clean_name)) or f"cat-{int(func.now())}"

    # Check for existing name or slug
    existing = db.query(PortfolioCategory).filter(
        or_(
            func.lower(PortfolioCategory.name) == clean_name.lower(),
            PortfolioCategory.slug == clean_slug
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"A category with name '{clean_name}' or slug '{clean_slug}' already exists.")

    # Max display order
    max_order = db.query(func.max(PortfolioCategory.display_order)).scalar() or 0
    display_order = payload.display_order if payload.display_order > 1 else max_order + 1

    cat = PortfolioCategory(
        name=clean_name,
        slug=clean_slug,
        description=payload.description.strip() if payload.description else None,
        display_order=display_order,
        is_active=payload.is_active,
        is_default=False,
        cover_image=payload.cover_image.strip() if payload.cover_image else None,
        puzzle_size=payload.puzzle_size or "small"
    )
    db.add(cat)
    db.flush()

    # Subcategories if provided
    if payload.subcategories:
        for idx, sub_name in enumerate(payload.subcategories, start=1):
            clean_sub = sub_name.strip()
            if clean_sub:
                sub = PortfolioSubcategory(
                    category_id=cat.id,
                    name=clean_sub,
                    slug=slugify(clean_sub) or f"sub-{idx}",
                    display_order=idx,
                    is_active=True
                )
                db.add(sub)

    db.commit()
    db.refresh(cat)

    log_activity(
        db,
        current_user,
        action="Created Portfolio Category",
        entity_type="category",
        entity_id=str(cat.id),
        details=f"Created category '{cat.name}'"
    )

    return build_category_out(cat, db)


@router.put("/admin/categories/{category_id}", response_model=PortfolioCategoryOut, summary="Update portfolio category")
def update_category(
    category_id: int,
    payload: PortfolioCategoryUpdate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    old_name = cat.name

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Category name cannot be empty")
        
        # Check duplicate
        dup = db.query(PortfolioCategory).filter(
            func.lower(PortfolioCategory.name) == clean_name.lower(),
            PortfolioCategory.id != category_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Category name '{clean_name}' is already taken.")
        cat.name = clean_name

    if payload.slug is not None:
        clean_slug = payload.slug.strip() or slugify(cat.name)
        dup = db.query(PortfolioCategory).filter(
            PortfolioCategory.slug == clean_slug,
            PortfolioCategory.id != category_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Category slug '{clean_slug}' is already taken.")
        cat.slug = clean_slug

    if payload.description is not None:
        cat.description = payload.description.strip() if payload.description else None

    if payload.display_order is not None:
        cat.display_order = payload.display_order

    if payload.is_active is not None:
        cat.is_active = payload.is_active

    if payload.cover_image is not None:
        cat.cover_image = payload.cover_image.strip() if payload.cover_image else None

    if payload.puzzle_size is not None:
        cat.puzzle_size = payload.puzzle_size

    if payload.featured_project_id is not None:
        if payload.featured_project_id <= 0:
            cat.featured_project_id = None
        else:
            proj = db.query(Project).filter(Project.id == payload.featured_project_id).first()
            if not proj:
                raise HTTPException(status_code=404, detail="Selected project not found")
            is_member = (proj.category_id == cat.id) or (
                proj.category and proj.category.strip().lower() == cat.name.strip().lower()
            )
            if not is_member:
                raise HTTPException(
                    status_code=400,
                    detail=f"Project '{proj.title}' does not belong to category '{cat.name}'. A project cannot be assigned as representative for an unrelated category."
                )
            if not proj.is_published:
                raise HTTPException(
                    status_code=400,
                    detail=f"Project '{proj.title}' is currently unpublished (Draft). Representative projects must be published before being featured on the homepage."
                )
            cat.featured_project_id = proj.id

    # Synchronize project category string names if name was updated
    if payload.name is not None and cat.name != old_name:
        db.query(Project).filter(
            or_(
                Project.category_id == cat.id,
                func.lower(Project.category) == old_name.lower()
            )
        ).update({"category": cat.name, "category_id": cat.id}, synchronize_session=False)

    db.commit()
    db.refresh(cat)

    log_activity(
        db,
        current_user,
        action="Updated Portfolio Category",
        entity_type="category",
        entity_id=str(cat.id),
        details=f"Updated category '{cat.name}'"
    )

    return build_category_out(cat, db, is_admin=True)


@router.put("/admin/categories/{category_id}/featured-project", response_model=PortfolioCategoryOut, summary="Set or clear category homepage representative project")
def set_category_featured_project(
    category_id: int,
    payload: SetFeaturedProjectPayload,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if not payload.project_id or payload.project_id <= 0:
        cat.featured_project_id = None
        action_msg = f"Cleared representative project for category '{cat.name}'"
    else:
        proj = db.query(Project).filter(Project.id == payload.project_id).first()
        if not proj:
            raise HTTPException(status_code=404, detail="Selected project not found")
        is_member = (proj.category_id == cat.id) or (
            proj.category and proj.category.strip().lower() == cat.name.strip().lower()
        )
        if not is_member:
            raise HTTPException(
                status_code=400,
                detail=f"Project '{proj.title}' does not belong to category '{cat.name}'. A project cannot be assigned as representative for an unrelated category."
            )
        if not proj.is_published:
            raise HTTPException(
                status_code=400,
                detail=f"Project '{proj.title}' is currently unpublished (Draft). Representative projects must be published before being featured on the homepage."
            )
        cat.featured_project_id = proj.id
        action_msg = f"Assigned representative project #{proj.id} ('{proj.title}') for category '{cat.name}'"

    db.commit()
    db.refresh(cat)

    log_activity(
        db,
        current_user,
        action="Updated Category Representative",
        entity_type="category",
        entity_id=str(cat.id),
        details=action_msg
    )

    return build_category_out(cat, db, is_admin=True)


@router.get("/admin/categories/{category_id}/eligible-projects", response_model=List[EligibleProjectItemOut], summary="List eligible projects for category representative assignment")
def list_eligible_projects_for_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    projects = db.query(Project).filter(
        or_(
            Project.category_id == cat.id,
            func.lower(Project.category) == cat.name.lower()
        )
    ).order_by(Project.is_published.desc(), Project.featured.desc(), Project.id.desc()).all()

    return [
        EligibleProjectItemOut(
            id=p.id,
            title=p.title,
            slug=p.slug,
            subtitle=p.subtitle,
            location=p.location,
            year=p.year,
            category=p.category,
            category_id=p.category_id,
            cover_image=p.cover_image,
            is_published=p.is_published,
            is_current_representative=(cat.featured_project_id == p.id)
        )
        for p in projects
    ]


@router.patch("/admin/categories/reorder", summary="Reorder portfolio categories")
def reorder_categories(
    payload: CategoryReorderPayload,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    for item in payload.items:
        db.query(PortfolioCategory).filter(PortfolioCategory.id == item.id).update(
            {"display_order": item.display_order},
            synchronize_session=False
        )
    db.commit()

    log_activity(
        db,
        current_user,
        action="Reordered Portfolio Categories",
        entity_type="category",
        details=f"Updated display order for {len(payload.items)} categories"
    )

    return {"success": True, "message": "Categories reordered successfully."}


@router.delete("/admin/categories/{category_id}", summary="Delete a category with reassignment protection")
def delete_category(
    category_id: int,
    reassign_to_id: Optional[int] = Query(None, description="Optional target category ID to safely reassign projects to before deletion"),
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    if cat.is_default or cat.slug in ("residential", "commercial", "hospitality"):
        raise HTTPException(
            status_code=400,
            detail=f"Category '{cat.name}' is a core portfolio category and cannot be deleted. You may deactivate it instead."
        )

    # Check assigned projects
    assigned_count = db.query(Project).filter(
        or_(
            Project.category_id == cat.id,
            func.lower(Project.category) == cat.name.lower()
        )
    ).count()

    if assigned_count > 0:
        if not reassign_to_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot delete category '{cat.name}' because it contains {assigned_count} assigned projects. "
                    "Please reassign those projects to another category before deleting, or provide 'reassign_to_id'."
                )
            )
        
        target_cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == reassign_to_id).first()
        if not target_cat or target_cat.id == category_id:
            raise HTTPException(status_code=400, detail="Invalid target category for project reassignment.")

        # Reassign projects
        db.query(Project).filter(
            or_(
                Project.category_id == cat.id,
                func.lower(Project.category) == cat.name.lower()
            )
        ).update(
            {"category": target_cat.name, "category_id": target_cat.id, "subcategory_id": None},
            synchronize_session=False
        )

    cat_name = cat.name
    db.delete(cat)
    db.commit()

    log_activity(
        db,
        current_user,
        action="Deleted Portfolio Category",
        entity_type="category",
        entity_id=str(category_id),
        details=f"Deleted category '{cat_name}' (reassigned {assigned_count} projects)"
    )

    return {"success": True, "message": f"Category '{cat_name}' deleted successfully."}


@router.post("/admin/categories/{category_id}/reassign", summary="Explicitly reassign all projects from one category to another")
def reassign_category_projects(
    category_id: int,
    payload: CategoryReassignPayload,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    source_cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not source_cat:
        raise HTTPException(status_code=404, detail="Source category not found")

    target_cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == payload.target_category_id).first()
    if not target_cat:
        raise HTTPException(status_code=404, detail="Target category not found")

    if source_cat.id == target_cat.id:
        raise HTTPException(status_code=400, detail="Source and target category must be different.")

    updated_count = db.query(Project).filter(
        or_(
            Project.category_id == source_cat.id,
            func.lower(Project.category) == source_cat.name.lower()
        )
    ).update(
        {"category": target_cat.name, "category_id": target_cat.id, "subcategory_id": None},
        synchronize_session=False
    )
    db.commit()

    log_activity(
        db,
        current_user,
        action="Reassigned Projects Category",
        entity_type="category",
        details=f"Reassigned {updated_count} projects from '{source_cat.name}' to '{target_cat.name}'"
    )

    return {
        "success": True,
        "reassigned_count": updated_count,
        "message": f"Successfully reassigned {updated_count} projects to '{target_cat.name}'."
    }


# ============================================================================
# 3. SUBCATEGORIES MANAGEMENT
# ============================================================================

@router.post("/admin/categories/{category_id}/subcategories", response_model=PortfolioSubcategoryOut, summary="Add a subcategory to a category")
def create_subcategory(
    category_id: int,
    payload: PortfolioSubcategoryCreate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Parent category not found")

    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Subcategory name cannot be empty")

    clean_slug = payload.slug.strip() if payload.slug else slugify(clean_name)

    existing = db.query(PortfolioSubcategory).filter(
        PortfolioSubcategory.category_id == category_id,
        func.lower(PortfolioSubcategory.name) == clean_name.lower()
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Subcategory '{clean_name}' already exists under '{cat.name}'.")

    max_order = db.query(func.max(PortfolioSubcategory.display_order)).filter(PortfolioSubcategory.category_id == category_id).scalar() or 0

    sub = PortfolioSubcategory(
        category_id=category_id,
        name=clean_name,
        slug=clean_slug,
        display_order=payload.display_order if payload.display_order > 1 else max_order + 1,
        is_active=payload.is_active
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)

    return PortfolioSubcategoryOut(
        id=sub.id,
        category_id=sub.category_id,
        name=sub.name,
        slug=sub.slug,
        display_order=sub.display_order,
        is_active=sub.is_active,
        created_at=sub.created_at
    )


@router.put("/admin/categories/{category_id}/subcategories/{sub_id}", response_model=PortfolioSubcategoryOut, summary="Update subcategory")
def update_subcategory(
    category_id: int,
    sub_id: int,
    payload: PortfolioSubcategoryUpdate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    sub = db.query(PortfolioSubcategory).filter(
        PortfolioSubcategory.id == sub_id,
        PortfolioSubcategory.category_id == category_id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subcategory not found under this category")

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Subcategory name cannot be empty")
        sub.name = clean_name

    if payload.slug is not None:
        sub.slug = payload.slug.strip() or slugify(sub.name)

    if payload.display_order is not None:
        sub.display_order = payload.display_order

    if payload.is_active is not None:
        sub.is_active = payload.is_active

    db.commit()
    db.refresh(sub)

    return PortfolioSubcategoryOut(
        id=sub.id,
        category_id=sub.category_id,
        name=sub.name,
        slug=sub.slug,
        display_order=sub.display_order,
        is_active=sub.is_active,
        created_at=sub.created_at
    )


@router.delete("/admin/categories/{category_id}/subcategories/{sub_id}", summary="Delete subcategory")
def delete_subcategory(
    category_id: int,
    sub_id: int,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN", "EDITOR"])),
    db: Session = Depends(get_db)
):
    sub = db.query(PortfolioSubcategory).filter(
        PortfolioSubcategory.id == sub_id,
        PortfolioSubcategory.category_id == category_id
    ).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    # Clear subcategory_id from projects using it
    db.query(Project).filter(Project.subcategory_id == sub_id).update({"subcategory_id": None}, synchronize_session=False)

    sub_name = sub.name
    db.delete(sub)
    db.commit()

    return {"success": True, "message": f"Subcategory '{sub_name}' deleted."}
