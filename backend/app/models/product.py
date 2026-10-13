from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    subtitle = Column(String(500), nullable=True)
    category = Column(String(100), index=True, nullable=False)  # Furniture, Seating, Tables, Storage, Beds, Lighting, Custom
    description = Column(Text, nullable=False)
    cover_image = Column(String(1000), nullable=False)
    year = Column(Integer, nullable=False, default=2026)
    materials = Column(String(500), nullable=True)     # e.g., "Solid White Oak, Bouclé, Brushed Brass"
    dimensions = Column(String(255), nullable=True)    # e.g., "W 920 × D 880 × H 720 mm"
    featured = Column(Boolean, default=False, index=True)
    is_demo = Column(Boolean, default=True)
    grid_span = Column(String(50), default="span-6")   # Editorial CSS grid span
    aspect_ratio = Column(String(50), default="ratio-standard")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    media = relationship(
        "ProductMedia",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductMedia.sort_order"
    )

class ProductMedia(Base):
    __tablename__ = "product_media"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    media_type = Column(String(50), nullable=False, default="image")  # "image"
    url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    caption = Column(String(500), nullable=True)
    alt_text = Column(String(500), nullable=True)
    sort_order = Column(Integer, default=0, index=True)

    product = relationship("Product", back_populates="media")
