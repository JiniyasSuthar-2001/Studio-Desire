import logging
import urllib.parse
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem
from app.models.task import Task
from app.models.meeting import Meeting
from app.models.user import User, UserRole
from app.schemas.google_calendar import (
    GoogleCalendarStatusOut,
    GoogleCalendarOAuthStartOut,
    GoogleCalendarEventItem,
    GoogleCalendarSyncResponse
)
from app.services.google_calendar_service import (
    GoogleCalendarService,
    GoogleCalendarError,
    GoogleConfigurationError,
    GoogleOAuthStateError,
    GoogleAuthException
)
from app.core.dependencies import get_current_user, require_roles, log_activity
from app.core.config import settings
from app.core.security import encrypt_token

logger = logging.getLogger("studio_desire.google_calendar.api")

router = APIRouter(prefix="/admin/google-calendar", tags=["Admin Google Calendar"])

CALENDAR_ALLOWED_ROLES = ["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER"]


@router.get("/status", response_model=GoogleCalendarStatusOut, summary="Get Google Calendar connection status")
def get_connection_status(
    current_user: User = Depends(require_roles(CALENDAR_ALLOWED_ROLES)),
    db: Session = Depends(get_db)
):
    """
    Returns connection status strictly isolated to the authenticated user.
    Includes configuration validation diagnostics.
    """
    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == current_user.id
    ).first()

    conf = settings.validate_google_calendar_configuration()

    if not conn:
        return GoogleCalendarStatusOut(
            connected=False,
            status="DISCONNECTED",
            client_id_configured=conf["configured"],
            configuration_valid=conf["valid"],
            configuration_errors=conf["errors"]
        )

    is_connected = conn.status == "CONNECTED"
    return GoogleCalendarStatusOut(
        connected=is_connected,
        status=conn.status,
        google_account_email=conn.google_account_email,
        calendar_id=conn.calendar_id,
        last_synced_at=conn.last_synced_at,
        client_id_configured=conf["configured"],
        configuration_valid=conf["valid"],
        configuration_errors=conf["errors"]
    )


@router.get("/oauth/start", summary="Start Google OAuth 2.0 flow")
def start_oauth(
    redirect: bool = Query(False, description="Set to true for direct HTTP 302 redirect to Google sign-in page"),
    current_user: User = Depends(require_roles(CALENDAR_ALLOWED_ROLES)),
    db: Session = Depends(get_db)
):
    """
    Generates a secure Google OAuth authorization URL bound to a single-use random state.
    Requires authenticated session; fails fast with HTTP 400 if server configuration is invalid.
    """
    try:
        auth_info = GoogleCalendarService.get_oauth_start_url(current_user, db=db)
    except GoogleConfigurationError as exc:
        logger.error(f"[Google OAuth Start Error] {exc.message}")
        raise HTTPException(status_code=400, detail=exc.message)
    except Exception as exc:
        logger.error(f"[Google OAuth Start Error] Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to initialize Google OAuth flow.")

    auth_url = auth_info.get("auth_url", "")
    if redirect:
        return RedirectResponse(url=auth_url, status_code=302)

    return GoogleCalendarOAuthStartOut(
        auth_url=auth_url,
        authorization_url=auth_info.get("authorization_url", auth_url),
        state=auth_info.get("state", "")
    )


