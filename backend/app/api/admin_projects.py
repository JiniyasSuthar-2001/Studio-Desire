import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.project import Project, ProjectMedia
    from app.models.client import Client
    from app.models.task import Task
    from app.models.milestone import ProjectMilestone
    from app.models.material import ProjectMaterial
    from app.models.file import ProjectFile
    from app.models.meeting import Meeting
    from app.models.finance import PaymentRecord
    from app.models.visualization import VisualizationSpace, VisualizationMedia
    from app.models.blueprint import BlueprintDrawing
    from app.models.user import User, UserRole
    from app.models.category import PortfolioCategory, PortfolioSubcategory
    from app.schemas.admin import (
        ProjectAdminOut,
        ProjectCreate,
        ProjectUpdate,
        ProjectCounts
    )
    from app.schemas.task import TaskOut
    from app.schemas.milestone import MilestoneOut, MilestoneCreate, MilestoneUpdate
    from app.schemas.material import MaterialOut
    from app.schemas.file import ProjectFileOut
    from app.schemas.meeting import MeetingOut
    from app.schemas.finance import ProjectFinanceOut, PaymentOut
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.models.client import Client
    from backend.app.models.task import Task
    from backend.app.models.milestone import ProjectMilestone
    from backend.app.models.material import ProjectMaterial
    from backend.app.models.file import ProjectFile
    from backend.app.models.meeting import Meeting
    from backend.app.models.finance import PaymentRecord
    from backend.app.models.visualization import VisualizationSpace, VisualizationMedia
    from backend.app.models.blueprint import BlueprintDrawing
    from backend.app.models.user import User, UserRole
    from backend.app.models.category import PortfolioCategory, PortfolioSubcategory
    from backend.app.schemas.admin import (
        ProjectAdminOut,
        ProjectCreate,
        ProjectUpdate,
        ProjectCounts
    )
    from backend.app.schemas.task import TaskOut
    from backend.app.schemas.milestone import MilestoneOut, MilestoneCreate, MilestoneUpdate
    from backend.app.schemas.material import MaterialOut
    from backend.app.schemas.file import ProjectFileOut
    from backend.app.schemas.meeting import MeetingOut
    from backend.app.schemas.finance import ProjectFinanceOut, PaymentOut
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/projects", tags=["Admin Projects & Workspace"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def get_project_counts(project: Project, db: Session) -> ProjectCounts:
    photos = db.query(ProjectMedia).filter(
        ProjectMedia.project_id == project.id, 
        ProjectMedia.media_type.in_(["image", "photo"])
    ).count()

    videos = db.query(ProjectMedia).filter(
        ProjectMedia.project_id == project.id, 
        ProjectMedia.media_type == "video"
    ).count()

    renders_3d = db.query(VisualizationMedia).join(VisualizationSpace).filter(
        (VisualizationSpace.project_id == project.id) | 
        (func.lower(VisualizationSpace.project_name) == project.title.lower())
    ).count()

    blueprints = db.query(BlueprintDrawing).filter(
        (BlueprintDrawing.project_id == project.id) | 
        (BlueprintDrawing.project_slug == project.slug)
    ).count()

    vr_rooms = db.query(VisualizationSpace).filter(
        ((VisualizationSpace.project_id == project.id) | (func.lower(VisualizationSpace.project_name) == project.title.lower())),
        ((VisualizationSpace.has_vr == True) | (VisualizationSpace.vr_url != None))
    ).count()

    tasks_open = db.query(Task).filter(
        Task.project_id == project.id,
        Task.status.in_(["TODO", "IN_PROGRESS", "WAITING"])
    ).count()

    materials_count = db.query(ProjectMaterial).filter(
        ProjectMaterial.project_id == project.id
    ).count()

    files_count = db.query(ProjectFile).filter(
        ProjectFile.project_id == project.id
    ).count()

    return ProjectCounts(
        photos=photos,
        videos=videos,
        renders_3d=renders_3d,
        blueprints=blueprints,
        vr_rooms=vr_rooms,
        tasks_open=tasks_open,
        materials_count=materials_count,
        files_count=files_count
    )


