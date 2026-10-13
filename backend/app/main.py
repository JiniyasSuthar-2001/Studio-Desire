import sys
import os
from pathlib import Path

# Add backend directory to sys.path if not present
current_dir = Path(__file__).resolve().parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database.session import engine, Base
from app.database.migrations import run_migrations

# Import all models to ensure metadata registration
from app.models.user import User, UserRole
from app.models.client import Client
from app.models.project import Project, ProjectMedia
from app.models.product import Product, ProductMedia
from app.models.contact import ContactInquiry
from app.models.visualization import VisualizationSpace, VisualizationMedia
from app.models.blueprint import BlueprintDrawing
from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
from app.models.task import Task, TaskAssignment, TaskComment
from app.models.milestone import ProjectMilestone
from app.models.material import ProjectMaterial
from app.models.meeting import Meeting
from app.models.file import ProjectFile
from app.models.finance import PaymentRecord
from app.models.activity import ActivityLog
from app.models.category import PortfolioCategory, PortfolioSubcategory
from app.models.google_calendar import GoogleCalendarConnection, CalendarSyncItem

# Public API Routers
from app.api.projects import router as projects_router
from app.api.products import router as products_router
from app.api.contact import router as contact_router
from app.api.visualizations import router as visualizations_router
from app.api.blueprints import router as blueprints_router
from app.api.enquiries import router as enquiries_router

# Owner & CMS Admin API Routers
from app.api.auth import router as auth_router
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.admin_projects import router as admin_projects_router
from app.api.admin_categories import router as admin_categories_router
from app.api.admin_clients import router as admin_clients_router
from app.api.admin_tasks import router as admin_tasks_router
from app.api.admin_materials import router as admin_materials_router
from app.api.admin_meetings import router as admin_meetings_router
from app.api.admin_files import router as admin_files_router
from app.api.admin_finance import router as admin_finance_router
from app.api.admin_media import router as admin_media_router
from app.api.admin_search import router as admin_search_router
from app.api.admin_upload import router as admin_upload_router
from app.api.admin_vr import router as admin_vr_router
from app.api.admin_visualizations import router as admin_visualizations_router
from app.api.admin_users import router as admin_users_router
from app.api.admin_content import router as admin_content_router
from app.api.admin_activity import router as admin_activity_router
from app.api.admin_enquiries import router as admin_enquiries_router
from app.api.google_calendar import router as google_calendar_router

# Create any missing database tables safely
Base.metadata.create_all(bind=engine)

import logging

# Configure centralized backend logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("studio_desire.main")

# Run safe SQLite schema migrations (add missing columns to existing tables)
try:
    run_migrations(engine)
