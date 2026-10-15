import json
import urllib.error
import urllib.request
import io
import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import Base, engine, SessionLocal
from app.models.user import User, UserRole
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem, GoogleOAuthState
from app.models.task import Task
from app.models.meeting import Meeting
from app.core.security import hash_password, create_access_token, encrypt_token, decrypt_token
from app.core.config import settings
from app.services.google_calendar_service import (
    GoogleCalendarService,
    GoogleConfigurationError,
    GoogleAuthException,
    GoogleCalendarError
)

client = TestClient(app)


def get_or_create_user(db, username, email, role=UserRole.OWNER.value):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password("StrongPassword123!"),
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Clean up any associations so test starts fresh and isolated
    db.query(GoogleCalendarConnection).filter(GoogleCalendarConnection.owner_user_id == user.id).delete()
    db.query(CalendarSyncItem).filter(CalendarSyncItem.owner_user_id == user.id).delete()
    db.query(GoogleOAuthState).filter(GoogleOAuthState.user_id == user.id).delete()
    db.commit()
    return user


def auth_header_for_user(user):
    token = create_access_token(data={"sub": user.username, "role": user.role, "user_id": user.id})
    return {"Authorization": f"Bearer {token}"}


class MockHTTPResponse:
    def __init__(self, data: dict, status: int = 200):
        self._data = json.dumps(data).encode("utf-8")
        self.status = status

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup test credentials
    orig_client_id = settings.GOOGLE_CALENDAR_CLIENT_ID
    orig_client_secret = settings.GOOGLE_CALENDAR_CLIENT_SECRET
    orig_redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI
    orig_scopes = settings.GOOGLE_CALENDAR_SCOPES
    orig_frontend = settings.FRONTEND_URL

    settings.GOOGLE_CALENDAR_CLIENT_ID = "test-client-id.apps.googleusercontent.com"
    settings.GOOGLE_CALENDAR_CLIENT_SECRET = "test-client-secret"
    settings.GOOGLE_CALENDAR_REDIRECT_URI = "http://localhost:8000/api/admin/google-calendar/oauth/callback"
    settings.GOOGLE_CALENDAR_SCOPES = "https://www.googleapis.com/auth/calendar.events openid email"
    settings.FRONTEND_URL = "http://localhost:5173"

    yield

    settings.GOOGLE_CALENDAR_CLIENT_ID = orig_client_id
    settings.GOOGLE_CALENDAR_CLIENT_SECRET = orig_client_secret
    settings.GOOGLE_CALENDAR_REDIRECT_URI = orig_redirect_uri
    settings.GOOGLE_CALENDAR_SCOPES = orig_scopes
    settings.FRONTEND_URL = orig_frontend


# ============================================================================
# 1. MISSING GOOGLE CREDENTIALS & FAST FAILURE
# ============================================================================
def test_missing_google_credentials_rejects_oauth_start():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_cfg", "owner_cfg@example.com")
        headers = auth_header_for_user(user)

        # Clear credentials
        settings.GOOGLE_CALENDAR_CLIENT_ID = ""
        res = client.get("/api/admin/google-calendar/oauth/start", headers=headers)
        assert res.status_code == 400
        assert "not configured" in res.json()["detail"].lower()

        # Placeholder rejected
        settings.GOOGLE_CALENDAR_CLIENT_ID = "DEMO_GOOGLE_CLIENT_ID"
        res2 = client.get("/api/admin/google-calendar/oauth/start", headers=headers)
        assert res2.status_code == 400
    finally:
        db.close()


# ============================================================================
# 2. OAUTH START REQUIRES AUTHENTICATION & ROLE POLICY
# ============================================================================
def test_oauth_start_requires_authentication_and_role():
    # Unauthenticated request rejected
    res = client.get("/api/admin/google-calendar/oauth/start")
    assert res.status_code == 401

    db = SessionLocal()
    try:
        # Observer/viewer rejected
        viewer = get_or_create_user(db, "test_viewer", "viewer@example.com", role=UserRole.VIEWER.value)
        headers = auth_header_for_user(viewer)
        res_viewer = client.get("/api/admin/google-calendar/oauth/start", headers=headers)
        assert res_viewer.status_code == 403
    finally:
        db.close()


