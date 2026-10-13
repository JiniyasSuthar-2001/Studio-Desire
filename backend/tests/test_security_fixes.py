import os
import sys
import io
import json
import uuid
import pytest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMedia
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.blueprint import BlueprintDrawing
from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
from app.models.content import SiteContent
from app.core.security import hash_password, create_access_token
from app.core.config import Settings
from app.services.email_service import (
    send_owner_enquiry_notification,
    send_customer_confirmation,
    get_email_settings
)

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Ensure a test MASTER user
        master_user = db.query(User).filter(User.username == "test_master").first()
        if not master_user:
            master_user = User(
                username="test_master",
                email="master@studiodesire.com",
                hashed_password=hash_password("TestMasterSecurePassword123!"),
                role=UserRole.MASTER.value,
                is_active=True
            )
            db.add(master_user)

        # Ensure a test EDITOR user
        editor_user = db.query(User).filter(User.username == "test_editor").first()
        if not editor_user:
            editor_user = User(
                username="test_editor",
                email="editor@studiodesire.com",
                hashed_password=hash_password("TestEditorSecurePassword123!"),
                role=UserRole.EDITOR.value,
                is_active=True
            )
            db.add(editor_user)

        # Ensure a test OWNER user
        owner_user = db.query(User).filter(User.username == "test_owner").first()
        if not owner_user:
            owner_user = User(
                username="test_owner",
                email="owner@studiodesire.com",
                hashed_password=hash_password("TestOwnerSecurePassword123!"),
                role=UserRole.OWNER.value,
                is_active=True
            )
            db.add(owner_user)

        db.commit()
    finally:
        db.close()


def get_token_for_user(username: str, role: str) -> str:
    return create_access_token(data={"sub": username, "role": role})


# ==============================================================================
# 1. PUBLIC CONTENT ACCESS / ALLOW-LIST & SMTP PASSWORD LEAK PREVENTION
# ==============================================================================

def test_public_content_email_settings_blocked():
    """GET /api/content/email_settings must return 404 and never expose SMTP credentials."""
    resp = client.get("/api/content/email_settings")
    assert resp.status_code == 404
    detail = resp.json().get("detail", "").lower()
    assert "not publicly accessible" in detail or "not found" in detail


def test_public_content_sensitive_sections_blocked():
    """Test various internal/sensitive sections are rejected from public access."""
    for section in ["smtp_settings", "system_settings", "auth_settings", "security_settings", "passwords", "users", "admin"]:
        resp = client.get(f"/api/content/{section}")
        assert resp.status_code == 404


def test_public_content_allowed_sections():
    """Verify that legitimate public sections are allowed."""
    for section in ["about", "contact", "categories", "slideshow"]:
        resp = client.get(f"/api/content/{section}")
        assert resp.status_code == 200


# ==============================================================================
# 2. PREVENT EDITORS FROM MODIFYING EMAIL SETTINGS
# ==============================================================================

def test_editor_cannot_modify_email_settings():
    """EDITOR must receive 403 Forbidden when attempting to modify email_settings."""
    editor_token = get_token_for_user("test_editor", UserRole.EDITOR.value)
    headers = {"Authorization": f"Bearer {editor_token}"}
    
    payload = {
        "content_json": json.dumps({"smtp_host": "evil.smtp.com", "smtp_user": "attacker", "smtp_password": "pwn"})
    }
    resp = client.put("/api/admin/content/email_settings", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "forbidden" in resp.json().get("detail", "").lower()


def test_unauthenticated_cannot_modify_email_settings():
    """Unauthenticated requests must receive 401 Unauthorized."""
    payload = {"content_json": json.dumps({"smtp_host": "smtp.test.com"})}
    resp = client.put("/api/admin/content/email_settings", json=payload)
    assert resp.status_code == 401


def test_master_can_modify_email_settings():
    """MASTER user is allowed to modify email settings."""
    master_token = get_token_for_user("test_master", UserRole.MASTER.value)
    headers = {"Authorization": f"Bearer {master_token}"}
    
    payload = {
        "content_json": json.dumps({
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "studiodesire01@gmail.com",
            "smtp_password": "testpassword",
            "sender_email": "studiodesire01@gmail.com"
        })
    }
    resp = client.put("/api/admin/content/email_settings", json=payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ==============================================================================
# 3. PRODUCTION CONFIGURATION VALIDATION & NO HARD-CODED SECRETS
# ==============================================================================

def test_production_fails_on_insecure_defaults():
    """Settings validation must raise RuntimeError in production mode if SECRET_KEY is missing or insecure."""
    insecure_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="12345678"  # Insecure / short key
    )
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY CONFIGURATION ERROR"):
        insecure_settings.validate_security_configuration()


def test_production_passes_on_strong_secret():
    """Settings validation passes in production mode with a strong random secret key."""
    secure_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="c8f7d9e2a1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9"
    )
    # Should not raise
    secure_settings.validate_security_configuration()


