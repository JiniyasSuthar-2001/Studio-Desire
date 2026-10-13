import os
import sys
from pathlib import Path
import pytest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.session import Base, get_db
from app.models.user import User, UserRole
from app.models.category import PortfolioCategory, PortfolioSubcategory
from app.models.project import Project
from app.core.security import hash_password, create_access_token

# Test database setup (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed test master user
        master_user = User(
            id=1,
            username="masterowner",
            email="owner@studiodesire.com",
            hashed_password=hash_password("ownerpassword123"),
            role=UserRole.MASTER.value,
            is_active=True
        )
        db.add(master_user)

        # Seed core portfolio categories
        res_cat = PortfolioCategory(
            id=1,
            name="Residential",
            slug="residential",
            description="Luxury residential architecture",
            display_order=1,
            is_active=True,
            is_default=True,
            puzzle_size="large"
        )
        hosp_cat = PortfolioCategory(
            id=2,
            name="Hospitality",
            slug="hospitality",
            description="Boutique hospitality and dining venues",
            display_order=2,
            is_active=True,
            is_default=True,
            puzzle_size="tall"
        )
        db.add_all([res_cat, hosp_cat])
        db.flush()

        # Seed subcategories
        sub1 = PortfolioSubcategory(id=1, category_id=1, name="Apartment", slug="apartment", display_order=1, is_active=True)
        sub2 = PortfolioSubcategory(id=2, category_id=1, name="Villa", slug="villa", display_order=2, is_active=True)
        sub3 = PortfolioSubcategory(id=3, category_id=2, name="Restaurant", slug="restaurant", display_order=1, is_active=True)
        db.add_all([sub1, sub2, sub3])

        # Seed sample project
        proj = Project(
            id=1,
            title="Hardik Bhai Project",
            slug="hardik-bhai-project",
            category="Residential",
            category_id=1,
            subcategory_id=1,
            project_type="Apartment",
            location="Ahmedabad, Gujarat",
            year=2026,
            description="Luxury 4BHK architectural residence",
            is_published=True
        )
        db.add(proj)
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def master_token(db_session):
    return create_access_token(data={"sub": "masterowner", "role": "MASTER"})


def test_get_public_categories(client):
    """Verify public categories endpoint returns active categories and their subcategories."""
    res = client.get("/api/categories")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    cat_names = [c["name"] for c in data]
    assert "Residential" in cat_names
    assert "Hospitality" in cat_names


def test_get_admin_categories_with_counts(client, master_token):
    """Verify admin categories returns live project counts."""
    headers = {"Authorization": f"Bearer {master_token}"}
    res = client.get("/api/admin/categories", headers=headers)
    assert res.status_code == 200
    data = res.json()
    res_cat = next((c for c in data if c["name"] == "Residential"), None)
    assert res_cat is not None
    assert res_cat["total_projects_count"] == 1
    assert res_cat["published_projects_count"] == 1
    assert len(res_cat["subcategories"]) == 2


def test_create_category_and_assign_project(client, master_token):
    """Verify owner can create a category, then create a project assigned to it."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # 1. Create Category
    cat_payload = {
        "name": "Commercial Headquarters",
        "description": "Corporate architecture and offices",
        "puzzle_size": "wide",
        "subcategories": ["Experience Center", "Flagship HQ"]
    }
    create_cat_res = client.post("/api/admin/categories", json=cat_payload, headers=headers)
    assert create_cat_res.status_code == 200
    new_cat = create_cat_res.json()
    assert new_cat["name"] == "Commercial Headquarters"
    assert new_cat["slug"] == "commercial-headquarters"
    assert len(new_cat["subcategories"]) == 2

    # 2. Create Project under this new category
    proj_payload = {
        "title": "Alpha Corporate Hub",
        "category_id": new_cat["id"],
        "subcategory_id": new_cat["subcategories"][0]["id"],
        "location": "Ahmedabad",
        "year": 2026,
        "is_published": True
    }
    create_proj_res = client.post("/api/admin/projects", json=proj_payload, headers=headers)
    assert create_proj_res.status_code == 200
    proj_data = create_proj_res.json()
    assert proj_data["category"] == "Commercial Headquarters"
    assert proj_data["category_id"] == new_cat["id"]


def test_deactivated_category_cannot_receive_new_projects(client, master_token):
    """Verify inactive category rejects new project creation."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # Deactivate Hospitality (id=2)
    update_res = client.put("/api/admin/categories/2", json={"is_active": False}, headers=headers)
    assert update_res.status_code == 200

    # Try creating project with category_id=2
    proj_payload = {
        "title": "Invalid Cafe",
        "category_id": 2,
        "location": "Ahmedabad",
        "year": 2026
    }
    proj_res = client.post("/api/admin/projects", json=proj_payload, headers=headers)
    assert proj_res.status_code == 400
    assert "inactive" in proj_res.json()["detail"].lower()