# ============================================================================
# 3. CORRECT REDIRECT URI AND SCOPE GENERATION
# ============================================================================
def test_correct_redirect_uri_and_scopes_generation():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_uri", "owner_uri@example.com")
        headers = auth_header_for_user(user)

        res = client.get("/api/admin/google-calendar/oauth/start", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "auth_url" in data
        auth_url = data["auth_url"]

        # Must target accounts.google.com
        assert auth_url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
        # Must include exact callback URL
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fadmin%2Fgoogle-calendar%2Foauth%2Fcallback" in auth_url
        # Must include calendar.events and openid email scopes
        assert "calendar.events" in auth_url
        assert "openid" in auth_url
    finally:
        db.close()


# ============================================================================
# 4. RANDOM STATE GENERATION & VALIDATION
# ============================================================================
def test_random_single_use_state_generation_and_consumption():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_state", "owner_state@example.com")
        headers = auth_header_for_user(user)

        res = client.get("/api/admin/google-calendar/oauth/start", headers=headers)
        assert res.status_code == 200
        state = res.json()["state"]

        # Ensure cryptographically random, not predictable user_{id}_{timestamp}
        assert f"user_{user.id}_" not in state
        assert len(state) >= 32

        # Check DB record
        record = db.query(GoogleOAuthState).filter(GoogleOAuthState.state == state).first()
        assert record is not None
        assert record.user_id == user.id
        assert record.used == 0

        # Validate and consume atomically
        consumed_user = GoogleCalendarService.validate_and_consume_state(db, state)
        assert consumed_user is not None
        assert consumed_user.id == user.id

        # Verify state is now marked used and cannot be replayed
        record_after = db.query(GoogleOAuthState).filter(GoogleOAuthState.state == state).first()
        assert record_after.used == 1

        replayed_user = GoogleCalendarService.validate_and_consume_state(db, state)
        assert replayed_user is None
    finally:
        db.close()


# ============================================================================
# 5. REJECT EXPIRED, MISMATCHED AND MALFORMED STATE
# ============================================================================
def test_reject_expired_and_malformed_state():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_exp", "owner_exp@example.com")

        # Expired state
        state_token = "mock_expired_state_token_1234567890"
        db.query(GoogleOAuthState).filter(GoogleOAuthState.state == state_token).delete()
        db.commit()
        expired_state = GoogleOAuthState(
            state=state_token,
            user_id=user.id,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=20),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            used=0
        )
        db.add(expired_state)
        db.commit()

        assert GoogleCalendarService.validate_and_consume_state(db, state_token) is None
        assert GoogleCalendarService.validate_and_consume_state(db, "non_existent_state_12345") is None
        assert GoogleCalendarService.validate_and_consume_state(db, "") is None
    finally:
        db.close()


# ============================================================================
# 6. CALLBACK CANCELLATION & GOOGLE ERROR RESPONSES
# ============================================================================
def test_callback_handles_google_cancellation():
    res = client.get(
        "/api/admin/google-calendar/oauth/callback?error=access_denied",
        follow_redirects=False
    )
    assert res.status_code == 302
    location = res.headers["location"]
    assert "calendar_error=access_denied" in location
    assert "access_token" not in location
    assert "code=" not in location


