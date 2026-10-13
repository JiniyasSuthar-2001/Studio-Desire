"""
End-to-End Test Suite for Studio Desire Owner Management System
Validates the complete backend, database, models, auth, workspace, publishing, and dashboard.
"""
import sys
import os
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal, engine, Base
from app.database.migrations import run_migrations
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMedia
from app.models.client import Client
from app.models.enquiry import ProjectEnquiry
from app.models.task import Task
from app.models.milestone import ProjectMilestone
from app.models.material import ProjectMaterial
from app.models.meeting import Meeting
from app.models.file import ProjectFile
from app.models.finance import PaymentRecord
from app.models.activity import ActivityLog
from app.core.security import create_access_token, hash_password

client = TestClient(app)

def run_e2e_tests():
    print("==================================================================")
    print("STUDIO DESIRE -- END-TO-END VERIFICATION & AUDIT SUITE")
    print("==================================================================")

    # 1. Migrations & Schema
    print("\n[STEP 1] Testing Database Migrations & Schema Creation...")
    run_migrations(engine)
    db = SessionLocal()
    try:
        master_user = db.query(User).filter(User.role.in_([UserRole.MASTER.value, UserRole.OWNER.value])).first()
        if not master_user:
            master_user = User(
                username="Studio Desire",
                email=f"studiodesire_{uuid.uuid4().hex[:4]}@gmail.com",
                hashed_password=hash_password("SecureMasterPassword123!"),
                role=UserRole.MASTER.value,
                is_active=True
            )
            db.add(master_user)
            db.commit()
            db.refresh(master_user)
        user_count = db.query(User).count()
        print(f"[OK] Database active. Found {user_count} existing users.")
        master_username = master_user.username
        master_role = master_user.role
    finally:
        db.close()

    # 2. Authentication & Login
    print("\n[STEP 2] Testing Owner Authentication & Role-Based Access...")
    token = create_access_token(data={"sub": master_username, "role": master_role})
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Owner JWT authenticated. Token acquired.")

    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    user_info = me_resp.json()
    print(f"[OK] /api/auth/me resolved user: {user_info['username']}, Role: {user_info['role']}")

    # 3. Client Management
    print("\n[STEP 3] Testing Client Management CRUD...")
    client_payload = {
        "name": f"Rajesh Mehta {uuid.uuid4().hex[:4]}",
        "company": "Mehta Jewels",
        "email": f"rajesh_{uuid.uuid4().hex[:4]}@mehtajewels.com",
        "phone": "+91 98250 11223",
        "address": "Bungalow 14, Bodakdev, Ahmedabad",
        "notes": "Interested in turnkey villa interior design with contemporary brass accents."
    }
    create_client_resp = client.post("/api/admin/clients", json=client_payload, headers=headers)
    assert create_client_resp.status_code == 200, f"Create client failed: {create_client_resp.text}"
    created_client = create_client_resp.json()
    client_id = created_client["id"]
    print(f"[OK] Client created: ID={client_id}, Name='{created_client['name']}'")

    clients_list_resp = client.get("/api/admin/clients", headers=headers)
    assert clients_list_resp.status_code == 200
    assert any(c["id"] == client_id for c in clients_list_resp.json())
    print("[OK] Client verified in directory list.")

    # 4. Public Enquiry & Conversion
    print("\n[STEP 4] Testing Public Enquiry Reception & Lead Conversion Pipeline...")
    enquiry_payload = {
        "name": "Aarav Shah",
        "email": "aarav.shah@example.com",
        "phone": "+91 98790 55443",
        "project_type": "Penthouse",
        "budget": "INR 50L - 1Cr",
        "message": "Looking for complete luxury penthouse redesign in Sindhu Bhavan Road.",
        "timeline": "6 Months"
    }
    public_enquiry_resp = client.post("/api/enquiries", data=enquiry_payload)
    assert public_enquiry_resp.status_code == 201
    enquiry_data = public_enquiry_resp.json()
    enquiry_id = enquiry_data["enquiry_id"]
    print(f"[OK] Public enquiry received & persisted: ID={enquiry_id}")

    # Convert enquiry to client
    conv_client_resp = client.post(
        f"/api/admin/enquiries/{enquiry_id}/convert-to-client",
        json={"name": "Aarav Shah", "company": "Shah Enterprises", "notes": "Converted from website lead"},
        headers=headers
    )
    assert conv_client_resp.status_code == 200
    aarav_client = conv_client_resp.json()
    aarav_client_id = aarav_client["client_id"]
    print(f"[OK] Lead successfully converted to Client: ID={aarav_client_id}")

    # Convert enquiry to project
    shah_slug = f"shah-sky-penthouse-{uuid.uuid4().hex[:6]}"
    conv_proj_resp = client.post(
        f"/api/admin/enquiries/{enquiry_id}/convert-to-project",
        json={
            "title": "Shah Sky Penthouse",
            "slug": shah_slug,
            "project_type": "PENTHOUSE",
            "category": "RESIDENTIAL",
            "budget": 7500000.0,
            "project_value": 8500000.0
        },
        headers=headers
    )
    assert conv_proj_resp.status_code == 200
    project_from_enquiry = conv_proj_resp.json()
    shah_project_id = project_from_enquiry["project_id"]
    print(f"[OK] Lead successfully converted to Project Workspace: ID={shah_project_id}, Title='{project_from_enquiry['project_title']}'")

    # 5. Project Workspace Lifecycle
    print("\n[STEP 5] Testing Project Workspace, Milestones, Tasks, Materials, Meetings, Files & Finance...")
    
    # Add Milestone
    ms_resp = client.post(
        f"/api/admin/projects/{shah_project_id}/milestones",
        json={"title": "Concept Design & Moodboards", "description": "Initial 3D palettes & layout proposals", "order": 1, "status": "IN_PROGRESS"},
        headers=headers
    )
    assert ms_resp.status_code == 200
    print("[OK] Milestone added to project.")

    # Add Task
    task_resp = client.post(
        f"/api/admin/tasks",
        json={
            "project_id": shah_project_id,
            "title": "Finalize Italian Marble sample approval",
            "description": "Visit showroom with client for living room slab selection",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "assigned_to": "Principal Designer"
        },
        headers=headers
    )
    assert task_resp.status_code == 200
    task_id = task_resp.json()["id"]
    print(f"[OK] Task created: ID={task_id}")

    # Add Material Specification
    mat_resp = client.post(
        f"/api/admin/materials",
        json={
            "project_id": shah_project_id,
            "name": "Statuario White Marble",
            "category": "FLOORING",
            "supplier": "Classic Marble Co.",
            "reference": "ST-092",
            "price": 650.0,
            "quantity": "2500 sq.ft",
            "status": "PROPOSED"
        },
        headers=headers
    )
    assert mat_resp.status_code == 200
    print("[OK] Material specification registered.")

    # Add Meeting
    meet_resp = client.post(
        f"/api/admin/meetings",
        json={
            "project_id": shah_project_id,
            "client_id": aarav_client_id,
            "title": "On-Site Spatial Review & 3D Walkthrough",
            "date": "2026-10-05",
            "time": "15:00",
            "location": "Shah Sky Penthouse Site",
            "meeting_type": "SITE_VISIT",
            "participants": "Owner, Aarav Shah, Structural Engineer",
            "status": "SCHEDULED"
        },
        headers=headers
    )
    assert meet_resp.status_code == 200
    print("[OK] Project meeting scheduled.")

    # Add Project File / Document
    file_resp = client.post(
        f"/api/admin/files",
        json={
            "project_id": shah_project_id,
            "name": "Approved Architectural Scope of Work.pdf",
            "category": "CONTRACTS",
            "file_url": "/uploads/contracts/shah_penthouse_scope.pdf",
            "file_type": "PDF",
            "file_size": 2450000,
            "uploaded_by": "Studio Desire Admin"
        },
        headers=headers
    )
    assert file_resp.status_code == 200
    print("[OK] Project document archived.")

    # Add Payment / Finance Record
    pay_resp = client.post(
        f"/api/admin/finance/payments",
        json={
            "project_id": shah_project_id,
            "title": "Initial Design Retainer & Advance",
            "amount": 2500000.0,
            "payment_date": "2026-09-24",
            "payment_method": "BANK_TRANSFER",
            "reference_number": "NEFT-HDFC-9928172",
            "status": "CONFIRMED"
        },
        headers=headers
    )
    assert pay_resp.status_code == 200
    print("[OK] Financial payment recorded.")

    # Fetch Complete Workspace Dossier
    workspace_resp = client.get(f"/api/admin/projects/{shah_project_id}/workspace", headers=headers)
    assert workspace_resp.status_code == 200
    ws_data = workspace_resp.json()
    assert "counts" in ws_data
    print(f"[OK] Workspace Dossier fully verified! (Progress: {ws_data.get('progress_percentage')}%)")

    # 6. Website Publishing & Public/Private Boundary
    print("\n[STEP 6] Testing Website Publishing & Strict Public vs Private Boundary...")
    pub_list_before = client.get("/api/projects").json()
    assert not any(p["id"] == shah_project_id for p in pub_list_before["projects"]), "Draft project leaked to public API!"
    print("[OK] Confirmed: Unpublished project is NOT visible on public /api/projects.")

    # Publish project via Admin API
    pub_resp = client.patch(f"/api/admin/projects/{shah_project_id}/publish", headers=headers)
    assert pub_resp.status_code == 200
    print("[OK] Project published via Owner API.")

    # Verify project is now available on public API
    pub_list_after = client.get("/api/projects").json()
    assert any(p["id"] == shah_project_id for p in pub_list_after["projects"]), "Published project missing from public API!"
    print(f"[OK] Confirmed: Project '{project_from_enquiry['project_title']}' is now live on public /api/projects!")

    # Unpublish project (toggle back)
    unpub_resp = client.patch(f"/api/admin/projects/{shah_project_id}/publish", headers=headers)
    assert unpub_resp.status_code == 200
    pub_list_final = client.get("/api/projects").json()
    assert not any(p["id"] == shah_project_id for p in pub_list_final["projects"]), "Unpublished project still visible publicly!"
    print("[OK] Confirmed: Unpublishing immediately removes project from public visibility.")

    # 7. Global Search
    print("\n[STEP 7] Testing Global Search across Projects, Clients, Enquiries & Files...")
    search_resp = client.get("/api/admin/search?q=Shah", headers=headers)
    assert search_resp.status_code == 200
    search_res = search_resp.json()
    assert len(search_res["projects"]) >= 1
    assert len(search_res["clients"]) >= 1
    print(f"[OK] Global search returned {len(search_res['projects'])} projects, {len(search_res['clients'])} clients matching 'Shah'.")

    # 8. Dashboard Intelligence & Action Items
    print("\n[STEP 8] Testing Real Owner Dashboard Metrics & Action Stream...")
    dash_resp = client.get("/api/admin/dashboard/stats", headers=headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    print(f"[OK] Dashboard Metrics: Active Projects: {dash_data['active_projects']}, Total Clients: {dash_data['total_clients']}, New Leads: {dash_data['new_enquiries']}, Overdue Tasks: {dash_data['overdue_tasks']}, Upcoming Meetings: {dash_data['upcoming_meetings_count']}")
    print(f"[OK] Action Items count: {len(dash_data['action_items'])}")

    # 9. Activity Log Audit
    print("\n[STEP 9] Testing Activity Logging...")
    act_resp = client.get("/api/admin/activity", headers=headers)
    assert act_resp.status_code == 200
    activities = act_resp.json()
    assert len(activities) > 0
    print(f"[OK] Activity log recorded {len(activities)} real business operations.")

    print("\n==================================================================")
    print("ALL 9 E2E SYSTEM INTEGRATION & BUSINESS WORKFLOW TESTS PASSED!")
    print("==================================================================")

if __name__ == "__main__":
    run_e2e_tests()
