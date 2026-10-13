import os
import sys
import pytest
from datetime import datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import get_db, engine, SessionLocal
from app.database.migrations import run_migrations
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task, TaskAssignment, TaskComment
from app.core.security import hash_password, create_access_token


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    run_migrations(engine)
    db = SessionLocal()
    try:
        # Create test users
        users_to_create = [
            ("test_task_master", "master_task@test.com", UserRole.MASTER.value),
            ("test_task_designer1", "designer1_task@test.com", UserRole.DESIGNER.value),
            ("test_task_designer2", "designer2_task@test.com", UserRole.DESIGNER.value),
            ("test_task_viewer", "viewer_task@test.com", UserRole.VIEWER.value),
        ]
        for uname, uemail, urole in users_to_create:
            existing = db.query(User).filter(User.username == uname).first()
            if not existing:
                u = User(
                    username=uname,
                    email=uemail,
                    hashed_password=hash_password("Password123!"),
                    role=urole,
                    is_active=True
                )
                db.add(u)
        
        # Create a test project
        existing_proj = db.query(Project).filter(Project.slug == "test-task-villa").first()
        if not existing_proj:
            p = Project(
                title="Test Task Villa",
                slug="test-task-villa",
                category="Residential",
                location="Ahmedabad",
                is_published=True
            )
            db.add(p)
        db.commit()
    finally:
        db.close()


