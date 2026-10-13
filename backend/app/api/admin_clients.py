from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.client import Client
    from app.models.project import Project
    from app.models.user import User
    from app.schemas.client import ClientCreate, ClientUpdate, ClientOut, ClientDetailOut, ProjectShortOut
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.client import Client
    from backend.app.models.project import Project
    from backend.app.models.user import User
    from backend.app.schemas.client import ClientCreate, ClientUpdate, ClientOut, ClientDetailOut, ProjectShortOut
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/clients", tags=["Admin Clients"])


@router.get("", response_model=List[ClientOut], summary="List all clients")
def list_clients(
    q: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Client)
    if q and q.strip():
        search = f"%{q.strip().lower()}%"
        query = query.filter(
            (func.lower(Client.name).like(search)) |
            (func.lower(Client.email).like(search)) |
            (func.lower(Client.company).like(search)) |
            (func.lower(Client.phone).like(search))
        )
    clients = query.order_by(Client.id.desc()).all()
    results = []
    for c in clients:
        p_count = db.query(Project).filter(Project.client_id == c.id).count()
        c_dict = {
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "email": c.email,
            "phone": c.phone,
            "address": c.address,
            "notes": c.notes,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "project_count": p_count
        }
        results.append(ClientOut(**c_dict))
    return results


@router.post("", response_model=ClientOut, summary="Create a new client")
def create_client(
    payload: ClientCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER", "DESIGNER"])),
    db: Session = Depends(get_db)
):
    client = Client(
        name=payload.name.strip(),
        company=payload.company.strip() if payload.company else None,
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        address=payload.address.strip() if payload.address else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    log_activity(db, current_user, action="Created Client", entity_type="client", entity_id=str(client.id), details=f"Client '{client.name}' created")

    return ClientOut(
        id=client.id,
        name=client.name,
        company=client.company,
        email=client.email,
        phone=client.phone,
        address=client.address,
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at,
        project_count=0
    )


@router.get("/{client_id}", response_model=ClientDetailOut, summary="Get client details with associated projects")
def get_client_detail(
    client_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    projects = db.query(Project).filter(Project.client_id == client.id).order_by(Project.id.desc()).all()
    p_outs = [
        ProjectShortOut(
            id=p.id,
            title=p.title,
            slug=p.slug,
            category=p.category,
            status=p.status or "PLANNING",
            is_published=bool(p.is_published),
            cover_image=p.cover_image
        ) for p in projects
    ]

    return ClientDetailOut(
        id=client.id,
        name=client.name,
        company=client.company,
        email=client.email,
        phone=client.phone,
        address=client.address,
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at,
        project_count=len(projects),
        projects=p_outs
    )


@router.put("/{client_id}", response_model=ClientOut, summary="Update client details")
def update_client(
    client_id: int,
    payload: ClientUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(client, key, value)

    db.commit()
    db.refresh(client)

    log_activity(db, current_user, action="Updated Client", entity_type="client", entity_id=str(client.id), details=f"Client '{client.name}' updated")

    p_count = db.query(Project).filter(Project.client_id == client.id).count()
    return ClientOut(
        id=client.id,
        name=client.name,
        company=client.company,
        email=client.email,
        phone=client.phone,
        address=client.address,
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at,
        project_count=p_count
    )


@router.delete("/{client_id}", summary="Delete client")
def delete_client(
    client_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    name = client.name
    # Unlink client from projects so projects are not orphaned
    db.query(Project).filter(Project.client_id == client.id).update({"client_id": None})
    db.delete(client)
    db.commit()

    log_activity(db, current_user, action="Deleted Client", entity_type="client", entity_id=str(client_id), details=f"Deleted client '{name}'")

    return {"success": True, "message": f"Client '{name}' deleted successfully."}