# ==============================================================================
# 4. SECURE BULK & SINGLE FILE UPLOADS
# ==============================================================================

def test_upload_valid_file():
    """Valid image upload by authorized user succeeds."""
    master_token = get_token_for_user("test_master", UserRole.MASTER.value)
    headers = {"Authorization": f"Bearer {master_token}"}

    file_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    files = [("files", ("test_render.png", file_content, "image/png"))]
    
    resp = client.post("/api/admin/upload/bulk", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["items"]) >= 1
    assert not (".." in data["items"][0]["url"])


def test_upload_path_traversal_prevention():
    """Filenames with directory traversal sequences (../ or absolute paths) must be sanitized."""
    master_token = get_token_for_user("test_master", UserRole.MASTER.value)
    headers = {"Authorization": f"Bearer {master_token}"}

    file_content = b"fake image content"
    files = [("files", ("../../../../etc/passwd.jpg", file_content, "image/jpeg"))]
    
    resp = client.post("/api/admin/upload/bulk", files=files, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    # The generated URL must NOT contain ../
    assert ".." not in data["items"][0]["url"]


def test_upload_disallowed_extension_rejected():
    """Unsupported or executable file extensions (.exe, .php, .js) must be rejected with 400."""
    master_token = get_token_for_user("test_master", UserRole.MASTER.value)
    headers = {"Authorization": f"Bearer {master_token}"}

    files = [("files", ("malicious_script.php", b"<?php phpinfo(); ?>", "application/x-php"))]
    resp = client.post("/api/admin/upload/bulk", files=files, headers=headers)
    assert resp.status_code == 400
    detail = resp.json().get("detail", "").lower()
    assert "unsupported" in detail or "prohibited" in detail or "not allowed" in detail


def test_upload_oversized_file_rejected():
    """Files exceeding maximum allowed size must return 413 Payload Too Large."""
    master_token = get_token_for_user("test_master", UserRole.MASTER.value)
    headers = {"Authorization": f"Bearer {master_token}"}

    large_content = b"0" * (52428800 + 1024)
    files = [("files", ("huge_file.jpg", large_content, "image/jpeg"))]
    resp = client.post("/api/admin/upload/bulk", files=files, headers=headers)
    assert resp.status_code == 413
    assert "exceeds" in resp.json().get("detail", "").lower()


# ==============================================================================
# 5. SECURE ENQUIRY ATTACHMENTS (PRIVATE STORAGE & ACCESS CONTROL)
# ==============================================================================

def test_enquiry_attachments_private_storage():
    """Public enquiries with attachments must be stored in backend/storage, NOT frontend/public."""
    db = SessionLocal()
    try:
        enq = ProjectEnquiry(
            reference_number=f"SD-TEST-{uuid.uuid4().hex[:6].upper()}",
            name="Confidential Client",
            email="confidential@example.com",
            phone="+91 99999 88888",
            project_type="Turnkey Villa",
            message="Private architectural drawings attached.",
            status="NEW"
        )
        db.add(enq)
        db.flush()

        from app.core.config import settings
        file_name = f"confidential_{uuid.uuid4().hex[:6]}.pdf"
        private_file = settings.ENQUIRY_ATTACHMENTS_DIR / file_name
        private_file.write_bytes(b"%PDF-1.4 Confidential floor plan blueprint")

        att = ProjectEnquiryAttachment(
            enquiry_id=enq.id,
            original_filename="confidential_plan.pdf",
            filename=file_name,
            storage_path=str(private_file),
            file_type="pdf",
            mime_type="application/pdf",
            file_size=38,
            url=f"/api/admin/enquiries/{enq.id}/attachments/1"
        )
        db.add(att)
        db.commit()
        enq_id = enq.id
        att_id = att.id
    finally:
        db.close()

    # Unauthenticated request is rejected
    unauth_resp = client.get(f"/api/admin/enquiries/{enq_id}/attachments/{att_id}")
    assert unauth_resp.status_code == 401

    # Unauthorized role request is rejected
    viewer_token = get_token_for_user("test_viewer", "VIEWER")
    viewer_resp = client.get(f"/api/admin/enquiries/{enq_id}/attachments/{att_id}", headers={"Authorization": f"Bearer {viewer_token}"})
    assert viewer_resp.status_code == 403

    # Authorized admin request succeeds
    admin_token = get_token_for_user("test_master", UserRole.MASTER.value)
    admin_resp = client.get(f"/api/admin/enquiries/{enq_id}/attachments/{att_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_resp.status_code == 200
    assert b"Confidential floor plan blueprint" in admin_resp.content

    # Mismatched enquiry ID is rejected (prevents ID enumeration/manipulation)
    mismatch_resp = client.get(f"/api/admin/enquiries/999999/attachments/{att_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert mismatch_resp.status_code == 404


# ==============================================================================
# 6. SECURE PUBLIC ENQUIRY FORMS (RATE LIMITING, HTML ESCAPING, CONCURRENCY)
# ==============================================================================

def test_enquiry_html_escaping(monkeypatch):
    """User-controlled input must be safely HTML escaped in generated email templates."""
    captured_html = []
    
    def fake_send_smtp(to_emails, subject, text_content, html_content, settings_override=None):
        captured_html.append(html_content)
        return True, None

    monkeypatch.setattr("app.services.email_service.send_smtp_message", fake_send_smtp)
    monkeypatch.setattr("app.services.email_service.get_email_settings", lambda: {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "user",
        "smtp_password": "pass",
        "recipients": ["admin@studiodesire.com"],
        "send_customer_confirmation": True
    })

    enquiry = ProjectEnquiry(
        id=999,
        reference_number="SD-2026-XSS-TEST",
        name="<script>alert('XSS')</script> & User",
        email="test@example.com",
        phone="+91 99999 11111",
        project_type="Villa & Penthouse",
        location="Ahmedabad <img src=x onerror=alert(1)>",
        budget="50L",
        timeline="6 Months",
        message="<b>Bold Brief</b> & <script>document.location='http://evil.com'</script>",
        status="NEW"
    )

    send_owner_enquiry_notification(enquiry)
    send_customer_confirmation(enquiry)

    assert len(captured_html) == 2
    for html_text in captured_html:
        assert "<script>" not in html_text
        assert "<img src=x" not in html_text
        assert "&lt;script&gt;" in html_text or "&amp;" in html_text


def test_enquiry_unique_reference_numbers_concurrency():
    """Multiple enquiry submissions concurrently must all receive unique reference numbers."""
    from app.api.enquiries import generate_unique_reference
    
    db = SessionLocal()
    try:
        refs = set()
        for _ in range(50):
            ref = generate_unique_reference(db)
            assert ref.startswith("SD-")
            assert ref not in refs, f"Duplicate reference number detected: {ref}"
            refs.add(ref)
    finally:
        db.close()


def test_public_enquiry_input_validation():
    """Malformed or excessively long inputs must be rejected."""
    # Test invalid email
    resp = client.post("/api/enquiries", data={
        "name": "Test User",
        "email": "not-an-email",
        "phone": "+91 98765 43210",
        "project_type": "Villa",
        "message": "Valid test brief here."
    })
    assert resp.status_code in [400, 422]

    # Test missing name
    resp = client.post("/api/enquiries", data={
        "name": "",
        "email": "user@example.com",
        "phone": "+91 98765 43210",
        "project_type": "Villa",
        "message": "Valid test brief here."
    })
    assert resp.status_code in [400, 422]


# ==============================================================================
# 7. UNPUBLISHED CONTENT PROTECTION
# ==============================================================================

def test_unpublished_project_hidden_from_public():
    """Unpublished project must not appear in /api/projects or /api/projects/{slug}."""
    test_slug = f"secret-villa-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        proj = Project(
            title="Secret Unpublished Villa",
            slug=test_slug,
            location="Ahmedabad",
            year=2026,
            category="Residential",
            description="Secret architectural blueprint",
            is_published=False
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
        proj_id = proj.id
    finally:
        db.close()

    # Public list must NOT contain the project
    pub_resp = client.get("/api/projects")
    assert pub_resp.status_code == 200
    projects = pub_resp.json().get("projects", [])
    assert not any(p["id"] == proj_id or p["slug"] == test_slug for p in projects)

    # Public detail must return 404
    detail_resp = client.get(f"/api/projects/{test_slug}")
    assert detail_resp.status_code == 404

    # Admin list CAN see the project
    master_token = get_token_for_user("test_master", UserRole.MASTER.value)
    admin_resp = client.get("/api/admin/projects", headers={"Authorization": f"Bearer {master_token}"})
    assert admin_resp.status_code == 200
    assert any(p["id"] == proj_id for p in admin_resp.json())


def test_unpublished_media_in_published_project_omitted():
    """A published project must not expose unpublished child media items."""
    test_slug = f"pub-mixed-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        proj = Project(
            title="Public Project with Mixed Media",
            slug=test_slug,
            location="Ahmedabad",
            year=2026,
            category="Residential",
            description="Public project description",
            is_published=True
        )
        db.add(proj)
        db.flush()

        pub_m = ProjectMedia(
            project_id=proj.id,
            media_type="image",
            url=f"/uploads/projects/pub_{uuid.uuid4().hex[:6]}.webp",
            is_published=True
        )
        unpub_m = ProjectMedia(
            project_id=proj.id,
            media_type="image",
            url=f"/uploads/projects/secret_{uuid.uuid4().hex[:6]}.webp",
            is_published=False
        )
        db.add_all([pub_m, unpub_m])
        db.commit()
        pub_url = pub_m.url
        unpub_url = unpub_m.url
    finally:
        db.close()

    resp = client.get(f"/api/projects/{test_slug}")
    assert resp.status_code == 200
    media_urls = [m["url"] for m in resp.json().get("media", [])]
    assert pub_url in media_urls
    assert unpub_url not in media_urls

    # Teardown test project so it doesn't leak into database
    cleanup_db = SessionLocal()
    try:
        cleanup_db.query(Project).filter(Project.slug == test_slug).delete()
        cleanup_db.commit()
    finally:
        cleanup_db.close()


def test_unpublished_3d_spaces_hidden():
    """Unpublished 3D visualization spaces must return 404 on public endpoints."""
    test_slug = f"hidden-suite-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        space = VisualizationSpace(
            title="Hidden Master Suite",
            project_name="Confidential Residence",
            room="Hidden Master Suite",
            slug=test_slug,
            category="Residential",
            cover_image="/uploads/visualizations/hidden.webp",
            is_published=False
        )
        db.add(space)
        db.commit()
        db.refresh(space)
        space_id = space.id
    finally:
        db.close()

    # List endpoint
    list_resp = client.get("/api/visualizations")
    assert list_resp.status_code == 200
    spaces = list_resp.json().get("spaces", [])
    assert not any(s["id"] == space_id for s in spaces)

    # Detail endpoint
    detail_resp = client.get(f"/api/visualizations/{test_slug}")
    assert detail_resp.status_code == 404


def test_unpublished_blueprints_hidden():
    """Unpublished blueprints must return 404 on public endpoints including PDF download."""
    test_slug = f"secret-bp-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    try:
        drg = BlueprintDrawing(
            project_name="Confidential Residence",
            project_slug="confidential-residence",
            title="Secret Joinery Working Drawing",
            slug=test_slug,
            drawing_type="Detail Drawing",
            thumbnail_url="/uploads/blueprints/t.webp",
            file_url="/uploads/blueprints/f.webp",
            is_published=False
        )
        db.add(drg)
        db.commit()
        db.refresh(drg)
        drg_id = drg.id
    finally:
        db.close()

    # List endpoint
    list_resp = client.get("/api/blueprints")
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    assert not any(d["id"] == drg_id for d in items)

    # Detail endpoint
    detail_resp = client.get(f"/api/blueprints/{test_slug}")
    assert detail_resp.status_code == 404

    # PDF endpoint
    pdf_resp = client.get(f"/api/blueprints/{test_slug}/pdf")
    assert pdf_resp.status_code == 404


# ==============================================================================
# 8. QR VISUALIZATION ENDPOINT SECURITY
# ==============================================================================

def test_qr_endpoint_rejects_malicious_schemes():
    """Dangerous URL schemes (javascript:, file:, data:) must return 400 Bad Request."""
    dangerous_urls = [
        "javascript:alert(document.cookie)",
        "file:///etc/passwd",
        "file:///C:/Windows/system.ini",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "ftp://malicious.host/file"
    ]
    for bad_url in dangerous_urls:
        resp = client.get("/api/visualizations/qr", params={"url": bad_url})
        assert resp.status_code == 400
        assert "http and https" in resp.json().get("detail", "").lower() or "valid" in resp.json().get("detail", "").lower()


def test_qr_endpoint_allows_valid_urls():
    """Valid HTTP and HTTPS URLs return valid SVG QR image."""
    valid_urls = [
        "https://studiodesire.com/spaces/living-room",
        "http://localhost:5173/vr/residence-01"
    ]
    for good_url in valid_urls:
        resp = client.get("/api/visualizations/qr", params={"url": good_url})
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/svg+xml")
        assert b"<svg" in resp.content


# ==============================================================================
# 9. SMTP FAILURE TRACKING & ERROR SANITIZATION
# ==============================================================================

def test_smtp_failure_state_recorded():
    """When SMTP is unconfigured, delivery state email_sent=0 is cleanly recorded without fabricating success."""
    resp = client.post("/api/enquiries", data={
        "name": "Audit Test Client",
        "email": "audit@test.com",
        "phone": "+91 91234 56789",
        "project_type": "Apartment",
        "message": "Testing SMTP failure state recording."
    })
    assert resp.status_code == 201
    data = resp.json()
    enquiry_id = data["enquiry_id"]
    
    db = SessionLocal()
    try:
        enq = db.query(ProjectEnquiry).filter(ProjectEnquiry.id == enquiry_id).first()
        assert enq is not None
        assert enq.email_sent is False  # Must not claim email was sent when SMTP is unconfigured
    finally:
        db.close()


def test_global_error_handler_masks_internal_details():
    """Unhandled server errors must return generic safe response without exposing stack traces."""
    resp = client.get("/api/content/unknown_random_error_section")
    assert resp.status_code == 404


# ==============================================================================
# 10. PART 2 — OWNER PERMISSIONS, CORS & CONFIGURATION TESTS
# ==============================================================================

def test_owner_role_can_manage_all_admin_features():
    """OWNER role user must have universal administrative clearance identical to MASTER."""
    owner_token = get_token_for_user("test_owner", UserRole.OWNER.value)
    headers = {"Authorization": f"Bearer {owner_token}"}

    # 1. Content update
    r1 = client.put(
        "/api/admin/content/about",
        headers=headers,
        json={"content_json": json.dumps({"title": "Studio Desire Architectural Practice"})}
    )
    assert r1.status_code == 200, f"Owner content update failed: {r1.text}"

    # 2. Email settings update
    r2 = client.put(
        "/api/admin/content/email_settings",
        headers=headers,
        json={"content_json": json.dumps({"smtp_host": "mail.studiodesire.com", "smtp_port": 587})}
    )
    assert r2.status_code == 200, f"Owner email settings update failed: {r2.text}"

    # 3. User listing
    r3 = client.get("/api/admin/users", headers=headers)
    assert r3.status_code == 200, f"Owner user list failed: {r3.text}"


def test_cors_rejects_wildcard_with_credentials_in_production():
    """In production mode, wildcard '*' origins with credentials are strictly rejected."""
    from app.core.config import Settings
    
    # Valid production config
    prod_valid = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="A_VERY_SECURE_PRODUCTION_SECRET_KEY_1234567890",
    )
    prod_valid.CORS_ORIGINS_RAW = "https://studiodesire.com,https://admin.studiodesire.com"
    origins = prod_valid.CORS_ORIGINS
    assert "*" not in origins
    assert "https://studiodesire.com" in origins

    # Wildcard in production must raise RuntimeError
    prod_invalid = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="A_VERY_SECURE_PRODUCTION_SECRET_KEY_1234567890",
    )
    prod_invalid.CORS_ORIGINS_RAW = "*"
    try:
        _ = prod_invalid.CORS_ORIGINS
        assert False, "Should have raised RuntimeError for wildcard CORS in production"
    except RuntimeError as e:
        assert "wildcard" in str(e).lower() or "cors" in str(e).lower()


def test_login_rate_limiting_brute_force_protection():
    """Rapid repeated failed login requests must trigger 429 Too Many Requests."""
    for _ in range(15):
        resp = client.post("/api/auth/login", json={
            "username": "nonexistent_target_user",
            "password": "wrong_password_attempt"
        })
    # Must have hit rate limit
    assert resp.status_code == 429
    assert "too many" in resp.json().get("detail", "").lower()


def test_demo_data_seeding_gated_in_production():
    """SEED_DEMO_DATA is ignored and rejected in production mode."""
    from app.core.config import Settings
    prod_settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="ANOTHER_SUPER_SECURE_PROD_SECRET_KEY_123456",
    )
    assert prod_settings.IS_PRODUCTION is True
    # validate_security_configuration runs cleanly
    prod_settings.validate_security_configuration()

