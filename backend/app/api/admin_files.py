from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.file import ProjectFile
    from app.models.project import Project
    from app.models.user import User
    from app.schemas.file import ProjectFileCreate, ProjectFileOut
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.file import ProjectFile
    from backend.app.models.project import Project
    from backend.app.models.user import User
    from backend.app.schemas.file import ProjectFileCreate, ProjectFileOut
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/files", tags=["Admin Project Files"])


@router.get("", response_model=List[ProjectFileOut], summary="List project files (all or by project/category)")
def list_files(
    project_id: Optional[int] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ProjectFile).join(Project, ProjectFile.project_id == Project.id)
    if project_id:
        query = query.filter(ProjectFile.project_id == project_id)
    if category:
        query = query.filter(func.lower(ProjectFile.category) == category.lower())

    files = query.order_by(ProjectFile.id.desc()).all()
    results = []
    for f in files:
        results.append(
            ProjectFileOut(
                id=f.id,
                project_id=f.project_id,
                project_title=f.project.title if f.project else "Unknown Project",
                name=f.name,
                category=f.category or "Other",
                file_url=f.file_url,
                file_type=f.file_type or "pdf",
                file_size=f.file_size or 0,
                uploaded_by=f.uploaded_by,
                notes=f.notes,
                created_at=f.created_at
            )
        )
    return results


@router.post("", response_model=ProjectFileOut, summary="Register project file record")
def create_file(
    payload: ProjectFileCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER", "EDITOR", "UPLOADER"])),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pfile = ProjectFile(
        project_id=payload.project_id,
        name=payload.name.strip(),
        category=payload.category.strip(),
        file_url=payload.file_url.strip(),
        file_type=payload.file_type.strip() if payload.file_type else "pdf",
        file_size=payload.file_size,
        uploaded_by=payload.uploaded_by or current_user.username,
        notes=payload.notes.strip() if payload.notes else None
    )
    db.add(pfile)
    db.commit()
    db.refresh(pfile)

    log_activity(db, current_user, action="Uploaded Project File", entity_type="file", entity_id=str(pfile.id), details=f"File '{pfile.name}' ({pfile.category}) added to '{project.title}'")

    return ProjectFileOut(
        id=pfile.id,
        project_id=pfile.project_id,
        project_title=project.title,
        name=pfile.name,
        category=pfile.category,
        file_url=pfile.file_url,
        file_type=pfile.file_type,
        file_size=pfile.file_size,
        uploaded_by=pfile.uploaded_by,
        notes=pfile.notes,
        created_at=pfile.created_at
    )


@router.delete("/{file_id}", summary="Delete project file record")
def delete_file(
    file_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    pfile = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not pfile:
        raise HTTPException(status_code=404, detail="File not found")

    name = pfile.name
    db.delete(pfile)
    db.commit()

    log_activity(db, current_user, action="Deleted Project File", entity_type="file", entity_id=str(file_id), details=f"Deleted file '{name}'")

    return {"success": True, "message": f"File '{name}' removed."}
