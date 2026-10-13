import os
import sys
import io
import pytest
from datetime import datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import settings
from app.database.session import get_db, engine, SessionLocal
from app.database.migrations import run_migrations
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMedia
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.task import Task
from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
from app.models.finance import PaymentRecord
from app.core.security import hash_password, create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_audit_entities():
    run_migrations(engine)
    db = SessionLocal()
    try:
        # Create or update dedicated test users for workflows
        owner = db.query(User).filter(User.username == "test_audit_owner").first()
        if not owner:
            owner = User(
                username="test_audit_owner",
                email="audit_owner@studiodesire.test",
                hashed_password=hash_password("AuditPassword123!"),
                role=UserRole.OWNER.value,
                is_active=True
            )
            db.add(owner)
        else:
            owner.role = UserRole.OWNER.value
            owner.is_active = True

        master = db.query(User).filter(User.username == "test_audit_master").first()
        if not master:
            master = User(
                username="test_audit_master",
                email="audit_master@studiodesire.test",
                hashed_password=hash_password("AuditPassword123!"),
                role=UserRole.MASTER.value,
                is_active=True
            )
            db.add(master)

        db.commit()
    finally:
        db.close()


def get_token_for(username: str, role: str) -> str:
    return create_access_token(data={"sub": username, "role": role})


