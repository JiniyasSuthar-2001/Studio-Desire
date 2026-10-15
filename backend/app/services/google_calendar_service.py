import json
import secrets
import re
import urllib.parse
import urllib.request
import urllib.error
import logging
from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem, GoogleOAuthState
from app.models.task import Task
from app.models.meeting import Meeting
from app.models.user import User

logger = logging.getLogger("studio_desire.google_calendar")


class GoogleCalendarError(Exception):
    """Base exception for Google Calendar operations."""
    def __init__(self, message: str, error_code: str = "google_calendar_error", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class GoogleConfigurationError(GoogleCalendarError):
    def __init__(self, message: str):
        super().__init__(message, error_code="config_error", status_code=400)


class GoogleOAuthStateError(GoogleCalendarError):
    def __init__(self, message: str):
        super().__init__(message, error_code="invalid_state", status_code=400)


class GoogleAuthException(GoogleCalendarError):
    def __init__(self, message: str, error_code: str = "auth_error", status_code: int = 401):
        super().__init__(message, error_code=error_code, status_code=status_code)


class GoogleCalendarService:

    @staticmethod
    def create_oauth_state(db: Session, user: User) -> str:
        """
        Generates a cryptographically secure, single-use OAuth state token,
        persisting it in the database with a 10-minute expiry bound to the initiating user.
        """
        raw_state = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        oauth_state = GoogleOAuthState(
            state=raw_state,
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            used=0
        )
        db.add(oauth_state)
        db.commit()
        return raw_state

    @staticmethod
    def validate_and_consume_state(db: Session, state: str) -> Optional[User]:
        """
        Validates and atomically consumes a single-use OAuth state token.
        Rejects missing, expired, tampered, or replayed states.
        Returns the initiating active User upon success, or None.
        """
        if not state or len(state.strip()) < 16:
            logger.warning("[OAuth Security] Callback received missing or malformed state parameter.")
            return None

        clean_state = state.strip()
        record = db.query(GoogleOAuthState).filter(GoogleOAuthState.state == clean_state).first()

        if not record:
            logger.warning("[OAuth Security] State parameter not found in database records.")
            return None

        if record.used == 1:
            logger.warning(f"[OAuth Security] Detected replayed state parameter: {clean_state[:8]}...")
            return None

        exp = record.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > exp:
            logger.warning(f"[OAuth Security] OAuth state expired: {clean_state[:8]}...")
            record.used = 1
            db.commit()
            return None

        # Atomically mark state consumed
        record.used = 1
        db.commit()

        user = db.query(User).filter(User.id == record.user_id, User.is_active == True).first()
        if not user:
            logger.warning(f"[OAuth Security] User ID {record.user_id} associated with state no longer active.")
            return None

        return user

    @classmethod
    def get_oauth_start_url(cls, owner_user: User, db: Optional[Session] = None) -> Dict[str, str]:
        """
        Generates Google OAuth 2.0 authorization URL with cryptographically secure, single-use state.
        Fails fast if Google Cloud credentials are not configured.
        """
        conf = settings.validate_google_calendar_configuration()
        if not conf["configured"]:
            error_str = "; ".join(conf["errors"]) if conf["errors"] else "Missing client ID or secret."
            raise GoogleConfigurationError(f"Google Calendar OAuth credentials not configured: {error_str}")

        if not conf["valid"]:
            error_str = "; ".join(conf["errors"])
            raise GoogleConfigurationError(f"Google Calendar configuration error: {error_str}")

        should_close = False
        if db is None:
            from app.database.session import SessionLocal
            db = SessionLocal()
            should_close = True

        try:
            state = cls.create_oauth_state(db, owner_user)
        finally:
            if should_close:
                db.close()

        params = {
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "response_type": "code",
            "scope": settings.GOOGLE_CALENDAR_SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return {"auth_url": auth_url, "authorization_url": auth_url, "state": state}

    @staticmethod
    def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
        """Exchanges OAuth authorization code for access and refresh tokens."""
        if not code or not code.strip():
            raise GoogleAuthException("Authorization code is missing or empty.", error_code="invalid_code", status_code=400)

        conf = settings.validate_google_calendar_configuration()
        if not conf["configured"]:
            raise GoogleConfigurationError("Google Calendar credentials not configured.")

        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "code": code.strip(),
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(
            token_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                err_code = err_json.get("error", "token_exchange_error")
                err_desc = err_json.get("error_description", f"Google HTTP {e.code}")
            except Exception:
                err_code = f"http_{e.code}"
                err_desc = err_body
            logger.error(f"[Google OAuth] Code exchange HTTP {e.code}: {err_code} - {err_desc}")
            raise GoogleAuthException(
                f"Google authorization exchange failed: {err_desc}",
                error_code=err_code,
                status_code=e.code
            )
        except Exception as e:
            logger.error(f"[Google OAuth] Network error during token exchange: {e}")
            raise GoogleCalendarError(
                f"Failed to communicate with Google authentication servers: {str(e)}",
                error_code="network_error",
                status_code=502
            )

    @staticmethod
    def refresh_access_token(connection: GoogleCalendarConnection, db: Session) -> str:
        """Refreshes access token using stored refresh_token if expired."""
        plain_refresh_token = decrypt_token(connection.refresh_token)
        if not plain_refresh_token:
            connection.status = "EXPIRED"
            db.commit()
            raise GoogleAuthException("No refresh token available. Connection requires reauthorization.", error_code="missing_refresh_token", status_code=401)

        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "refresh_token": plain_refresh_token,
            "grant_type": "refresh_token"
        }).encode("utf-8")

        req = urllib.request.Request(
            token_url,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                new_access = res_data.get("access_token")
                connection.access_token = encrypt_token(new_access)
                if res_data.get("refresh_token"):
                    connection.refresh_token = encrypt_token(res_data.get("refresh_token"))
                expires_in = int(res_data.get("expires_in", 3600))
                connection.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                connection.status = "CONNECTED"
                db.commit()
                return new_access
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                err_code = err_json.get("error", "refresh_error")
                err_desc = err_json.get("error_description", f"Google HTTP {e.code}")
            except Exception:
                err_code = f"http_{e.code}"
                err_desc = err_body
            if err_code in ("invalid_grant", "unauthorized_client") or e.code in (400, 401):
                connection.status = "EXPIRED"
                connection.access_token = None
                db.commit()
            logger.error(f"[Google OAuth] Token refresh HTTP {e.code}: {err_code} - {err_desc}")
            raise GoogleAuthException(
                f"Failed to refresh Google Calendar token: {err_desc}",
                error_code=err_code,
                status_code=e.code
            )
        except Exception as e:
            logger.error(f"[Google OAuth] Network error refreshing token: {e}")
            raise GoogleCalendarError(
                f"Failed to connect to Google authentication service: {str(e)}",
                error_code="network_error",
                status_code=502
            )

    @staticmethod
    def get_valid_access_token(connection: GoogleCalendarConnection, db: Session) -> str:
        """Returns valid decrypted access token, refreshing before expiry if necessary."""
        if not connection or connection.status != "CONNECTED":
            return ""
        now = datetime.now(timezone.utc)
        expiry = connection.token_expiry
        if expiry:
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= now + timedelta(minutes=5):
                return GoogleCalendarService.refresh_access_token(connection, db)
        return decrypt_token(connection.access_token) or ""

    @staticmethod
    def fetch_user_info(access_token: str) -> Dict[str, Any]:
        """Fetches Google account user info profile securely."""
        url = "https://www.googleapis.com/oauth2/v2/userinfo"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except Exception as e:
            logger.warning(f"[Google OAuth] Could not fetch Google user info: {e}")
            return {}

    @staticmethod
    def fetch_user_email(access_token: str) -> Optional[str]:
        """Fetches Google account email using userinfo endpoint."""
        info = GoogleCalendarService.fetch_user_info(access_token)
        return info.get("email")

    @staticmethod
    def verify_calendar_access(access_token: str, calendar_id: str = "primary") -> bool:
        """Verifies that the provided access token has valid access to the Google Calendar API."""
        url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"[Google OAuth] Calendar verification failed: {e}")
            return False

    @staticmethod
    def parse_datetime_safe(val: Any) -> Optional[datetime]:
        """Safely parses various date/datetime inputs into timezone-aware UTC datetime."""
        if val is None:
            return None
        if isinstance(val, datetime):
            if val.tzinfo is None:
                return val.replace(tzinfo=timezone.utc)
            return val.astimezone(timezone.utc)
        if isinstance(val, date):
            return datetime.combine(val, time.min, tzinfo=timezone.utc)

        s = str(val).strip()
        if not s:
            return None

        # Try ISO format
        try:
            cleaned = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

        # Try YYYY-MM-DD
        try:
            d = datetime.strptime(s[:10], "%Y-%m-%d").date()
            return datetime.combine(d, time.min, tzinfo=timezone.utc)
        except Exception:
            pass

        return None

    @staticmethod
    def build_google_event_timing(
        start_val: Any,
        end_val: Optional[Any] = None,
        duration_minutes: int = 60,
        default_time: Optional[str] = None
    ) -> Tuple[Dict[str, str], Dict[str, str], bool]:
        """
        Converts task/meeting dates into valid Google Calendar API start and end timing dictionaries.
        Guarantees:
        - Timed events have valid RFC 3339 dateTime with start < end.
        - All-day events have YYYY-MM-DD date with end date strictly > start date (Google Calendar API requirement).
        """
        start_str = str(start_val).strip() if start_val is not None else ""
        has_time_component = ("T" in start_str) or (default_time is not None and ":" in default_time)

        if not has_time_component and start_val is not None:
            # All-day event
            start_date_obj = None
            if isinstance(start_val, (date, datetime)):
                start_date_obj = start_val.date() if isinstance(start_val, datetime) else start_val
            else:
                try:
                    start_date_obj = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
                except Exception:
                    start_date_obj = datetime.now(timezone.utc).date()

            end_date_obj = None
            if end_val is not None:
                if isinstance(end_val, (date, datetime)):
                    end_date_obj = end_val.date() if isinstance(end_val, datetime) else end_val
                else:
                    try:
                        end_date_obj = datetime.strptime(str(end_val)[:10], "%Y-%m-%d").date()
                    except Exception:
                        end_date_obj = None

            # Google Calendar rule: all-day end date is exclusive, so must be at least start + 1 day
            if end_date_obj is None or end_date_obj <= start_date_obj:
                end_date_obj = start_date_obj + timedelta(days=1)
            else:
                end_date_obj = end_date_obj + timedelta(days=1)

            return (
                {"date": start_date_obj.strftime("%Y-%m-%d")},
                {"date": end_date_obj.strftime("%Y-%m-%d")},
                True
            )

        # Timed event
        start_dt = None
        d_part = start_str[:10] if len(start_str) >= 10 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if default_time and ":" in default_time and "T" not in start_str:
            t_part = default_time.strip()
            if "pm" in t_part.lower() or "am" in t_part.lower():
                try:
                    clean_t = re.sub(r"\s+", " ", t_part.strip().upper())
                    t_obj = datetime.strptime(clean_t, "%I:%M %p").time()
                    t_part = t_obj.strftime("%H:%M:%S")
                except Exception:
                    t_part = "10:00:00"
            elif len(t_part.split(":")) == 2:
                t_part = f"{t_part}:00"
            try:
                start_dt = datetime.fromisoformat(f"{d_part}T{t_part}").replace(tzinfo=timezone.utc)
            except Exception:
                start_dt = None

        if start_dt is None:
            start_dt = GoogleCalendarService.parse_datetime_safe(start_val)
        if start_dt is None:
            start_dt = datetime.now(timezone.utc)

        end_dt = GoogleCalendarService.parse_datetime_safe(end_val) if end_val else None
        if end_dt is None or end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=duration_minutes or 60)

        return (
            {"dateTime": start_dt.isoformat()},
            {"dateTime": end_dt.isoformat()},
            False
        )

    @staticmethod
    def push_sd_event_to_google(
        db: Session,
        connection: GoogleCalendarConnection,
        entity_type: str,
        entity_id: int,
        title: str,
        description: Optional[str],
        start_time_iso: Any,
        end_time_iso: Optional[Any] = None,
        duration_minutes: int = 60,
        default_time: Optional[str] = None
    ) -> Optional[str]:
        """Pushes a Studio Desire task or meeting to Google Calendar API with duplicate prevention and update support."""
        if not connection or connection.status != "CONNECTED":
            logger.warning("[Google Calendar] Push skipped: connection is not connected.")
            return None

        token = GoogleCalendarService.get_valid_access_token(connection, db)
        if not token:
            logger.warning("[Google Calendar] Push failed: unable to obtain valid access token.")
            return None

        calendar_id = connection.calendar_id or "primary"

        start_timing, end_timing, _ = GoogleCalendarService.build_google_event_timing(
            start_time_iso, end_time_iso, duration_minutes=duration_minutes, default_time=default_time
        )

        sync_item = db.query(CalendarSyncItem).filter(
            CalendarSyncItem.owner_user_id == connection.owner_user_id,
            CalendarSyncItem.entity_type == entity_type,
            CalendarSyncItem.entity_id == entity_id
        ).first()

        event_body = {
            "summary": f"[Studio Desire] {title.strip()}",
            "description": description or f"Studio Desire {entity_type.capitalize()}",
            "start": start_timing,
            "end": end_timing,
            "extendedProperties": {
                "private": {
                    "studio_desire_source": "studio_desire",
                    "studio_desire_entity_type": entity_type,
                    "studio_desire_entity_id": str(entity_id),
                    "studio_desire_owner_user_id": str(connection.owner_user_id)
                }
            }
        }
        json_data = json.dumps(event_body).encode("utf-8")

        # If sync item exists with google_event_id, update it via PUT
        if sync_item and sync_item.google_event_id:
            url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(sync_item.google_event_id)}"
            req = urllib.request.Request(
                url,
                data=json_data,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="PUT"
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_json = json.loads(resp.read().decode("utf-8"))
                    sync_item.last_synced_at = datetime.now(timezone.utc)
                    sync_item.google_etag = resp_json.get("etag")
                    db.commit()
                    return sync_item.google_event_id
            except urllib.error.HTTPError as he:
                if he.code == 404:
                    # Event was removed on Google; recreate below
                    sync_item = None
                else:
                    db.rollback()
                    logger.error(f"[Google Calendar] Error updating event #{sync_item.google_event_id}: HTTP {he.code}")
                    return None
            except Exception as e:
                db.rollback()
                logger.error(f"[Google Calendar] Error updating event: {e}")
                return None

        # Insert new event via POST
        url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events"
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                g_event_id = resp_json.get("id")
                if g_event_id:
                    sync_item = db.query(CalendarSyncItem).filter(
                        CalendarSyncItem.owner_user_id == connection.owner_user_id,
                        CalendarSyncItem.entity_type == entity_type,
                        CalendarSyncItem.entity_id == entity_id
                    ).first()
                    if not sync_item:
                        sync_item = CalendarSyncItem(
                            owner_user_id=connection.owner_user_id,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            google_calendar_id=calendar_id,
                            google_event_id=g_event_id,
                            google_etag=resp_json.get("etag"),
                            last_synced_at=datetime.now(timezone.utc)
                        )
                        db.add(sync_item)
                    else:
                        sync_item.google_event_id = g_event_id
                        sync_item.google_etag = resp_json.get("etag")
                        sync_item.last_synced_at = datetime.now(timezone.utc)
                    db.commit()
                    return g_event_id
                return None
        except Exception as e:
            db.rollback()
            logger.error(f"[Google Calendar] Error creating event: {e}")
            return None

    @staticmethod
    def fetch_google_events(
        connection: GoogleCalendarConnection,
        db: Session,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetches events directly from owner's Google Calendar API with pagination."""
        if not connection or connection.status != "CONNECTED":
            return []

        token = GoogleCalendarService.get_valid_access_token(connection, db)
        if not token:
            return []

        calendar_id = connection.calendar_id or "primary"
        now = datetime.now(timezone.utc)
        if not time_min:
            time_min = (now - timedelta(days=60)).isoformat().replace("+00:00", "Z")
        if not time_max:
            time_max = (now + timedelta(days=90)).isoformat().replace("+00:00", "Z")

        all_events: List[Dict[str, Any]] = []
        page_token: Optional[str] = None
        pages_fetched = 0
        max_pages = 5

        while pages_fetched < max_pages:
            pages_fetched += 1
            query_params = {
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime",
                "maxResults": 100
            }
            if page_token:
                query_params["pageToken"] = page_token

            url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events?" + urllib.parse.urlencode(query_params)
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    items = data.get("items", [])
                    for item in items:
                        if item.get("status") != "cancelled":
                            all_events.append(item)
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
            except Exception as e:
                logger.error(f"[Google Calendar] Failed fetching events page {pages_fetched}: {e}")
                break

        return all_events

    @staticmethod
    def get_merged_calendar_items(db: Session, current_user: User) -> List[Dict[str, Any]]:
        """Combines Studio Desire Tasks, Meetings, and Google Calendar events into one unified view with user authorization."""
        items: List[Dict[str, Any]] = []

        # 1. Fetch Studio Desire Tasks strictly applying user visibility filter
        from app.api.admin_tasks import apply_task_visibility_filter
        task_query = db.query(Task).filter(or_(Task.start_date.isnot(None), Task.due_date.isnot(None)))
        visible_tasks = apply_task_visibility_filter(task_query, current_user, db).all()

        for t in visible_tasks:
            start_val = t.start_date or t.due_date
            end_val = t.due_date or t.start_date
            start_iso = start_val.isoformat() if isinstance(start_val, datetime) else str(start_val) if start_val else datetime.now(timezone.utc).isoformat()
            end_iso = end_val.isoformat() if isinstance(end_val, datetime) else str(end_val) if end_val else start_iso

            items.append({
                "id": f"task_{t.id}",
                "title": t.title,
                "description": t.description,
                "start_time": start_iso,
                "end_time": end_iso,
                "all_day": True if "T" not in start_iso else False,
                "source_type": "SD_TASK",
                "entity_id": t.id,
                "project_id": t.project_id,
                "project_title": t.project.title if t.project else "Studio Task",
                "assignee_name": t.assigned_to,
                "status": t.status,
                "priority": t.priority,
                "synced_to_google": False
            })

        # 2. Fetch Studio Desire Meetings
        meetings = db.query(Meeting).all()
        for m in meetings:
            date_str = m.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            time_str = m.time or "10:00"
            try:
                start_timing, end_timing, _ = GoogleCalendarService.build_google_event_timing(
                    date_str, duration_minutes=60, default_time=time_str
                )
                start_iso = start_timing.get("dateTime") or start_timing.get("date") or f"{date_str}T{time_str}:00"
                end_iso = end_timing.get("dateTime") or end_timing.get("date") or start_iso
            except Exception:
                start_iso = f"{date_str}T10:00:00"
                end_iso = f"{date_str}T11:00:00"

            items.append({
                "id": f"meeting_{m.id}",
                "title": m.title,
                "description": getattr(m, "notes", "") or "",
                "start_time": start_iso,
                "end_time": end_iso,
                "all_day": False,
                "source_type": "SD_MEETING",
                "entity_id": m.id,
                "project_id": m.project_id,
                "project_title": m.project.title if m.project else "Studio Meeting",
                "status": m.status,
                "location": m.location,
                "synced_to_google": False
            })

        # 3. Check Google Connection & Fetch Google Events for CURRENT USER ONLY
        connection = db.query(GoogleCalendarConnection).filter(
            GoogleCalendarConnection.owner_user_id == current_user.id
        ).first()

        if connection and connection.status == "CONNECTED":
            sync_map = {
                (si.entity_type, si.entity_id): si
                for si in db.query(CalendarSyncItem).filter(CalendarSyncItem.owner_user_id == current_user.id).all()
            }
            for item in items:
                ent_type = "task" if item["source_type"] == "SD_TASK" else "meeting"
                if (ent_type, item["entity_id"]) in sync_map:
                    item["synced_to_google"] = True
                    item["google_event_id"] = sync_map[(ent_type, item["entity_id"])].google_event_id

            g_events = GoogleCalendarService.fetch_google_events(connection, db)
            for ge in g_events:
                ext_props = ge.get("extendedProperties", {}).get("private", {})
                if ext_props.get("studio_desire_source") == "studio_desire":
                    continue

                start_obj = ge.get("start", {})
                end_obj = ge.get("end", {})
                start_str = start_obj.get("dateTime") or start_obj.get("date") or datetime.now(timezone.utc).isoformat()
                end_str = end_obj.get("dateTime") or end_obj.get("date") or start_str
                is_all_day = "date" in start_obj and "dateTime" not in start_obj

                items.append({
                    "id": f"google_{ge.get('id')}",
                    "title": ge.get("summary", "External Google Event"),
                    "description": ge.get("description"),
                    "start_time": start_str,
                    "end_time": end_str,
                    "all_day": is_all_day,
                    "source_type": "GOOGLE_EVENT",
                    "location": ge.get("location"),
                    "html_link": ge.get("htmlLink"),
                    "google_event_id": ge.get("id"),
                    "synced_to_google": True
                })

        return items

    @staticmethod
    def sync_calendar(db: Session, current_user: User) -> Dict[str, Any]:
        """
        Executes honest synchronization for the current user:
        1. Checks connection. If disconnected, raises GoogleCalendarError.
        2. Pushes user-authorized tasks with dates.
        3. Pushes meetings.
        4. Fetches Google events.
        5. Tracks attempted, success, failed, and updates last_synced_at only if valid.
        """
        conn = db.query(GoogleCalendarConnection).filter(
            GoogleCalendarConnection.owner_user_id == current_user.id
        ).first()

        if not conn or conn.status != "CONNECTED":
            raise GoogleCalendarError("Google Calendar is not connected.", error_code="disconnected", status_code=400)

        from app.api.admin_tasks import apply_task_visibility_filter
        task_query = db.query(Task).filter(or_(Task.start_date.isnot(None), Task.due_date.isnot(None)))
        tasks = apply_task_visibility_filter(task_query, current_user, db).all()

        pushed_success = 0
        pushed_failed = 0
        errors: List[str] = []

        for t in tasks:
            start_date_val = t.start_date or t.due_date
            try:
                g_id = GoogleCalendarService.push_sd_event_to_google(
                    db, conn, "task", t.id, t.title, t.description, start_date_val, t.due_date
                )
                if g_id:
                    pushed_success += 1
                else:
                    pushed_failed += 1
                    errors.append(f"Failed to push task #{t.id} '{t.title}'")
            except Exception as err:
                pushed_failed += 1
                errors.append(f"Task #{t.id} push error: {str(err)}")

        meetings = db.query(Meeting).all()
        for m in meetings:
            date_str = m.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            time_str = m.time or "10:00"
            try:
                g_id = GoogleCalendarService.push_sd_event_to_google(
                    db, conn, "meeting", m.id, m.title, m.notes or "", date_str, duration_minutes=60, default_time=time_str
                )
                if g_id:
                    pushed_success += 1
                else:
                    pushed_failed += 1
                    errors.append(f"Failed to push meeting #{m.id} '{m.title}'")
            except Exception as err:
                pushed_failed += 1
                errors.append(f"Meeting #{m.id} push error: {str(err)}")

        # Fetch Google events
        g_events = GoogleCalendarService.fetch_google_events(conn, db)
        pulled_count = len(g_events)

        if pushed_failed == 0:
            conn.last_synced_at = datetime.now(timezone.utc)
            db.commit()
            sync_status = "COMPLETED"
            success = True
            msg = f"Sync completed successfully. Pushed {pushed_success} items, fetched {pulled_count} Google events."
        elif pushed_success > 0:
            conn.last_synced_at = datetime.now(timezone.utc)
            db.commit()
            sync_status = "PARTIAL"
            success = False
            msg = f"Partial sync: {pushed_success} pushed, {pushed_failed} failed, {pulled_count} Google events fetched."
        else:
            sync_status = "FAILED"
            success = False
            msg = f"Sync failed: could not push any items to Google Calendar. Errors: {'; '.join(errors[:3])}"

        return {
            "success": success,
            "status": sync_status,
            "pushed_to_google": pushed_success,
            "pulled_from_google": pulled_count,
            "failed_pushes": pushed_failed,
            "last_synced_at": conn.last_synced_at,
            "message": msg,
            "errors": errors
        }