@router.get("/oauth/callback", summary="Google OAuth 2.0 Authorization Callback")
def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handles Google OAuth redirect:
    1. Validates and consumes single-use random state.
    2. Exchanges authorization code for tokens.
    3. Verifies email identity and calendar permissions.
    4. Persists encrypted credentials.
    5. Redirects to frontend using clean, safe status indicators without leaking secrets or codes.
    """
    frontend_base = settings.FRONTEND_URL.rstrip("/")
    target_dashboard = f"{frontend_base}/#owner/dashboard?tab=meetings"

    if error:
        logger.warning(f"[Google OAuth Callback] Google reported error: {error}")
        safe_code = "access_denied" if "denied" in error.lower() or "cancel" in error.lower() else "google_auth_error"
        return RedirectResponse(url=f"{target_dashboard}&calendar_error={safe_code}", status_code=302)

    if not code or not state:
        logger.warning("[Google OAuth Callback] Missing code or state parameter.")
        return RedirectResponse(url=f"{target_dashboard}&calendar_error=missing_code_or_state", status_code=302)

    # Validate and atomically consume state (prevent replay attacks and bind to initiating user)
    owner_user = GoogleCalendarService.validate_and_consume_state(db, state)
    if not owner_user:
        logger.warning(f"[Google OAuth Callback] Invalid, expired or replayed state: {state[:8]}...")
        return RedirectResponse(url=f"{target_dashboard}&calendar_error=invalid_or_expired_state", status_code=302)

    try:
        tokens = GoogleCalendarService.exchange_code_for_tokens(code)
    except GoogleAuthException as auth_exc:
        logger.error(f"[Google OAuth Callback] Token exchange failed: {auth_exc.message}")
        return RedirectResponse(url=f"{target_dashboard}&calendar_error=token_exchange_failed", status_code=302)
    except Exception as exc:
        logger.error(f"[Google OAuth Callback] Unexpected exchange error: {exc}")
        return RedirectResponse(url=f"{target_dashboard}&calendar_error=token_exchange_failed", status_code=302)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = int(tokens.get("expires_in", 3600))
    scopes = tokens.get("scope", settings.GOOGLE_CALENDAR_SCOPES)

    if not access_token:
        logger.error("[Google OAuth Callback] Google token response omitted access_token.")
        return RedirectResponse(url=f"{target_dashboard}&calendar_error=token_exchange_failed", status_code=302)

    # Fetch identity and verify calendar permissions
    email = GoogleCalendarService.fetch_user_email(access_token)
    calendar_ok = GoogleCalendarService.verify_calendar_access(access_token)
    if not calendar_ok:
        logger.warning(f"[Google OAuth Callback] Token lacks valid calendar permissions for account: {email}")

    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == owner_user.id
    ).first()

    now_utc = datetime.now(timezone.utc)
    token_expiry = now_utc + timedelta(seconds=expires_in)

    if not conn:
        conn = GoogleCalendarConnection(
            owner_user_id=owner_user.id,
            google_account_email=email,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token) if refresh_token else None,
            token_expiry=token_expiry,
            scopes=scopes,
            calendar_id="primary",
            status="CONNECTED",
            last_synced_at=now_utc
        )
        db.add(conn)
    else:
        conn.google_account_email = email or conn.google_account_email
        conn.access_token = encrypt_token(access_token)
        # CRITICAL: Preserve existing refresh token if Google omitted replacement
        if refresh_token:
            conn.refresh_token = encrypt_token(refresh_token)
        conn.token_expiry = token_expiry
        conn.scopes = scopes
        conn.status = "CONNECTED"
        conn.last_synced_at = now_utc

    db.commit()

    log_activity(
        db,
        owner_user,
        action="Connected Google Calendar",
        entity_type="google_calendar",
        entity_id=str(conn.id),
        details=f"Connected Google Calendar for account '{email or 'Owner'}'."
    )

    return RedirectResponse(url=f"{target_dashboard}&calendar_connected=true", status_code=302)


@router.post("/disconnect", summary="Disconnect Google Calendar integration")
def disconnect_google_calendar(
    current_user: User = Depends(require_roles(CALENDAR_ALLOWED_ROLES)),
    db: Session = Depends(get_db)
):
    """
    Disconnects the authenticated user's Google Calendar integration and wipes stored tokens.
    """
    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == current_user.id
    ).first()

    if conn:
        conn.status = "DISCONNECTED"
        conn.access_token = None
        conn.refresh_token = None
        db.commit()

    log_activity(
        db,
        current_user,
        action="Disconnected Google Calendar",
        entity_type="google_calendar",
        entity_id=str(current_user.id),
        details="User disconnected Google Calendar integration."
    )

    return {"message": "Google Calendar integration disconnected successfully."}


@router.get("/events", response_model=List[GoogleCalendarEventItem], summary="Get unified merged calendar events")
def get_merged_calendar_events(
    current_user: User = Depends(require_roles(CALENDAR_ALLOWED_ROLES)),
    db: Session = Depends(get_db)
):
    """
    Returns unified calendar events:
    - Studio Desire tasks filtered by the current user's visibility permissions.
    - Studio Desire meetings.
    - External Google Calendar events belonging exclusively to the current user.
    """
    items = GoogleCalendarService.get_merged_calendar_items(db, current_user)
    return [GoogleCalendarEventItem(**item) for item in items]


@router.post("/sync", response_model=GoogleCalendarSyncResponse, summary="Perform honest synchronization")
def sync_google_calendar(
    current_user: User = Depends(require_roles(CALENDAR_ALLOWED_ROLES)),
    db: Session = Depends(get_db)
):
    """
    Executes synchronization with honest error and status tracking:
    - Rejects sync with HTTP 400 if disconnected.
    - Only synchronizes tasks and meetings authorized for the current user.
    - Tracks per-operation push results and pulls Google events.
    - Updates last_synced_at only upon successful synchronization.
    """
    try:
        result = GoogleCalendarService.sync_calendar(db, current_user)
    except GoogleCalendarError as ge:
        raise HTTPException(status_code=ge.status_code, detail=ge.message)
    except Exception as exc:
        logger.error(f"[Google Calendar Sync] Unexpected error: {exc}")
        raise HTTPException(status_code=500, detail="Internal error during calendar synchronization.")

    log_activity(
        db,
        current_user,
        action="Synced Google Calendar",
        entity_type="google_calendar",
        entity_id=str(current_user.id),
        details=f"Sync status: {result['status']}. Pushed {result['pushed_to_google']}, fetched {result['pulled_from_google']} Google events."
    )

    return GoogleCalendarSyncResponse(**result)


@router.post("/push-task/{task_id}", summary="Manually push single task to Google Calendar")
def push_task_to_google(
    task_id: int,
    current_user: User = Depends(require_roles(CALENDAR_ALLOWED_ROLES)),
    db: Session = Depends(get_db)
):
    """
    Pushes an individual Studio Desire task to Google Calendar:
    - Verifies that task exists.
    - Strictly checks authorization using the task access control policy.
    - Verifies Google Calendar is connected for the authenticated user.
    """
    from app.api.admin_tasks import check_task_access

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not check_task_access(task, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access or synchronize this task."
        )

    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == current_user.id
    ).first()

    if not conn or conn.status != "CONNECTED":
        raise HTTPException(status_code=400, detail="Google Calendar is not connected. Please connect your account first.")

    start_date_val = task.start_date or task.due_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    g_id = GoogleCalendarService.push_sd_event_to_google(
        db, conn, "task", task.id, task.title, task.description, start_date_val, task.due_date
    )

    if not g_id:
        raise HTTPException(status_code=500, detail="Failed to push task to Google Calendar API.")

    return {"message": f"Task '{task.title}' synchronized to Google Calendar.", "google_event_id": g_id}
