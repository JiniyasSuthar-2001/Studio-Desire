from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[str] = None
    role: str = Field("VIEWER", description="OWNER, ADMIN, DESIGNER, PROJECT_MANAGER, VIEWER")


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    email: Optional[str] = None


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6)


class ProjectCounts(BaseModel):
    photos: int = 0
    videos: int = 0
    renders_3d: int = 0
    blueprints: int = 0
    vr_rooms: int = 0
    tasks_open: int = 0
    materials_count: int = 0
    files_count: int = 0


class ProjectAdminOut(BaseModel):
    id: int
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    title: str
    slug: str
    subtitle: Optional[str] = None
    location: str
    year: int
    category: str
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    project_type: Optional[str] = None
    area: Optional[str] = None
    description: str
    cover_image: str
    status: str = "PLANNING"
    start_date: Optional[str] = None
    expected_completion_date: Optional[str] = None
    actual_completion_date: Optional[str] = None
    budget: float = 0.0
    project_value: float = 0.0
    amount_received: float = 0.0
    amount_pending: float = 0.0
    featured: bool = False
    is_demo: bool = False
    is_published: bool = True
    vr_url: Optional[str] = None
    vr_qr_code: Optional[str] = None
    show_qr: bool = True
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    counts: ProjectCounts
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    client_id: Optional[int] = None
    subtitle: Optional[str] = None
    location: str = "Ahmedabad, Gujarat"
    year: int = 2026
    category: Optional[str] = "Residential"
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    project_type: Optional[str] = "Private Residence"
    area: Optional[str] = None
    description: str = ""
    cover_image: Optional[str] = None
    status: str = "PLANNING"
    start_date: Optional[str] = None
    expected_completion_date: Optional[str] = None
    budget: float = 0.0
    project_value: float = 0.0
    featured: bool = False
    is_published: bool = True
    vr_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[int] = None
    subtitle: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    project_type: Optional[str] = None
    area: Optional[str] = None
    description: Optional[str] = None
    cover_image: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    expected_completion_date: Optional[str] = None
    actual_completion_date: Optional[str] = None
    budget: Optional[float] = None
    project_value: Optional[float] = None
    amount_received: Optional[float] = None
    amount_pending: Optional[float] = None
    featured: Optional[bool] = None
    is_published: Optional[bool] = None
    vr_url: Optional[str] = None


class ActionItemOut(BaseModel):
    type: str  # enquiry, task, meeting, approval, project
    title: str
    subtitle: Optional[str] = None
    badge: str
    badge_color: str  # green, red, amber, blue
    link_tab: str
    link_context: Optional[Dict[str, Any]] = None
    date: Optional[str] = None


class DashboardStatsOut(BaseModel):
    total_projects: int = 0
    active_projects: int = 0
    published_projects_count: int = 0
    draft_projects_count: int = 0
    total_clients: int = 0
    total_enquiries: int = 0
    new_enquiries: int = 0
    tasks_due_today: int = 0
    overdue_tasks: int = 0
    upcoming_meetings_count: int = 0
    pending_approvals_count: int = 0
    total_photos: int = 0
    total_videos: int = 0
    total_3d_renders: int = 0
    total_blueprints: int = 0
    total_vr_rooms: int = 0
    unassigned_media_count: int = 0
    total_project_value: float = 0.0
    total_amount_received: float = 0.0
    action_items: List[ActionItemOut] = []


class SearchResultItem(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    category: str  # project, client, enquiry, product, file
    url_tab: str
    context_data: Optional[Dict[str, Any]] = None


class GlobalSearchOut(BaseModel):
    query: str
    total_results: int
    projects: List[SearchResultItem] = []
    clients: List[SearchResultItem] = []
    enquiries: List[SearchResultItem] = []
    products: List[SearchResultItem] = []
    files: List[SearchResultItem] = []


class UnifiedMediaItemOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    project_title: Optional[str] = None
    media_type: str  # photo, video, 3d, blueprint, vr, document
    url: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    room_name: Optional[str] = None
    status: str = "published"
    is_published: bool = True
    version: Optional[str] = "v1"
    uploaded_by: Optional[str] = None
    sort_order: int = 0
    vr_url: Optional[str] = None
    has_vr: bool = False
    show_qr: bool = False
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    created_at: datetime


class ActivityLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: str
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BulkUploadItem(BaseModel):
    id: int
    url: str
    thumbnail_url: Optional[str] = None
    filename: str
    detected_type: str  # image, video, 3d, blueprint, document
    project_id: Optional[int] = None
    room_name: Optional[str] = None
    drawing_type: Optional[str] = None
    caption: Optional[str] = None
    sort_order: int = 0
    status: str = "draft"


class BulkUploadCommitRequest(BaseModel):
    items: List[BulkUploadItem]
    publish_now: bool = False


class AssignMediaRequest(BaseModel):
    media_ids: List[int]
    project_id: int
    media_type: Optional[str] = None
    room_name: Optional[str] = None
    drawing_type: Optional[str] = None
    publish_now: bool = True


class ContentSectionUpdate(BaseModel):
    content_json: str
