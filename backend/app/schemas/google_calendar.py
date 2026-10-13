from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class GoogleCalendarStatusOut(BaseModel):
    connected: bool
    status: str  # "CONNECTED", "DISCONNECTED", "EXPIRED", "NOT_CONFIGURED"
    google_account_email: Optional[str] = None
    calendar_id: Optional[str] = "primary"
    last_synced_at: Optional[datetime] = None
    client_id_configured: bool = False


class GoogleCalendarOAuthStartOut(BaseModel):
    auth_url: str
    authorization_url: str
    state: str


class GoogleCalendarEventItem(BaseModel):
    id: str  # Event ID or internal task/meeting ID string
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    all_day: bool = False
    source_type: str  # "SD_TASK", "SD_MEETING", "GOOGLE_EVENT"
    entity_id: Optional[int] = None
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    assignee_name: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    location: Optional[str] = None
    html_link: Optional[str] = None
    google_event_id: Optional[str] = None
    synced_to_google: bool = False


class GoogleCalendarSyncResponse(BaseModel):
    success: bool
    pushed_to_google: int
    pulled_from_google: int
    last_synced_at: datetime
    message: str
