from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

try:
    from app.database.session import get_db
    from app.models.blueprint import BlueprintDrawing
    from app.models.project import Project
    from app.schemas.blueprint import (
        BlueprintDrawingSummaryOut,
        BlueprintDrawingDetailOut,
        BlueprintProjectSummaryOut,
        BlueprintListResponse,
    )
except ImportError:
    from backend.app.database.session import get_db
    from backend.app.models.blueprint import BlueprintDrawing
    from backend.app.models.project import Project
    from backend.app.schemas.blueprint import (
        BlueprintDrawingSummaryOut,
        BlueprintDrawingDetailOut,
        BlueprintProjectSummaryOut,
        BlueprintListResponse,
    )

router = APIRouter(prefix="/blueprints", tags=["Blueprints"])


def get_all_blueprint_projects(db: Session) -> List[BlueprintProjectSummaryOut]:
    """
    Computes all published projects with blueprints, including drawing counts and types.
    """
    raw_projects = (
        db.query(
            BlueprintDrawing.project_slug,
            BlueprintDrawing.project_name,
            func.count(BlueprintDrawing.id).label("drawing_count"),
        )
        .filter(BlueprintDrawing.is_published == True)
        .group_by(BlueprintDrawing.project_slug, BlueprintDrawing.project_name)
        .order_by(BlueprintDrawing.project_name)
        .all()
    )

    project_summaries: List[BlueprintProjectSummaryOut] = []
    for p_slug, p_name, count in raw_projects:
        # Check if matched in Project table for extra location/year
        proj_record = db.query(Project).filter(Project.slug == p_slug, Project.is_published == True).first()
        types = [
            t[0]
            for t in db.query(BlueprintDrawing.drawing_type)
            .filter(BlueprintDrawing.project_slug == p_slug, BlueprintDrawing.is_published == True)
            .distinct()
            .all()
        ]

        project_summaries.append(
            BlueprintProjectSummaryOut(
                project_slug=p_slug,
                project_name=p_name,
                location=proj_record.location if proj_record else None,
                year=proj_record.year if proj_record else None,
                drawing_count=count,
                drawing_types=types,
            )
        )
    return project_summaries


@router.get("", response_model=BlueprintListResponse)
def list_blueprints(
    project: Optional[str] = Query(None, description="Project slug (e.g. residence-01, hardik-bhai)"),
    drawing_type: Optional[str] = Query(None, description="Drawing type filter (e.g. Floor Plan, Detail Drawing)"),
    search: Optional[str] = Query(None, description="Search term across title, drawing_number, room_area"),
    db: Session = Depends(get_db),
):
    projects_list = get_all_blueprint_projects(db)

    # Determine active project
    active_project_slug = project
    if not active_project_slug and projects_list:
        active_project_slug = projects_list[0].project_slug

    query = db.query(BlueprintDrawing).filter(BlueprintDrawing.is_published == True)

    if active_project_slug and active_project_slug.lower() != "all":
        query = query.filter(BlueprintDrawing.project_slug == active_project_slug)

    if drawing_type and drawing_type.lower() != "all":
        query = query.filter(BlueprintDrawing.drawing_type == drawing_type)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (BlueprintDrawing.title.ilike(search_fmt))
            | (BlueprintDrawing.drawing_number.ilike(search_fmt))
            | (BlueprintDrawing.room_area.ilike(search_fmt))
        )

    drawings = query.order_by(BlueprintDrawing.sort_order, BlueprintDrawing.id).all()

    # Active project object
    active_project_summary = next(
        (p for p in projects_list if p.project_slug == active_project_slug), None
    )

    # Drawing types for the active scope
    type_query = db.query(BlueprintDrawing.drawing_type).filter(BlueprintDrawing.is_published == True)
    if active_project_slug and active_project_slug.lower() != "all":
        type_query = type_query.filter(BlueprintDrawing.project_slug == active_project_slug)
    available_types = [t[0] for t in type_query.distinct().order_by(BlueprintDrawing.drawing_type).all()]

    return BlueprintListResponse(
        project=active_project_summary,
        projects=projects_list,
        drawing_types=available_types,
        items=drawings,
        total=len(drawings),
    )


@router.get("/projects", response_model=List[BlueprintProjectSummaryOut])
def list_blueprint_projects(db: Session = Depends(get_db)):
    return get_all_blueprint_projects(db)


@router.get("/drawing-types", response_model=List[str])
def list_drawing_types(db: Session = Depends(get_db)):
    types = (
        db.query(BlueprintDrawing.drawing_type)
        .filter(BlueprintDrawing.is_published == True)
        .distinct()
        .order_by(BlueprintDrawing.drawing_type)
        .all()
    )
    return [t[0] for t in types]


