from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class VisualizationMediaOut(BaseModel):
    id: int
    url: str
    caption: Optional[str] = None
    angle: Optional[str] = None
    vr_url: Optional[str] = None
    has_vr: bool = False
    show_qr: bool = False
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    sort_order: int

    model_config = ConfigDict(from_attributes=True)

class VisualizationSpaceSummaryOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    slug: str
    project_name: str
    room: str
    category: str
    year: int
    location: Optional[str] = None
    software: Optional[str] = None
    cover_image: str
    vr_url: Optional[str] = None
    has_vr: bool
    show_qr: bool = True
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    sort_order: int
    media_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class VisualizationSpaceDetailOut(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    slug: str
    project_name: str
    room: str
    category: str
    year: int
    location: Optional[str] = None
    description: Optional[str] = None
    software: Optional[str] = None
    cover_image: str
    vr_url: Optional[str] = None
    has_vr: bool
    show_qr: bool = True
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    sort_order: int
    created_at: datetime
    media: List[VisualizationMediaOut] = []

    model_config = ConfigDict(from_attributes=True)

class VisualizationProjectArchiveOut(BaseModel):
    id: int
    title: str
    slug: str
    subtitle: Optional[str] = None
    location: Optional[str] = None
    year: int
    category: str
    description: str
    cover_image: str
    vr_url: Optional[str] = None
    has_central_vr: bool = False
    show_qr: bool = True
    vr_type: Optional[str] = "external"
    vr_build_entry: Optional[str] = None
    rooms: List[VisualizationSpaceDetailOut] = []

    model_config = ConfigDict(from_attributes=True)

class VisualizationListResponse(BaseModel):
    total: int
    spaces: List[VisualizationSpaceDetailOut]

class VisualizationSpaceCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    room: str = "Living Room"
    category: str = "Residential"
    year: int = 2026
    location: Optional[str] = "Ahmedabad, Gujarat"
    description: Optional[str] = None
    software: Optional[str] = "Corona Renderer · 3ds Max · Unreal Engine VR"
    cover_image: str
    vr_url: Optional[str] = None
    show_qr: bool = True
    vr_type: Optional[str] = "external"
    is_published: bool = True
    sort_order: int = 0

class VisualizationSpaceUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    room: Optional[str] = None
    category: Optional[str] = None
    year: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    software: Optional[str] = None
    cover_image: Optional[str] = None
    vr_url: Optional[str] = None
    show_qr: Optional[bool] = None
    vr_type: Optional[str] = None
    is_published: Optional[bool] = None
    sort_order: Optional[int] = None

class VisualizationMediaCreate(BaseModel):
    url: str
    caption: Optional[str] = None
    angle: Optional[str] = None
    sort_order: int = 0
    vr_url: Optional[str] = None
    show_qr: bool = False
    vr_type: Optional[str] = "external"

class VisualizationMediaUpdate(BaseModel):
    caption: Optional[str] = None
    angle: Optional[str] = None
    sort_order: Optional[int] = None
    vr_url: Optional[str] = None
    show_qr: Optional[bool] = None
    vr_type: Optional[str] = None