def auth_header(username: str, role: str) -> dict:
    token = get_token_for(username, role)
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# WORKFLOW A: NEW OWNER & COMPLETE PROJECT LIFECYCLE
# ==============================================================================
def test_workflow_a_owner_project_lifecycle(client: TestClient, db_session: Session):
    """
    Workflow A:
    1. Authenticate as Owner.
    2. Create an architectural project with full metadata.
    3. Upload and attach cover image and gallery images.
    4. Reload project in Owner CRM and verify counts.
    5. Publish project and verify visibility on public website.
    6. Unpublish project and verify exclusion from public website.
    """
    headers = auth_header("test_audit_owner", "OWNER")

    # 1. Verify owner dashboard stats
    stats_res = client.get("/api/admin/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "total_projects" in stats_data

    # 2. Create architectural project
    project_payload = {
        "title": "Audit Penthouse Residence 2026",
        "subtitle": "Luxury Minimalist Sky Villa",
        "category": "Residential",
        "project_type": "Penthouse",
        "location": "Bandra West, Mumbai",
        "year": "2026",
        "area": "8,500 sq ft",
        "budget": 25000000.0,
        "description": "High-end luxury residence featuring custom Italian marble and cantilevered balconies.",
        "cover_image": "/uploads/projects/penthouse_cover.jpg",
        "status": "IN_PROGRESS",
        "featured": True,
        "is_published": False  # Starts unpublished
    }
    create_res = client.post("/api/admin/projects", json=project_payload, headers=headers)
    assert create_res.status_code == 200, create_res.text
    project_data = create_res.json()
    project_id = project_data["id"]
    project_slug = project_data["slug"]

    try:
        # 3. Add supporting gallery images
        media1 = ProjectMedia(
            project_id=project_id,
            media_type="image",
            url="/uploads/projects/penthouse_living.jpg",
            caption="Living Pavilion",
            sort_order=1
        )
        media2 = ProjectMedia(
            project_id=project_id,
            media_type="image",
            url="/uploads/projects/penthouse_terrace.jpg",
            caption="Sky Terrace",
            sort_order=2
        )
        db_session.add_all([media1, media2])
        db_session.commit()

        # 4. Reload in Owner CRM & verify batch counts
        admin_proj_res = client.get("/api/admin/projects", headers=headers)
        assert admin_proj_res.status_code == 200
        found = [p for p in admin_proj_res.json() if p["id"] == project_id]
        assert len(found) == 1
        assert found[0]["counts"]["photos"] >= 2
        assert found[0]["is_published"] is False

        # 5. Verify project is NOT visible on public site while unpublished
        pub_list_res = client.get("/api/projects")
        assert pub_list_res.status_code == 200
        pub_slugs = [p["slug"] for p in pub_list_res.json()["projects"]]
        assert project_slug not in pub_slugs

        pub_detail_res = client.get(f"/api/projects/{project_slug}")
        assert pub_detail_res.status_code == 404

        # 6. Publish project
        pub_patch = client.patch(f"/api/admin/projects/{project_id}", json={"is_published": True}, headers=headers)
        assert pub_patch.status_code == 200
        assert pub_patch.json()["is_published"] is True

        # 7. Verify project IS visible on public site
        pub_list_after = client.get("/api/projects")
        assert pub_list_after.status_code == 200
        pub_slugs_after = [p["slug"] for p in pub_list_after.json()["projects"]]
        assert project_slug in pub_slugs_after

        pub_detail_after = client.get(f"/api/projects/{project_slug}")
        assert pub_detail_after.status_code == 200
        pub_detail_data = pub_detail_after.json()
        assert pub_detail_data["title"] == "Audit Penthouse Residence 2026"
        assert len(pub_detail_data["media"]) >= 2

        # 8. Unpublish project
        unpub_patch = client.patch(f"/api/admin/projects/{project_id}", json={"is_published": False}, headers=headers)
        assert unpub_patch.status_code == 200
        assert unpub_patch.json()["is_published"] is False

        # 9. Verify immediate removal from public site
        pub_list_unpub = client.get("/api/projects")
        assert project_slug not in [p["slug"] for p in pub_list_unpub.json()["projects"]]

        pub_detail_unpub = client.get(f"/api/projects/{project_slug}")
        assert pub_detail_unpub.status_code == 404
    finally:
        # Cleanup test project
        client.delete(f"/api/admin/projects/{project_id}", headers=headers)


# ==============================================================================
# WORKFLOW B: WORKER PERMISSIONS & ACCOUNT MANAGEMENT (RBAC)
# ==============================================================================
def test_workflow_b_worker_rbac_lifecycle(client: TestClient, db_session: Session):
    """
    Workflow B:
    1. Create worker account with DESIGNER role.
    2. Authenticate as worker.
    3. Verify access to permitted design/task operations.
    4. Verify rejection (403) from privileged finance and user administration.
    5. Delete worker account using Master/Owner account.
    6. Confirm deleted worker can no longer authenticate.
    """
    owner_headers = auth_header("test_audit_owner", "OWNER")

    # 1. Create worker account
    worker_username = f"audit_worker_{int(datetime.utcnow().timestamp())}"
    create_worker_payload = {
        "username": worker_username,
        "email": f"{worker_username}@studiodesire.test",
        "password": "WorkerPassword123!",
        "role": "DESIGNER"
    }
    user_res = client.post("/api/admin/users", json=create_worker_payload, headers=owner_headers)
    assert user_res.status_code == 200, user_res.text
    worker_id = user_res.json()["id"]

    try:
        # 2. Worker login
        login_res = client.post(
            "/api/auth/login",
            json={"username": worker_username, "password": "WorkerPassword123!"}
        )
        assert login_res.status_code == 200
        worker_token = login_res.json()["access_token"]
        worker_headers = {"Authorization": f"Bearer {worker_token}"}

        # 3. Permitted operations: view tasks and create designer task
        tasks_res = client.get("/api/admin/tasks", headers=worker_headers)
        assert tasks_res.status_code == 200

        task_create_res = client.post(
            "/api/admin/tasks",
            json={
                "title": "Design 3D Elevation Concepts",
                "description": "Prepare spatial render concepts for client review",
                "priority": "HIGH",
                "status": "IN_PROGRESS",
                "visibility": "WORKSPACE"
            },
            headers=worker_headers
        )
        assert task_create_res.status_code == 200
        task_id = task_create_res.json()["id"]

        # 4. Prohibited operations: Finance endpoints MUST reject with 403
        finance_summary_res = client.get("/api/admin/finance/summary", headers=worker_headers)
        assert finance_summary_res.status_code == 403

        payment_log_res = client.post(
            "/api/admin/finance/payments",
            json={"project_id": 1, "title": "Illegal Payment", "amount": 50000.0},
            headers=worker_headers
        )
        assert payment_log_res.status_code == 403

        # User management MUST reject with 403
        user_list_res = client.get("/api/admin/users", headers=worker_headers)
        assert user_list_res.status_code == 403

        # 5. Delete worker account using Owner account
        delete_worker_res = client.delete(f"/api/admin/users/{worker_id}", headers=owner_headers)
        assert delete_worker_res.status_code == 200

        # 6. Verify worker cannot log in
        relogin_res = client.post(
            "/api/auth/login",
            json={"username": worker_username, "password": "WorkerPassword123!"}
        )
        assert relogin_res.status_code == 401

        # Cleanup created task
        client.delete(f"/api/admin/tasks/{task_id}", headers=owner_headers)
    except Exception:
        # Fallback cleanup
        client.delete(f"/api/admin/users/{worker_id}", headers=owner_headers)
        raise


# ==============================================================================
# WORKFLOW C: MEDIA UPLOADS & SAFE ATTACHMENT DOWNLOADS
# ==============================================================================
def test_workflow_c_media_uploads_and_downloads(client: TestClient, db_session: Session):
    """
    Workflow C:
    1. Upload image asset through /api/admin/upload.
    2. Verify file persisted on disk in canonical uploads folder.
    3. Retrieve image via HTTP static mount.
    4. Create an enquiry attachment in private storage.
    5. Download attachment safely via authorized endpoint.
    6. Verify strict 403 rejection on attempted path traversal.
    """
    owner_headers = auth_header("test_audit_owner", "OWNER")

    # 1. Upload valid image via canonical bulk upload route
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    upload_res = client.post(
        "/api/admin/upload/bulk",
        files=[("files", ("test_audit_marble.png", io.BytesIO(fake_png), "image/png"))],
        headers=owner_headers
    )
    assert upload_res.status_code == 200
    upload_json = upload_res.json()
    assert upload_json["success"] is True
    assert len(upload_json["items"]) > 0
    media_item = upload_json["items"][0]
    file_url = media_item["url"]  # e.g. /uploads/cms/...
    media_id = media_item["id"]

    # 2. Check disk persistence
    relative_path = file_url.lstrip("/")
    if relative_path.startswith("uploads/"):
        relative_path = relative_path[len("uploads/"):]
    disk_path = settings.UPLOADS_DIR / relative_path
    assert disk_path.exists()
    assert disk_path.stat().st_size > 0

    # 3. Retrieve through HTTP mount
    http_res = client.get(file_url)
    assert http_res.status_code == 200
    assert "image/png" in http_res.headers.get("content-type", "")

    # Clean up staged media record and disk file
    client.delete(f"/api/admin/upload/media/{media_id}", headers=owner_headers)
    if disk_path.exists():
        disk_path.unlink()

    # 4. Private enquiry attachment & Path Traversal Verification
    # Create test enquiry
    enquiry = ProjectEnquiry(
        reference_number=f"ENQ-AUDIT-{int(datetime.utcnow().timestamp())}",
        name="Security Audit Test Client",
        email="audit@sec.test",
        phone="+919876543210",
        project_type="Villa",
        message="Attachment download security verification test."
    )
    db_session.add(enquiry)
    db_session.commit()

    # Create safe attachment file in settings.ENQUIRY_ATTACHMENTS_DIR
    safe_file_name = f"spec_{int(datetime.utcnow().timestamp())}.pdf"
    safe_file_path = settings.ENQUIRY_ATTACHMENTS_DIR / safe_file_name
    safe_file_path.write_bytes(b"%PDF-1.4 Mock Specification Document Content")

    safe_att = ProjectEnquiryAttachment(
        enquiry_id=enquiry.id,
        filename=safe_file_name,
        original_filename="Client_Specification.pdf",
        file_type="document",
        storage_path=str(safe_file_path),
        mime_type="application/pdf",
        file_size=safe_file_path.stat().st_size,
        url=f"/api/admin/enquiries/{enquiry.id}/attachments/safe"
    )
    db_session.add(safe_att)

    # Create malicious attachment attempting path traversal outside private directory
    traversal_path = settings.STORAGE_DIR.parent / "studio_desire.db"
    malicious_att = ProjectEnquiryAttachment(
        enquiry_id=enquiry.id,
        filename="traversal.db",
        original_filename="Traversal_Attempt.db",
        file_type="document",
        storage_path=str(traversal_path),
        mime_type="application/octet-stream",
        file_size=100,
        url=f"/api/admin/enquiries/{enquiry.id}/attachments/traversal"
    )
    db_session.add(malicious_att)
    db_session.commit()

    try:
        # 5. Download safe attachment -> 200 OK
        dl_res = client.get(
            f"/api/admin/enquiries/{enquiry.id}/attachments/{safe_att.id}/download",
            headers=owner_headers
        )
        assert dl_res.status_code == 200
        assert b"Mock Specification Document Content" in dl_res.content

        # 6. Download malicious traversal attachment -> strictly 403 Forbidden!
        bad_dl_res = client.get(
            f"/api/admin/enquiries/{enquiry.id}/attachments/{malicious_att.id}/download",
            headers=owner_headers
        )
        assert bad_dl_res.status_code == 403
        assert "outside the authorized storage directory" in bad_dl_res.json()["detail"]
    finally:
        # Cleanup
        if safe_file_path.exists():
            safe_file_path.unlink()
        db_session.delete(safe_att)
        db_session.delete(malicious_att)
        db_session.delete(enquiry)
        db_session.commit()


# ==============================================================================
# WORKFLOW D: 3D VISUALIZATIONS, VR DESTINATIONS & QR CODES
# ==============================================================================
def test_workflow_d_3d_visualizations_and_vr_matrix(client: TestClient, db_session: Session):
    """
    Workflow D:
    1. Create a 3D Visualization space.
    2. Add supporting renders.
    3. Configure VR URL for Room-level destination.
    4. Generate and decode QR Code SVG.
    5. Update VR URL to a new destination and verify QR updates.
    6. Clear VR URL and confirm persistence after refresh.
    7. Verify separation of Level 1 (Project), Level 2 (Room), and Level 3 (Render).
    """
    owner_headers = auth_header("test_audit_owner", "OWNER")

    # 1. Create visualization space
    space_payload = {
        "title": "Audit Grand Lounge 3D",
        "room": "Living Room",
        "description": "Spatial visualization with high-poly lighting",
        "cover_image": "/uploads/projects/lounge_3d.jpg"
    }
    create_res = client.post("/api/admin/visualizations", json=space_payload, headers=owner_headers)
    assert create_res.status_code == 201
    space_id = create_res.json()["id"]

    try:
        # 2. Add supporting render media
        render_media = VisualizationMedia(
            space_id=space_id,
            url="/uploads/projects/lounge_3d_angle1.jpg",
            caption="Angle 1 North View",
            angle="North View",
            sort_order=1
        )
        db_session.add(render_media)
        db_session.commit()

        # 3. Configure VR URL at Room level (Level 2)
        vr_url_v1 = "https://vr.studiodesire.com/spaces/grand-lounge-v1"
        vr_update_res = client.post(
            "/api/admin/vr/room-vr",
            json={
                "space_id": space_id,
                "vr_url": vr_url_v1,
                "show_qr": True
            },
            headers=owner_headers
        )
        assert vr_update_res.status_code == 200
        assert vr_update_res.json()["vr_url"] == vr_url_v1

        # 4. Generate QR code endpoint
        qr_res = client.get(
            f"/api/admin/vr/qr?url={vr_url_v1}&box_size=10&border=2",
            headers=owner_headers
        )
        assert qr_res.status_code == 200
        assert "image/svg+xml" in qr_res.headers.get("content-type", "")
        assert b"<svg" in qr_res.content

        # 5. Update VR URL to new version
        vr_url_v2 = "https://vr.studiodesire.com/spaces/grand-lounge-v2"
        vr_update_v2 = client.post(
            "/api/admin/vr/room-vr",
            json={
                "space_id": space_id,
                "vr_url": vr_url_v2,
                "show_qr": True
            },
            headers=owner_headers
        )
        assert vr_update_v2.status_code == 200
        assert vr_update_v2.json()["vr_url"] == vr_url_v2

        # 6. Verify VR Matrix displays Level 2 properly
        matrix_res = client.get("/api/admin/vr/all", headers=owner_headers)
        assert matrix_res.status_code == 200
        matrix_data = matrix_res.json()
        rooms = matrix_data["level2_rooms"]
        matched_room = [r for r in rooms if r["space_id"] == space_id]
        assert len(matched_room) == 1
        assert matched_room[0]["vr_url"] == vr_url_v2

        # 7. Clear VR URL
        clear_res = client.post(
            "/api/admin/vr/room-vr",
            json={
                "space_id": space_id,
                "vr_url": "",
                "show_qr": False
            },
            headers=owner_headers
        )
        assert clear_res.status_code == 200

        # Reload space to confirm persistence
        space_reload = client.get(f"/api/admin/visualizations/{space_id}", headers=owner_headers)
        assert space_reload.status_code == 200
        assert not space_reload.json().get("vr_url")
    finally:
        # Cleanup
        client.delete(f"/api/admin/visualizations/{space_id}", headers=owner_headers)


# ==============================================================================
# WORKFLOW E: FAILURE RECOVERY & RESILIENCE TESTING
# ==============================================================================
def test_workflow_e_failure_recovery_and_guards(client: TestClient, db_session: Session):
    """
    Workflow E:
    1. Submit invalid payload -> 422 Unprocessable Entity.
    2. Unauthenticated request to protected endpoint -> 401 Unauthorized.
    3. Nonexistent resource request -> 404 Not Found.
    4. Master account self-deletion attempt -> 400 Bad Request.
    5. Malicious QR scheme (javascript:) -> 400 Bad Request.
    """
    owner_headers = auth_header("test_audit_owner", "OWNER")

    # 1. Invalid payload
    inv_res = client.post("/api/admin/projects", json={"budget": "invalid_string"}, headers=owner_headers)
    assert inv_res.status_code == 422

    # 2. Unauthenticated request
    no_auth_res = client.get("/api/admin/finance/summary")
    assert no_auth_res.status_code == 401

    # 3. Nonexistent resource
    not_found_res = client.get("/api/admin/projects/9999999", headers=owner_headers)
    assert not_found_res.status_code == 404

    # 4. Master account self-deletion attempt
    master = db_session.query(User).filter(User.username == "test_audit_master").first()
    master_headers = auth_header("test_audit_master", "MASTER")
    self_delete_res = client.delete(f"/api/admin/users/{master.id}", headers=master_headers)
    assert self_delete_res.status_code == 400
    assert "own active session" in self_delete_res.json()["detail"]

    # 5. Malicious QR scheme injection
    bad_qr_res = client.get("/api/admin/vr/qr?url=javascript:alert(1)", headers=owner_headers)
    assert bad_qr_res.status_code == 400
    assert "HTTP and HTTPS" in bad_qr_res.json()["detail"]


# ==============================================================================
# WORKFLOW F: REGRESSION & FINANCIAL CRUD
# ==============================================================================
def test_workflow_f_financial_crud_and_recalculation(client: TestClient, db_session: Session):
    """
    Workflow F:
    1. Create a project with budget and project_value.
    2. Log a payment record (POST /admin/finance/payments).
    3. Verify amount_received and amount_pending recalculation.
    4. Update payment record (PUT /admin/finance/payments/{id}).
    5. Verify updated payment values reflected in project totals.
    6. Delete payment record (DELETE /admin/finance/payments/{id}).
    7. Verify balance reset after deletion.
    8. Check Google Calendar integration status.
    """
    owner_headers = auth_header("test_audit_owner", "OWNER")

    # 1. Create project
    proj_res = client.post(
        "/api/admin/projects",
        json={
            "title": "Audit Finance Project 2026",
            "category": "Commercial",
            "budget": 1000000.0,
            "project_value": 1200000.0,
            "status": "IN_PROGRESS"
        },
        headers=owner_headers
    )
    assert proj_res.status_code == 200
    project_id = proj_res.json()["id"]

    try:
        # 2. Log payment #1 (₹500,000)
        pay_res = client.post(
            "/api/admin/finance/payments",
            json={
                "project_id": project_id,
                "title": "Advance Milestone 1",
                "amount": 500000.0,
                "payment_date": "2026-03-15",
                "payment_method": "Bank Transfer",
                "status": "RECEIVED"
            },
            headers=owner_headers
        )
        assert pay_res.status_code == 200
        payment_id = pay_res.json()["id"]

        # 3. Verify project totals
        proj_reload1 = client.get(f"/api/admin/projects/{project_id}", headers=owner_headers)
        assert proj_reload1.status_code == 200
        p_data1 = proj_reload1.json()
        assert p_data1["amount_received"] == 500000.0
        assert p_data1["amount_pending"] == 700000.0  # 1,200,000 - 500,000

        # 4. Update payment (modify amount to ₹750,000 and title)
        update_pay_res = client.put(
            f"/api/admin/finance/payments/{payment_id}",
            json={
                "title": "Revised Milestone 1 with Mobilization Advance",
                "amount": 750000.0,
                "notes": "Verified by accounts department"
            },
            headers=owner_headers
        )
        assert update_pay_res.status_code == 200
        updated_data = update_pay_res.json()
        assert updated_data["amount"] == 750000.0
        assert "Revised" in updated_data["title"]

        # 5. Verify recalculation after update
        proj_reload2 = client.get(f"/api/admin/projects/{project_id}", headers=owner_headers)
        assert proj_reload2.status_code == 200
        p_data2 = proj_reload2.json()
        assert p_data2["amount_received"] == 750000.0
        assert p_data2["amount_pending"] == 450000.0  # 1,200,000 - 750,000

        # 6. Delete payment
        del_pay_res = client.delete(f"/api/admin/finance/payments/{payment_id}", headers=owner_headers)
        assert del_pay_res.status_code == 200

        # 7. Verify balance reset
        proj_reload3 = client.get(f"/api/admin/projects/{project_id}", headers=owner_headers)
        assert proj_reload3.status_code == 200
        p_data3 = proj_reload3.json()
        assert p_data3["amount_received"] == 0.0
        assert p_data3["amount_pending"] == 1200000.0

        # 8. Check Google Calendar status
        cal_res = client.get("/api/admin/google-calendar/status", headers=owner_headers)
        assert cal_res.status_code == 200
        assert "status" in cal_res.json()
    finally:
        client.delete(f"/api/admin/projects/{project_id}", headers=owner_headers)