def get_auth_headers(username: str, role: str) -> dict:
    token = create_access_token(data={"sub": username, "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(app)


def test_list_assignees(client):
    headers = get_auth_headers("test_task_designer1", "DESIGNER")
    res = client.get("/api/admin/tasks/assignees", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    usernames = [u["username"] for u in data]
    assert "test_task_master" in usernames
    assert "test_task_designer1" in usernames


def test_create_workspace_task_without_project(client):
    headers = get_auth_headers("test_task_designer1", "DESIGNER")
    payload = {
        "title": "General Studio Sample Board Preparation",
        "description": "Prepare veneer and marble swatches for reception display",
        "visibility": "WORKSPACE",
        "priority": "MEDIUM",
        "status": "TODO",
        "project_id": None
    }
    res = client.post("/api/admin/tasks", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == payload["title"]
    assert data["visibility"] == "WORKSPACE"
    assert data["project_id"] is None
    assert data["project_title"] == "Studio Task"
    assert data["created_by_name"] == "test_task_designer1"


def test_create_workspace_task_with_project_and_multi_assign(client):
    db = SessionLocal()
    proj = db.query(Project).filter(Project.slug == "test-task-villa").first()
    u1 = db.query(User).filter(User.username == "test_task_designer1").first()
    u2 = db.query(User).filter(User.username == "test_task_designer2").first()
    db.close()

    headers = get_auth_headers("test_task_master", "MASTER")
    payload = {
        "title": "HVAC Ducting Layout Review",
        "description": "Review AC duct routing for First Floor Master Suite",
        "visibility": "WORKSPACE",
        "priority": "HIGH",
        "status": "IN_PROGRESS",
        "project_id": proj.id,
        "assignee_ids": [u1.id, u2.id],
        "due_date": (datetime.utcnow() + timedelta(days=3)).isoformat()
    }
    res = client.post("/api/admin/tasks", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == proj.id
    assert data["project_title"] == "Test Task Villa"
    assert len(data["assignees"]) == 2
    assignee_names = [a["username"] for a in data["assignees"]]
    assert "test_task_designer1" in assignee_names
    assert "test_task_designer2" in assignee_names


def test_private_task_visibility_and_isolation(client):
    db = SessionLocal()
    u1 = db.query(User).filter(User.username == "test_task_designer1").first()
    db.close()

    # Designer 1 creates a private task assigned only to them
    d1_headers = get_auth_headers("test_task_designer1", "DESIGNER")
    payload = {
        "title": "Confidential Performance Review Notes",
        "description": "Private appraisal deliverables",
        "visibility": "PRIVATE",
        "priority": "URGENT",
        "status": "TODO",
        "assignee_ids": [u1.id]
    }
    create_res = client.post("/api/admin/tasks", json=payload, headers=d1_headers)
    assert create_res.status_code == 200
    task_id = create_res.json()["id"]

    # 1. Designer 1 (Creator/Assignee) CAN see and get details of this private task
    res_d1 = client.get(f"/api/admin/tasks/{task_id}", headers=d1_headers)
    assert res_d1.status_code == 200
    assert res_d1.json()["id"] == task_id

    # 2. Master Administrator (Executive) CAN see and get details of this private task
    master_headers = get_auth_headers("test_task_master", "MASTER")
    res_master = client.get(f"/api/admin/tasks/{task_id}", headers=master_headers)
    assert res_master.status_code == 200
    assert res_master.json()["id"] == task_id

    # 3. Designer 2 (Unauthorized non-participant) CANNOT see details (403 Forbidden)
    d2_headers = get_auth_headers("test_task_designer2", "DESIGNER")
    res_d2 = client.get(f"/api/admin/tasks/{task_id}", headers=d2_headers)
    assert res_d2.status_code == 403

    # 4. Designer 2 list query DOES NOT include this private task
    list_d2 = client.get("/api/admin/tasks", headers=d2_headers)
    assert list_d2.status_code == 200
    d2_task_ids = [t["id"] for t in list_d2.json()]
    assert task_id not in d2_task_ids

    # 5. Designer 1 list query DOES include this private task
    list_d1 = client.get("/api/admin/tasks", headers=d1_headers)
    assert list_d1.status_code == 200
    d1_task_ids = [t["id"] for t in list_d1.json()]
    assert task_id in d1_task_ids


def test_task_status_workflow_and_completion(client):
    headers = get_auth_headers("test_task_designer1", "DESIGNER")
    
    # Create task
    payload = {
        "title": "Procure Hardware Samples",
        "visibility": "WORKSPACE",
        "status": "TODO"
    }
    c_res = client.post("/api/admin/tasks", json=payload, headers=headers)
    task_id = c_res.json()["id"]

    # 1. Update to IN_PROGRESS
    p1 = client.patch(f"/api/admin/tasks/{task_id}/status?status=IN_PROGRESS", headers=headers)
    assert p1.status_code == 200
    assert p1.json()["status"] == "IN_PROGRESS"

    # 2. Complete task
    p2 = client.patch(f"/api/admin/tasks/{task_id}/status?status=COMPLETED", headers=headers)
    assert p2.status_code == 200
    assert p2.json()["status"] == "COMPLETED"

    # 3. Reopen task
    p3 = client.patch(f"/api/admin/tasks/{task_id}/status?status=TODO", headers=headers)
    assert p3.status_code == 200
    assert p3.json()["status"] == "TODO"


def test_task_comments_discussion(client):
    headers = get_auth_headers("test_task_designer1", "DESIGNER")
    
    # Create task
    c_res = client.post("/api/admin/tasks", json={"title": "Lighting Mockup Test", "visibility": "WORKSPACE"}, headers=headers)
    task_id = c_res.json()["id"]

    # Add comments
    cm1 = client.post(f"/api/admin/tasks/{task_id}/comments", json={"content": "3000K warm fixtures received at site."}, headers=headers)
    assert cm1.status_code == 200
    assert cm1.json()["content"] == "3000K warm fixtures received at site."
    assert cm1.json()["author_name"] == "test_task_designer1"

    d2_headers = get_auth_headers("test_task_designer2", "DESIGNER")
    cm2 = client.post(f"/api/admin/tasks/{task_id}/comments", json={"content": "Approved, proceeding with false ceiling cove mounting."}, headers=d2_headers)
    assert cm2.status_code == 200
    assert cm2.json()["author_name"] == "test_task_designer2"

    # Fetch comments
    list_cm = client.get(f"/api/admin/tasks/{task_id}/comments", headers=headers)
    assert list_cm.status_code == 200
    comments = list_cm.json()
    assert len(comments) == 2


def test_task_deletion_permissions(client):
    d1_headers = get_auth_headers("test_task_designer1", "DESIGNER")
    d2_headers = get_auth_headers("test_task_designer2", "DESIGNER")
    master_headers = get_auth_headers("test_task_master", "MASTER")

    # D1 creates a task
    c_res = client.post("/api/admin/tasks", json={"title": "Delete Permission Test Task", "visibility": "WORKSPACE"}, headers=d1_headers)
    task_id = c_res.json()["id"]

    # D2 (not creator, not admin) CANNOT delete D1's task (403)
    del_d2 = client.delete(f"/api/admin/tasks/{task_id}", headers=d2_headers)
    assert del_d2.status_code == 403

    # D1 (Creator) CAN delete their task
    del_d1 = client.delete(f"/api/admin/tasks/{task_id}", headers=d1_headers)
    assert del_d1.status_code == 200
    assert del_d1.json()["success"] is True


def test_task_stats(client):
    headers = get_auth_headers("test_task_master", "MASTER")
    res = client.get("/api/admin/tasks/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert "total" in stats
    assert "my_tasks" in stats
    assert "in_progress" in stats
    assert "completed" in stats
    assert stats["total"] >= 1
