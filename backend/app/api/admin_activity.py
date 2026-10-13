from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

try:
    from app.database.session import get_db
    from app.models.activity import ActivityLog
    from app.models.user import User
    from app.schemas.admin import ActivityLogOut
    from app.core.dependencies import get_current_user
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.activity import ActivityLog
    from backend.app.models.user import User
    from backend.app.schemas.admin import ActivityLogOut
    from backend.app.core.dependencies import get_current_user

router = APIRouter(prefix="/admin/activity", tags=["Admin Activity Log"])


@router.get("", response_model=List[ActivityLogOut], summary="List chronological studio activity logs")
def get_activity_logs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(ActivityLog).order_by(ActivityLog.id.desc()).limit(limit).all()
    return logs
