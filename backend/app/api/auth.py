from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.user import User, UserRole
    from app.schemas.auth import (
        LoginRequest,
        TokenResponse,
        UserProfileOut,
        ChangePasswordRequest,
        UpdateProfileRequest
    )
    from app.core.security import verify_password, hash_password, create_access_token
    from app.core.dependencies import get_current_user, log_activity
    from app.core.rate_limiter import rate_limiter
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.user import User, UserRole
    from backend.app.schemas.auth import (
        LoginRequest,
        TokenResponse,
        UserProfileOut,
        ChangePasswordRequest,
        UpdateProfileRequest
    )
    from backend.app.core.security import verify_password, hash_password, create_access_token
    from backend.app.core.dependencies import get_current_user, log_activity
    from backend.app.core.rate_limiter import rate_limiter

router = APIRouter(prefix="/auth", tags=["Owner Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Authenticate Studio Desire Owner / Team")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate owner/team user and return JWT bearer token.
    Checks for first-login mandatory password change flag.
    Includes rate-limiting for brute force protection.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(f"auth_login:{client_ip}", max_requests=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later."
        )

    req_username = payload.username.strip()
    
    # Case-insensitive lookup
    user = db.query(User).filter(func.lower(User.username) == req_username.lower()).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your username and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your username and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue JWT token
    access_token = create_access_token(data={"sub": user.username, "role": user.role, "id": user.id})
    log_activity(db, user, action="Owner Login", entity_type="user", entity_id=str(user.id), details=f"Logged in as {user.role}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        username=user.username,
        role=user.role,
        must_change_password=user.must_change_password,
        user_id=user.id
    )


@router.get("/me", response_model=UserProfileOut, summary="Get current authenticated user profile")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", summary="Update account password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Updates the authenticated user's password.
    Clears the must_change_password flag if currently set.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed.",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.must_change_password = False
    db.commit()

    log_activity(db, current_user, action="Password Changed", entity_type="user", entity_id=str(current_user.id), details="User updated account password")

    return {
        "success": True,
        "message": "Password updated successfully. You may now access the full dashboard.",
        "must_change_password": False
    }


@router.post("/update-profile", response_model=UserProfileOut, summary="Update user username / email")
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows user to update their username or email.
    """
    if payload.username and payload.username.strip():
        new_username = payload.username.strip()
        existing = db.query(User).filter(func.lower(User.username) == new_username.lower(), User.id != current_user.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{new_username}' is already in use.",
            )
        current_user.username = new_username

    if payload.email is not None:
        current_user.email = payload.email.strip() if payload.email else None

    db.commit()
    db.refresh(current_user)

    log_activity(db, current_user, action="Profile Updated", entity_type="user", entity_id=str(current_user.id), details=f"Username updated to {current_user.username}")

    return current_user