@router.get("", response_model=List[ProjectAdminOut], summary="List all projects with real counts and metrics")
def list_admin_projects(
    status: Optional[str] = None,
    category: Optional[str] = None,
    client_id: Optional[int] = None,
    published: Optional[bool] = None,
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Project).options(joinedload(Project.client))

    if status:
        query = query.filter(Project.status == status.upper())
    if category:
        query = query.filter(func.lower(Project.category) == category.lower())
    if client_id:
        query = query.filter(Project.client_id == client_id)
    if published is not None:
        query = query.filter(Project.is_published == published)
    if q and q.strip():
        search = f"%{q.strip().lower()}%"
        query = query.filter(
            (func.lower(Project.title).like(search)) |
            (func.lower(Project.location).like(search)) |
            (func.lower(Project.description).like(search))
        )

    projects = query.order_by(Project.id.desc()).all()
    if not projects:
        return []

    project_ids = [p.id for p in projects]
    project_title_map = {p.title.lower(): p.id for p in projects if p.title}
    project_slug_map = {p.slug: p.id for p in projects if p.slug}

    # Batch counts to eliminate N+1 roundtrips
    # 1. Media: photos & videos
    media_rows = db.query(
        ProjectMedia.project_id,
        ProjectMedia.media_type,
        func.count(ProjectMedia.id)
    ).filter(
        ProjectMedia.project_id.in_(project_ids)
    ).group_by(ProjectMedia.project_id, ProjectMedia.media_type).all()

    photos_map: Dict[int, int] = {}
    videos_map: Dict[int, int] = {}
    for pid, mtype, cnt in media_rows:
        if mtype in ("image", "photo"):
            photos_map[pid] = photos_map.get(pid, 0) + cnt
        elif mtype == "video":
            videos_map[pid] = videos_map.get(pid, 0) + cnt

    # 2. 3D Renders (by project_id or project_name)
    renders_rows = db.query(
        VisualizationSpace.project_id,
        func.lower(VisualizationSpace.project_name),
        func.count(VisualizationMedia.id)
    ).join(VisualizationMedia, VisualizationMedia.space_id == VisualizationSpace.id).filter(
        (VisualizationSpace.project_id.in_(project_ids)) |
        (func.lower(VisualizationSpace.project_name).in_(list(project_title_map.keys())))
    ).group_by(VisualizationSpace.project_id, func.lower(VisualizationSpace.project_name)).all()

    renders_map: Dict[int, int] = {}
    for pid, pname, cnt in renders_rows:
        target_pid = pid if pid in project_ids else project_title_map.get(pname)
        if target_pid:
            renders_map[target_pid] = renders_map.get(target_pid, 0) + cnt

    # 3. Blueprints (by project_id or project_slug)
    blueprints_rows = db.query(
        BlueprintDrawing.project_id,
        BlueprintDrawing.project_slug,
        func.count(BlueprintDrawing.id)
    ).filter(
        (BlueprintDrawing.project_id.in_(project_ids)) |
        (BlueprintDrawing.project_slug.in_(list(project_slug_map.keys())))
    ).group_by(BlueprintDrawing.project_id, BlueprintDrawing.project_slug).all()

    blueprints_map: Dict[int, int] = {}
    for pid, pslug, cnt in blueprints_rows:
        target_pid = pid if pid in project_ids else project_slug_map.get(pslug)
        if target_pid:
            blueprints_map[target_pid] = blueprints_map.get(target_pid, 0) + cnt

    # 4. VR Rooms (by project_id or project_name)
    vr_rows = db.query(
        VisualizationSpace.project_id,
        func.lower(VisualizationSpace.project_name),
        func.count(VisualizationSpace.id)
    ).filter(
        ((VisualizationSpace.project_id.in_(project_ids)) | (func.lower(VisualizationSpace.project_name).in_(list(project_title_map.keys())))),
        ((VisualizationSpace.has_vr == True) | (VisualizationSpace.vr_url != None))
    ).group_by(VisualizationSpace.project_id, func.lower(VisualizationSpace.project_name)).all()

    vr_map: Dict[int, int] = {}
    for pid, pname, cnt in vr_rows:
        target_pid = pid if pid in project_ids else project_title_map.get(pname)
        if target_pid:
            vr_map[target_pid] = vr_map.get(target_pid, 0) + cnt

    # 5. Open Tasks
    tasks_rows = db.query(
        Task.project_id,
        func.count(Task.id)
    ).filter(
        Task.project_id.in_(project_ids),
        Task.status.in_(["TODO", "IN_PROGRESS", "WAITING"])
    ).group_by(Task.project_id).all()
    tasks_map: Dict[int, int] = {pid: cnt for pid, cnt in tasks_rows if pid is not None}

    # 6. Materials
    materials_rows = db.query(
        ProjectMaterial.project_id,
        func.count(ProjectMaterial.id)
    ).filter(
        ProjectMaterial.project_id.in_(project_ids)
    ).group_by(ProjectMaterial.project_id).all()
    materials_map: Dict[int, int] = {pid: cnt for pid, cnt in materials_rows if pid is not None}

    # 7. Files
    files_rows = db.query(
        ProjectFile.project_id,
        func.count(ProjectFile.id)
    ).filter(
        ProjectFile.project_id.in_(project_ids)
    ).group_by(ProjectFile.project_id).all()
    files_map: Dict[int, int] = {pid: cnt for pid, cnt in files_rows if pid is not None}

    results = []
    for p in projects:
        pid = p.id
        counts = ProjectCounts(
            photos=photos_map.get(pid, 0),
            videos=videos_map.get(pid, 0),
            renders_3d=renders_map.get(pid, 0),
            blueprints=blueprints_map.get(pid, 0),
            vr_rooms=vr_map.get(pid, 0),
            tasks_open=tasks_map.get(pid, 0),
            materials_count=materials_map.get(pid, 0),
            files_count=files_map.get(pid, 0)
        )
        c_name = p.client.name if p.client else None
        p_dict = {
            "id": p.id,
            "client_id": p.client_id,
            "client_name": c_name,
            "title": p.title,
            "slug": p.slug,
            "subtitle": p.subtitle,
            "location": p.location,
            "year": p.year,
            "category": p.category,
            "category_id": p.category_id,
            "subcategory_id": p.subcategory_id,
            "project_type": p.project_type,
            "area": p.area,
            "description": p.description,
            "cover_image": p.cover_image or "",
            "status": p.status or "PLANNING",
            "start_date": p.start_date,
            "expected_completion_date": p.expected_completion_date,
            "actual_completion_date": p.actual_completion_date,
            "budget": p.budget or 0.0,
            "project_value": p.project_value or 0.0,
            "amount_received": p.amount_received or 0.0,
            "amount_pending": p.amount_pending or 0.0,
            "featured": bool(p.featured),
            "is_demo": bool(p.is_demo),
            "is_published": bool(p.is_published),
            "vr_url": p.vr_url,
            "vr_qr_code": p.vr_qr_code,
            "show_qr": getattr(p, "show_qr", True) if getattr(p, "show_qr", True) is not None else True,
            "vr_type": getattr(p, "vr_type", "external") or "external",
            "vr_build_entry": getattr(p, "vr_build_entry", None),
            "counts": counts,
            "created_at": p.created_at,
            "updated_at": p.updated_at
        }
        results.append(ProjectAdminOut(**p_dict))
    return results


