import os
import sys
import logging
from pathlib import Path
from typing import List, Optional

# Setup logger for configuration notices
logger = logging.getLogger("studio_desire.config")

# Anchor paths to backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = (BACKEND_DIR / "studio_desire.db").resolve()
STORAGE_DIR = (BACKEND_DIR / "storage").resolve()
ENQUIRY_ATTACHMENTS_DIR = (STORAGE_DIR / "enquiry_attachments").resolve()

# Ensure private storage directory exists
ENQUIRY_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

INSECURE_DEV_SECRETS = {
    "studio-desire-arch-secret-key-2026-auth-token-salt-secure",
    "12345678",
    "secret",
    "changeme",
    "default",
}


class Settings:
    def __init__(
        self,
        PROJECT_NAME: Optional[str] = None,
        ENVIRONMENT: Optional[str] = None,
        SECRET_KEY: Optional[str] = None,
        DATABASE_URL: Optional[str] = None,
        MAX_UPLOAD_SIZE_BYTES: Optional[int] = None,
        ENQUIRY_RATE_LIMIT: Optional[int] = None,
        ENQUIRY_RATE_WINDOW_SECONDS: Optional[int] = None
    ):
        self.PROJECT_NAME = PROJECT_NAME or os.getenv("PROJECT_NAME", "Studio Desire Architectural Portfolio API")
        self.VERSION = "1.0.0"
        self.API_PREFIX = "/api"
        self.ENVIRONMENT = (ENVIRONMENT or os.getenv("ENVIRONMENT", "development")).lower()
        self.DATABASE_URL = DATABASE_URL or os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
        self._secret_key_override = SECRET_KEY

        # CORS Origins
        self.CORS_ORIGINS_RAW = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
        )

        # Security & Auth
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours default

        # Upload & Attachment Constraints
        self.MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_BYTES or int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))
        self.STORAGE_DIR = STORAGE_DIR
        self.ENQUIRY_ATTACHMENTS_DIR = ENQUIRY_ATTACHMENTS_DIR

        # Centralized Canonical Media Storage Root
        self.UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str((BACKEND_DIR.parent / "frontend" / "public" / "uploads").resolve()))).resolve()
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        (self.UPLOADS_DIR / "cms").mkdir(parents=True, exist_ok=True)
        (self.UPLOADS_DIR / "projects").mkdir(parents=True, exist_ok=True)
        (self.UPLOADS_DIR / "enquiries").mkdir(parents=True, exist_ok=True)
        (self.UPLOADS_DIR / "vr_builds").mkdir(parents=True, exist_ok=True)

        # Rate Limiting
        self.ENQUIRY_RATE_LIMIT = ENQUIRY_RATE_LIMIT or int(os.getenv("ENQUIRY_RATE_LIMIT", "10"))
        self.ENQUIRY_RATE_WINDOW_SECONDS = ENQUIRY_RATE_WINDOW_SECONDS or int(os.getenv("ENQUIRY_RATE_WINDOW_SECONDS", "600"))

        # Demo Data Seeding Gate
        self.SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "false").lower() in ("true", "1", "yes")

        # Initial Admin Bootstrap
        self.INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "Studio Desire")
        self.INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "studiodesire01@gmail.com")
        self.INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD", "")

        # Google OAuth Calendar Integration & Frontend URL
        self.FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        self.GOOGLE_CALENDAR_CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "")
        self.GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", "")
        self.GOOGLE_CALENDAR_REDIRECT_URI = os.getenv(
            "GOOGLE_CALENDAR_REDIRECT_URI",
            "http://localhost:8000/api/admin/google-calendar/oauth/callback"
        )
        self.GOOGLE_CALENDAR_SCOPES = os.getenv(
            "GOOGLE_CALENDAR_SCOPES",
            "https://www.googleapis.com/auth/calendar.events openid email"
        )

    def validate_google_calendar_configuration(self) -> dict:
        """
        Validates Google Calendar OAuth configuration.
        Returns a dict with 'valid': bool, 'errors': List[str], 'warnings': List[str], 'configured': bool.
        """
        errors = []
        warnings = []
        client_id = (self.GOOGLE_CALENDAR_CLIENT_ID or "").strip()
        client_secret = (self.GOOGLE_CALENDAR_CLIENT_SECRET or "").strip()
        redirect_uri = (self.GOOGLE_CALENDAR_REDIRECT_URI or "").strip()
        frontend_url = (self.FRONTEND_URL or "").strip()
        scopes = (self.GOOGLE_CALENDAR_SCOPES or "").strip()

        placeholder_patterns = {"demo_google_client_id", "placeholder", "changeme", "your-client-id"}
        if not client_id or client_id.lower() in placeholder_patterns:
            errors.append("GOOGLE_CALENDAR_CLIENT_ID is missing or configured with a placeholder.")
        if not client_secret or client_secret.lower() in placeholder_patterns:
            errors.append("GOOGLE_CALENDAR_CLIENT_SECRET is missing or configured with a placeholder.")

        if not redirect_uri:
            errors.append("GOOGLE_CALENDAR_REDIRECT_URI is not set.")
        elif "/admin/google-calendar/oauth/callback" not in redirect_uri:
            errors.append(
                f"GOOGLE_CALENDAR_REDIRECT_URI ('{redirect_uri}') does not match the mounted router path '/api/admin/google-calendar/oauth/callback'."
            )

        if not frontend_url:
            errors.append("FRONTEND_URL is not set.")

        if "calendar.events" not in scopes:
            warnings.append("GOOGLE_CALENDAR_SCOPES does not include 'https://www.googleapis.com/auth/calendar.events'.")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "configured": bool(client_id and client_secret and client_id.lower() not in placeholder_patterns)
        }

    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT in ["production", "prod"]

    @property
    def SECRET_KEY(self) -> str:
        key = (self._secret_key_override if self._secret_key_override is not None else os.getenv("SECRET_KEY", "")).strip()
        if self.IS_PRODUCTION:
            if not key or key in INSECURE_DEV_SECRETS or len(key) < 32:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: In production mode ('ENVIRONMENT=production'), "
                    "a cryptographically strong SECRET_KEY (at least 32 characters) must be configured via environment variables. "
                    "Insecure default or weak keys are strictly rejected."
                )
            return key
        # Development / Testing fallback
        if not key:
            logger.warning(
                "[SECURITY NOTICE] No SECRET_KEY provided in development mode. Using transient development secret."
            )
            return "studio-desire-development-only-session-token-secret-2026-salt"
        return key

    @property
    def CORS_ORIGINS(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]
        # Wildcard '*' is strictly prohibited when allow_credentials=True
        clean_origins = [o for o in origins if o != "*"]
        if self.IS_PRODUCTION and ("*" in origins or not clean_origins):
            raise RuntimeError(
                "CRITICAL CORS CONFIGURATION ERROR: Wildcard '*' origins cannot be used in production with credentials. "
                "Specify explicit allowed origins in CORS_ORIGINS (e.g. 'https://studiodesire.com')."
            )
        return clean_origins if clean_origins else ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]

    def validate_security_configuration(self) -> None:
        """Validates that production settings meet all security invariants."""
        _ = self.SECRET_KEY
        _ = self.CORS_ORIGINS
        if self.IS_PRODUCTION and self.SEED_DEMO_DATA:
            logger.warning("[SECURITY] SEED_DEMO_DATA is ignored in production mode.")


settings = Settings()