def test_delete_category_reassignment_protection(client, master_token):
    """Verify category with assigned projects cannot be deleted without reassignment."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # 1. Create custom category
    cat_payload = {"name": "Penthouse Living"}
    create_res = client.post("/api/admin/categories", json=cat_payload, headers=headers)
    custom_cat_id = create_res.json()["id"]

    # 2. Assign project to it
    proj_payload = {
        "title": "Sky Penthouse 01",
        "category_id": custom_cat_id,
        "location": "Ahmedabad"
    }
    proj_res = client.post("/api/admin/projects", json=proj_payload, headers=headers)
    created_proj_id = proj_res.json()["id"]

    # 3. Attempt deleting category without reassignment -> Should Fail (400)
    del_fail = client.delete(f"/api/admin/categories/{custom_cat_id}", headers=headers)
    assert del_fail.status_code == 400
    assert "contains 1 assigned project" in del_fail.json()["detail"].lower()

    # 4. Delete with explicit reassignment to Residential (id=1) -> Should Succeed
    del_success = client.delete(f"/api/admin/categories/{custom_cat_id}?reassign_to_id=1", headers=headers)
    assert del_success.status_code == 200

    # 5. Verify the project is now safely reassigned to Residential
    workspace_res = client.get(f"/api/admin/projects/{created_proj_id}/workspace", headers=headers)
    assert workspace_res.status_code == 200
    assert workspace_res.json()["project"]["category_id"] == 1
    assert workspace_res.json()["project"]["category"] == "Residential"


def test_reorder_categories(client, master_token):
    """Verify reordering categories updates display_order persistently."""
    headers = {"Authorization": f"Bearer {master_token}"}
    reorder_payload = {
        "items": [
            {"id": 2, "display_order": 1},
            {"id": 1, "display_order": 2}
        ]
    }
    res = client.patch("/api/admin/categories/reorder", json=reorder_payload, headers=headers)
    assert res.status_code == 200

    # Check public order
    pub_res = client.get("/api/categories")
    data = pub_res.json()
    assert data[0]["id"] == 2
    assert data[1]["id"] == 1


def test_representative_project_assignment_and_validation(client, master_token):
    """Test assigning a valid published project as category homepage representative."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # 1. Create a published project in Residential (id=1)
    proj_payload = {
        "title": "Bespoke Villa Alpha",
        "category_id": 1,
        "location": "Ahmedabad",
        "is_published": True
    }
    proj_res = client.post("/api/admin/projects", json=proj_payload, headers=headers)
    assert proj_res.status_code == 200
    proj_id = proj_res.json()["id"]

    # 2. Assign project as representative of Residential
    assign_res = client.put(
        f"/api/admin/categories/1/featured-project",
        json={"project_id": proj_id},
        headers=headers
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["featured_project_id"] == proj_id
    assert assign_res.json()["featured_project"]["title"] == "Bespoke Villa Alpha"

    # 3. Check public categories endpoint exposes the representative project
    pub_res = client.get("/api/categories")
    assert pub_res.status_code == 200
    res_cat = next(c for c in pub_res.json() if c["id"] == 1)
    assert res_cat["featured_project_id"] == proj_id
    assert res_cat["featured_project"]["title"] == "Bespoke Villa Alpha"

    # 4. Clear representative assignment
    clear_res = client.put(
        f"/api/admin/categories/1/featured-project",
        json={"project_id": None},
        headers=headers
    )
    assert clear_res.status_code == 200
    assert clear_res.json()["featured_project_id"] is None
    assert clear_res.json()["featured_project"] is None


def test_representative_project_unrelated_category_rejected(client, master_token):
    """A project cannot be assigned as the representative of an unrelated category."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # Create published project in Hospitality (id=2)
    hosp_proj = {
        "title": "Grand Luxury Hotel",
        "category_id": 2,
        "location": "Goa",
        "is_published": True
    }
    h_res = client.post("/api/admin/projects", json=hosp_proj, headers=headers)
    hosp_proj_id = h_res.json()["id"]

    # Try assigning Hospitality project to Residential (id=1) -> Must Fail (400)
    fail_res = client.put(
        f"/api/admin/categories/1/featured-project",
        json={"project_id": hosp_proj_id},
        headers=headers
    )
    assert fail_res.status_code == 400
    assert "does not belong to category" in fail_res.json()["detail"].lower()


def test_representative_project_draft_rejected(client, master_token):
    """An unpublished (draft) project cannot be assigned as category representative."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # Create unpublished project in Residential (id=1)
    draft_proj = {
        "title": "Secret Draft Residence",
        "category_id": 1,
        "location": "Surat",
        "is_published": False
    }
    d_res = client.post("/api/admin/projects", json=draft_proj, headers=headers)
    draft_proj_id = d_res.json()["id"]

    # Try assigning draft project -> Must Fail (400)
    fail_res = client.put(
        f"/api/admin/categories/1/featured-project",
        json={"project_id": draft_proj_id},
        headers=headers
    )
    assert fail_res.status_code == 400
    assert "unpublished" in fail_res.json()["detail"].lower()


def test_list_eligible_projects_for_category(client, master_token):
    """Verify listing eligible projects for category representative assignment."""
    headers = {"Authorization": f"Bearer {master_token}"}

    # Create two projects in Hospitality (id=2)
    client.post("/api/admin/projects", json={"title": "Boutique Cafe", "category_id": 2, "is_published": True}, headers=headers)
    client.post("/api/admin/projects", json={"title": "Draft Restaurant", "category_id": 2, "is_published": False}, headers=headers)

    res = client.get("/api/admin/categories/2/eligible-projects", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2
    titles = [p["title"] for p in items]
    assert "Boutique Cafe" in titles
    assert "Draft Restaurant" in titles

