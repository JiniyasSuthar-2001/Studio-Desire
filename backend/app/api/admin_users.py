from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.user import User, UserRole
    from app.schemas.admin import UserCreate, UserUpdate, UserResetPassword
    from app.schemas.auth import UserProfileOut
    from app.core.security import hash_password
    from app.core.dependencies import get_current_user, require_roles, log_activity
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.admin import UserCreate, UserUpdate, UserResetPassword
    from backend.app.schemas.auth import UserProfileOut
    from backend.app.core.security import hash_password
    from backend.app.core.dependencies import get_current_user, require_roles, log_activity

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])


@router.get("", response_model=List[UserProfileOut], summary="List all studio team users")
def list_users(
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserProfileOut, summary="Create a new authorized team user")
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    target_role = payload.role.upper()
    valid_roles = [r.value for r in UserRole]
    if target_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Must be one of: {', '.join(valid_roles)}"
        )

    # Constraint: Only MASTER or OWNER can create another MASTER or OWNER
    is_executive = current_user.role.upper() in (UserRole.MASTER.value, UserRole.OWNER.value)
    if target_role in (UserRole.MASTER.value, UserRole.OWNER.value) and not is_executive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Master Administrator or Owner can create Master/Owner accounts."
        )

    clean_username = payload.username.strip()
    existing = db.query(User).filter(func.lower(User.username) == clean_username.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{clean_username}' is already registered."
        )

    new_user = User(
        username=clean_username,
        email=payload.email.strip() if payload.email else None,
        hashed_password=hash_password(payload.password),
        role=target_role,
        is_active=True,
        must_change_password=True  # Require change on first login
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_activity(db, current_user, action="Created User", entity_type="user", entity_id=str(new_user.id), details=f"Created user '{new_user.username}' with role '{new_user.role}'")

    return new_user


@router.patch("/{user_id}", response_model=UserProfileOut, summary="Update user role or active status")
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    is_executive = current_user.role.upper() in (UserRole.MASTER.value, UserRole.OWNER.value)
    target_is_executive = target_user.role.upper() in (UserRole.MASTER.value, UserRole.OWNER.value)

    # Protection: Non-executive cannot modify an executive (Master/Owner) user
    if target_is_executive and not is_executive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Master Administrator or Owner can modify Master/Owner accounts."
        )

    if payload.role:
        role_upper = payload.role.upper()
        if role_upper in (UserRole.MASTER.value, UserRole.OWNER.value) and not is_executive:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the Master Administrator or Owner can elevate users to Master/Owner role."
            )
        target_user.role = role_upper

    if payload.is_active is not None:
        if target_user.id == current_user.id and not payload.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own active session account."
            )
        target_user.is_active = payload.is_active

    if payload.email is not None:
        target_user.email = payload.email.strip() if payload.email else None

    db.commit()
    db.refresh(target_user)

    log_activity(db, current_user, action="Updated User", entity_type="user", entity_id=str(target_user.id), details=f"Updated settings for '{target_user.username}'")

    return target_user


@router.post("/{user_id}/reset-password", summary="Reset a user's password")
def reset_user_password(
    user_id: int,
    payload: UserResetPassword,
    current_user: User = Depends(require_roles(["MASTER", "OWNER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    is_executive = current_user.role.upper() in (UserRole.MASTER.value, UserRole.OWNER.value)
    target_is_executive = target_user.role.upper() in (UserRole.MASTER.value, UserRole.OWNER.value)

    if target_is_executive and not is_executive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Master Administrator or Owner can reset passwords for Master/Owner accounts."
        )

    target_user.hashed_password = hash_password(payload.new_password)
    target_user.must_change_password = True
    db.commit()

    log_activity(db, current_user, action="Reset User Password", entity_type="user", entity_id=str(target_user.id), details=f"Reset password for '{target_user.username}'")

    return {"success": True, "message": f"Password reset for '{target_user.username}'. First-time change flag set."}


@router.delete("/{user_id}", summary="Delete an authorized user account")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles(["MASTER", "OWNER"])),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own active session user account."
        )

    # Safeguard: prevent deleting the last active Master
    if target_user.role.upper() == UserRole.MASTER.value:
        active_masters = db.query(User).filter(
            User.role == UserRole.MASTER.value,
            User.is_active == True,
            User.id != target_user.id
        ).count()
        if active_masters == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the sole active Master Administrator account."
            )

    username = target_user.username

    # Clean up user associations
    try:
        from app.models.task import TaskAssignment
        db.query(TaskAssignment).filter(TaskAssignment.user_id == user_id).delete(synchronize_session=False)
    except Exception:
        pass

    try:
        from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem
        db.query(CalendarSyncItem).filter(CalendarSyncItem.owner_user_id == user_id).delete(synchronize_session=False)
        db.query(GoogleCalendarConnection).filter(GoogleCalendarConnection.owner_user_id == user_id).delete(synchronize_session=False)
    except Exception:
        pass

    db.delete(target_user)
    db.commit()

    log_activity(db, current_user, action="Deleted User", entity_type="user", entity_id=str(user_id), details=f"Permanently deleted user '{username}'")

    return {"success": True, "message": f"User '{username}' successfully deleted."}
