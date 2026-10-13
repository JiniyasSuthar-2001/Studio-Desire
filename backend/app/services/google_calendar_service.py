import json
import urllib.parse
import urllib.request
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem
from app.models.task import Task, TaskAssignment
from app.models.meeting import Meeting
from app.models.user import User

logger = logging.getLogger("studio_desire.google_calendar")


class GoogleCalendarService:
    @staticmethod
    def get_oauth_start_url(owner_user: User) -> Dict[str, str]:
        """Generates Google OAuth 2.0 authorization URL with state parameter."""
        client_id = settings.GOOGLE_CALENDAR_CLIENT_ID or "DEMO_GOOGLE_CLIENT_ID"
        redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI
        scopes = settings.GOOGLE_CALENDAR_SCOPES

        state = f"user_{owner_user.id}_{int(datetime.utcnow().timestamp())}"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state
        }
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return {"auth_url": auth_url, "authorization_url": auth_url, "state": state}

    @staticmethod
    def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
        """Exchanges OAuth authorization code for access and refresh tokens."""
        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "code": code,
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_CALENDAR_REDIRECT_URI,
            "grant_type": "authorization_code"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data
        except Exception as e:
            logger.error(f"Google OAuth code exchange failed: {e}")
            raise Exception(f"Failed to exchange authorization code with Google: {str(e)}")

    @staticmethod
    def refresh_access_token(connection: GoogleCalendarConnection, db: Session) -> str:
        """Refreshes access token using refresh_token if expired."""
        if not connection.refresh_token:
            raise Exception("No refresh token available. Connection requires reauthorization.")

        token_url = "https://oauth2.googleapis.com/token"
        payload = urllib.parse.urlencode({
            "client_id": settings.GOOGLE_CALENDAR_CLIENT_ID,
            "client_secret": settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            "refresh_token": connection.refresh_token,
            "grant_type": "refresh_token"
        }).encode("utf-8")

        req = urllib.request.Request(token_url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                connection.access_token = res_data.get("access_token")
                expires_in = res_data.get("expires_in", 3600)
                connection.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                db.commit()
                return connection.access_token
        except Exception as e:
            connection.status = "EXPIRED"
            db.commit()
            raise Exception(f"Failed to refresh Google Calendar token: {str(e)}")

    @staticmethod
    def get_valid_access_token(connection: GoogleCalendarConnection, db: Session) -> str:
        """Returns valid access token, refreshing if necessary."""
        if connection.token_expiry and connection.token_expiry <= datetime.utcnow() + timedelta(minutes=5):
            return GoogleCalendarService.refresh_access_token(connection, db)
        return connection.access_token or ""

    @staticmethod
    def fetch_user_email(access_token: str) -> Optional[str]:
        """Fetches Google account email using userinfo endpoint."""
        url = "https://www.googleapis.com/oauth2/v2/userinfo"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("email")
        except Exception:
            return None

    @staticmethod
    def push_sd_event_to_google(
        db: Session,
        connection: GoogleCalendarConnection,
        entity_type: str,
        entity_id: int,
        title: str,
        description: Optional[str],
        start_time_iso: str,
        end_time_iso: Optional[str] = None
    ) -> Optional[str]:
        """Pushes a Studio Desire task or meeting to Google Calendar API."""
        if not connection or connection.status != "CONNECTED" or not connection.access_token:
            return None

        token = GoogleCalendarService.get_valid_access_token(connection, db)
        calendar_id = connection.calendar_id or "primary"

        if isinstance(start_time_iso, datetime):
            start_time_iso = start_time_iso.isoformat()
        if isinstance(end_time_iso, datetime):
            end_time_iso = end_time_iso.isoformat()

        # Check existing sync item
        sync_item = db.query(CalendarSyncItem).filter(
            CalendarSyncItem.owner_user_id == connection.owner_user_id,
            CalendarSyncItem.entity_type == entity_type,
            CalendarSyncItem.entity_id == entity_id
        ).first()

        # Build start and end datetime
        if not end_time_iso:
            try:
                dt_start = datetime.fromisoformat(start_time_iso.replace("Z", "+00:00"))
                end_time_iso = (dt_start + timedelta(hours=1)).isoformat()
            except Exception:
                end_time_iso = start_time_iso

        event_body = {
            "summary": f"[Studio Desire] {title}",
            "description": description or f"Studio Desire {entity_type.capitalize()}",
            "start": {"dateTime": start_time_iso} if "T" in start_time_iso else {"date": start_time_iso},
            "end": {"dateTime": end_time_iso} if "T" in end_time_iso else {"date": end_time_iso},
            "extendedProperties": {
                "private": {
                    "studio_desire_source": "studio_desire",
                    "studio_desire_entity_type": entity_type,
                    "studio_desire_entity_id": str(entity_id)
                }
            }
        }

        json_data = json.dumps(event_body).encode("utf-8")

        if sync_item and sync_item.google_event_id:
            # Update event
            url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events/{urllib.parse.quote(sync_item.google_event_id)}"
            req = urllib.request.Request(url, data=json_data, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }, method="PUT")
        else:
            # Insert event
            url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events"
            req = urllib.request.Request(url, data=json_data, headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                g_event_id = resp_json.get("id")

                if not sync_item and g_event_id:
                    sync_item = CalendarSyncItem(
                        owner_user_id=connection.owner_user_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        google_calendar_id=calendar_id,
                        google_event_id=g_event_id,
                        last_synced_at=datetime.utcnow()
                    )
                    db.add(sync_item)
                elif sync_item:
                    sync_item.last_synced_at = datetime.utcnow()

                db.commit()
                return g_event_id
        except Exception as e:
            logger.error(f"Error pushing event to Google Calendar: {e}")
            return None

    @staticmethod
    def fetch_google_events(connection: GoogleCalendarConnection, db: Session) -> List[Dict[str, Any]]:
        """Fetches events directly from owner's Google Calendar API."""
        if not connection or connection.status != "CONNECTED" or not connection.access_token:
            return []

        try:
            token = GoogleCalendarService.get_valid_access_token(connection, db)
            calendar_id = connection.calendar_id or "primary"
            now = datetime.utcnow()
            time_min = (now - timedelta(days=60)).isoformat() + "Z"
            time_max = (now + timedelta(days=90)).isoformat() + "Z"

            url = f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(calendar_id)}/events?" + urllib.parse.urlencode({
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": "true",
                "orderBy": "startTime"
            })

            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("items", [])
        except Exception as e:
            logger.error(f"Failed to fetch Google Calendar events: {e}")
            return []

    @staticmethod
    def get_merged_calendar_items(db: Session, current_user: User) -> List[Dict[str, Any]]:
        """Combines Studio Desire Tasks, Meetings, and Google Calendar events into one unified view."""
        items: List[Dict[str, Any]] = []

        # 1. Fetch Studio Desire Tasks with due/start dates
        tasks = db.query(Task).filter(
            or_(Task.start_date.isnot(None), Task.due_date.isnot(None))
        ).all()

        for t in tasks:
            start_val = t.start_date or t.due_date
            end_val = t.due_date or t.start_date
            
            start_iso = start_val.isoformat() if isinstance(start_val, datetime) else str(start_val) if start_val else datetime.utcnow().isoformat()
            end_iso = end_val.isoformat() if isinstance(end_val, datetime) else str(end_val) if end_val else datetime.utcnow().isoformat()

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
            date_str = m.date or datetime.utcnow().strftime("%Y-%m-%d")
            time_str = m.time or "10:00"
            start_iso = f"{date_str}T{time_str}:00"
            try:
                dt_start = datetime.fromisoformat(start_iso)
                end_iso = (dt_start + timedelta(minutes=m.duration_minutes or 60)).isoformat()
            except Exception:
                end_iso = start_iso

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
                "location": m.location or m.meeting_link,
                "synced_to_google": False
            })

        # 3. Check Google Connection & Fetch Google Events
        connection = db.query(GoogleCalendarConnection).filter(
            GoogleCalendarConnection.owner_user_id == current_user.id
        ).first()

        if connection and connection.status == "CONNECTED":
            # Map sync items
            sync_map = {
                (si.entity_type, si.entity_id): si
                for si in db.query(CalendarSyncItem).filter(CalendarSyncItem.owner_user_id == current_user.id).all()
            }
            # Mark SD items synced
            for item in items:
                ent_type = "task" if item["source_type"] == "SD_TASK" else "meeting"
                if (ent_type, item["entity_id"]) in sync_map:
                    item["synced_to_google"] = True
                    item["google_event_id"] = sync_map[(ent_type, item["entity_id"])].google_event_id

            g_events = GoogleCalendarService.fetch_google_events(connection, db)
            for ge in g_events:
                ext_props = ge.get("extendedProperties", {}).get("private", {})
                if ext_props.get("studio_desire_source") == "studio_desire":
                    # Skip since already included from internal SD model
                    continue

                start_obj = ge.get("start", {})
                end_obj = ge.get("end", {})
                start_str = start_obj.get("dateTime") or start_obj.get("date") or datetime.utcnow().isoformat()
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
