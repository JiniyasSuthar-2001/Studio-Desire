from datetime import datetime, date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.project import Project, ProjectMedia
    from app.models.client import Client
    from app.models.task import Task
    from app.models.meeting import Meeting
    from app.models.material import ProjectMaterial
    from app.models.visualization import VisualizationSpace, VisualizationMedia
    from app.models.blueprint import BlueprintDrawing
    from app.models.enquiry import ProjectEnquiry
    from app.models.finance import PaymentRecord
    from app.models.user import User
    from app.schemas.admin import DashboardStatsOut, ActionItemOut
    from app.core.dependencies import get_current_user
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.models.client import Client
    from backend.app.models.task import Task
    from backend.app.models.meeting import Meeting
    from backend.app.models.material import ProjectMaterial
    from backend.app.models.visualization import VisualizationSpace, VisualizationMedia
    from backend.app.models.blueprint import BlueprintDrawing
    from backend.app.models.enquiry import ProjectEnquiry
    from backend.app.models.finance import PaymentRecord
    from backend.app.models.user import User
    from backend.app.schemas.admin import DashboardStatsOut, ActionItemOut
    from backend.app.core.dependencies import get_current_user

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])


@router.get("/stats", response_model=DashboardStatsOut, summary="Get real actionable dashboard metrics")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    total_projects = db.query(Project).count()
    active_projects = db.query(Project).filter(
        Project.status.notin_(["COMPLETED", "ARCHIVED"])
    ).count()
    published_projects = db.query(Project).filter(Project.is_published == True).count()
    draft_projects = db.query(Project).filter(Project.is_published == False).count()

    total_clients = db.query(Client).count()
    total_enquiries = db.query(ProjectEnquiry).count()
    new_enquiries = db.query(ProjectEnquiry).filter(ProjectEnquiry.status.in_(["NEW", "CONTACTED"])).count()

    # Tasks metrics
    tasks_due_today = db.query(Task).filter(
        func.date(Task.due_date) == today_str,
        Task.status.notin_(["COMPLETED", "CANCELLED"])
    ).count()

    overdue_tasks = db.query(Task).filter(
        Task.due_date < now,
        Task.status.notin_(["COMPLETED", "CANCELLED"])
    ).count()

    # Upcoming meetings (today or future)
    upcoming_meetings = db.query(Meeting).filter(
        Meeting.status == "SCHEDULED",
        Meeting.date >= today_str
    ).count()

    # Pending Approvals (Materials or Blueprints or Visualizations awaiting review)
    pending_materials = db.query(ProjectMaterial).filter(ProjectMaterial.status.in_(["PROPOSED", "CLIENT_REVIEW"])).count()
    pending_blueprints = db.query(BlueprintDrawing).filter(BlueprintDrawing.status.in_(["DRAFT", "CLIENT_REVIEW", "INTERNAL_REVIEW"])).count()
    pending_vis = db.query(VisualizationSpace).filter(VisualizationSpace.status.in_(["DRAFT", "CLIENT_REVIEW", "INTERNAL_REVIEW"])).count()
    pending_approvals = pending_materials + pending_blueprints + pending_vis

    # Asset counts
    total_photos = db.query(ProjectMedia).filter(ProjectMedia.media_type.in_(["image", "photo"])).count()
    total_videos = db.query(ProjectMedia).filter(ProjectMedia.media_type == "video").count()
    total_3d_renders = db.query(VisualizationMedia).count()
    total_blueprints = db.query(BlueprintDrawing).count()
    total_vr_rooms = db.query(VisualizationSpace).filter(
        (VisualizationSpace.has_vr == True) | (VisualizationSpace.vr_url != None)
    ).count()
    unassigned_count = db.query(ProjectMedia).filter(
        (ProjectMedia.project_id == None) | (ProjectMedia.status == "unassigned")
    ).count()

    # Financial totals
    total_val = db.query(func.sum(Project.project_value)).scalar() or db.query(func.sum(Project.budget)).scalar() or 0.0
    total_rec = db.query(func.sum(PaymentRecord.amount)).filter(PaymentRecord.status == "RECEIVED").scalar() or 0.0

    # Build High-Priority Action Items ("What needs my attention right now?")
    action_items: list[ActionItemOut] = []

    # 1. New Enquiries
    new_enqs_list = db.query(ProjectEnquiry).filter(ProjectEnquiry.status == "NEW").order_by(ProjectEnquiry.created_at.desc()).limit(3).all()
    for ne in new_enqs_list:
        action_items.append(
            ActionItemOut(
                type="enquiry",
                title=f"New Lead: {ne.name} ({ne.project_type})",
                subtitle=f"{ne.location or 'Location unspecified'} · Reference: {ne.reference_number}",
                badge="NEW ENQUIRY",
                badge_color="green",
                link_tab="enquiries",
                link_context={"id": ne.id},
                date=ne.created_at.strftime("%d %b, %H:%M") if ne.created_at else None
            )
        )

    # 2. Overdue or Urgent Tasks
    urgent_tasks = db.query(Task).filter(
        Task.status.notin_(["COMPLETED", "CANCELLED"]),
        (Task.priority == "URGENT") | (Task.due_date < now)
    ).order_by(Task.due_date.asc().nullslast()).limit(3).all()
    for ut in urgent_tasks:
        is_od = ut.due_date and ut.due_date < now
        action_items.append(
            ActionItemOut(
                type="task",
                title=f"Task: {ut.title}",
                subtitle=f"Assigned to {ut.assigned_to or 'Unassigned'} · Project: {ut.project.title if ut.project else ''}",
                badge="OVERDUE" if is_od else f"PRIORITY: {ut.priority}",
                badge_color="red" if is_od else "amber",
                link_tab="tasks",
                link_context={"id": ut.id, "projectId": ut.project_id},
                date=ut.due_date.strftime("%d %b %Y") if ut.due_date else None
            )
        )

    # 3. Today's or Next Meetings
    next_meetings = db.query(Meeting).filter(
        Meeting.status == "SCHEDULED",
        Meeting.date >= today_str
    ).order_by(Meeting.date.asc(), Meeting.time.asc()).limit(3).all()
    for nm in next_meetings:
        action_items.append(
            ActionItemOut(
                type="meeting",
                title=f"Meeting: {nm.title}",
                subtitle=f"{nm.meeting_type} at {nm.location} · {nm.participants or 'Team'}",
                badge="TODAY" if nm.date == today_str else "UPCOMING",
                badge_color="blue",
                link_tab="meetings",
                link_context={"id": nm.id},
                date=f"{nm.date} {nm.time or ''}".strip()
            )
        )

    return DashboardStatsOut(
        total_projects=total_projects,
        active_projects=active_projects,
        published_projects_count=published_projects,
        draft_projects_count=draft_projects,
        total_clients=total_clients,
        total_enquiries=total_enquiries,
        new_enquiries=new_enquiries,
        tasks_due_today=tasks_due_today,
        overdue_tasks=overdue_tasks,
        upcoming_meetings_count=upcoming_meetings,
        pending_approvals_count=pending_approvals,
        total_photos=total_photos,
        total_videos=total_videos,
        total_3d_renders=total_3d_renders,
        total_blueprints=total_blueprints,
        total_vr_rooms=total_vr_rooms,
        unassigned_media_count=unassigned_count,
        total_project_value=float(total_val),
        total_amount_received=float(total_rec),
        action_items=action_items
    )
