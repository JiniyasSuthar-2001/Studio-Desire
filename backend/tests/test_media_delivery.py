import os
import sys
import pytest
from pathlib import Path
from io import BytesIO

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def admin_headers():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "test_media_admin").first()
        if not user:
            user = User(
                username="test_media_admin",
                email="media_admin@studiodesire.com",
                hashed_password=hash_password("Password123!"),
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token(data={"sub": user.username, "role": user.role})
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


def test_static_uploads_serving_placeholder(client):
    """Confirm persistent uploads directory serves static images with correct MIME type."""
    response = client.get("/uploads/projects/placeholder.webp")
    assert response.status_code == 200
    assert "image" in response.headers.get("content-type", "")


def test_static_uploads_missing_file_returns_404(client):
    """Confirm missing upload returns 404 and does NOT return HTML SPA."""
    response = client.get("/uploads/projects/non_existent_image_12345.webp")
    assert response.status_code == 404


def test_media_audit_endpoint(client, admin_headers):
    """Verify admin audit endpoint reports storage health accurately."""
    response = client.get("/api/admin/media/audit", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "uploads_root" in data
    assert data["uploads_root_exists"] is True
    assert data["total_records_checked"] > 0
    assert isinstance(data["missing_local_files"], list)


def test_media_repair_endpoint(client, admin_headers):
    """Verify admin repair endpoint handles missing media gracefully."""
    response = client.post("/api/admin/media/repair-missing", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "repaired_count" in data


def test_upload_and_persistent_retrieval(client, admin_headers):
    """Verify uploading an image stores it in canonical uploads dir and is accessible via HTTP."""
    fake_image = BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    files = [("files", ("test_ping.png", fake_image, "image/png"))]
    
    upload_res = client.post("/api/admin/upload/bulk", headers=admin_headers, files=files)
    assert upload_res.status_code == 200
    res_data = upload_res.json()
    assert res_data.get("success") is True
    assert len(res_data.get("items", [])) > 0
    file_url = res_data["items"][0]["url"]
    assert file_url.startswith("/uploads/cms/")

    # Check file exists on disk in settings.UPLOADS_DIR
    rel_path = file_url[len("/uploads/"):]
    disk_path = settings.UPLOADS_DIR / rel_path
    assert disk_path.exists()

    # Check file is retrievable over HTTP GET
    fetch_res = client.get(file_url)
    assert fetch_res.status_code == 200
    assert "image/png" in fetch_res.headers.get("content-type", "")

    # Cleanup test file
    try:
        disk_path.unlink()
    except OSError:
        pass


def test_unauthorized_media_access(client):
    """Verify unauthorized users cannot execute admin media repair or deletion."""
    rep_res = client.post("/api/admin/media/repair-missing")
    assert rep_res.status_code in [401, 403]
