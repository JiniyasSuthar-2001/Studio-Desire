"""
STUDIO DESIRE — DATABASE SEED SCRIPT
Usage: py backend/seed.py

This script wipes existing demo tables and seeds:
1. 10 realistic architectural interior projects with photography & video walkthroughs.
2. 12 bespoke interior products and furniture concepts with archival imagery & specifications.
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

try:
    from app.database.session import SessionLocal, engine, Base
    from app.models.project import Project, ProjectMedia
    from app.models.product import Product, ProductMedia
    from app.models.contact import ContactInquiry
    from app.models.visualization import VisualizationSpace, VisualizationMedia
    from app.models.blueprint import BlueprintDrawing
    from app.models.user import User, UserRole
    from app.models.activity import ActivityLog
    from app.models.content import SiteContent
    from app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
    from app.core.security import hash_password
except ImportError:
    from backend.app.database.session import SessionLocal, engine, Base
    from backend.app.models.project import Project, ProjectMedia
    from backend.app.models.product import Product, ProductMedia
    from backend.app.models.contact import ContactInquiry
    from backend.app.models.visualization import VisualizationSpace, VisualizationMedia
    from backend.app.models.blueprint import BlueprintDrawing
    from backend.app.models.user import User, UserRole
    from backend.app.models.activity import ActivityLog
    from backend.app.models.content import SiteContent
    from backend.app.models.enquiry import ProjectEnquiry, ProjectEnquiryAttachment
    from backend.app.core.security import hash_password


DEMO_PROJECTS = [
    {
        "title": "Hardikbhai",
        "slug": "hardikbhai",
        "subtitle": "Comprehensive Residential Interior 3D Visualization",
        "location": "Ahmedabad, Gujarat",
        "year": 2026,
        "category": "Residential",
        "project_type": "Private Residence",
        "area": "Residential Interior",
        "featured": True,
        "is_demo": False,
        "grid_span": "span-7",
        "aspect_ratio": "ratio-landscape",
        "description": "Completed residential interior 3D visualization for client Hardikbhai executed by Studio Desire (Designers: Zenith Suthar & Chetna Bhati, Ahmedabad). The project spans 24 comprehensive rendered perspectives across 6 primary living zones: Entrance, Living Room, Dining & Kitchen, Parents Room, Guest Room, and Master Bedroom, featuring custom timber paneling, concealed joinery, and layered ambient lighting.",
        "cover_image": "/uploads/projects/hardik-bhai/cover.webp",
        "media": [
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/entrance-01.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/entrance-01-thumb.webp",
                "caption": "Entrance — Primary Entry Axis with custom fluted timber wall cladding.",
                "alt_text": "Hardikbhai Entrance Render 01",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/entrance-02.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/entrance-02-thumb.webp",
                "caption": "Entrance — Integrated console table and vertical acoustic wall paneling.",
                "alt_text": "Hardikbhai Entrance Render 02",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/entrance-03.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/entrance-03-thumb.webp",
                "caption": "Entrance — Spatial threshold perspective looking toward living salon.",
                "alt_text": "Hardikbhai Entrance Render 03",
                "sort_order": 3
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/living-room-01.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/living-room-01-thumb.webp",
                "caption": "Living Room — Primary lounge seating and monolithic media wall joinery.",
                "alt_text": "Hardikbhai Living Room Render 01",
                "sort_order": 4
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/living-room-02.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/living-room-02-thumb.webp",
                "caption": "Living Room — Opposite perspective highlighting glazing and ceiling cove wash.",
                "alt_text": "Hardikbhai Living Room Render 02",
                "sort_order": 5
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/living-room-03.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/living-room-03-thumb.webp",
                "caption": "Living Room — Cross-axis architectural overview of the seating arrangement.",
                "alt_text": "Hardikbhai Living Room Render 03",
                "sort_order": 6
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/living-room-04.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/living-room-04-thumb.webp",
                "caption": "Living Room — Detail angle framing bespoke upholstery and textured accents.",
                "alt_text": "Hardikbhai Living Room Render 04",
                "sort_order": 7
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-01.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/dining-kitchen-01-thumb.webp",
                "caption": "Dining & Kitchen — Dining table ensemble and culinary island relationship.",
                "alt_text": "Hardikbhai Dining and Kitchen Render 01",
                "sort_order": 8
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-02.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/dining-kitchen-02-thumb.webp",
                "caption": "Dining & Kitchen — Minimalist handleless cabinetry and quartz work surfaces.",
                "alt_text": "Hardikbhai Dining and Kitchen Render 02",
                "sort_order": 9
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-03.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/dining-kitchen-03-thumb.webp",
                "caption": "Dining & Kitchen — Wide spatial view toward custom storage towers.",
                "alt_text": "Hardikbhai Dining and Kitchen Render 03",
                "sort_order": 10
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-04.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/dining-kitchen-04-thumb.webp",
                "caption": "Dining & Kitchen — Breakfast counter and integrated appliance wall.",
                "alt_text": "Hardikbhai Dining and Kitchen Render 04",
                "sort_order": 11
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/parents-room-01.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/parents-room-01-thumb.webp",
                "caption": "Parents Room — Fluted bed back paneling with symmetrical nightstand niches.",
                "alt_text": "Hardikbhai Parents Room Render 01",
                "sort_order": 12
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/parents-room-02.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/parents-room-02-thumb.webp",
                "caption": "Parents Room — Full room perspective showing tailored wardrobe wall.",
                "alt_text": "Hardikbhai Parents Room Render 02",
                "sort_order": 13
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/parents-room-03.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/parents-room-03-thumb.webp",
                "caption": "Parents Room — Glazing and quiet contemplation seating nook.",
                "alt_text": "Hardikbhai Parents Room Render 03",
                "sort_order": 14
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/parents-room-04.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/parents-room-04-thumb.webp",
                "caption": "Parents Room — Floating vanity counter and television credenza.",
                "alt_text": "Hardikbhai Parents Room Render 04",
                "sort_order": 15
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/guest-room-01.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/guest-room-01-thumb.webp",
                "caption": "Guest Room — Neutral minimalist sleeping area with bespoke headboard.",
                "alt_text": "Hardikbhai Guest Room Render 01",
                "sort_order": 16
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/guest-room-02.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/guest-room-02-thumb.webp",
                "caption": "Guest Room — Full-height wardrobe joinery and dressing mirror.",
                "alt_text": "Hardikbhai Guest Room Render 02",
                "sort_order": 17
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/guest-room-03.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/guest-room-03-thumb.webp",
                "caption": "Guest Room — Diagonal spatial overview with natural daylight filtering.",
                "alt_text": "Hardikbhai Guest Room Render 03",
                "sort_order": 18
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/guest-room-04.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/guest-room-04-thumb.webp",
                "caption": "Guest Room — Study desk niche with floating shelf storage.",
                "alt_text": "Hardikbhai Guest Room Render 04",
                "sort_order": 19
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/master-bedroom-01.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-01-thumb.webp",
                "caption": "Master Bedroom — Monolithic fluted wall backdrop and king bed suite.",
                "alt_text": "Hardikbhai Master Bedroom Render 01",
                "sort_order": 20
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/master-bedroom-02.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-02-thumb.webp",
                "caption": "Master Bedroom — Dressing area with bronze-tinted glass shutter wardrobe.",
                "alt_text": "Hardikbhai Master Bedroom Render 02",
                "sort_order": 21
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/master-bedroom-03.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-03-thumb.webp",
                "caption": "Master Bedroom — Lounge armchair corner with expansive window view.",
                "alt_text": "Hardikbhai Master Bedroom Render 03",
                "sort_order": 22
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/master-bedroom-04.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-04-thumb.webp",
                "caption": "Master Bedroom — Architectural media wall and floating dresser console.",
                "alt_text": "Hardikbhai Master Bedroom Render 04",
                "sort_order": 23
            },
            {
                "media_type": "image",
                "url": "/uploads/projects/hardik-bhai/master-bedroom-05.webp",
                "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-05-thumb.webp",
                "caption": "Master Bedroom — Comprehensive room overview across main spatial axis.",
                "alt_text": "Hardikbhai Master Bedroom Render 05",
                "sort_order": 24
            }
        ]
    },
    {
        "title": "Project AA",
        "slug": "project-aa",
        "subtitle": "Contemporary Minimalist Residence with Multi-Tier Spatial VR Portals",
        "location": "Ahmedabad, Gujarat",
        "year": 2026,
        "category": "Residential",
        "project_type": "Private Residence",
        "area": "7,200 sq.ft",
        "featured": True,
        "is_demo": False,
        "grid_span": "span-7",
        "aspect_ratio": "ratio-landscape",
        "description": "An architectural dwelling designed around fluid spatial transitions, tactile natural materials, and multi-tier interactive virtual reality portals. Explores open culinary volumes, meditative sleeping suites, and deep sheltered outdoor verandas.",
        "cover_image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=85",
        "vr_url": "https://vr.studiodesire.design/project-aa-full-property",
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1600&q=85",
                "caption": "Project AA — Culinary kitchen island with honed travertine finish.",
                "alt_text": "Project AA Kitchen",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1600&q=85",
                "caption": "Project AA — Primary suite with slatted timber backdrop.",
                "alt_text": "Project AA Bedroom",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1600&q=85",
                "caption": "Project AA — Deep sheltered balcony and sunset deck.",
                "alt_text": "Project AA Balcony",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Residence 01",
        "slug": "residence-01",
        "subtitle": "Minimalist Haven with Natural Travertine & Raw Oak",
        "location": "Ahmedabad",
        "year": 2026,
        "category": "Residential",
        "project_type": "Private Residence",
        "area": "6,400 sq.ft",
        "featured": True,
        "is_demo": True,
        "grid_span": "span-7",
        "aspect_ratio": "ratio-landscape",
        "description": "A serene residential interior exploring monolithic spatial volumes, warm lime plaster textures, and bespoke Japanese joinery. The design harmonizes soft daylight filtering through floor-to-ceiling fenestrations with organic travertine stone accents and quiet contemplation alcoves.",
        "cover_image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=85",
        "media": [
            {
                "media_type": "video",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=85",
                "caption": "Spatial walkthrough of the central living pavilion and garden lightwell.",
                "alt_text": "Residence 01 Video Walkthrough",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Main living gallery featuring monolithic hearth and bespoke linen lounge.",
                "alt_text": "Living Pavilion with monolithic hearth",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1600&q=85",
                "caption": "Culinary studio with fluted travertine island and concealed joinery.",
                "alt_text": "Kitchen and culinary studio",
                "sort_order": 3
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1600&q=85",
                "caption": "Primary suite highlighting limewashed planes and morning sunlight.",
                "alt_text": "Primary suite interior view",
                "sort_order": 4
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Bath sanctuary carved from split-face sandstone with concealed perimeter illumination.",
                "alt_text": "Sandstone bath sanctuary",
                "sort_order": 5
            }
        ]
    },
    {
        "title": "Villa 02",
        "slug": "villa-02",
        "subtitle": "Coastal Sanctuary Framed in Tactile Earth & Teak",
        "location": "Alibaug",
        "year": 2025,
        "category": "Residential",
        "project_type": "Coastal Retreat",
        "area": "8,200 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-5",
        "aspect_ratio": "ratio-portrait",
        "description": "Nestled between coastal groves and saline breezes, Villa 02 utilizes rammed earth tones, reclaimed Burma teak timber, and generous open-air colonnades to create a tranquil sanctuary where interior and landscape dissolve effortlessly.",
        "cover_image": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Enclosed courtyard gallery framing local coastal flora.",
                "alt_text": "Courtyard gallery and flora",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1600&q=85",
                "caption": "Dining colonnade finished in textured lime wash and hand-rubbed teak.",
                "alt_text": "Dining colonnade with teak details",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1600&q=85",
                "caption": "Reading salon with custom low-slung upholstery and brushed brass fixtures.",
                "alt_text": "Reading salon interior",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Apartment 03",
        "slug": "apartment-03",
        "subtitle": "Urban Penthouse with Refined Architectural Lines",
        "location": "Mumbai",
        "year": 2025,
        "category": "Residential",
        "project_type": "High-Rise Penthouse",
        "area": "3,800 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-4",
        "aspect_ratio": "ratio-standard",
        "description": "An elevated urban dwelling designed as a tranquil counterpoint to city density. The layout leverages floating micro-cement partitions, dark stained walnut cabinetry, and bronze-framed glazing to capture uninterrupted skyline panoramas.",
        "cover_image": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "video",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1400&q=85",
                "caption": "Twilight sequence showing the interplay of indirect lighting and walnut panelling.",
                "alt_text": "Apartment 03 Twilight Video",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1600&q=85",
                "caption": "Open living composition with integrated cantilevered credenza.",
                "alt_text": "Open living area with credenza",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1600&q=85",
                "caption": "Master dressing suite clad in smoked oak and textured linen screens.",
                "alt_text": "Master dressing suite",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Restaurant 04",
        "slug": "restaurant-04",
        "subtitle": "Intimate Fine Dining Architecture of Shadow & Stone",
        "location": "New Delhi",
        "year": 2024,
        "category": "Hospitality",
        "project_type": "Fine Dining Space",
        "area": "4,500 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-4",
        "aspect_ratio": "ratio-standard",
        "description": "An experiential culinary journey centered around atmospheric chiaroscuro. Raw volcanic basalt stone, acoustic wool baffle ceilings, and pin-spot illuminating tables create intimate social enclaves within a generous vaulted volume.",
        "cover_image": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1600&q=85",
                "caption": "The central dining nave with sculptural basalt banquet tables.",
                "alt_text": "Central dining room with basalt tables",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1600&q=85",
                "caption": "Private wine cellar lounge lined with blackened steel vitrines.",
                "alt_text": "Wine cellar lounge",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1559339352-11d035aa65de?auto=format&fit=crop&w=1600&q=85",
                "caption": "Omakase counter showcasing a single unbroken slab of honed black granite.",
                "alt_text": "Omakase granite counter",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Office Space 05",
        "slug": "office-space-05",
        "subtitle": "Biophilic Creative Headquarters with Acoustic Timber Enclosures",
        "location": "Bengaluru",
        "year": 2025,
        "category": "Office",
        "project_type": "Design Studio & Headquarters",
        "area": "12,000 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-4",
        "aspect_ratio": "ratio-standard",
        "description": "A forward-thinking workspace that challenges corporate orthodoxy. Through modular acoustic timber pods, cascading indoor botanical gardens, and ambient diffused skylights, the environment fosters quiet concentration alongside collaborative cross-pollination.",
        "cover_image": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "video",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=85",
                "caption": "Exploration of modular meeting volumes and diffused light ceiling canopy.",
                "alt_text": "Office Space 05 Walkthrough",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Collaborative atrium with custom terrazzo amphitheater seating.",
                "alt_text": "Collaborative atrium amphitheater",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1600&q=85",
                "caption": "Executive think-tank enclosed in curved reeded glass partitions.",
                "alt_text": "Think-tank with reeded glass",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Residence 06",
        "slug": "residence-06",
        "subtitle": "Tropical Vernacular Villa Clad in Hand-Chiseled Laterite",
        "location": "Goa",
        "year": 2024,
        "category": "Residential",
        "project_type": "Tropical Residence",
        "area": "5,800 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-12",
        "aspect_ratio": "ratio-hero",
        "description": "Rooted in Goa's rich architectural legacy, Residence 06 pairs traditional deep verandas and hand-cut red laterite stone with razor-sharp modernist geometry. Polished IPS cement floors and terracotta louvers allow monsoon winds to naturally cool every wing.",
        "cover_image": "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1800&q=85",
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1600&q=85",
                "caption": "Transition veranda connecting the living pavilion to the reflection pond.",
                "alt_text": "Veranda and reflection pond",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1600&q=85",
                "caption": "Open-plan dining space featuring hand-cast terrazzo dining suite.",
                "alt_text": "Open dining area in terrazzo",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1600&q=85",
                "caption": "Outdoor courtyard shower surrounded by lush philodendrons and laterite masonry.",
                "alt_text": "Courtyard outdoor shower",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Villa 07",
        "slug": "villa-07",
        "subtitle": "Courtyard Palace Reimagined in White Makrana Marble",
        "location": "Udaipur",
        "year": 2025,
        "category": "Residential",
        "project_type": "Lakeside Estate",
        "area": "9,500 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-5",
        "aspect_ratio": "ratio-portrait",
        "description": "An estate celebrating the timeless dignity of stone craftsmanship. Overlooking calm waters, the residence interprets classical jali screens as dynamic kinetic bronze louvers that throw intricate shadow tapestries across white Makrana marble floors.",
        "cover_image": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "video",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1400&q=85",
                "caption": "Afternoon sun casting dynamic geometry across the marble courtyard arcade.",
                "alt_text": "Villa 07 Walkthrough",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1600&q=85",
                "caption": "The grand portico showcasing double-height fluted marble colonnades.",
                "alt_text": "Grand portico with marble colonnades",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1600&q=85",
                "caption": "Drawing room featuring bespoke bouclé seating and antique brass hardware.",
                "alt_text": "Drawing room with bouclé seating",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Cafe 08",
        "slug": "cafe-08",
        "subtitle": "Artisanal Roastery in Terracotta, Lime, & Cast Bronze",
        "location": "Jaipur",
        "year": 2024,
        "category": "Hospitality",
        "project_type": "Specialty Cafe & Roastery",
        "area": "2,200 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-7",
        "aspect_ratio": "ratio-landscape",
        "description": "Honoring Jaipur's terracotta pottery heritage, Cafe 08 features a sculptural central counter cast entirely from indigenous pink terracotta clay. Curved lime-plaster arches and unlacquered bronze details create a sensory haven for specialty coffee enthusiasts.",
        "cover_image": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1600&q=85",
                "caption": "Sculptural terracotta brew bar with custom brass pour-over fittings.",
                "alt_text": "Terracotta brew bar",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=1600&q=85",
                "caption": "Seating alcoves recessed into arched lime plaster niches.",
                "alt_text": "Seating niches and arches",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?auto=format&fit=crop&w=1600&q=85",
                "caption": "Sunlit rear courtyard with hand-thrown ceramic planters and olive trees.",
                "alt_text": "Rear courtyard with olive trees",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Apartment 09",
        "slug": "apartment-09",
        "subtitle": "Monochromatic Sanctuary Defined by Silence and Form",
        "location": "Pune",
        "year": 2026,
        "category": "Residential",
        "project_type": "Duplex Residence",
        "area": "4,100 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-6",
        "aspect_ratio": "ratio-standard",
        "description": "Conceived as an exercise in architectural reduction. A strictly controlled palette of warm chalk tones, raw silk upholstery, and smoked Belgian oak floors allows subtle gradations of natural sunlight to define the spatial boundaries throughout the day.",
        "cover_image": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1600&q=85",
                "caption": "Double-height living volume with monolithic floating fireplace.",
                "alt_text": "Living volume with floating fireplace",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1600&q=85",
                "caption": "Study mezzanine overlooking the internal courtyard garden.",
                "alt_text": "Study mezzanine",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Minimalist entry foyer with recessed shadow-gap reveals.",
                "alt_text": "Entry foyer with shadow-gap details",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Studio 10",
        "slug": "studio-10",
        "subtitle": "Curated Fashion & Object Atelier with Sculptural Volumes",
        "location": "Ahmedabad",
        "year": 2025,
        "category": "Retail",
        "project_type": "Flagship Atelier & Gallery",
        "area": "3,100 sq.ft",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-6",
        "aspect_ratio": "ratio-landscape",
        "description": "An architectural retail concept designed like an art archive. Garments and artisanal objects are displayed on custom cast-concrete plinths against hand-scraped lime plaster walls, transforming the shopping experience into a serene gallery walkthrough.",
        "cover_image": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1400&q=85",
        "media": [
            {
                "media_type": "video",
                "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
                "thumbnail_url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1400&q=85",
                "caption": "Spatial walkthrough showcasing cast-concrete plinths and suspended light channels.",
                "alt_text": "Studio 10 Walkthrough",
                "sort_order": 1
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1600&q=85",
                "caption": "Main gallery displaying curated textiles on monolithic cast-concrete blocks.",
                "alt_text": "Main gallery with concrete plinths",
                "sort_order": 2
            },
            {
                "media_type": "image",
                "url": "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1600&q=85",
                "caption": "Accessory display niche with warm directional fiber-optic lighting.",
                "alt_text": "Accessory display niche",
                "sort_order": 3
            }
        ]
    }
]

DEMO_PRODUCTS = [
    {
        "title": "Modular Lounge Chair",
        "slug": "modular-lounge-chair",
        "subtitle": "Sculptural Low-Profile Armchair in Bouclé & Smoked Ash",
        "category": "Seating",
        "description": "A low-slung modular armchair conceived for architectural reception areas and meditative residential alcoves. Deep pocket springs wrapped in tactile natural wool bouclé rest upon an internal solid smoked-ash cradle with concealed shadow reveals.",
        "cover_image": "https://images.unsplash.com/photo-1580481077195-c3a821a7884d?auto=format&fit=crop&w=1200&q=85",
        "year": 2026,
        "materials": "Smoked Ash, Natural Wool Bouclé, High-Resilience Core",
        "dimensions": "W 940 × D 880 × H 710 mm",
        "featured": True,
        "is_demo": True,
        "grid_span": "span-7",
        "aspect_ratio": "ratio-landscape",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1580481077195-c3a821a7884d?auto=format&fit=crop&w=1600&q=85",
                "caption": "Primary perspective displaying geometric volume and tailored upholstery lines.",
                "alt_text": "Modular Lounge Chair Perspective",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Detail of wool bouclé texture and shadow-gap joinery on smoked ash plinth.",
                "alt_text": "Boucle texture close up",
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Sculptural Side Table",
        "slug": "sculptural-side-table",
        "subtitle": "Monolithic Cylindrical Pedestal in Honed Travertine",
        "category": "Tables",
        "description": "Carved from a singular block of unpolished Roman travertine, this sculptural pedestal features soft fluted vertical relief work and an inset circular top that catches grazing raking daylight.",
        "cover_image": "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?auto=format&fit=crop&w=1200&q=85",
        "year": 2025,
        "materials": "Roman Travertine, Honed Matte Sealant",
        "dimensions": "Ø 420 × H 520 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-5",
        "aspect_ratio": "ratio-portrait",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1533090161767-e6ffed986c88?auto=format&fit=crop&w=1600&q=85",
                "caption": "Architectural silhouette showing stone vein continuity.",
                "alt_text": "Travertine side table pedestal",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Linear Dining Table",
        "slug": "linear-dining-table",
        "subtitle": "Minimalist 10-Seater in Solid White Oak & Patinated Bronze",
        "category": "Tables",
        "description": "A 3.2-meter dining table celebrating long architectural sightlines. A continuous grain European white oak slab is suspended across two monolithic blade trestles joined with hand-patinated dark bronze tension ties.",
        "cover_image": "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?auto=format&fit=crop&w=1400&q=85",
        "year": 2026,
        "materials": "European White Oak, Cast Bronze Hardware",
        "dimensions": "L 3200 × W 1050 × H 750 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-12",
        "aspect_ratio": "ratio-hero",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?auto=format&fit=crop&w=1600&q=85",
                "caption": "Panoramic table composition showing continuous wood slab grain.",
                "alt_text": "Solid white oak dining table",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1577140917170-285929fb55b7?auto=format&fit=crop&w=1600&q=85",
                "caption": "Trestle joinery detail with patinated dark bronze fasteners.",
                "alt_text": "Bronze joinery detail",
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Minimal Bed System",
        "slug": "minimal-bed-system",
        "subtitle": "Cantilevered Low Platform Bed with Floating Side Consoles",
        "category": "Beds",
        "description": "An architectural sleeping platform engineered with a recessed plinth that creates a floating visual lightness. The wide headboard features integrated soft indirect perimeter warmth and cantilevered stone ledges.",
        "cover_image": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1200&q=85",
        "year": 2025,
        "materials": "Bleached American Walnut, Belgian Linen, Sandstone",
        "dimensions": "W 2400 × L 2250 × H 820 mm (Mattress 1800×2000)",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-6",
        "aspect_ratio": "ratio-standard",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1600&q=85",
                "caption": "Platform bed system installed in contemporary limewashed suite.",
                "alt_text": "Minimalist low platform bed",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Oak Storage Unit",
        "slug": "oak-storage-unit",
        "subtitle": "Wall-Mounted Architectural Credenza with Concealed Shadow Reveals",
        "category": "Storage",
        "description": "A precision-crafted floating credenza designed to integrate seamlessly into lime plaster walls. Features touch-latched sliding panel doors with acoustic fabric infills and internal cable management channels.",
        "cover_image": "https://images.unsplash.com/photo-1595428774223-ef52624120d2?auto=format&fit=crop&w=1200&q=85",
        "year": 2025,
        "materials": "Quarter-Sawn White Oak, Acoustic Linen, Steel Subframe",
        "dimensions": "W 2200 × D 460 × H 550 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-6",
        "aspect_ratio": "ratio-standard",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1595428774223-ef52624120d2?auto=format&fit=crop&w=1600&q=85",
                "caption": "Floating credenza showcasing subtle continuous oak woodgrain.",
                "alt_text": "Wall mounted oak credenza",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Pendant Light 01",
        "slug": "pendant-light-01",
        "subtitle": "Hand-Spun Raw Brass Disc with Warm Diffused Downlight",
        "category": "Lighting",
        "description": "A poetic minimal pendant composed of a wide hand-spun raw brass reflector dish and a central frosted matte glass sphere. Emits a soft ambient halo upward while washing table surfaces in flattering 2700K warmth.",
        "cover_image": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1200&q=85",
        "year": 2024,
        "materials": "Hand-Spun Unlacquered Brass, Mouth-Blown Matte Glass",
        "dimensions": "Ø 580 × H 180 mm (Suspension up to 2500 mm)",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-4",
        "aspect_ratio": "ratio-portrait",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Illuminated brass disc creating ambient atmospheric gradients.",
                "alt_text": "Spun brass pendant luminaire",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Statement Lounge Chair",
        "slug": "statement-lounge-chair",
        "subtitle": "Organic Contoured Occasional Chair in Cognac Saddle Leather",
        "category": "Seating",
        "description": "An architectural lounge chair that pairs organic curvature with rigorous geometric balance. Full-grain vegetable-tanned saddle leather is hand-stitched over a molded beech wood shell and cantilevered gunmetal steel legs.",
        "cover_image": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=1200&q=85",
        "year": 2025,
        "materials": "Saddle Leather, Molded Beech, Blackened Gunmetal Steel",
        "dimensions": "W 860 × D 820 × H 740 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-4",
        "aspect_ratio": "ratio-portrait",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&w=1600&q=85",
                "caption": "Profile view highlighting saddle stitch details and bronze brackets.",
                "alt_text": "Cognac leather lounge chair",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Floating Console",
        "slug": "floating-console",
        "subtitle": "Cantilevered Foyer Shelf in Honed Basalt & Smoked Oak",
        "category": "Storage",
        "description": "Conceived for entrance foyers and residential hallways. A monolithic slab of volcanic basalt stone is embedded onto a concealed steel bracket with an under-slung slim drawer carved from smoked Belgian oak.",
        "cover_image": "https://images.unsplash.com/photo-1538688525198-9b88f6f53126?auto=format&fit=crop&w=1200&q=85",
        "year": 2026,
        "materials": "Volcanic Basalt, Smoked Oak, Internal Structural Steel",
        "dimensions": "W 1600 × D 380 × H 160 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-4",
        "aspect_ratio": "ratio-portrait",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1538688525198-9b88f6f53126?auto=format&fit=crop&w=1600&q=85",
                "caption": "Entryway installation with subtle shadow-line reveal.",
                "alt_text": "Floating stone console shelf",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Custom Wardrobe System",
        "slug": "custom-wardrobe-system",
        "subtitle": "Floor-to-Ceiling Millwork with Fluted Glass & Bronze Hardware",
        "category": "Custom",
        "description": "A bespoke dressing room joinery system customized to client spatial heights. Combines fluted safety glass doors with integrated micro-LED reveals and interior drawers lined in natural saddle suede.",
        "cover_image": "https://images.unsplash.com/photo-1558997519-83ea9252def8?auto=format&fit=crop&w=1400&q=85",
        "year": 2026,
        "materials": "Smoked Eucalyptus, Fluted Glass, Patinated Bronze, Suede",
        "dimensions": "Custom Bespoke Architectural Commission",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-7",
        "aspect_ratio": "ratio-landscape",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1558997519-83ea9252def8?auto=format&fit=crop&w=1600&q=85",
                "caption": "Integrated wardrobe pavilion with internal warm fiber illumination.",
                "alt_text": "Bespoke wardrobe millwork system",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Architectural Coffee Table",
        "slug": "architectural-coffee-table",
        "subtitle": "Low Cast-Concrete Plinth with Inset Fluted Walnut Tray",
        "category": "Tables",
        "description": "Inspired by brutalist concrete architectural foundations. A low-slung, ultra-matte micro-cement plinth is punctuated by an asymmetrical recessed removable tray crafted from dark American walnut.",
        "cover_image": "https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=1200&q=85",
        "year": 2025,
        "materials": "Engineered Micro-Cement, Solid Walnut, Felt Base",
        "dimensions": "W 1400 × D 900 × H 320 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-5",
        "aspect_ratio": "ratio-portrait",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1532372320572-cda25653a26d?auto=format&fit=crop&w=1600&q=85",
                "caption": "Low-profile perspective showing contrast between concrete and walnut.",
                "alt_text": "Low concrete coffee table",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Soft Lounge Sofa",
        "slug": "soft-lounge-sofa",
        "subtitle": "Deep Modular 3-Piece Landscape Sofa in Textured Neutral Linen",
        "category": "Furniture",
        "description": "An architectural landscape sofa designed for deep lounging and relaxed hospitality. Constructed with generous proportions, down feather wrapped cushioning, and durable Italian textural linen slipcovers.",
        "cover_image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=1400&q=85",
        "year": 2026,
        "materials": "Italian Textured Linen, Feather & Down Core, FSC Pine Subframe",
        "dimensions": "W 3100 × D 1120 × H 720 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-6",
        "aspect_ratio": "ratio-standard",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=1600&q=85",
                "caption": "Living room landscape arrangement with tactile linen upholstery.",
                "alt_text": "Soft neutral lounge sofa",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Studio Floor Lamp",
        "slug": "studio-floor-lamp",
        "subtitle": "Slender Architectural Floor Luminaire in Bronzed Steel & Travertine",
        "category": "Lighting",
        "description": "A tall, minimal floor lamp composed of a heavy circular travertine balance base, a slender 1.8-meter bronzed steel stem, and a directional curved reflector shield for reading and ambient wall washing.",
        "cover_image": "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?auto=format&fit=crop&w=1200&q=85",
        "year": 2025,
        "materials": "Bronzed Steel, Roman Travertine, Diffused Warm LED",
        "dimensions": "Ø 340 (base) × H 1820 mm",
        "featured": False,
        "is_demo": True,
        "grid_span": "span-6",
        "aspect_ratio": "ratio-standard",
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1513506003901-1e6a229e2d15?auto=format&fit=crop&w=1600&q=85",
                "caption": "Slender silhouette providing soft directional warmth.",
                "alt_text": "Architectural floor lamp",
                "sort_order": 1
            }
        ]
    }
]

DEMO_VISUALIZATIONS = [
    {
        "title": "Entrance Foyer",
        "slug": "hardikbhai-entrance",
        "project_name": "Hardikbhai",
        "room": "Entrance",
        "category": "Entrance",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "3ds Max · Corona Renderer",
        "description": "Architectural entry foyer designed for client Hardikbhai. Features full-height vertical timber fluting, concealed storage joinery, and warm directional cove illumination creating an inviting arrival threshold.",
        "cover_image": "/uploads/projects/hardik-bhai/entrance-01.webp",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 1,
        "media": [
            {
                "url": "/uploads/projects/hardik-bhai/entrance-01.webp",
                "caption": "Primary entry vista with fluted acoustic timber cladding and seamless concealed doors.",
                "angle": "Axial Entry View",
                "sort_order": 1
            },
            {
                "url": "/uploads/projects/hardik-bhai/entrance-02.webp",
                "caption": "Floating entry console table with minimalist accessories and vertical linear shadow reveals.",
                "angle": "Console Perspective",
                "sort_order": 2
            },
            {
                "url": "/uploads/projects/hardik-bhai/entrance-03.webp",
                "caption": "Threshold perspective overlooking the transition from foyer to formal living areas.",
                "angle": "Living Transition",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Main Living Room",
        "slug": "hardikbhai-living-room",
        "project_name": "Hardikbhai",
        "room": "Living Room",
        "category": "Living Room",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "3ds Max · Corona Renderer",
        "description": "Expansive central living room featuring tailored low-profile sectional seating, fluted timber media partition, and perimeter architectural ceiling cove lighting.",
        "cover_image": "/uploads/projects/hardik-bhai/living-room-01.webp",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 2,
        "media": [
            {
                "url": "/uploads/projects/hardik-bhai/living-room-01.webp",
                "caption": "Primary lounge perspective featuring bespoke upholstery and monolithic media joinery.",
                "angle": "Lounge & Media Wall",
                "sort_order": 1
            },
            {
                "url": "/uploads/projects/hardik-bhai/living-room-02.webp",
                "caption": "Opposite angle looking toward the full-height glazing and recessed curtain coves.",
                "angle": "Glazing Elevation",
                "sort_order": 2
            },
            {
                "url": "/uploads/projects/hardik-bhai/living-room-03.webp",
                "caption": "Cross-axis architectural overview capturing the dialogue between seating and foyer threshold.",
                "angle": "Spatial Overview",
                "sort_order": 3
            },
            {
                "url": "/uploads/projects/hardik-bhai/living-room-04.webp",
                "caption": "Detail vignette focusing on material transitions, fluted timber, and tactile fabric textures.",
                "angle": "Material Vignette",
                "sort_order": 4
            }
        ]
    },
    {
        "title": "Dining and Kitchen",
        "slug": "hardikbhai-dining-kitchen",
        "project_name": "Hardikbhai",
        "room": "Dining & Kitchen",
        "category": "Kitchen & Dining",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "3ds Max · Corona Renderer",
        "description": "Harmonious culinary and dining zone featuring an open-concept dining arrangement, integrated breakfast counter, seamless quartz surfaces, and concealed cabinetry.",
        "cover_image": "/uploads/projects/hardik-bhai/dining-kitchen-01.webp",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 3,
        "media": [
            {
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-01.webp",
                "caption": "Dining ensemble with sculptural table, upholstered armchairs, and linear task pendant.",
                "angle": "Dining Table & Island",
                "sort_order": 1
            },
            {
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-02.webp",
                "caption": "Kitchen preparation counter highlighting clean handleless finishes and stone splashbacks.",
                "angle": "Kitchen Prep Counter",
                "sort_order": 2
            },
            {
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-03.webp",
                "caption": "Wide spatial angle coordinating dining table, kitchen island, and custom storage towers.",
                "angle": "Wide Culinary View",
                "sort_order": 3
            },
            {
                "url": "/uploads/projects/hardik-bhai/dining-kitchen-04.webp",
                "caption": "Breakfast bar and integrated appliance wall with concealed LED profile lighting.",
                "angle": "Appliance Wall Angle",
                "sort_order": 4
            }
        ]
    },
    {
        "title": "Parents Room",
        "slug": "hardikbhai-parents-room",
        "project_name": "Hardikbhai",
        "room": "Parents Room",
        "category": "Bedroom",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "3ds Max · Corona Renderer",
        "description": "Quiet, grounded bedroom retreat with natural earth tones, acoustic fluted headboard paneling, tailored wardrobe storage, and gentle indirect illumination.",
        "cover_image": "/uploads/projects/hardik-bhai/parents-room-01.webp",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 4,
        "media": [
            {
                "url": "/uploads/projects/hardik-bhai/parents-room-01.webp",
                "caption": "Symmetrical bed back elevation with warm timber acoustic slats and integrated nightstands.",
                "angle": "Bed Back Elevation",
                "sort_order": 1
            },
            {
                "url": "/uploads/projects/hardik-bhai/parents-room-02.webp",
                "caption": "Full bedroom perspective displaying generous wardrobe carpentry and circulation space.",
                "angle": "Room Overview",
                "sort_order": 2
            },
            {
                "url": "/uploads/projects/hardik-bhai/parents-room-03.webp",
                "caption": "Window seating alcove with soft upholstery and natural daylight illumination.",
                "angle": "Window Seating",
                "sort_order": 3
            },
            {
                "url": "/uploads/projects/hardik-bhai/parents-room-04.webp",
                "caption": "Wall-mounted entertainment console and floating dressing vanity unit.",
                "angle": "Console & Dresser",
                "sort_order": 4
            }
        ]
    },
    {
        "title": "Guest Room",
        "slug": "hardikbhai-guest-room",
        "project_name": "Hardikbhai",
        "room": "Guest Room",
        "category": "Bedroom",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "3ds Max · Corona Renderer",
        "description": "Tailored guest suite utilizing neutral tones, bespoke wardrobe joinery, compact working study desk, and subtle indirect lighting.",
        "cover_image": "/uploads/projects/hardik-bhai/guest-room-01.webp",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 5,
        "media": [
            {
                "url": "/uploads/projects/hardik-bhai/guest-room-01.webp",
                "caption": "Guest bed setting with cushioned headboard and textured wall paneling.",
                "angle": "Bed Setting",
                "sort_order": 1
            },
            {
                "url": "/uploads/projects/hardik-bhai/guest-room-02.webp",
                "caption": "Integrated wardrobe storage and full-length dressing mirror perspective.",
                "angle": "Wardrobe Wall",
                "sort_order": 2
            },
            {
                "url": "/uploads/projects/hardik-bhai/guest-room-03.webp",
                "caption": "Diagonal spatial overview highlighting the calm, cohesive neutral palette.",
                "angle": "Diagonal Room View",
                "sort_order": 3
            },
            {
                "url": "/uploads/projects/hardik-bhai/guest-room-04.webp",
                "caption": "Built-in study desk corner with overhead display shelves and task lighting.",
                "angle": "Study Desk Alcove",
                "sort_order": 4
            }
        ]
    },
    {
        "title": "Master Bedroom",
        "slug": "hardikbhai-master-bedroom",
        "project_name": "Hardikbhai",
        "room": "Master Bedroom",
        "category": "Bedroom",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "3ds Max · Corona Renderer",
        "description": "Flagship master suite defined by an architectural fluted timber headboard backdrop, bronze-tinted glass shutter wardrobe suite, expansive window lounge, and integrated media console.",
        "cover_image": "/uploads/projects/hardik-bhai/master-bedroom-01.webp",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 6,
        "media": [
            {
                "url": "/uploads/projects/hardik-bhai/master-bedroom-01.webp",
                "caption": "Master bed focal vista with fluted timber paneling and ambient backlighting.",
                "angle": "Master Bed Focal View",
                "sort_order": 1
            },
            {
                "url": "/uploads/projects/hardik-bhai/master-bedroom-02.webp",
                "caption": "Bespoke dressing wardrobe suite featuring bronze-tinted glass shutters and internal lighting.",
                "angle": "Wardrobe & Dressing Suite",
                "sort_order": 2
            },
            {
                "url": "/uploads/projects/hardik-bhai/master-bedroom-03.webp",
                "caption": "Private lounge corner with sculptural armchair, shear drapes, and natural daylight.",
                "angle": "Lounge Seating Angle",
                "sort_order": 3
            },
            {
                "url": "/uploads/projects/hardik-bhai/master-bedroom-04.webp",
                "caption": "Architectural television console wall with cantilevered floating drawers.",
                "angle": "Media Wall & Dresser",
                "sort_order": 4
            },
            {
                "url": "/uploads/projects/hardik-bhai/master-bedroom-05.webp",
                "caption": "Comprehensive master suite spatial overview from the entrance threshold.",
                "angle": "Room Overview Axis",
                "sort_order": 5
            }
        ]
    },
    {
        "title": "Central Living Pavilion & Lightwell",
        "slug": "residence-01-living-pavilion",
        "project_name": "Residence 01",
        "room": "Living Room",
        "category": "Living Room",
        "year": 2026,
        "location": "Ahmedabad",
        "software": "Corona Renderer 11 · 3ds Max · Unreal Engine 5.4 VR",
        "description": "Double-height living pavilion exploring diffuse daylight calibration, monolithic honed travertine, and acoustic linen wall panels. Spatial lighting study captures the golden hour transition through 6-meter motorized glazing.",
        "cover_image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/residence-01-living",
        "has_vr": True,
        "sort_order": 1,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1600&q=85",
                "caption": "Dusk lighting study emphasizing recessed linear warm perimeter illumination.",
                "angle": "Dusk Atmosphere",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1600&q=85",
                "caption": "Material detail: Fluted travertine fireplace hearth and bespoke low-slung bouclé sofa.",
                "angle": "Detail Elevation",
                "sort_order": 2
            },
            {
                "url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1600&q=85",
                "caption": "Axial view looking toward the sunken conversation alcove and internal courtyard.",
                "angle": "Axial Wide Perspective",
                "sort_order": 3
            }
        ]
    },
    {
        "title": "Culinary Studio & Dining Alcove",
        "slug": "residence-01-culinary-studio",
        "project_name": "Residence 01",
        "room": "Dining & Kitchen",
        "category": "Kitchen & Dining",
        "year": 2026,
        "location": "Ahmedabad",
        "software": "Corona Renderer 11 · 3ds Max · Chaos Vantage VR",
        "description": "Monolithic fluted travertine island, seamless quarter-sawn oak cabinetry, and an intimate dining alcove overlooking a private bamboo lightwell. Engineered for culinary artistry and atmospheric hosting.",
        "cover_image": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/residence-01-kitchen",
        "has_vr": True,
        "sort_order": 2,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=1600&q=85",
                "caption": "Travertine preparation counter with integrated patinated bronze fixtures.",
                "angle": "Island Close-Up",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1617806118233-18e1de247200?auto=format&fit=crop&w=1600&q=85",
                "caption": "Minimalist dining setting with sculptural blackened timber table and linen pendants.",
                "angle": "Dining Elevation",
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Master Sanctuary Suite",
        "slug": "monolith-master-sanctuary",
        "project_name": "The Monolith Penthouse",
        "room": "Master Bedroom",
        "category": "Bedroom",
        "year": 2026,
        "location": "Mumbai",
        "software": "V-Ray 6 · 3ds Max · Unreal Engine VR",
        "description": "Private residential sanctuary balancing acoustic raw wool fabric walls, low-profile custom platform bed, and floor-to-ceiling skyline apertures with automated sheer drapery.",
        "cover_image": "https://images.unsplash.com/photo-1616594039964-ae9021a400a0?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/monolith-master-suite",
        "has_vr": True,
        "sort_order": 3,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=1600&q=85",
                "caption": "Early morning sunlight raking across the warm lime plaster accent wall.",
                "angle": "Morning Atmosphere",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?auto=format&fit=crop&w=1600&q=85",
                "caption": "Custom smoked oak floating nightstand and recessed warm LED reading beam.",
                "angle": "Joinery Detail",
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Skyline Lounge & Observatory",
        "slug": "monolith-skyline-lounge",
        "project_name": "The Monolith Penthouse",
        "room": "Penthouse Lounge",
        "category": "Lounge",
        "year": 2026,
        "location": "Mumbai",
        "software": "Corona Renderer 11 · 3ds Max · Unreal Engine 5.4 VR",
        "description": "Double-height observation lounge perched high above the Arabian Sea. Conceived with monolithic volcanic basalt hearth, curved bouclé conversation pit, and calibrated twilight tone balance.",
        "cover_image": "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/monolith-skyline-lounge",
        "has_vr": True,
        "sort_order": 4,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1600&q=85",
                "caption": "Twilight horizon study showing equilibrium between city ambient glow and interior lighting.",
                "angle": "Twilight Panorama",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1600&q=85",
                "caption": "Monolithic blackened metal fireplace column and integrated cocktail bar counter.",
                "angle": "Fireplace Elevation",
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Entrance Lightwell & Water Court",
        "slug": "hillside-entrance-gallery",
        "project_name": "Hillside Villa",
        "room": "Entrance Gallery",
        "category": "Entrance",
        "year": 2026,
        "location": "Udaipur",
        "software": "Corona Renderer 11 · 3ds Max",
        "description": "Monolithic gallery threshold featuring a circular architectural oculus casting sweeping sun angles across rough-hewn granite walls and an interior reflection basin.",
        "cover_image": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=2000&q=85",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 5,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1600573472591-ee6c563aaec9?auto=format&fit=crop&w=1600&q=85",
                "caption": "Midday zenith sunbeam piercing the circular concrete lightwell and reflection water court.",
                "angle": "Oculus Zenith Study",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Primary Bath & Spa Alcove",
        "slug": "hillside-bath-spa",
        "project_name": "Hillside Villa",
        "room": "Primary Bath",
        "category": "Bathroom",
        "year": 2026,
        "location": "Udaipur",
        "software": "V-Ray 6 · 3ds Max · Chaos Vantage VR",
        "description": "Subterranean spa bathroom carved into local bedrock, illuminated by high clerestory slits. Free-standing monolithic stone soaking tub and concealed rain shower with seamless microcement finishes.",
        "cover_image": "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/hillside-bath-spa",
        "has_vr": True,
        "sort_order": 6,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1600&q=85",
                "caption": "Carved basalt stone basin and raw unlacquered brass tapware detail.",
                "angle": "Basin Close-Up",
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1620626011761-996317b8d101?auto=format&fit=crop&w=1600&q=85",
                "caption": "Open shower enclosure framed by textured monolithic quartzite slabs.",
                "angle": "Shower Perspective",
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Private Guest Suite & Library",
        "slug": "bespoke-villa-guest-suite",
        "project_name": "Bespoke Villa",
        "room": "Guest Suite & Study",
        "category": "Bedroom",
        "year": 2026,
        "location": "Surat",
        "software": "Corona Renderer 11 · 3ds Max",
        "description": "Quiet study and guest chamber lined with floor-to-ceiling quarter-sawn white oak millwork, leather writing surface, and an integrated daybed alcove overlooking private garden courtyard.",
        "cover_image": "https://images.unsplash.com/photo-1617806118233-18e1de247200?auto=format&fit=crop&w=2000&q=85",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 7,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=1600&q=85",
                "caption": "Integrated white oak writing desk with concealed acoustic felt backboard.",
                "angle": "Desk Study",
                "sort_order": 1
            }
        ]
    },
    {
        "title": "Kitchen Culinary Studio",
        "slug": "project-aa-kitchen",
        "project_name": "Project AA",
        "room": "Kitchen",
        "category": "Kitchen & Dining",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "Corona Renderer 11 · 3ds Max · Unreal Engine VR",
        "description": "Monolithic honed travertine prep island with seamless quarter-sawn oak cabinetry and integrated architectural linear task illumination.",
        "cover_image": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/project-aa-kitchen",
        "has_vr": True,
        "sort_order": 1,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1800&q=85",
                "caption": "Kitchen — Honed Travertine Island & Prep Counter",
                "angle": "Island Perspective 01",
                "vr_url": "https://vr.studiodesire.design/project-aa-kitchen-render-01",
                "has_vr": True,
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=1800&q=85",
                "caption": "Kitchen — Appliance Tower & Barista Niche",
                "angle": "Appliance Elevation 02",
                "vr_url": None,
                "has_vr": False,
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Master Bedroom Suite",
        "slug": "project-aa-bedroom",
        "project_name": "Project AA",
        "room": "Bedroom",
        "category": "Bedroom",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "Corona Renderer 11 · 3ds Max · Unreal Engine VR",
        "description": "Grounded master sleeping volume featuring acoustic timber slats, floating cantilevered nightstands, and soft indirect perimeter ceiling coves.",
        "cover_image": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=2000&q=85",
        "vr_url": "https://vr.studiodesire.design/project-aa-bedroom",
        "has_vr": True,
        "sort_order": 2,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1800&q=85",
                "caption": "Bedroom — Symmetrical Bed Back Elevation & Ambient Coves",
                "angle": "Bed Back Elevation",
                "vr_url": None,
                "has_vr": False,
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=1800&q=85",
                "caption": "Bedroom — Morning Sunlight & Smoked Oak Vanity Console",
                "angle": "Vanity Console View",
                "vr_url": None,
                "has_vr": False,
                "sort_order": 2
            }
        ]
    },
    {
        "title": "Sheltered Balcony Lounge",
        "slug": "project-aa-balcony",
        "project_name": "Project AA",
        "room": "Balcony",
        "category": "Lounge",
        "year": 2026,
        "location": "Ahmedabad, Gujarat",
        "software": "Corona Renderer 11 · 3ds Max",
        "description": "Deep outdoor veranda with reclaimed teak floorboards, custom linear planter balustrade, and low-slung all-weather conversation armchairs.",
        "cover_image": "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=2000&q=85",
        "vr_url": None,
        "has_vr": False,
        "sort_order": 3,
        "media": [
            {
                "url": "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1800&q=85",
                "caption": "Balcony — Reclaimed Teak Decking & Sunset Horizon Lounge",
                "angle": "Sunset Horizon View 01",
                "vr_url": None,
                "has_vr": False,
                "sort_order": 1
            },
            {
                "url": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1800&q=85",
                "caption": "Balcony — Planter Edge & Outdoor Dining Niche",
                "angle": "Dining Niche View 02",
                "vr_url": None,
                "has_vr": False,
                "sort_order": 2
            }
        ]
    }
]

DEMO_BLUEPRINTS = [
    # RESIDENCE 01
    {
        "project_slug": "residence-01",
        "project_name": "Residence 01",
        "title": "Ground Level Master Spatial Layout",
        "slug": "residence-01-ground-level-layout",
        "drawing_type": "Floor Plan",
        "room_area": "Ground Level",
        "drawing_number": "SD-R01-A-101",
        "revision": "R1",
        "date": "12-05-2026",
        "scale": "1:50 @ A1",
        "sheet_size": "A1",
        "description": "Architectural partition, spatial zoning, fenestration datum, and courtyard transition layout for the ground level private residence.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 1,
    },
    {
        "project_slug": "residence-01",
        "project_name": "Residence 01",
        "title": "Living Pavilion Furniture & Material Plan",
        "slug": "residence-01-furniture-plan",
        "drawing_type": "Furniture Plan",
        "room_area": "Living Pavilion",
        "drawing_number": "SD-R01-FP-02",
        "revision": "R0",
        "date": "18-05-2026",
        "scale": "1:50 @ A1",
        "sheet_size": "A1",
        "description": "Bespoke modular seating placement, hearth relationship, circulation clearances, and custom timber furniture positioning.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 2,
    },
    {
        "project_slug": "residence-01",
        "project_name": "Residence 01",
        "title": "Reflected Ceiling & Architectural Lighting Plan",
        "slug": "residence-01-ceiling-plan",
        "drawing_type": "Ceiling Plan",
        "room_area": "Overall Ground",
        "drawing_number": "SD-R01-RCP-01",
        "revision": "R1",
        "date": "22-05-2026",
        "scale": "1:50 @ A1",
        "sheet_size": "A1",
        "description": "Recessed architectural perimeter coves, plasterboard drop levels, flush linear diffusers, and coordinated luminaire switching.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 3,
    },
    {
        "project_slug": "residence-01",
        "project_name": "Residence 01",
        "title": "Living Pavilion Monolithic Hearth Section & Cladding",
        "slug": "residence-01-hearth-section",
        "drawing_type": "Section",
        "room_area": "Living Pavilion",
        "drawing_number": "SD-R01-SEC-03",
        "revision": "R0",
        "date": "28-05-2026",
        "scale": "1:20 @ A2",
        "sheet_size": "A2",
        "description": "Detailed vertical cross-section illustrating natural travertine slab anchoring, thermal isolation layer, and recessed hearth firebox.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 4,
    },
    {
        "project_slug": "residence-01",
        "project_name": "Residence 01",
        "title": "Culinary Studio Fluted Travertine Island Detail",
        "slug": "residence-01-island-detail",
        "drawing_type": "Detail Drawing",
        "room_area": "Culinary Studio",
        "drawing_number": "SD-R01-DET-07",
        "revision": "R2",
        "date": "04-06-2026",
        "scale": "1:10 @ A3",
        "sheet_size": "A3",
        "description": "1:10 fabrication detail for cantilevered fluted travertine prep island, internal welded steel subframe, and concealed power raceways.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 5,
    },
    {
        "project_slug": "residence-01",
        "project_name": "Residence 01",
        "title": "Primary Suite Wall Paneling & Japanese Joinery",
        "slug": "residence-01-joinery-detail",
        "drawing_type": "Joinery Detail",
        "room_area": "Master Suite",
        "drawing_number": "SD-R01-JN-01",
        "revision": "R1",
        "date": "10-06-2026",
        "scale": "1:15 @ A3",
        "sheet_size": "A3",
        "description": "Solid white oak acoustic slatted wall cladding, concealed door leaf integration, shadow gap reveal details, and integrated bedside niche.",
        "thumbnail_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 6,
    },

    # HARDIKBHAI
    {
        "project_slug": "hardikbhai",
        "project_name": "Hardikbhai",
        "title": "Master Room Wardrobe Detail",
        "slug": "hardik-bhai-master-room-wardrobe-detail",
        "drawing_type": "Wardrobe Detail",
        "room_area": "Master Bedroom",
        "drawing_number": "SD-HB-WD-04",
        "revision": "R0",
        "date": "01-08-2026",
        "scale": "1:20 @ A2",
        "sheet_size": "A2",
        "description": "Full-height wardrobe carpentry detail including concealed aluminium edge profiles, internal soft-close drawer partitions, bronze tinted glass shutters, and integrated vertical LED channel.",
        "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-02.webp",
        "file_url": "/api/blueprints/hardik-bhai-master-room-wardrobe-detail/pdf",
        "file_type": "pdf",
        "sort_order": 1,
    },
    {
        "project_slug": "hardikbhai",
        "project_name": "Hardikbhai",
        "title": "Master Suite Electrical & Switching Plan",
        "slug": "hardik-bhai-electrical-plan",
        "drawing_type": "Electrical Plan",
        "room_area": "Master Bedroom",
        "drawing_number": "SD-HB-E-02",
        "revision": "R1",
        "date": "03-08-2026",
        "scale": "1:50 @ A2",
        "sheet_size": "A2",
        "description": "Conduit routing, low-voltage DALI dimming zones, smart keypad locations, motorized blind power supplies, and bedside control modules.",
        "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-01.webp",
        "file_url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 2,
    },
    {
        "project_slug": "hardikbhai",
        "project_name": "Hardikbhai",
        "title": "Dressing & Vanity Joinery Detail",
        "slug": "hardik-bhai-vanity-joinery",
        "drawing_type": "Joinery Detail",
        "room_area": "Dressing Alcove",
        "drawing_number": "SD-HB-JN-09",
        "revision": "R0",
        "date": "08-08-2026",
        "scale": "1:10 @ A3",
        "sheet_size": "A3",
        "description": "Floating dressing island with fluted smoked oak fascia, leather-lined accessory trays, frameless mirror illumination, and brass pull tabs.",
        "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-04.webp",
        "file_url": "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 3,
    },
    {
        "project_slug": "hardikbhai",
        "project_name": "Hardikbhai",
        "title": "Bed Back Fluted Paneling Construction Detail",
        "slug": "hardik-bhai-bed-back-detail",
        "drawing_type": "Construction Detail",
        "room_area": "Master Bedroom",
        "drawing_number": "SD-HB-CD-01",
        "revision": "R0",
        "date": "12-08-2026",
        "scale": "1:10 @ A3",
        "sheet_size": "A3",
        "description": "Sectional assembly drawing for acoustic fabric panels, micro-cement border cladding, concealed LED uplight tray, and floating marble nightstand anchors.",
        "thumbnail_url": "/uploads/projects/hardik-bhai/master-bedroom-05.webp",
        "file_url": "/api/blueprints/hardik-bhai-bed-back-detail/pdf",
        "file_type": "pdf",
        "sort_order": 4,
    },

    # VILLA 02
    {
        "project_slug": "villa-02",
        "project_name": "Villa 02",
        "title": "Ground & Courtyard Master Floor Plan",
        "slug": "villa-02-ground-floor-plan",
        "drawing_type": "Floor Plan",
        "room_area": "Ground Floor & Courtyard",
        "drawing_number": "SD-V02-A-101",
        "revision": "R1",
        "date": "14-03-2025",
        "scale": "1:100 @ A1",
        "sheet_size": "A1",
        "description": "Overall architectural layout coordinating internal courtyards, teak verandas, central colonnade, and private family sleeping quarters.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 1,
    },
    {
        "project_slug": "villa-02",
        "project_name": "Villa 02",
        "title": "Courtyard Colonnade Elevation & Rammed Earth Spec",
        "slug": "villa-02-colonnade-elevation",
        "drawing_type": "Elevation",
        "room_area": "Courtyard Colonnade",
        "drawing_number": "SD-V02-EL-01",
        "revision": "R0",
        "date": "20-03-2025",
        "scale": "1:50 @ A1",
        "sheet_size": "A1",
        "description": "Exterior architectural elevation illustrating rammed earth lift lines, lime wash pigments, column spacing, and integrated copper water spouts.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 2,
    },
    {
        "project_slug": "villa-02",
        "project_name": "Villa 02",
        "title": "Reclaimed Teak Pergola & Ceiling Framing Plan",
        "slug": "villa-02-ceiling-framing-plan",
        "drawing_type": "Ceiling Plan",
        "room_area": "Outdoor Pergola",
        "drawing_number": "SD-V02-CP-02",
        "revision": "R0",
        "date": "25-03-2025",
        "scale": "1:50 @ A2",
        "sheet_size": "A2",
        "description": "Heavy timber joist layout, mortise and tenon jointing schedule, louvered solar shading angles, and concealed downspout routing.",
        "thumbnail_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 3,
    },
    {
        "project_slug": "villa-02",
        "project_name": "Villa 02",
        "title": "Reading Salon Built-in Bookcase Joinery Detail",
        "slug": "villa-02-bookcase-detail",
        "drawing_type": "Detail Drawing",
        "room_area": "Reading Salon",
        "drawing_number": "SD-V02-DET-04",
        "revision": "R1",
        "date": "02-04-2025",
        "scale": "1:20 @ A3",
        "sheet_size": "A3",
        "description": "Architectural carpentry section for solid Burma teak shelving, integrated rolling ladder track, brushed brass shelf supports, and shadow reveals.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 4,
    },

    # APARTMENT 03
    {
        "project_slug": "apartment-03",
        "project_name": "Apartment 03",
        "title": "Penthouse Overall Spatial Layout",
        "slug": "apartment-03-penthouse-layout",
        "drawing_type": "Floor Plan",
        "room_area": "Overall Penthouse",
        "drawing_number": "SD-A03-A-101",
        "revision": "R2",
        "date": "10-09-2025",
        "scale": "1:50 @ A1",
        "sheet_size": "A1",
        "description": "High-rise penthouse spatial plan coordinating structural shear walls, floor-to-ceiling glass envelopes, central entry gallery, and wraparound terrace.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 1,
    },
    {
        "project_slug": "apartment-03",
        "project_name": "Apartment 03",
        "title": "Concealed Pantry & Bar Wardrobe Detail",
        "slug": "apartment-03-wardrobe-bar-detail",
        "drawing_type": "Wardrobe Detail",
        "room_area": "Culinary Pantry",
        "drawing_number": "SD-A03-WD-02",
        "revision": "R1",
        "date": "18-09-2025",
        "scale": "1:15 @ A2",
        "sheet_size": "A2",
        "description": "Pocket door assembly, fold-away fluted oak shutters, integrated wine cooler housing, brushed quartz worktop, and perimeter lighting.",
        "thumbnail_url": "https://images.unsplash.com/photo-1558997519-83ea9252edf8?auto=format&fit=crop&w=1200&q=80",
        "file_url": "/api/blueprints/apartment-03-wardrobe-bar-detail/pdf",
        "file_type": "pdf",
        "sort_order": 2,
    },
    {
        "project_slug": "apartment-03",
        "project_name": "Apartment 03",
        "title": "Master Bath Floating Vanity Construction Detail",
        "slug": "apartment-03-vanity-detail",
        "drawing_type": "Construction Detail",
        "room_area": "Master Sanctuary Bath",
        "drawing_number": "SD-A03-CD-05",
        "revision": "R0",
        "date": "24-09-2025",
        "scale": "1:10 @ A3",
        "sheet_size": "A3",
        "description": "Wall-hung monolithic basalt vanity basin detail with heavy-duty structural steel brackets, concealed waste traps, and undermount motion illumination.",
        "thumbnail_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 3,
    },
    {
        "project_slug": "apartment-03",
        "project_name": "Apartment 03",
        "title": "Living Gallery Longitudinal Cross Section",
        "slug": "apartment-03-living-section",
        "drawing_type": "Section",
        "room_area": "Main Living Gallery",
        "drawing_number": "SD-A03-SEC-01",
        "revision": "R1",
        "date": "01-10-2025",
        "scale": "1:50 @ A2",
        "sheet_size": "A2",
        "description": "Full vertical section across open-concept salon, double-height glazing facade, floor slab screed build-ups, and perimeter curtain pockets.",
        "thumbnail_url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 4,
    },

    # OFFICE SPACE 05
    {
        "project_slug": "office-space-05",
        "project_name": "Office Space 05",
        "title": "Acoustic Spatial Partition & Executive Layout",
        "slug": "office-space-05-executive-layout",
        "drawing_type": "Floor Plan",
        "room_area": "Floor 14 Executive Suite",
        "drawing_number": "SD-OS05-A-101",
        "revision": "R0",
        "date": "15-01-2026",
        "scale": "1:100 @ A1",
        "sheet_size": "A1",
        "description": "Workplace zoning, acoustic partition STC-52 ratings, collaborative hubs, executive meeting suites, and emergency egress routes.",
        "thumbnail_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 1,
    },
    {
        "project_slug": "office-space-05",
        "project_name": "Office Space 05",
        "title": "Boardroom Acoustic Oak Baffle Ceiling Plan",
        "slug": "office-space-05-baffle-ceiling-plan",
        "drawing_type": "Ceiling Plan",
        "room_area": "Boardroom",
        "drawing_number": "SD-OS05-CP-01",
        "revision": "R1",
        "date": "22-01-2026",
        "scale": "1:50 @ A2",
        "sheet_size": "A2",
        "description": "Suspended solid oak timber baffles, black acoustic absorption felt backing, integrated microphone sensors, and dimmable linears.",
        "thumbnail_url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1200&q=80",
        "file_url": "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=2400&q=95",
        "file_type": "image",
        "sort_order": 2,
    },
    {
        "project_slug": "office-space-05",
        "project_name": "Office Space 05",
        "title": "Executive Desk Architectural Fabrication Detail",
        "slug": "office-space-05-desk-detail",
        "drawing_type": "Detail Drawing",
        "room_area": "Executive Office",
        "drawing_number": "SD-OS05-DET-03",
        "revision": "R0",
        "date": "30-01-2026",
        "scale": "1:10 @ A3",
        "sheet_size": "A3",
        "description": "Custom cantilevered smoked oak and gunmetal desk, integrated wire management trough, flush leather blotter, and concealed lockable drawer.",
        "thumbnail_url": "https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&w=1200&q=80",
        "file_url": "/api/blueprints/office-space-05-desk-detail/pdf",
        "file_type": "pdf",
        "sort_order": 3,
    }
]


def seed_database():
    print("=== Studio Desire Database Seeding ===")
    print("Recreating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed Projects
        proj_count = 0
        proj_media_count = 0
        project_map = {}
        for proj in DEMO_PROJECTS:
            data = dict(proj)
            media_items = data.pop("media", [])
            project = Project(**data)
            db.add(project)
            db.flush()
            project_map[project.slug] = project.id

            for m in media_items:
                media_entry = ProjectMedia(project_id=project.id, **m)
                db.add(media_entry)
                proj_media_count += 1
            proj_count += 1

        # Seed Products
        prod_count = 0
        prod_media_count = 0
        for prod in DEMO_PRODUCTS:
            data = dict(prod)
            media_items = data.pop("media", [])
            product = Product(**data)
            db.add(product)
            db.flush()

            for m in media_items:
                media_entry = ProductMedia(product_id=product.id, **m)
                db.add(media_entry)
                prod_media_count += 1
            prod_count += 1

        # Seed 3D Visualizations
        vis_count = 0
        vis_media_count = 0
        for vis in DEMO_VISUALIZATIONS:
            data = dict(vis)
            media_items = data.pop("media", [])
            p_name = data.get("project_name")
            if p_name == "Hardikbhai":
                data["project_id"] = project_map.get("hardikbhai")
            elif p_name == "Project AA":
                data["project_id"] = project_map.get("project-aa")
            elif p_name == "Residence 01":
                data["project_id"] = project_map.get("residence-01")
            elif p_name == "The Monolith Penthouse":
                data["project_id"] = project_map.get("apartment-03")
            elif p_name == "Hillside Villa":
                data["project_id"] = project_map.get("villa-07")
            elif p_name == "Bespoke Villa":
                data["project_id"] = project_map.get("villa-02")
            space = VisualizationSpace(**data)
            db.add(space)
            db.flush()

            for m in media_items:
                media_entry = VisualizationMedia(space_id=space.id, **m)
                db.add(media_entry)
                vis_media_count += 1
            vis_count += 1

        # Seed Blueprint Drawings
        blueprint_count = 0
        for bp in DEMO_BLUEPRINTS:
            data = dict(bp)
            p_slug = data.get("project_slug")
            # Link to existing project id if matched
            matched_project_id = project_map.get(p_slug)
            data["project_id"] = matched_project_id

            blueprint = BlueprintDrawing(**data)
            db.add(blueprint)
            blueprint_count += 1

        # Seed Initial Master User
        master_user = User(
            username="Studio Desier",
            email="studiodesire01@gmail.com",
            hashed_password=hash_password("12345678"),
            role=UserRole.MASTER.value,
            is_active=True,
            must_change_password=True
        )
        db.add(master_user)

        # Seed Initial Activity Log
        init_log = ActivityLog(
            username="System",
            action="System Initialized",
            entity_type="system",
            details="Studio Desire platform initialized with Master account and architectural archive."
        )
        db.add(init_log)

        # Seed Sample Customer Enquiries
        enq1 = ProjectEnquiry(
            reference_number="#0027",
            name="Rahul Sharma",
            email="rahul.sharma@example.com",
            phone="+91 98250 12345",
            project_type="Residential Villa",
            location="Bopal, Ahmedabad",
            budget="₹ 1 Crore – 2.5 Crores",
            timeline="3 — 6 Months",
            message="We are planning a contemporary 4-bedroom private villa on a 600 sq. yard plot in Bopal. Looking for monolithic lime plaster textures, raw oak millwork, and open double-height courtyards. Attached our architect's initial boundary outline and interior mood board.",
            source="planning",
            status="NEW",
            email_sent=True
        )
        db.add(enq1)
        db.flush()

        att1 = ProjectEnquiryAttachment(
            enquiry_id=enq1.id,
            original_filename="villa-rough-sketch.webp",
            filename="demo_sketch_01.webp",
            file_type="image",
            mime_type="image/webp",
            file_size=245000,
            storage_path="demo",
            url="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80"
        )
        att2 = ProjectEnquiryAttachment(
            enquiry_id=enq1.id,
            original_filename="architectural-floor-plan.pdf",
            filename="demo_plan_02.pdf",
            file_type="pdf",
            mime_type="application/pdf",
            file_size=1420000,
            storage_path="demo",
            url="/api/blueprints/hardik-bhai-master-room-wardrobe-detail/pdf"
        )
        att3 = ProjectEnquiryAttachment(
            enquiry_id=enq1.id,
            original_filename="material-moodboard.webp",
            filename="demo_moodboard_03.webp",
            file_type="image",
            mime_type="image/webp",
            file_size=380000,
            storage_path="demo",
            url="https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1200&q=80"
        )
        db.add_all([att1, att2, att3])

        enq2 = ProjectEnquiry(
            reference_number="#0028",
            name="Ananya Desai",
            email="ananya.desai@designcraft.in",
            phone="+91 97240 88990",
            project_type="Restaurant",
            location="Sindhu Bhavan Road, Ahmedabad",
            budget="₹ 50 Lakhs – 1 Crore",
            timeline="Immediate (1 — 3 Months)",
            message="Specialty artisanal coffee and sourdough bakery space. Want warm terracotta textures, brass counter fittings, and fluted acoustic timber ceilings.",
            source="planning",
            status="IN REVIEW",
            email_sent=True,
            internal_notes="Spoke with client on phone. Reviewing floor area and kitchen extractor ducting specs."
        )
        db.add(enq2)

        enq3 = ProjectEnquiry(
            reference_number="#0029",
            name="Vikramaditya Singhania",
            email="v.singhania@apexcorp.com",
            phone="+91 99090 44556",
            project_type="Office",
            location="GIFT City, Gandhinagar",
            budget="₹ 2.5 Crores – 5 Crores",
            timeline="6 — 12 Months",
            message="Executive headquarters design spanning 8,000 sq.ft in GIFT City. Looking for acoustic timber enclosures and minimalist reception gallery.",
            source="contact",
            status="CONTACTED",
            email_sent=True,
            internal_notes="Site inspection scheduled for coming Tuesday."
        )
        db.add(enq3)

        db.commit()
        print(f"Successfully seeded {proj_count} demo projects with {proj_media_count} media items.")
        print(f"Successfully seeded {prod_count} demo design products with {prod_media_count} media items.")
        print(f"Successfully seeded {vis_count} 3D visualization spaces with {vis_media_count} render perspectives.")
        print(f"Successfully seeded {blueprint_count} architectural blueprint drawings.")
        print("Successfully seeded sample client project enquiries (including #0027 Rahul Sharma with attachments).")
        print("Successfully seeded Master account: Studio Desier / 12345678 (mandatory change on first login).")
        print("Database seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
