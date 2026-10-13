from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

try:
    from app.database.session import Base
except ImportError:
    from backend.app.database.session import Base


class PortfolioCategory(Base):
    __tablename__ = "portfolio_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=1, index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)
    cover_image = Column(String(1000), nullable=True)
    puzzle_size = Column(String(50), default="small")  # large, tall, wide, small
    featured_project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL", use_alter=True, name="fk_category_featured_project"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subcategories = relationship(
        "PortfolioSubcategory",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="PortfolioSubcategory.display_order"
    )
    projects = relationship(
        "Project",
        back_populates="portfolio_category",
        foreign_keys="Project.category_id"
    )
    featured_project = relationship(
        "Project",
        foreign_keys=[featured_project_id],
        post_update=True
    )


class PortfolioSubcategory(Base):
    __tablename__ = "portfolio_subcategories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("portfolio_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)
    display_order = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("PortfolioCategory", back_populates="subcategories")
    projects = relationship(
        "Project",
        back_populates="portfolio_subcategory",
        foreign_keys="Project.subcategory_id"
    )
