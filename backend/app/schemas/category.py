from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class PortfolioSubcategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None
    display_order: int = 1
    is_active: bool = True


class PortfolioSubcategoryCreate(PortfolioSubcategoryBase):
    pass


class PortfolioSubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class PortfolioSubcategoryOut(PortfolioSubcategoryBase):
    id: int
    category_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeaturedProjectSummary(BaseModel):
    id: int
    title: str
    slug: str
    subtitle: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    cover_image: Optional[str] = None
    is_published: bool = True

    class Config:
        from_attributes = True


class EligibleProjectItemOut(BaseModel):
    id: int
    title: str
    slug: str
    subtitle: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    cover_image: Optional[str] = None
    is_published: bool = True
    is_current_representative: bool = False

    class Config:
        from_attributes = True


class SetFeaturedProjectPayload(BaseModel):
    project_id: Optional[int] = None


class PortfolioCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 1
    is_active: bool = True
    cover_image: Optional[str] = None
    puzzle_size: str = "small"  # large, tall, wide, small
    featured_project_id: Optional[int] = None


class PortfolioCategoryCreate(PortfolioCategoryBase):
    subcategories: Optional[List[str]] = []


class PortfolioCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    cover_image: Optional[str] = None
    puzzle_size: Optional[str] = None
    featured_project_id: Optional[int] = None


class PortfolioCategoryOut(PortfolioCategoryBase):
    id: int
    is_default: bool = False
    featured_project: Optional[FeaturedProjectSummary] = None
    subcategories: List[PortfolioSubcategoryOut] = []
    total_projects: int = 0
    published_projects: int = 0
    unpublished_projects: int = 0
    total_projects_count: int = 0
    published_projects_count: int = 0
    unpublished_projects_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryReorderItem(BaseModel):
    id: int
    display_order: int


class CategoryReorderPayload(BaseModel):
    items: List[CategoryReorderItem]


class CategoryReassignPayload(BaseModel):
    target_category_id: int
