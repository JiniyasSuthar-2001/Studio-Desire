# App models package initialization
# Pre-registers all models with SQLAlchemy's declarative base
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