@router.post("", response_model=ProjectAdminOut, summary="Create new project")
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER", "EDITOR"])),
    db: Session = Depends(get_db)
):
    import secrets

    # 1. Authoritative Portfolio Category Validation
    category_id = payload.category_id
    category_name = None
    target_category = None

    if category_id:
        target_category = db.query(PortfolioCategory).filter(PortfolioCategory.id == category_id).first()
        if not target_category:
            raise HTTPException(status_code=400, detail=f"Category with ID {category_id} does not exist.")
        if not target_category.is_active:
            raise HTTPException(status_code=400, detail=f"Category '{target_category.name}' is inactive and cannot receive new projects.")
        category_name = target_category.name
    elif payload.category and payload.category.strip():
        # Match case-insensitively to registered portfolio category
        clean_cat_input = payload.category.strip()
        target_category = db.query(PortfolioCategory).filter(func.lower(PortfolioCategory.name) == clean_cat_input.lower()).first()
        if not target_category:
            # Check if an active default category exists, otherwise create or reject
            # Portfolio Category Manager is the single source of truth:
            first_cat = db.query(PortfolioCategory).filter(PortfolioCategory.is_active == True).order_by(PortfolioCategory.display_order.asc()).first()
            if first_cat:
                target_category = first_cat
                category_id = first_cat.id
                category_name = first_cat.name
            else:
                raise HTTPException(status_code=400, detail=f"Category '{clean_cat_input}' is not an authoritative portfolio category.")
        else:
            if not target_category.is_active:
                raise HTTPException(status_code=400, detail=f"Category '{target_category.name}' is inactive and cannot receive new projects.")
            category_id = target_category.id
            category_name = target_category.name
    else:
        # Require category selection
        first_cat = db.query(PortfolioCategory).filter(PortfolioCategory.is_active == True).order_by(PortfolioCategory.display_order.asc()).first()
        if not first_cat:
            raise HTTPException(status_code=400, detail="No active portfolio categories found. Please create a category first.")
        category_id = first_cat.id
        category_name = first_cat.name

    # 2. Subcategory Validation (if provided)
    subcategory_id = payload.subcategory_id
    if subcategory_id:
        subcat = db.query(PortfolioSubcategory).filter(
            PortfolioSubcategory.id == subcategory_id,
            PortfolioSubcategory.category_id == category_id
        ).first()
        if not subcat:
            raise HTTPException(status_code=400, detail="Selected subcategory is invalid or does not belong to the selected category.")

    slug = payload.slug or slugify(payload.title)
    existing = db.query(Project).filter(Project.slug == slug).first()
    if existing:
        slug = f"{slug}-{secrets.randbelow(9000) + 1000}"

    cover_img = payload.cover_image or "/uploads/projects/placeholder.webp"

    project = Project(
        title=payload.title.strip(),
        slug=slug,
        client_id=payload.client_id,
        subtitle=payload.subtitle.strip() if payload.subtitle else None,
        location=payload.location.strip() if payload.location else "Ahmedabad, Gujarat",
        year=payload.year,
        category=category_name or "Residential",
        category_id=category_id,
        subcategory_id=subcategory_id,
        project_type=payload.project_type.strip() if payload.project_type else "Private Residence",
        area=payload.area.strip() if payload.area else None,
        description=payload.description.strip() if payload.description else "",
        cover_image=cover_img,
        status=payload.status.upper() if payload.status else "PLANNING",
        start_date=payload.start_date,
        expected_completion_date=payload.expected_completion_date,
        budget=payload.budget,
        project_value=payload.project_value or payload.budget,
        amount_received=0.0,
        amount_pending=payload.project_value or payload.budget,
        featured=payload.featured,
        is_demo=False,
        is_published=payload.is_published,
        vr_url=payload.vr_url
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Initialize standard interior-design milestones
    standard_milestones = [
        ("Consultation & Briefing", "Client needs analysis, site measurements, and project charter", 1),
        ("Concept & Space Planning", "2D layout options, furniture zoning, and mood boards", 2),
        ("3D Design & Visualizations", "Photorealistic rendering of spatial rooms and material textures", 3),
        ("Client Review & Approvals", "Design iteration feedback and sign-off", 4),
        ("Working Drawings & Blueprints", "Electrical, plumbing, ceiling, joinery, and HVAC drawings", 5),
        ("Material Procurement & Site Execution", "On-site civil, carpentry, electrical, and finishing work", 6),
        ("Final Styling & Handover", "Furniture staging, lighting commissioning, and client handover", 7),
    ]
    for m_title, m_desc, m_order in standard_milestones:
        db.add(ProjectMilestone(
            project_id=project.id,
            title=m_title,
            description=m_desc,
            order=m_order,
            status="IN_PROGRESS" if m_order == 1 else "PENDING"
        ))
    db.commit()

    log_activity(db, current_user, action="Created Project", entity_type="project", entity_id=str(project.id), details=f"Created '{project.title}' with category '{project.category}'")

    counts = get_project_counts(project, db)
    c_name = project.client.name if project.client else None
    return ProjectAdminOut(
        id=project.id,
        client_id=project.client_id,
        client_name=c_name,
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
        status=project.status,
        start_date=project.start_date,
        expected_completion_date=project.expected_completion_date,
        actual_completion_date=project.actual_completion_date,
        budget=project.budget,
        project_value=project.project_value,
        amount_received=project.amount_received,
        amount_pending=project.amount_pending,
        featured=bool(project.featured),
        is_demo=bool(project.is_demo),
        is_published=bool(project.is_published),
        vr_url=project.vr_url,
        vr_qr_code=project.vr_qr_code,
        counts=counts,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


@router.get("/{project_id}/workspace", summary="Get complete Project Workspace dossier")
def get_project_workspace(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    counts = get_project_counts(project, db)
    client_data = None
    if project.client:
        client_data = {
            "id": project.client.id,
            "name": project.client.name,
            "company": project.client.company,
            "email": project.client.email,
            "phone": project.client.phone,
            "address": project.client.address
        }

    # Milestones & Progress calculation
    milestones_db = db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project.id).order_by(ProjectMilestone.order).all()
    completed_m = sum(1 for m in milestones_db if m.status == "COMPLETED")
    milestone_progress = (completed_m / len(milestones_db) * 100.0) if milestones_db else 0.0

    return {
        "project": {
            "id": project.id,
            "client_id": project.client_id,
            "title": project.title,
            "slug": project.slug,
            "subtitle": project.subtitle,
            "location": project.location,
            "year": project.year,
            "category": project.category,
            "category_id": project.category_id,
            "subcategory_id": project.subcategory_id,
            "project_type": project.project_type,
            "area": project.area,
            "description": project.description,
            "cover_image": project.cover_image,
            "status": project.status or "PLANNING",
            "start_date": project.start_date,
            "expected_completion_date": project.expected_completion_date,
            "actual_completion_date": project.actual_completion_date,
            "budget": project.budget or 0.0,
            "project_value": project.project_value or 0.0,
            "amount_received": project.amount_received or 0.0,
            "amount_pending": project.amount_pending or 0.0,
            "featured": bool(project.featured),
            "is_published": bool(project.is_published),
            "vr_url": project.vr_url,
            "show_qr": getattr(project, "show_qr", True) if getattr(project, "show_qr", True) is not None else True,
            "vr_type": getattr(project, "vr_type", "external") or "external",
            "vr_build_entry": getattr(project, "vr_build_entry", None),
            "created_at": project.created_at,
            "updated_at": project.updated_at
        },
        "client": client_data,
        "counts": counts,
        "progress_percentage": round(milestone_progress, 1)
    }


@router.get("/{project_id}", response_model=ProjectAdminOut, summary="Get single project detail")
def get_admin_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    counts = get_project_counts(project, db)
    c_name = project.client.name if project.client else None
    p_dict = {
        "id": project.id,
        "client_id": project.client_id,
        "client_name": c_name,
        "title": project.title,
        "slug": project.slug,
        "subtitle": project.subtitle,
        "location": project.location,
        "year": project.year,
        "category": project.category,
        "category_id": project.category_id,
        "subcategory_id": project.subcategory_id,
        "project_type": project.project_type,
        "area": project.area,
        "description": project.description,
        "cover_image": project.cover_image or "",
        "status": project.status or "PLANNING",
        "start_date": project.start_date,
        "expected_completion_date": project.expected_completion_date,
        "actual_completion_date": project.actual_completion_date,
        "budget": project.budget or 0.0,
        "project_value": project.project_value or 0.0,
        "amount_received": project.amount_received or 0.0,
        "amount_pending": project.amount_pending or 0.0,
        "featured": bool(project.featured),
        "is_demo": bool(project.is_demo),
        "is_published": bool(project.is_published),
        "vr_url": project.vr_url,
        "vr_qr_code": project.vr_qr_code,
        "show_qr": getattr(project, "show_qr", True) if getattr(project, "show_qr", True) is not None else True,
        "vr_type": getattr(project, "vr_type", "external") or "external",
        "vr_build_entry": getattr(project, "vr_build_entry", None),
        "counts": counts,
        "created_at": project.created_at,
        "updated_at": project.updated_at
    }
    return ProjectAdminOut(**p_dict)


@router.put("/{project_id}", response_model=ProjectAdminOut, summary="Update project metadata")
@router.patch("/{project_id}", response_model=ProjectAdminOut, summary="Partially update project metadata")
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER", "EDITOR"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.dict(exclude_unset=True)

    # Validate category changes if provided
    if "category_id" in update_data and update_data["category_id"] is not None:
        new_cat = db.query(PortfolioCategory).filter(PortfolioCategory.id == update_data["category_id"]).first()
        if not new_cat:
            raise HTTPException(status_code=400, detail=f"Category with ID {update_data['category_id']} does not exist.")
        project.category_id = new_cat.id
        project.category = new_cat.name
        del update_data["category_id"]
        if "category" in update_data:
            del update_data["category"]
    elif "category" in update_data and update_data["category"]:
        cat_str = update_data["category"].strip()
        new_cat = db.query(PortfolioCategory).filter(func.lower(PortfolioCategory.name) == cat_str.lower()).first()
        if new_cat:
            project.category_id = new_cat.id
            project.category = new_cat.name
            del update_data["category"]
        else:
            project.category = cat_str

    if "subcategory_id" in update_data:
        sub_id = update_data["subcategory_id"]
        if sub_id is not None:
            subcat = db.query(PortfolioSubcategory).filter(
                PortfolioSubcategory.id == sub_id,
                PortfolioSubcategory.category_id == project.category_id
            ).first()
            if not subcat:
                raise HTTPException(status_code=400, detail="Subcategory does not belong to the assigned category.")
        project.subcategory_id = sub_id
        del update_data["subcategory_id"]

    for key, value in update_data.items():
        if key == "status" and isinstance(value, str):
            value = value.upper()
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    log_activity(db, current_user, action="Updated Project", entity_type="project", entity_id=str(project.id), details=f"Updated details for '{project.title}'")

    counts = get_project_counts(project, db)
    c_name = project.client.name if project.client else None
    return ProjectAdminOut(
        id=project.id,
        client_id=project.client_id,
        client_name=c_name,
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
        status=project.status,
        start_date=project.start_date,
        expected_completion_date=project.expected_completion_date,
        actual_completion_date=project.actual_completion_date,
        budget=project.budget,
        project_value=project.project_value,
        amount_received=project.amount_received,
        amount_pending=project.amount_pending,
        featured=bool(project.featured),
        is_demo=bool(project.is_demo),
        is_published=bool(project.is_published),
        vr_url=project.vr_url,
        vr_qr_code=project.vr_qr_code,
        show_qr=getattr(project, "show_qr", True) if getattr(project, "show_qr", True) is not None else True,
        vr_type=getattr(project, "vr_type", "external") or "external",
        vr_build_entry=getattr(project, "vr_build_entry", None),
        counts=counts,
        created_at=project.created_at,
        updated_at=project.updated_at
    )


# Milestones management
@router.get("/{project_id}/milestones", response_model=List[MilestoneOut], summary="List milestones for project")
def list_project_milestones(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project_id).order_by(ProjectMilestone.order).all()


@router.post("/{project_id}/milestones", response_model=MilestoneOut, summary="Add milestone to project")
def create_project_milestone(
    project_id: int,
    payload: MilestoneCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    milestone = ProjectMilestone(
        project_id=project_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        status=payload.status.upper(),
        start_date=payload.start_date,
        due_date=payload.due_date,
        completed_date=payload.completed_date,
        order=payload.order
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.put("/milestones/{milestone_id}", response_model=MilestoneOut, summary="Update milestone")
def update_project_milestone(
    milestone_id: int,
    payload: MilestoneUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and isinstance(value, str):
            value = value.upper()
        setattr(milestone, key, value)

    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete("/milestones/{milestone_id}", summary="Delete milestone")
def delete_project_milestone(
    milestone_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    milestone = db.query(ProjectMilestone).filter(ProjectMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")

    db.delete(milestone)
    db.commit()
    return {"success": True, "message": "Milestone deleted successfully"}


@router.patch("/{project_id}/publish", summary="Toggle project publish/draft status")
def toggle_publish_status(
    project_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.is_published = not project.is_published
    db.commit()

    status_str = "Published" if project.is_published else "Draft"
    log_activity(db, current_user, action=f"Set Status to {status_str}", entity_type="project", entity_id=str(project.id), details=f"'{project.title}' is now {status_str}")

    return {
        "success": True,
        "is_published": project.is_published,
        "message": f"Project '{project.title}' is now {status_str} on the public website."
    }


@router.delete("/{project_id}", summary="Delete project (Requires Owner / Master)")
def delete_project(
    project_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    title = project.title
    db.delete(project)
    db.commit()

    log_activity(db, current_user, action="Deleted Project", entity_type="project", entity_id=str(project_id), details=f"Permanently deleted '{title}'")

    return {"success": True, "message": f"Project '{title}' has been deleted."}
