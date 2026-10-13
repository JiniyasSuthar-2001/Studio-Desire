from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.project import Project
    from app.models.client import Client
    from app.models.enquiry import ProjectEnquiry
    from app.models.product import Product
    from app.models.file import ProjectFile
    from app.models.user import User
    from app.schemas.admin import GlobalSearchOut, SearchResultItem
    from app.core.dependencies import get_current_user
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.project import Project
    from backend.app.models.client import Client
    from backend.app.models.enquiry import ProjectEnquiry
    from backend.app.models.product import Product
    from backend.app.models.file import ProjectFile
    from backend.app.models.user import User
    from backend.app.schemas.admin import GlobalSearchOut, SearchResultItem
    from backend.app.core.dependencies import get_current_user

router = APIRouter(prefix="/admin/search", tags=["Admin Global Search"])


@router.get("", response_model=GlobalSearchOut, summary="Search across projects, clients, enquiries, products, files")
def global_search(
    q: str = Query(..., min_length=1, description="Search query string"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query_str = q.strip()
    pattern = f"%{query_str.lower()}%"

    # 1. Projects
    projects_db = db.query(Project).filter(
        (func.lower(Project.title).like(pattern)) |
        (func.lower(Project.location).like(pattern)) |
        (func.lower(Project.category).like(pattern)) |
        (func.lower(Project.description).like(pattern))
    ).limit(8).all()
    project_results = [
        SearchResultItem(
            id=p.id,
            title=p.title,
            subtitle=f"{p.category} · {p.location} ({p.status})",
            category="project",
            url_tab="projects",
            context_data={"slug": p.slug, "id": p.id}
        ) for p in projects_db
    ]

    # 2. Clients
    clients_db = db.query(Client).filter(
        (func.lower(Client.name).like(pattern)) |
        (func.lower(Client.email).like(pattern)) |
        (func.lower(Client.company).like(pattern)) |
        (func.lower(Client.phone).like(pattern))
    ).limit(8).all()
    client_results = [
        SearchResultItem(
            id=c.id,
            title=c.name,
            subtitle=f"{c.company or 'Individual'} · {c.phone or c.email or ''}",
            category="client",
            url_tab="clients",
            context_data={"id": c.id}
        ) for c in clients_db
    ]

    # 3. Enquiries
    enquiries_db = db.query(ProjectEnquiry).filter(
        (func.lower(ProjectEnquiry.name).like(pattern)) |
        (func.lower(ProjectEnquiry.email).like(pattern)) |
        (func.lower(ProjectEnquiry.reference_number).like(pattern)) |
        (func.lower(ProjectEnquiry.project_type).like(pattern)) |
        (func.lower(ProjectEnquiry.location).like(pattern))
    ).limit(8).all()
    enquiry_results = [
        SearchResultItem(
            id=e.id,
            title=f"{e.name} ({e.reference_number})",
            subtitle=f"{e.project_type} · Status: {e.status}",
            category="enquiry",
            url_tab="enquiries",
            context_data={"id": e.id}
        ) for e in enquiries_db
    ]

    # 4. Products
    products_db = db.query(Product).filter(
        (func.lower(Product.title).like(pattern)) |
        (func.lower(Product.category).like(pattern)) |
        (func.lower(Product.materials).like(pattern))
    ).limit(8).all()
    product_results = [
        SearchResultItem(
            id=pr.id,
            title=pr.title,
            subtitle=f"Product · {pr.category}",
            category="product",
            url_tab="content",
            context_data={"slug": pr.slug, "id": pr.id}
        ) for pr in products_db
    ]

    # 5. Files
    files_db = db.query(ProjectFile).filter(
        (func.lower(ProjectFile.name).like(pattern)) |
        (func.lower(ProjectFile.category).like(pattern)) |
        (func.lower(ProjectFile.notes).like(pattern))
    ).limit(8).all()
    file_results = [
        SearchResultItem(
            id=f.id,
            title=f.name,
            subtitle=f"File ({f.category}) · {f.file_type}",
            category="file",
            url_tab="files",
            context_data={"id": f.id, "project_id": f.project_id}
        ) for f in files_db
    ]

    total = len(project_results) + len(client_results) + len(enquiry_results) + len(product_results) + len(file_results)

    return GlobalSearchOut(
        query=query_str,
        total_results=total,
        projects=project_results,
        clients=client_results,
        enquiries=enquiry_results,
        products=product_results,
        files=file_results
    )