# ============================================================================
# 7. SUCCESSFUL CODE EXCHANGE, CREDENTIAL ENCRYPTION & PERSISTENCE
# ============================================================================
def test_successful_token_exchange_and_encryption():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_exch", "owner_exch@example.com")
        state_str = GoogleCalendarService.create_oauth_state(db, user)

        mock_tokens = {
            "access_token": "ya29.mock_access_token_secret_12345",
            "refresh_token": "1//mock_refresh_token_secret_67890",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/calendar.events openid email"
        }
        mock_userinfo = {"email": "owner_exch@gmail.com", "id": "google_uid_999"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            # Responses: 1 for token exchange, 1 for userinfo, 1 for calendar verification
            mock_urlopen.side_effect = [
                MockHTTPResponse(mock_tokens),
                MockHTTPResponse(mock_userinfo),
                MockHTTPResponse({"id": "primary"})
            ]

            res = client.get(
                f"/api/admin/google-calendar/oauth/callback?code=valid_test_code&state={state_str}",
                follow_redirects=False
            )
            assert res.status_code == 302
            assert "calendar_connected=true" in res.headers["location"]

            conn = db.query(GoogleCalendarConnection).filter(
                GoogleCalendarConnection.owner_user_id == user.id
            ).first()
            assert conn is not None
            assert conn.status == "CONNECTED"
            assert conn.google_account_email == "owner_exch@gmail.com"

            # Tokens must be stored encrypted (starts with 'enc:')
            assert conn.access_token.startswith("enc:")
            assert conn.refresh_token.startswith("enc:")
            # Decrypted matches plaintext
            assert decrypt_token(conn.access_token) == "ya29.mock_access_token_secret_12345"
            assert decrypt_token(conn.refresh_token) == "1//mock_refresh_token_secret_67890"
    finally:
        db.close()


# ============================================================================
# 8. PRESERVATION OF EXISTING REFRESH TOKEN ON RE-AUTHORIZATION
# ============================================================================
def test_preserves_existing_refresh_token_when_reauth_omits_it():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_reauth", "owner_reauth@example.com")
        existing_conn = GoogleCalendarConnection(
            owner_user_id=user.id,
            google_account_email="owner_reauth@gmail.com",
            access_token=encrypt_token("old_access_token"),
            refresh_token=encrypt_token("permanent_refresh_token_keep_me"),
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            status="CONNECTED"
        )
        db.add(existing_conn)
        db.commit()

        state_str = GoogleCalendarService.create_oauth_state(db, user)

        # Google returns new access_token, but NO refresh_token on subsequent authorizations
        mock_tokens = {
            "access_token": "ya29.new_fresh_access_token",
            "expires_in": 3600
        }
        mock_userinfo = {"email": "owner_reauth@gmail.com"}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                MockHTTPResponse(mock_tokens),
                MockHTTPResponse(mock_userinfo),
                MockHTTPResponse({"id": "primary"})
            ]

            res = client.get(
                f"/api/admin/google-calendar/oauth/callback?code=new_code&state={state_str}",
                follow_redirects=False
            )
            assert res.status_code == 302
            assert "calendar_connected=true" in res.headers["location"]

            db.refresh(existing_conn)
            assert decrypt_token(existing_conn.access_token) == "ya29.new_fresh_access_token"
            # Refresh token preserved!
            assert decrypt_token(existing_conn.refresh_token) == "permanent_refresh_token_keep_me"
    finally:
        db.close()


# ============================================================================
# 9. TOKEN EXCHANGE HTTP 400 ERROR HANDLING
# ============================================================================
def test_token_exchange_http_400_response():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_tokerr", "owner_tokerr@example.com")
        state_str = GoogleCalendarService.create_oauth_state(db, user)

        error_body = json.dumps({"error": "invalid_grant", "error_description": "Code expired"}).encode()
        fp = io.BytesIO(error_body)
        http_err = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/token",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=fp
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            res = client.get(
                f"/api/admin/google-calendar/oauth/callback?code=bad_code&state={state_str}",
                follow_redirects=False
            )
            assert res.status_code == 302
            assert "calendar_error=token_exchange_failed" in res.headers["location"]
    finally:
        db.close()


