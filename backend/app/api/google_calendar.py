import logging
import urllib.parse
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem
from app.models.task import Task
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.google_calendar import (
    GoogleCalendarStatusOut,
    GoogleCalendarOAuthStartOut,
    GoogleCalendarEventItem,
    GoogleCalendarSyncResponse
)
from app.services.google_calendar_service import GoogleCalendarService
from app.core.dependencies import get_current_user, require_roles, log_activity
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/google-calendar", tags=["Admin Google Calendar"])


@router.get("/status", response_model=GoogleCalendarStatusOut, summary="Get Google Calendar connection status")
def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == current_user.id
    ).first()

    client_configured = bool(settings.GOOGLE_CALENDAR_CLIENT_ID and settings.GOOGLE_CALENDAR_CLIENT_SECRET)

    if not conn:
        return GoogleCalendarStatusOut(
            connected=False,
            status="DISCONNECTED",
            client_id_configured=client_configured
        )

    return GoogleCalendarStatusOut(
        connected=conn.status == "CONNECTED",
        status=conn.status,
        google_account_email=conn.google_account_email,
        calendar_id=conn.calendar_id,
        last_synced_at=conn.last_synced_at,
        client_id_configured=client_configured
    )


@router.get("/oauth/start", summary="Start Google OAuth 2.0 flow")
def start_oauth(
    redirect: bool = Query(False, description="Set to true for direct HTTP 302 redirect to Google sign-in page"),
    current_user: User = Depends(get_current_user)
):
    auth_info = GoogleCalendarService.get_oauth_start_url(current_user)
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
    if error:
        logger.warning(f"Google OAuth denied or returned error: {error}")
        return RedirectResponse(url="http://localhost:5173/#owner/dashboard?calendar_error=" + urllib.parse.quote(error))

    if not code or not state:
        return RedirectResponse(url="http://localhost:5173/#owner/dashboard?calendar_error=Missing+authorization+code+or+state")

    try:
        # Parse owner_user_id from state (format: user_{id}_{timestamp})
        parts = state.split("_")
        user_id = int(parts[1])
        owner_user = db.query(User).filter(User.id == user_id).first()
        if not owner_user:
            return RedirectResponse(url="http://localhost:5173/#owner/dashboard?calendar_error=Owner+user+not+found")

        # Exchange code for tokens
        tokens = GoogleCalendarService.exchange_code_for_tokens(code)
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        scopes = tokens.get("scope", settings.GOOGLE_CALENDAR_SCOPES)

        email = GoogleCalendarService.fetch_user_email(access_token) if access_token else None

        conn = db.query(GoogleCalendarConnection).filter(
            GoogleCalendarConnection.owner_user_id == owner_user.id
        ).first()

        if not conn:
            conn = GoogleCalendarConnection(
                owner_user_id=owner_user.id,
                google_account_email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=datetime.utcnow() + timedelta(seconds=expires_in),
                scopes=scopes,
                calendar_id="primary",
                status="CONNECTED",
                last_synced_at=datetime.utcnow()
            )
            db.add(conn)
        else:
            conn.google_account_email = email or conn.google_account_email
            conn.access_token = access_token
            if refresh_token:
                conn.refresh_token = refresh_token
            conn.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            conn.scopes = scopes
            conn.status = "CONNECTED"
            conn.last_synced_at = datetime.utcnow()

        db.commit()

        log_activity(
            db,
            owner_user,
            action="Connected Google Calendar",
            entity_type="google_calendar",
            entity_id=str(conn.id),
            details=f"Connected account '{email or 'Owner Google Calendar'}'"
        )

        return RedirectResponse(url="http://localhost:5173/#owner/dashboard?calendar_connected=true")
    except Exception as exc:
        logger.error(f"OAuth callback error: {exc}")
        return RedirectResponse(url="http://localhost:5173/#owner/dashboard?calendar_error=" + urllib.parse.quote(str(exc)))


@router.post("/disconnect", summary="Disconnect Google Calendar integration")
def disconnect_google_calendar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
        details="Owner disconnected Google Calendar integration."
    )

    return {"message": "Google Calendar integration disconnected successfully."}


@router.get("/events", response_model=List[GoogleCalendarEventItem], summary="Get unified merged calendar events")
def get_merged_calendar_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items = GoogleCalendarService.get_merged_calendar_items(db, current_user)
    return [GoogleCalendarEventItem(**item) for item in items]


@router.post("/sync", response_model=GoogleCalendarSyncResponse, summary="Perform manual two-way synchronization")
def sync_google_calendar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == current_user.id
    ).first()

    pushed_count = 0
    pulled_count = 0

    if conn and conn.status == "CONNECTED":
        # Push tasks
        tasks_with_dates = db.query(Task).filter(
            Task.start_date.isnot(None) | Task.due_date.isnot(None)
        ).all()
        for t in tasks_with_dates:
            start_date_val = t.start_date or t.due_date
            if start_date_val:
                res = GoogleCalendarService.push_sd_event_to_google(
                    db, conn, "task", t.id, t.title, t.description, start_date_val, t.due_date
                )
                if res:
                    pushed_count += 1

        # Push meetings
        meetings = db.query(Meeting).all()
        for m in meetings:
            date_str = m.date or datetime.utcnow().strftime("%Y-%m-%d")
            time_str = m.time or "10:00"
            start_iso = f"{date_str}T{time_str}:00"
            res = GoogleCalendarService.push_sd_event_to_google(
                db, conn, "meeting", m.id, m.title, m.notes or "", start_iso
            )
            if res:
                pushed_count += 1

        # Pull count
        g_events = GoogleCalendarService.fetch_google_events(conn, db)
        pulled_count = len(g_events)

        conn.last_synced_at = datetime.utcnow()
        db.commit()

        log_activity(
            db,
            current_user,
            action="Synced Google Calendar",
            entity_type="google_calendar",
            entity_id=str(conn.id),
            details=f"Pushed {pushed_count} items, pulled {pulled_count} Google events."
        )

    return GoogleCalendarSyncResponse(
        success=True,
        pushed_to_google=pushed_count,
        pulled_from_google=pulled_count,
        last_synced_at=datetime.utcnow(),
        message=f"Sync completed successfully. Pushed {pushed_count} SD items to Google, fetched {pulled_count} Google events."
    )


@router.post("/push-task/{task_id}", summary="Manually push single task to Google Calendar")
def push_task_to_google(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    conn = db.query(GoogleCalendarConnection).filter(
        GoogleCalendarConnection.owner_user_id == current_user.id
    ).first()

    if not conn or conn.status != "CONNECTED":
        raise HTTPException(status_code=400, detail="Google Calendar is not connected.")

    start_date_val = task.start_date or task.due_date or datetime.utcnow().strftime("%Y-%m-%d")
    g_id = GoogleCalendarService.push_sd_event_to_google(
        db, conn, "task", task.id, task.title, task.description, start_date_val, task.due_date
    )

    if not g_id:
        raise HTTPException(status_code=500, detail="Failed to push task to Google Calendar API.")

    return {"message": f"Task '{task.title}' synchronized to Google Calendar.", "google_event_id": g_id}
