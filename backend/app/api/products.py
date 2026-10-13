from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.product import Product, ProductMedia
    from app.schemas.product import (
        ProductSummaryOut,
        ProductDetailOut,
        ProductListResponse
    )
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.product import Product, ProductMedia
    from backend.app.schemas.product import (
        ProductSummaryOut,
        ProductDetailOut,
        ProductListResponse
    )

router = APIRouter(prefix="/products", tags=["Products Archive"])

@router.get("", response_model=ProductListResponse, summary="List all design products and custom furniture with optional filters")
def get_products(
    category: Optional[str] = Query(None, description="Filter by category (e.g., Seating, Tables, Lighting, Custom)"),
    featured: Optional[bool] = Query(None, description="Filter only featured products"),
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    # Category Filter
    if category and category.upper() != "ALL":
        query = query.filter(func.lower(Product.category) == category.lower())

    # Featured Filter
    if featured is not None:
        query = query.filter(Product.featured == featured)

    products = query.order_by(Product.id.asc()).all()

    summaries = []
    for p in products:
        summary = ProductSummaryOut(
            id=p.id,
            title=p.title,
            slug=p.slug,
            subtitle=p.subtitle,
            category=p.category,
            description=p.description,
            cover_image=p.cover_image,
            year=p.year,
            materials=p.materials,
            dimensions=p.dimensions,
            featured=p.featured,
            is_demo=p.is_demo,
            grid_span=p.grid_span,
            aspect_ratio=p.aspect_ratio,
            created_at=p.created_at,
            updated_at=p.updated_at,
            media_count=len(p.media)
        )
        summaries.append(summary)

    return ProductListResponse(total=len(summaries), products=summaries)

@router.get("/categories", response_model=List[str], summary="Get list of available product categories")
def get_product_categories(db: Session = Depends(get_db)):
    results = db.query(Product.category).distinct().all()
    categories = ["ALL"] + [r[0] for r in results if r[0]]
    return categories

@router.get("/{slug_or_id}", response_model=ProductDetailOut, summary="Retrieve a full product design dossier")
def get_product_by_slug(slug_or_id: str, db: Session = Depends(get_db)):
    product = None
    if slug_or_id.isdigit():
        product = db.query(Product).filter(Product.id == int(slug_or_id)).first()

    if not product:
        product = db.query(Product).filter(Product.slug == slug_or_id.lower()).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{slug_or_id}' was not found in the Studio Desire design archive"
        )

    return product