# ============================================================================
# 10. TOKEN REFRESH & INVALID_GRANT STATUS EXPIRED
# ============================================================================
def test_token_refresh_lifecycle_and_revocation():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_refr", "owner_refr@example.com")
        conn = GoogleCalendarConnection(
            owner_user_id=user.id,
            google_account_email="owner_refr@gmail.com",
            access_token=encrypt_token("expired_access_token"),
            refresh_token=encrypt_token("active_refresh_token"),
            token_expiry=datetime.now(timezone.utc) - timedelta(minutes=10),
            status="CONNECTED"
        )
        db.add(conn)
        db.commit()

        # 1. Successful Refresh
        mock_refresh_res = {
            "access_token": "ya29.refreshed_access_token",
            "expires_in": 3600
        }
        with patch("urllib.request.urlopen", return_value=MockHTTPResponse(mock_refresh_res)):
            new_token = GoogleCalendarService.get_valid_access_token(conn, db)
            assert new_token == "ya29.refreshed_access_token"
            db.refresh(conn)
            assert decrypt_token(conn.access_token) == "ya29.refreshed_access_token"
            assert conn.status == "CONNECTED"

        # 2. Revoked Token (Google invalid_grant)
        conn.token_expiry = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()

        error_body = json.dumps({"error": "invalid_grant", "error_description": "Token has been expired or revoked."}).encode()
        fp = io.BytesIO(error_body)
        http_err = urllib.error.HTTPError(
            url="https://oauth2.googleapis.com/token",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=fp
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(GoogleAuthException) as exc_info:
                GoogleCalendarService.get_valid_access_token(conn, db)
            assert exc_info.value.error_code == "invalid_grant"
            db.refresh(conn)
            assert conn.status == "EXPIRED"
            assert conn.access_token is None
    finally:
        db.close()


# ============================================================================
# 11. TIMING & ALL-DAY EVENT VALIDITY
# ============================================================================
def test_all_day_and_timed_event_timing_rules():
    # All day event: end date MUST be strictly after start date (exclusive)
    start_timing, end_timing, is_all_day = GoogleCalendarService.build_google_event_timing("2026-10-15")
    assert is_all_day is True
    assert start_timing == {"date": "2026-10-15"}
    assert end_timing == {"date": "2026-10-16"}

    # Timed event: end dateTime strictly after start dateTime
    t_start, t_end, t_is_all_day = GoogleCalendarService.build_google_event_timing(
        "2026-10-15", duration_minutes=90, default_time="2:30 PM"
    )
    assert t_is_all_day is False
    assert "T14:30:00" in t_start["dateTime"]
    assert "T16:00:00" in t_end["dateTime"]


# ============================================================================
# 12. DISCONNECTED SYNC REJECTED WITH HTTP 400
# ============================================================================
def test_disconnected_sync_returns_http_400():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_nosync", "owner_nosync@example.com")
        headers = auth_header_for_user(user)

        # Clear connection
        db.query(GoogleCalendarConnection).filter(GoogleCalendarConnection.owner_user_id == user.id).delete()
        db.commit()

        res = client.post("/api/admin/google-calendar/sync", headers=headers)
        assert res.status_code == 400
        assert "not connected" in res.json()["detail"].lower()
    finally:
        db.close()


# ============================================================================
# 13. HONEST SYNC SUCCESS & ERROR REPORTING
# ============================================================================
def test_honest_sync_success_and_push():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_sync", "owner_sync@example.com")
        headers = auth_header_for_user(user)

        conn = GoogleCalendarConnection(
            owner_user_id=user.id,
            google_account_email="owner_sync@gmail.com",
            access_token=encrypt_token("valid_token"),
            refresh_token=encrypt_token("valid_refresh"),
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            status="CONNECTED"
        )
        db.add(conn)

        # Clean up prior tasks/sync items
        db.query(CalendarSyncItem).filter(CalendarSyncItem.owner_user_id == user.id).delete()
        db.query(Task).filter(Task.created_by_id == user.id).delete()
        db.commit()

        task = Task(
            created_by_id=user.id,
            title="Design Review Task",
            start_date=datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc),
            status="TODO",
            priority="HIGH"
        )
        db.add(task)
        db.commit()

        # Mock pushing task to Google and pulling events
        mock_events_list = {"items": [{"id": "external_1", "summary": "Client Call"}]}
        evt_counter = [0]

        def urlopen_handler(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "events?" in url:
                return MockHTTPResponse(mock_events_list)
            evt_counter[0] += 1
            return MockHTTPResponse({"id": f"google_evt_task_{evt_counter[0]}", "etag": f"etag_{evt_counter[0]}"})

        with patch("urllib.request.urlopen", side_effect=urlopen_handler):
            res = client.post("/api/admin/google-calendar/sync", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["status"] == "COMPLETED"
            assert data["pushed_to_google"] >= 1
            assert data["pulled_from_google"] == 1
    finally:
        db.close()


# ============================================================================
# 14. CROSS-USER CALENDAR & TASK ISOLATION
# ============================================================================
def test_cross_user_isolation_tasks_and_calendar():
    db = SessionLocal()
    try:
        user_a = get_or_create_user(db, "test_user_a", "user_a@example.com", role=UserRole.DESIGNER.value)
        user_b = get_or_create_user(db, "test_user_b", "user_b@example.com", role=UserRole.DESIGNER.value)

        headers_a = auth_header_for_user(user_a)
        headers_b = auth_header_for_user(user_b)

        # User B creates a PRIVATE task
        task_b = Task(
            created_by_id=user_b.id,
            title="User B Private Task",
            visibility="PRIVATE",
            start_date=datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc),
            due_date=datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc),
            status="TODO",
            priority="LOW"
        )
        db.add(task_b)
        db.commit()

        # User A cannot push User B's private task
        res_push = client.post(f"/api/admin/google-calendar/push-task/{task_b.id}", headers=headers_a)
        assert res_push.status_code == 403

        # User A viewing events does NOT see User B's private task
        res_events_a = client.get("/api/admin/google-calendar/events", headers=headers_a)
        assert res_events_a.status_code == 200
        events_a = res_events_a.json()
        assert not any(e["title"] == "User B Private Task" for e in events_a)

        # User B viewing events DOES see their own task
        res_events_b = client.get("/api/admin/google-calendar/events", headers=headers_b)
        assert res_events_b.status_code == 200
        events_b = res_events_b.json()
        assert any(e["title"] == "User B Private Task" for e in events_b)
    finally:
        db.close()


