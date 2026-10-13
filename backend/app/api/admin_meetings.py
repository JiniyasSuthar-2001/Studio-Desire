from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.meeting import Meeting
    from app.models.project import Project
    from app.models.client import Client
    from app.models.user import User
    from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingOut
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.meeting import Meeting
    from backend.app.models.project import Project
    from backend.app.models.client import Client
    from backend.app.models.user import User
    from backend.app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingOut
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/meetings", tags=["Admin Meetings"])


@router.get("", response_model=List[MeetingOut], summary="List meetings (all or filtered by project/client)")
def list_meetings(
    project_id: Optional[int] = None,
    client_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Meeting)
    if project_id:
        query = query.filter(Meeting.project_id == project_id)
    if client_id:
        query = query.filter(Meeting.client_id == client_id)
    if status:
        query = query.filter(Meeting.status == status.upper())

    meetings = query.order_by(Meeting.date.desc(), Meeting.time.asc().nullslast()).all()
    results = []
    for m in meetings:
        p_title = m.project.title if m.project else None
        c_name = m.client.name if m.client else None
        results.append(
            MeetingOut(
                id=m.id,
                project_id=m.project_id,
                client_id=m.client_id,
                project_title=p_title,
                client_name=c_name,
                title=m.title,
                date=m.date,
                time=m.time,
                location=m.location,
                meeting_type=m.meeting_type or "Client Consultation",
                notes=m.notes,
                participants=m.participants,
                status=m.status or "SCHEDULED",
                created_at=m.created_at,
                updated_at=m.updated_at
            )
        )
    return results


@router.post("", response_model=MeetingOut, summary="Schedule a new meeting")
def create_meeting(
    payload: MeetingCreate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    meeting = Meeting(
        project_id=payload.project_id,
        client_id=payload.client_id,
        title=payload.title.strip(),
        date=payload.date.strip(),
        time=payload.time.strip() if payload.time else None,
        location=payload.location.strip() if payload.location else "Studio Desire HQ",
        meeting_type=payload.meeting_type.strip(),
        notes=payload.notes.strip() if payload.notes else None,
        participants=payload.participants.strip() if payload.participants else None,
        status=payload.status.upper()
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    log_activity(db, current_user, action="Scheduled Meeting", entity_type="meeting", entity_id=str(meeting.id), details=f"Meeting '{meeting.title}' on {meeting.date}")

    p_title = meeting.project.title if meeting.project else None
    c_name = meeting.client.name if meeting.client else None

    return MeetingOut(
        id=meeting.id,
        project_id=meeting.project_id,
        client_id=meeting.client_id,
        project_title=p_title,
        client_name=c_name,
        title=meeting.title,
        date=meeting.date,
        time=meeting.time,
        location=meeting.location,
        meeting_type=meeting.meeting_type,
        notes=meeting.notes,
        participants=meeting.participants,
        status=meeting.status,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at
    )


@router.put("/{meeting_id}", response_model=MeetingOut, summary="Update meeting details")
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdate,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "DESIGNER", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and isinstance(value, str):
            value = value.upper()
        setattr(meeting, key, value)

    db.commit()
    db.refresh(meeting)

    log_activity(db, current_user, action="Updated Meeting", entity_type="meeting", entity_id=str(meeting.id), details=f"Meeting '{meeting.title}' updated (Status: {meeting.status})")

    p_title = meeting.project.title if meeting.project else None
    c_name = meeting.client.name if meeting.client else None

    return MeetingOut(
        id=meeting.id,
        project_id=meeting.project_id,
        client_id=meeting.client_id,
        project_title=p_title,
        client_name=c_name,
        title=meeting.title,
        date=meeting.date,
        time=meeting.time,
        location=meeting.location,
        meeting_type=meeting.meeting_type,
        notes=meeting.notes,
        participants=meeting.participants,
        status=meeting.status,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at
    )


@router.delete("/{meeting_id}", summary="Delete meeting")
def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(require_roles(["OWNER", "MASTER", "ADMIN", "PROJECT_MANAGER"])),
    db: Session = Depends(get_db)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    title = meeting.title
    db.delete(meeting)
    db.commit()

    log_activity(db, current_user, action="Cancelled/Deleted Meeting", entity_type="meeting", entity_id=str(meeting_id), details=f"Deleted meeting '{title}'")

    return {"success": True, "message": f"Meeting '{title}' deleted."}