except Exception as err:
    logger.warning(f"[STARTUP NOTE] Migration check: {err}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Studio Desire — Architectural & Interior Design Archive REST API & Owner Management System",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Public API Routers
app.include_router(projects_router, prefix=settings.API_PREFIX)
app.include_router(products_router, prefix=settings.API_PREFIX)
app.include_router(contact_router, prefix=settings.API_PREFIX)
app.include_router(visualizations_router, prefix=settings.API_PREFIX)
app.include_router(blueprints_router, prefix=settings.API_PREFIX)
app.include_router(enquiries_router, prefix=settings.API_PREFIX)

# Mount Owner & CMS Admin API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(admin_dashboard_router, prefix=settings.API_PREFIX)
app.include_router(admin_projects_router, prefix=settings.API_PREFIX)
app.include_router(admin_categories_router, prefix=settings.API_PREFIX)
app.include_router(admin_clients_router, prefix=settings.API_PREFIX)
app.include_router(admin_tasks_router, prefix=settings.API_PREFIX)
app.include_router(admin_materials_router, prefix=settings.API_PREFIX)
app.include_router(admin_meetings_router, prefix=settings.API_PREFIX)
app.include_router(admin_files_router, prefix=settings.API_PREFIX)
app.include_router(admin_finance_router, prefix=settings.API_PREFIX)
app.include_router(admin_media_router, prefix=settings.API_PREFIX)
app.include_router(admin_search_router, prefix=settings.API_PREFIX)
app.include_router(admin_upload_router, prefix=settings.API_PREFIX)
app.include_router(admin_vr_router, prefix=settings.API_PREFIX)
app.include_router(admin_visualizations_router, prefix=settings.API_PREFIX)
app.include_router(admin_users_router, prefix=settings.API_PREFIX)
app.include_router(admin_content_router, prefix=settings.API_PREFIX)
app.include_router(admin_activity_router, prefix=settings.API_PREFIX)
app.include_router(admin_enquiries_router, prefix=settings.API_PREFIX)
app.include_router(google_calendar_router, prefix=settings.API_PREFIX)

# Mount static public project assets (photos, 3D renders, CAD drawings, CMS uploads)
from fastapi.staticfiles import StaticFiles
settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
def ensure_default_data():
    try:
        from app.database.session import SessionLocal
        from app.models.blueprint import BlueprintDrawing
        from app.models.project import Project, ProjectMedia
        from app.models.visualization import VisualizationSpace, VisualizationMedia
        from app.models.user import User, UserRole
        from app.models.client import Client
        from app.core.security import hash_password
        try:
            from seed import DEMO_PROJECTS, DEMO_VISUALIZATIONS, DEMO_BLUEPRINTS
        except ImportError:
            from backend.seed import DEMO_PROJECTS, DEMO_VISUALIZATIONS, DEMO_BLUEPRINTS

        db = SessionLocal()
        try:
            # 1. Optional Demo Data Seeding (strictly gated behind SEED_DEMO_DATA in development)
            if settings.SEED_DEMO_DATA and not settings.IS_PRODUCTION:
                hardik_client = db.query(Client).filter(Client.name == "Hardikbhai Patel").first()
                if not hardik_client:
                    hardik_client = Client(
                        name="Hardikbhai Patel",
                        company="Patel Enterprises",
                        email="hardikbhai@gmail.com",
                        phone="+91 98765 43210",
                        address="Bopal, Ahmedabad, Gujarat",
                        notes="Client commission for luxury 4BHK architectural residence"
                    )
                    db.add(hardik_client)
                    db.commit()
                    db.refresh(hardik_client)

                hardik_proj = db.query(Project).filter(Project.slug == "hardikbhai").first()
                if not hardik_proj:
                    logger.info("SEED_DEMO_DATA enabled: Seeding demo project Hardikbhai...")
                    hb_data = next((p for p in DEMO_PROJECTS if p["slug"] == "hardikbhai"), None)
                    if hb_data:
                        data = dict(hb_data)
                        media_items = data.pop("media", [])
                        data["client_id"] = hardik_client.id
                        data["status"] = "EXECUTION"
                        data["budget"] = 4500000.0
                        data["project_value"] = 4500000.0
                        data["amount_received"] = 2500000.0
                        data["amount_pending"] = 2000000.0
                        hardik_proj = Project(**data)
                        db.add(hardik_proj)
                        db.flush()

                        for m in media_items:
                            db.add(ProjectMedia(project_id=hardik_proj.id, **m))
                        db.commit()
                        logger.info(f"Hardikbhai project seeded with {len(media_items)} renders.")

            # 2. Ensure initial Master / Owner accounts securely
            master_user = db.query(User).filter(User.role.in_([UserRole.MASTER.value, UserRole.OWNER.value])).first()
            if not master_user:
                # Require explicit environment credentials or first-run setup
                init_pwd = settings.INITIAL_ADMIN_PASSWORD.strip()
                if init_pwd:
                    initial_master = User(
                        username=settings.INITIAL_ADMIN_USERNAME.strip() or "Studio Desire",
                        email=settings.INITIAL_ADMIN_EMAIL.strip() or "studiodesire01@gmail.com",
                        hashed_password=hash_password(init_pwd),
                        role=UserRole.MASTER.value,
                        is_active=True,
                        must_change_password=True
                    )
                    db.add(initial_master)
                    db.commit()
                    logger.info(f"Initial administrator account '{initial_master.username}' initialized securely from environment configuration.")
                else:
                    if settings.IS_PRODUCTION:
                        logger.error(
                            "CRITICAL: No administrator account exists in database and INITIAL_ADMIN_PASSWORD was not provided. "
                            "Please provide INITIAL_ADMIN_PASSWORD in environment to bootstrap the administrator account."
                        )
                    else:
                        logger.warning(
                            "No administrator account found in database. Set INITIAL_ADMIN_PASSWORD in your environment / .env file to create the initial admin account."
                        )
        finally:
            db.close()
    except Exception as err:
        logger.warning(f"Startup data check note: {err}")


@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "Studio Desire Interior Design & Architecture API",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please try again later."}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
