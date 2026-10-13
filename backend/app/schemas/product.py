from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProductMediaOut(BaseModel):
    id: int
    product_id: int
    media_type: str
    url: str
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    sort_order: int = 0

    model_config = ConfigDict(from_attributes=True)

class ProductBase(BaseModel):
    title: str
    slug: str
    subtitle: Optional[str] = None
    category: str
    description: str
    cover_image: str
    year: int = 2026
    materials: Optional[str] = None
    dimensions: Optional[str] = None
    featured: bool = False
    is_demo: bool = True
    grid_span: Optional[str] = "span-6"
    aspect_ratio: Optional[str] = "ratio-standard"

class ProductSummaryOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    media_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class ProductDetailOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    media: List[ProductMediaOut] = []

    model_config = ConfigDict(from_attributes=True)

class ProductListResponse(BaseModel):
    total: int
    products: List[ProductSummaryOut]