# ============================================================================
# 15. DISCONNECT AND RECONNECT WITHOUT DUPLICATE EVENTS
# ============================================================================
def test_disconnect_and_reconnect_without_duplicate_events():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_reconn", "owner_reconn@example.com")
        headers = auth_header_for_user(user)

        conn = GoogleCalendarConnection(
            owner_user_id=user.id,
            google_account_email="reconn@gmail.com",
            access_token=encrypt_token("tok_1"),
            refresh_token=encrypt_token("ref_1"),
            status="CONNECTED"
        )
        db.add(conn)
        db.commit()

        # Disconnect
        res_disc = client.post("/api/admin/google-calendar/disconnect", headers=headers)
        assert res_disc.status_code == 200
        db.refresh(conn)
        assert conn.status == "DISCONNECTED"
        assert conn.access_token is None

        # Reconnect
        state_str = GoogleCalendarService.create_oauth_state(db, user)
        mock_tokens = {
            "access_token": "tok_2",
            "refresh_token": "ref_2",
            "expires_in": 3600
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [
                MockHTTPResponse(mock_tokens),
                MockHTTPResponse({"email": "reconn@gmail.com"}),
                MockHTTPResponse({"id": "primary"})
            ]
            res_cb = client.get(
                f"/api/admin/google-calendar/oauth/callback?code=code_2&state={state_str}",
                follow_redirects=False
            )
            assert res_cb.status_code == 302

        db.refresh(conn)
        assert conn.status == "CONNECTED"
        assert decrypt_token(conn.access_token) == "tok_2"
    finally:
        db.close()


# ============================================================================
# 16. GOOGLE EVENT PAGINATION
# ============================================================================
def test_google_event_pagination_handling():
    db = SessionLocal()
    try:
        user = get_or_create_user(db, "test_owner_page", "owner_page@example.com")
        conn = GoogleCalendarConnection(
            owner_user_id=user.id,
            google_account_email="page@gmail.com",
            access_token=encrypt_token("page_tok"),
            status="CONNECTED"
        )
        db.add(conn)
        db.commit()

        page1 = {
            "items": [{"id": "evt_1", "summary": "Page 1 Event"}],
            "nextPageToken": "token_for_page_2"
        }
        page2 = {
            "items": [{"id": "evt_2", "summary": "Page 2 Event"}]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [MockHTTPResponse(page1), MockHTTPResponse(page2)]
            events = GoogleCalendarService.fetch_google_events(conn, db)
            assert len(events) == 2
            summaries = [e["summary"] for e in events]
            assert "Page 1 Event" in summaries
            assert "Page 2 Event" in summaries
    finally:
        db.close()
