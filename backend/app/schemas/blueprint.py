from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class BlueprintDrawingSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: Optional[int] = None
    project_name: str
    project_slug: str
    title: str
    slug: str
    drawing_type: str
    room_area: Optional[str] = None
    drawing_number: Optional[str] = None
    revision: Optional[str] = "R0"
    date: Optional[str] = None
    scale: Optional[str] = None
    sheet_size: Optional[str] = None
    thumbnail_url: str
    file_url: str
    file_type: str = "image"
    sort_order: int = 0
    is_demo: bool = True


class BlueprintDrawingDetailOut(BlueprintDrawingSummaryOut):
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BlueprintProjectSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_slug: str
    project_name: str
    location: Optional[str] = None
    year: Optional[int] = None
    drawing_count: int
    drawing_types: List[str]


class BlueprintListResponse(BaseModel):
    project: Optional[BlueprintProjectSummaryOut] = None
    projects: List[BlueprintProjectSummaryOut]
    drawing_types: List[str]
    items: List[BlueprintDrawingSummaryOut]
    total: int
