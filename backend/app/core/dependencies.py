from typing import List, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

try:
    from app.database.session import get_db
    from app.core.security import decode_access_token
    from app.models.user import User, UserRole
    from app.models.activity import ActivityLog
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.core.security import decode_access_token
    from backend.app.models.user import User, UserRole
    from backend.app.models.activity import ActivityLog

security_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates JWT token and fetches active user from database.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_access_token(auth.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub") or payload.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    
    return user


def require_roles(allowed_roles: List[str]):
    """
    Dependency factory that checks if the authenticated user has one of the allowed roles.
    MASTER always has access to all authorized endpoints.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").upper()
        # MASTER and OWNER have universal executive clearance across all administrative functions
        if user_role in (UserRole.MASTER.value, UserRole.OWNER.value):
            return current_user

        normalized_allowed = [r.upper() for r in allowed_roles]
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles: {', '.join(allowed_roles)} (current role: {user_role})",
            )
        return current_user

    return role_checker


def log_activity(
    db: Session,
    user: User,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[str] = None,
):
    """
    Audit log helper to track owner actions.
    """
    try:
        log_entry = ActivityLog(
            user_id=user.id,
            username=user.username,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AUDIT LOG ERROR] Failed to record activity: {e}")
