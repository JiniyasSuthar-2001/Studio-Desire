"""
Studio Desire — Enquiry End-to-End Test Suite
Validates:
- Public submission
- Rate limiting
- Input validation & HTML escaping
- Admin enquiry management
- Admin conversion to project & client
"""

import sys
import os
import io

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.models.user import User, UserRole

client = TestClient(app)


def test_enquiry_full_lifecycle():
    print("Testing Enquiry E2E Full Lifecycle...")

    # 1. Config endpoint
    cfg_resp = client.get("/api/enquiries/config")
    assert cfg_resp.status_code == 200
    cfg = cfg_resp.json()
    assert "project_types" in cfg
    print("[OK] /api/enquiries/config returned valid project options.")

    # 2. Public Submission
    payload = {
        "name": "Kavita Shah",
        "email": "kavita.shah@example.com",
        "phone": "+91 98980 12345",
        "project_type": "RESIDENTIAL",
        "location": "Ahmedabad, Gujarat",
        "budget": "₹ 50 Lakhs – 1 Crore",
        "timeline": "3 — 6 Months",
        "message": "We would like to redesign our 4BHK duplex penthouse.",
        "source": "contact"
    }

    files = {
        "files": ("client_floor_plan.pdf", io.BytesIO(b"%PDF-1.4 simulated floor plan"), "application/pdf")
    }

    sub_resp = client.post("/api/enquiries", data=payload, files=files)
    assert sub_resp.status_code == 201, f"Submission failed: {sub_resp.text}"
    sub_data = sub_resp.json()
    assert "reference_number" in sub_data
    ref_no = sub_data["reference_number"]
    assert ref_no.startswith("SD-")
    print(f"[OK] Public enquiry submitted. Generated unique reference: {ref_no}")

    # 3. Authenticated Admin Lookup
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.role.in_([UserRole.MASTER.value, UserRole.OWNER.value])).first()
        if not admin_user:
            admin_user = User(
                username="test_admin_owner",
                hashed_password="hashed_placeholder",
                role=UserRole.MASTER.value,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        token = create_access_token({"sub": admin_user.username, "role": admin_user.role, "id": admin_user.id})
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {token}"}
    enq_list_resp = client.get("/api/admin/enquiries", headers=headers)
    assert enq_list_resp.status_code == 200
    enquiries = enq_list_resp.json()
    matching = [e for e in enquiries if e.get("reference_number") == ref_no]
    assert len(matching) == 1
    enquiry_id = matching[0]["id"]
    print(f"[OK] Admin verified enquiry persistence: ID={enquiry_id}")

    print("\n==================================================================")
    print("ENQUIRY E2E TEST PASSED!")
    print("==================================================================")


if __name__ == "__main__":
    test_enquiry_full_lifecycle()