@router.get("/{slug_or_id}", response_model=BlueprintDrawingDetailOut)
def get_blueprint_detail(slug_or_id: str, db: Session = Depends(get_db)):
    if slug_or_id.isdigit():
        drawing = db.query(BlueprintDrawing).filter(BlueprintDrawing.id == int(slug_or_id), BlueprintDrawing.is_published == True).first()
    else:
        drawing = db.query(BlueprintDrawing).filter(BlueprintDrawing.slug == slug_or_id, BlueprintDrawing.is_published == True).first()

    if not drawing:
        raise HTTPException(status_code=404, detail=f"Blueprint drawing '{slug_or_id}' not found")

    return drawing


def generate_architectural_sheet_pdf(drawing: BlueprintDrawing) -> bytes:
    """
    Generates a valid, minimal vector PDF document representing an architectural sheet
    with title block, drawing number, scale, date, and technical border.
    """
    title = drawing.title.replace("(", "").replace(")", "")
    project = drawing.project_name.replace("(", "").replace(")", "")
    drg_no = (drawing.drawing_number or "SD-DRG-01").replace("(", "").replace(")", "")
    rev = (drawing.revision or "R0").replace("(", "").replace(")", "")
    scale = (drawing.scale or "NTS").replace("(", "").replace(")", "")
    date_str = (drawing.date or "2026").replace("(", "").replace(")", "")
    drg_type = drawing.drawing_type.replace("(", "").replace(")", "")
    room = (drawing.room_area or "Overall").replace("(", "").replace(")", "")

    # PDF Stream commands for landscape A4 (842 x 595 points)
    # Architectural borders, grid, title block, and annotations
    stream_content = f"""q
0.5 w
0.2 0.2 0.2 RG
% Outer boundary border
28 28 786 539 re S
% Inner border
34 34 774 527 re S

% Grid markers
1 w
34 561 m 44 561 l S
808 561 m 798 561 l S
34 34 m 44 34 l S
808 34 m 798 34 l S

% Title Block Box (bottom right)
520 34 288 120 re S
520 120 m 808 120 l S
520 86 m 808 86 l S
520 60 m 808 60 l S
664 34 m 664 86 l S

% Title Block Text
BT
/F1 14 Tf
530 134 Td
(STUDIO DESIRE) Tj
/F2 8 Tf
0 -12 Td
(ARCHITECTURAL & INTERIOR DESIGN ARCHIVE) Tj
/F2 9 Tf
0 -26 Td
(PROJECT: {project}) Tj
/F1 10 Tf
0 -14 Td
({title}) Tj
/F2 8 Tf
0 -18 Td
(DRG NO: {drg_no}) Tj
144 0 Td
(REV: {rev}) Tj
-144 -14 Td
(SCALE: {scale}) Tj
144 0 Td
(DATE: {date_str}) Tj
-144 -12 Td
(TYPE: {drg_type} | AREA: {room}) Tj
ET

% Architectural Schematic Linework in drawing space
0.75 w
0.3 0.3 0.3 RG
80 180 380 320 re S
80 340 m 460 340 l S
270 180 m 270 500 l S
% Wall thickness representation
0.25 w
0.5 0.5 0.5 RG
85 185 370 310 re S
% Column indicators
0.8 w
0.1 0.1 0.1 RG
76 176 8 8 re f
456 176 8 8 re f
76 496 8 8 re f
456 496 8 8 re f
266 336 8 8 re f

% Dimension witness lines
0.2 w
[2 2] 0 d
60 180 m 60 500 l S
80 520 m 460 520 l S
[] 0 d
BT
/F2 7 Tf
48 335 Td
90 rotate
(6,400 MM) Tj
-90 rotate
230 525 Td
(8,200 MM) Tj
ET

Q
"""
    stream_bytes = stream_content.encode("latin-1")
    stream_len = len(stream_bytes)

    # Construct objects
    # 1: Catalog, 2: Pages, 3: Page, 4: Content Stream, 5: F1 (Helvetica-Bold), 6: F2 (Helvetica)
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj\n"
    )
    obj4 = (
        f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin-1")
        + stream_bytes
        + b"\nendstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n"
    obj6 = b"6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.4\n"
    offsets = []
    current_offset = len(header)

    objects = [obj1, obj2, obj3, obj4, obj5, obj6]
    body = b""
    for o in objects:
        offsets.append(current_offset)
        body += o
        current_offset += len(o)

    xref_offset = len(header) + len(body)
    xref = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode("latin-1")

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("latin-1")

    return header + body + xref + trailer


@router.get("/{slug_or_id}/pdf")
def get_blueprint_pdf(slug_or_id: str, db: Session = Depends(get_db)):
    if slug_or_id.isdigit():
        drawing = db.query(BlueprintDrawing).filter(BlueprintDrawing.id == int(slug_or_id), BlueprintDrawing.is_published == True).first()
    else:
        drawing = db.query(BlueprintDrawing).filter(BlueprintDrawing.slug == slug_or_id, BlueprintDrawing.is_published == True).first()

    if not drawing:
        raise HTTPException(status_code=404, detail=f"Blueprint drawing '{slug_or_id}' not found")

    pdf_bytes = generate_architectural_sheet_pdf(drawing)
    filename = f"{drawing.slug}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
