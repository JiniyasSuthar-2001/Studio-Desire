from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.session import Base


class GoogleCalendarConnection(Base):
    __tablename__ = "google_calendar_connections"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    google_account_email = Column(String(255), nullable=True)
    google_user_id = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(String(500), nullable=True)
    calendar_id = Column(String(255), default="primary")
    sync_token = Column(String(500), nullable=True)
    status = Column(String(50), default="CONNECTED")  # CONNECTED, EXPIRED, DISCONNECTED
    connected_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)

    owner_user = relationship("User", backref="google_calendar_connection")


class CalendarSyncItem(Base):
    __tablename__ = "calendar_sync_items"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    entity_type = Column(String(50), nullable=False)  # "task" or "meeting"
    entity_id = Column(Integer, nullable=False, index=True)
    google_calendar_id = Column(String(255), default="primary")
    google_event_id = Column(String(255), unique=True, index=True, nullable=False)
    google_etag = Column(String(255), nullable=True)
    last_synced_at = Column(DateTime, default=datetime.utcnow)
    sync_direction = Column(String(50), default="TWO_WAY")
    sync_status = Column(String(50), default="SYNCED")

    owner_user = relationship("User", backref="calendar_sync_items")
