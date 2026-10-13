from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.material import ProjectMaterial
    from app.models.project import Project
    from app.models.user import User
    from app.schemas.material import MaterialCreate, MaterialUpdate, MaterialOut
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.material import ProjectMaterial
    from backend.app.models.project import Project
    from backend.app.models.user import User
    from backend.app.schemas.material import MaterialCreate, MaterialUpdate, MaterialOut
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/materials", tags=["Admin Materials"])


@router.get("", response_model=List[MaterialOut], summary="List materials across projects or filtered")
def list_materials(
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectMaterial).join(Project, ProjectMaterial.project_id == Project.id)
    if project_id:
        query = query.filter(ProjectMaterial.project_id == project_id)
    if category:
        query = query.filter(func.lower(ProjectMaterial.category) == category.lower())
    if status:
        query = query.filter(ProjectMaterial.status == status.upper())

    materials = query.order_by(ProjectMaterial.id.desc()).all()
    results = []
    for m in materials:
        results.append(
            MaterialOut(
                id=m.id,
                project_id=m.project_id,
                project_title=m.project.title if m.project else "Unknown Project",
                name=m.name,
                category=m.category,
                supplier=m.supplier,
                reference=m.reference,
                price=m.price or 0.0,
                quantity=m.quantity,
                notes=m.notes,
                image_url=m.image_url,
                status=m.status or "PROPOSED",
                created_at=m.created_at,
                updated_at=m.updated_at
            )
        )
    return results


@router.post("", response_model=MaterialOut, summary="Add material specification")
def create_material(
    payload: MaterialCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    material = ProjectMaterial(
        project_id=payload.project_id,
        name=payload.name.strip(),
        category=payload.category.strip(),
        supplier=payload.supplier.strip() if payload.supplier else None,
        reference=payload.reference.strip() if payload.reference else None,
        price=payload.price,
        quantity=payload.quantity.strip() if payload.quantity else None,
        notes=payload.notes.strip() if payload.notes else None,
        image_url=payload.image_url.strip() if payload.image_url else None,
        status=payload.status.upper()
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    log_activity(db, current_user, action="Added Material Specification", entity_type="material", entity_id=str(material.id), details=f"'{material.name}' ({material.category}) added to '{project.title}'")

    return MaterialOut(
        id=material.id,
        project_id=material.project_id,
        project_title=project.title,
        name=material.name,
        category=material.category,
        supplier=material.supplier,
        reference=material.reference,
        price=material.price,
        quantity=material.quantity,
        notes=material.notes,
        image_url=material.image_url,
        status=material.status,
        created_at=material.created_at,
        updated_at=material.updated_at
    )


@router.put("/{material_id}", response_model=MaterialOut, summary="Update material specification")
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    material = db.query(ProjectMaterial).filter(ProjectMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and isinstance(value, str):
            value = value.upper()
        setattr(material, key, value)

    db.commit()
    db.refresh(material)

    log_activity(db, current_user, action="Updated Material", entity_type="material", entity_id=str(material.id), details=f"Material '{material.name}' updated")

    p_title = material.project.title if material.project else "Unknown Project"
    return MaterialOut(
        id=material.id,
        project_id=material.project_id,
        project_title=p_title,
        name=material.name,
        category=material.category,
        supplier=material.supplier,
        reference=material.reference,
        price=material.price,
        quantity=material.quantity,
        notes=material.notes,
        image_url=material.image_url,
        status=material.status,
        created_at=material.created_at,
        updated_at=material.updated_at
    )


@router.delete("/{material_id}", summary="Delete material")
def delete_material(
    material_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER"])),
    db: Session = Depends(get_db)
):
    material = db.query(ProjectMaterial).filter(ProjectMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    name = material.name
    db.delete(material)
    db.commit()

    log_activity(db, current_user, action="Deleted Material", entity_type="material", entity_id=str(material_id), details=f"Deleted material '{name}'")

    return {"success": True, "message": f"Material '{name}' removed."}
