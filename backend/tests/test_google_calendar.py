import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import Base, engine, SessionLocal
from app.models.user import User, UserRole
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem
from app.models.task import Task
from app.core.security import hash_password, create_access_token

client = TestClient(app)


def test_google_calendar_status_and_oauth_flow():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "test_gc_owner").first()
        if not user:
            user = User(
                username="test_gc_owner",
                email="gc_owner@example.com",
                hashed_password=hash_password("OwnerPass123!"),
                role=UserRole.OWNER.value,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Ensure clean initial state
        db.query(GoogleCalendarConnection).filter(GoogleCalendarConnection.owner_user_id == user.id).delete()
        db.commit()

        token = create_access_token(data={"sub": user.username, "role": user.role, "user_id": user.id})
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Status when disconnected
        res = client.get("/api/admin/google-calendar/status", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is False
        assert data["status"] == "DISCONNECTED"

        # 2. OAuth Start
        res_start = client.get("/api/admin/google-calendar/oauth/start", headers=headers)
        assert res_start.status_code == 200
        start_data = res_start.json()
        assert "auth_url" in start_data
        assert f"user_{user.id}_" in start_data["state"]

        # 3. Connection State
        conn = db.query(GoogleCalendarConnection).filter(GoogleCalendarConnection.owner_user_id == user.id).first()
        if not conn:
            conn = GoogleCalendarConnection(
                owner_user_id=user.id,
                google_account_email="owner@studiodesire.com",
                access_token="mock_access_token",
                refresh_token="mock_refresh_token",
                token_expiry=datetime.utcnow() + timedelta(hours=1),
                calendar_id="primary",
                status="CONNECTED",
                last_synced_at=datetime.utcnow()
            )
            db.add(conn)
            db.commit()
        else:
            conn.status = "CONNECTED"
            conn.google_account_email = "owner@studiodesire.com"
            db.commit()

        # 4. Status when connected
        res_conn = client.get("/api/admin/google-calendar/status", headers=headers)
        assert res_conn.status_code == 200
        assert res_conn.json()["connected"] is True
        assert res_conn.json()["google_account_email"] == "owner@studiodesire.com"

        # 5. Get Merged Events
        task = Task(
            created_by_id=user.id,
            title="Site Inspection Task",
            start_date=datetime(2026, 10, 15, 10, 0),
            due_date=datetime(2026, 10, 15, 12, 0),
            status="TODO",
            priority="HIGH"
        )
        db.add(task)
        db.commit()

        res_events = client.get("/api/admin/google-calendar/events", headers=headers)
        assert res_events.status_code == 200
        events = res_events.json()
        assert len(events) >= 1
        assert any(e["title"] == "Site Inspection Task" for e in events)

        # 6. Disconnect
        res_disc = client.post("/api/admin/google-calendar/disconnect", headers=headers)
        assert res_disc.status_code == 200
        assert res_disc.json()["message"] == "Google Calendar integration disconnected successfully."
    finally:
        db.close()
