from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

# -----------------------------------------------------------------------------
# MEDIA SCHEMAS
# -----------------------------------------------------------------------------
class MediaBase(BaseModel):
    media_type: str  # "image" or "video"
    url: str
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    sort_order: int = 0
    vr_url: Optional[str] = None
    has_vr: bool = False
    show_qr: bool = False
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None

class MediaCreate(MediaBase):
    pass

class MediaOut(MediaBase):
    id: int
    project_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

# -----------------------------------------------------------------------------
# PROJECT SCHEMAS
# -----------------------------------------------------------------------------
class ProjectBase(BaseModel):
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
    featured: bool = False
    is_demo: bool = True
    is_published: bool = False
    vr_url: Optional[str] = None
    vr_qr_code: Optional[str] = None
    show_qr: bool = True
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    grid_span: Optional[str] = "span-6"
    aspect_ratio: Optional[str] = "ratio-standard"

class ProjectCreate(ProjectBase):
    media: Optional[List[MediaCreate]] = []

class ProjectSummaryOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    has_video: bool = False
    media_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class ProjectDetailOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime
    media: List[MediaOut] = []

    model_config = ConfigDict(from_attributes=True)

class ProjectListResponse(BaseModel):
    total: int
    projects: List[ProjectSummaryOut]
