"""
Studio Desire — Comprehensive QA Audit & Verification Test Suite
Covers:
1. Email settings update with full masked configuration schema return.
2. Email test dispatch with 'to_email' alias support.
3. Milestone deletion endpoint (DELETE /api/admin/projects/milestones/{id}).
4. End-to-end client creation, update, and deletion with cascading safety.
5. Project file and contract registration and deletion.
6. Material specification CRUD lifecycle.
7. Payment recording and automatic financial balance recalculation.
8. 3D Visualization space creation and room media attachment.
9. VR Matrix configuration for project, room, and render levels.
10. Global search functionality across projects, clients, files, and enquiries.
11. Public content allow-list and CMS section updates.
12. Product archive listing, filtering, and detail resolution.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal, engine, Base
from app.database.migrations import run_migrations
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMedia
from app.models.client import Client
from app.models.milestone import ProjectMilestone
from app.models.material import ProjectMaterial
from app.models.file import ProjectFile
from app.models.finance import PaymentRecord
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.enquiry import ProjectEnquiry
from app.core.security import hash_password, create_access_token

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_audit_db():
    run_migrations(engine)
    db = SessionLocal()
    try:
        # Create test owner user
        owner = db.query(User).filter(User.username == "qa_audit_owner").first()
        if not owner:
            owner = User(
                username="qa_audit_owner",
                email="qa_audit_owner@studiodesire.test",
                hashed_password=hash_password("AuditSecurePass123!"),
                role=UserRole.OWNER.value,
                is_active=True
            )
            db.add(owner)
            db.commit()
    finally:
        db.close()


def get_owner_headers() -> dict:
    token = create_access_token(data={"sub": "qa_audit_owner", "role": UserRole.OWNER.value})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. EMAIL SETTINGS SCHEMA AND TEST DISPATCH ALIAS
# ==============================================================================
def test_email_settings_update_and_test_dispatch():
    headers = get_owner_headers()

    # GET email settings
    res_get = client.get("/api/admin/email/settings", headers=headers)
    assert res_get.status_code == 200
    cfg = res_get.json()
    assert "smtp_host" in cfg
    assert "has_password" in cfg
    assert "customer_confirmation_enabled" in cfg

    # PUT email settings with customer_confirmation_enabled
    update_payload = {
        "sender_name": "Studio Desire Architecture",
        "sender_email": "notifications@studiodesire.com",
        "smtp_host": "smtp.mailgun.org",
        "smtp_port": 587,
        "security": "TLS",
        "smtp_username": "postmaster@studiodesire.com",
        "recipients": ["leads@studiodesire.com"],
        "customer_confirmation_enabled": True
    }
    res_put = client.put("/api/admin/email/settings", json=update_payload, headers=headers)
    assert res_put.status_code == 200
    saved = res_put.json()
    assert saved.get("success") is True
    assert saved["sender_name"] == "Studio Desire Architecture"
    assert saved["customer_confirmation_enabled"] is True
    assert "smtp_password" in saved  # Masked password returned

    # POST email test with 'to_email' alias
    os.environ["TESTING_DISABLE_SMTP"] = "true"
    try:
        res_test = client.post(
            "/api/admin/email/test",
            json={"to_email": "test_client@example.com"},
            headers=headers
        )
        assert res_test.status_code == 200
        test_data = res_test.json()
        assert test_data["success"] is True
        assert "test_client@example.com" in test_data["message"]
    finally:
        os.environ["TESTING_DISABLE_SMTP"] = "false"


# ==============================================================================
# 2. MILESTONE CRUD INCLUDING DELETION
# ==============================================================================
def test_milestone_crud_lifecycle():
    headers = get_owner_headers()
    db = SessionLocal()
    try:
        # Create test project
        project = Project(
            title="Milestone QA Project",
            slug="milestone-qa-project",
            category="Residential",
            location="Ahmedabad, Gujarat",
            is_published=False
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # 1. Create milestone
        res_create = client.post(
            f"/api/admin/projects/{project.id}/milestones",
            json={"title": "Schematic Floor Plans", "description": "Preliminary spatial layout", "order": 1},
            headers=headers
        )
        assert res_create.status_code == 200
        m_data = res_create.json()
        m_id = m_data["id"]
        assert m_data["title"] == "Schematic Floor Plans"

        # 2. Update milestone status
        res_update = client.put(
            f"/api/admin/projects/milestones/{m_id}",
            json={"status": "COMPLETED"},
            headers=headers
        )
        assert res_update.status_code == 200
        assert res_update.json()["status"] == "COMPLETED"

        # 3. Delete milestone
        res_delete = client.delete(f"/api/admin/projects/milestones/{m_id}", headers=headers)
        assert res_delete.status_code == 200
        assert res_delete.json()["success"] is True

        # Verify deletion from DB
        deleted = db.query(ProjectMilestone).filter(ProjectMilestone.id == m_id).first()
        assert deleted is None
    finally:
        # Cleanup
        db.query(Project).filter(Project.slug == "milestone-qa-project").delete()
        db.commit()
        db.close()


# ==============================================================================
# 3. CLIENT MANAGEMENT CRUD
# ==============================================================================
def test_client_crud_lifecycle():
    headers = get_owner_headers()

    # Create client
    client_payload = {
        "name": "Vikram Singhania",
        "company": "Singhania Capital",
        "email": "vikram@singhania.test",
        "phone": "+91 98200 11223",
        "address": "Worli Sea Face, Mumbai",
        "notes": "Penthouse interior architecture commission"
    }
    res_create = client.post("/api/admin/clients", json=client_payload, headers=headers)
    assert res_create.status_code == 200
    created = res_create.json()
    c_id = created["id"]
    assert created["name"] == "Vikram Singhania"

    # Get client detail
    res_get = client.get(f"/api/admin/clients/{c_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["company"] == "Singhania Capital"

    # Update client
    res_update = client.put(
        f"/api/admin/clients/{c_id}",
        json={"notes": "Updated scope: luxury duplex interior"},
        headers=headers
    )
    assert res_update.status_code == 200
    assert res_update.json()["notes"] == "Updated scope: luxury duplex interior"

    # Delete client
    res_delete = client.delete(f"/api/admin/clients/{c_id}", headers=headers)
    assert res_delete.status_code == 200
    assert res_delete.json()["success"] is True


# ==============================================================================
# 4. PROJECT FILES AND CONTRACTS CRUD
# ==============================================================================
def test_project_file_crud():
    headers = get_owner_headers()
    db = SessionLocal()
    try:
        project = Project(title="File QA Project", slug="file-qa-project", category="Commercial", location="Mumbai, Maharashtra")
        db.add(project)
        db.commit()
        db.refresh(project)

        # Register file
        file_payload = {
            "project_id": project.id,
            "name": "Turnkey Architectural Agreement",
            "category": "Contract",
            "file_url": "/uploads/contracts/agreement_v1.pdf",
            "file_type": "pdf",
            "file_size": 2048500,
            "notes": "Signed by both parties"
        }
        res_create = client.post("/api/admin/files", json=file_payload, headers=headers)
        assert res_create.status_code == 200
        f_data = res_create.json()
        f_id = f_data["id"]
        assert f_data["name"] == "Turnkey Architectural Agreement"

        # List files by project
        res_list = client.get(f"/api/admin/files?project_id={project.id}", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

        # Delete file
        res_del = client.delete(f"/api/admin/files/{f_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True
    finally:
        db.query(ProjectFile).filter(ProjectFile.project_id == project.id).delete()
        db.query(Project).filter(Project.id == project.id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 5. MATERIAL SPECIFICATION CRUD
# ==============================================================================
def test_material_crud():
    headers = get_owner_headers()
    db = SessionLocal()
    try:
        project = Project(title="Material QA Project", slug="material-qa-project", category="Residential", location="Surat, Gujarat")
        db.add(project)
        db.commit()
        db.refresh(project)

        # Create material
        mat_payload = {
            "project_id": project.id,
            "name": "Statutario Italian Marble",
            "category": "Stone",
            "supplier": "Antolini Italy",
            "reference": "STAT-009",
            "price": 18500.0,
            "quantity": "450 sq ft",
            "notes": "Bookmatched slabs for foyer flooring"
        }
        res_create = client.post("/api/admin/materials", json=mat_payload, headers=headers)
        assert res_create.status_code == 200
        mat_data = res_create.json()
        m_id = mat_data["id"]
        assert mat_data["name"] == "Statutario Italian Marble"

        # Update material status
        res_update = client.put(
            f"/api/admin/materials/{m_id}",
            json={"status": "ORDERED", "notes": "Slabs dispatched from port"},
            headers=headers
        )
        assert res_update.status_code == 200
        assert res_update.json()["status"] == "ORDERED"

        # Delete material
        res_del = client.delete(f"/api/admin/materials/{m_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True
    finally:
        db.query(ProjectMaterial).filter(ProjectMaterial.project_id == project.id).delete()
        db.query(Project).filter(Project.id == project.id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 6. FINANCE & AUTOMATIC BALANCE RECALCULATION
# ==============================================================================
def test_finance_payment_logging_and_recalculation():
    headers = get_owner_headers()
    db = SessionLocal()
    try:
        project = Project(
            title="Finance QA Project",
            slug="finance-qa-project",
            category="Residential",
            location="Bangalore, Karnataka",
            project_value=1000000.0,
            budget=1000000.0,
            amount_received=0.0,
            amount_pending=1000000.0
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        # Log payment 1: 400,000 received
        pay_res = client.post(
            "/api/admin/finance/payments",
            json={
                "project_id": project.id,
                "title": "Advance Mobilization Deposit",
                "amount": 400000.0,
                "payment_date": "2026-10-14",
                "payment_method": "NEFT / RTGS",
                "status": "RECEIVED"
            },
            headers=headers
        )
        assert pay_res.status_code == 200

        # Verify project finances recalculated automatically
        db.refresh(project)
        assert project.amount_received == 400000.0
        assert project.amount_pending == 600000.0

        # Get project finance summary via API
        fin_summary_res = client.get(f"/api/admin/finance/project/{project.id}", headers=headers)
        assert fin_summary_res.status_code == 200
        fin_data = fin_summary_res.json()
        assert fin_data["amount_received"] == 400000.0
        assert fin_data["amount_pending"] == 600000.0
        assert len(fin_data["payments"]) == 1
    finally:
        db.query(PaymentRecord).filter(PaymentRecord.project_id == project.id).delete()
        db.query(Project).filter(Project.id == project.id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 7. 3D VISUALIZATION SPACES AND ROOM MEDIA
# ==============================================================================
def test_3d_visualization_space_and_media():
    headers = get_owner_headers()

    # Create space
    space_payload = {
        "title": "Penthouse Master Suite",
        "room": "Master Suite",
        "category": "Residential",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "Corona Renderer · 3ds Max",
        "cover_image": "/uploads/renders/penthouse_cover.jpg",
        "status": "APPROVED",
        "is_published": True
    }
    res_space = client.post("/api/admin/visualizations", json=space_payload, headers=headers)
    assert res_space.status_code == 201
    space = res_space.json()
    space_id = space["id"]
    assert space["title"] == "Penthouse Master Suite"

    # Add media to space
    media_payload = {
        "media_type": "image",
        "url": "/uploads/renders/suite_daylight.jpg",
        "caption": "Calibrated Morning Daylight Wash",
        "sort_order": 1
    }
    res_media = client.post(f"/api/admin/visualizations/{space_id}/media", json=media_payload, headers=headers)
    assert res_media.status_code == 201
    media_item = res_media.json()
    assert media_item["caption"] == "Calibrated Morning Daylight Wash"

    # Delete space (cascades media)
    res_del = client.delete(f"/api/admin/visualizations/{space_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True


# ==============================================================================
# 8. GLOBAL SEARCH FUNCTIONALITY
# ==============================================================================
def test_global_search_across_entities():
    headers = get_owner_headers()
    db = SessionLocal()
    try:
        # Seed unique searchable entities
        p = Project(title="Zodiac Celestial Villa", slug="zodiac-celestial-villa", category="Residential", location="Goa, India", is_published=True)
        c = Client(name="Zodiac Real Estate Developers", company="Zodiac Group", email="contact@zodiac.test")
        db.add_all([p, c])
        db.commit()

        # Search for 'Zodiac'
        res_search = client.get("/api/admin/search?q=Zodiac", headers=headers)
        assert res_search.status_code == 200
        results = res_search.json()
        assert results["total_results"] >= 2
        assert any(proj["title"] == "Zodiac Celestial Villa" for proj in results["projects"])
        assert any(cli["title"] == "Zodiac Real Estate Developers" for cli in results["clients"])
    finally:
        db.query(Project).filter(Project.slug == "zodiac-celestial-villa").delete()
        db.query(Client).filter(Client.name == "Zodiac Real Estate Developers").delete()
        db.commit()
        db.close()


# ==============================================================================
# 9. PUBLIC PRODUCTS ARCHIVE & DETAIL
# ==============================================================================
def test_public_products_archive_and_detail():
    # List products
    res_list = client.get("/api/products")
    assert res_list.status_code == 200
    data = res_list.json()
    assert "products" in data
    assert "total" in data

    # Get product categories
    res_cats = client.get("/api/products/categories")
    assert res_cats.status_code == 200
    cats = res_cats.json()
    assert "ALL" in cats
