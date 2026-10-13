/**
 * STUDIO DESIRE — PROJECT ARCHIVE CENTRAL DATA SOURCE
 * 
 * IMPORTANT:
 * All project content, images, videos, and metadata are centralized here.
 * To update or replace prototype demo projects with real client work,
 * simply modify the entries in this dataset.
 */

const CATEGORIES = [
  "ALL",
  "RESIDENTIAL",
  "COMMERCIAL",
  "HOSPITALITY",
  "OFFICE",
  "RETAIL"
];

const MEDIA_TYPES = [
  { id: "all", label: "ALL" },
  { id: "photos", label: "PHOTOS" },
  { id: "videos", label: "VIDEOS" }
];

const PROJECTS = [
  {
    id: "project-hardikbhai",
    slug: "hardikbhai",
    title: "Hardikbhai",
    subtitle: "Comprehensive Residential Interior 3D Visualization",
    location: "Ahmedabad, Gujarat",
    year: "2026",
    category: "RESIDENTIAL",
    type: "Private Residence",
    area: "Residential Interior",
    featured: true,
    isDemo: false,
    description: "Completed residential interior 3D visualization for client Hardikbhai executed by Studio Desire (Designers: Zenith Suthar & Chetna Bhati, Ahmedabad). The project spans 24 comprehensive rendered perspectives across 6 primary living zones: Entrance, Living Room, Dining & Kitchen, Parents Room, Guest Room, and Master Bedroom, featuring custom timber paneling, concealed joinery, and layered ambient lighting.",
    coverImage: "/uploads/projects/hardik-bhai/cover.webp",
    aspectRatio: "wide",
    gridSpan: "hero",
    hasVideo: false,
    images: [
      {
        url: "/uploads/projects/hardik-bhai/entrance-01.webp",
        caption: "Entrance — Primary Entry Axis with custom fluted timber wall cladding."
      },
      {
        url: "/uploads/projects/hardik-bhai/entrance-02.webp",
        caption: "Entrance — Integrated console table and vertical acoustic wall paneling."
      },
      {
        url: "/uploads/projects/hardik-bhai/entrance-03.webp",
        caption: "Entrance — Spatial threshold perspective looking toward living salon."
      },
      {
        url: "/uploads/projects/hardik-bhai/living-room-01.webp",
        caption: "Living Room — Primary lounge seating and monolithic media wall joinery."
      },
      {
        url: "/uploads/projects/hardik-bhai/living-room-02.webp",
        caption: "Living Room — Opposite perspective highlighting glazing and ceiling cove wash."
      },
      {
        url: "/uploads/projects/hardik-bhai/living-room-03.webp",
        caption: "Living Room — Cross-axis architectural overview of the seating arrangement."
      },
      {
        url: "/uploads/projects/hardik-bhai/living-room-04.webp",
        caption: "Living Room — Detail angle framing bespoke upholstery and textured accents."
      },
      {
        url: "/uploads/projects/hardik-bhai/dining-kitchen-01.webp",
        caption: "Dining & Kitchen — Dining table ensemble and culinary island relationship."
      },
      {
        url: "/uploads/projects/hardik-bhai/dining-kitchen-02.webp",
        caption: "Dining & Kitchen — Minimalist handleless cabinetry and quartz work surfaces."
      },
      {
        url: "/uploads/projects/hardik-bhai/dining-kitchen-03.webp",
        caption: "Dining & Kitchen — Wide spatial view toward custom storage towers."
      },
      {
        url: "/uploads/projects/hardik-bhai/dining-kitchen-04.webp",
        caption: "Dining & Kitchen — Breakfast counter and integrated appliance wall."
      },
      {
        url: "/uploads/projects/hardik-bhai/parents-room-01.webp",
        caption: "Parents Room — Fluted bed back paneling with symmetrical nightstand niches."
      },
      {
        url: "/uploads/projects/hardik-bhai/parents-room-02.webp",
        caption: "Parents Room — Full room perspective showing tailored wardrobe wall."
      },
      {
        url: "/uploads/projects/hardik-bhai/parents-room-03.webp",
        caption: "Parents Room — Glazing and quiet contemplation seating nook."
      },
      {
        url: "/uploads/projects/hardik-bhai/parents-room-04.webp",
        caption: "Parents Room — Floating vanity counter and television credenza."
      },
      {
        url: "/uploads/projects/hardik-bhai/guest-room-01.webp",
        caption: "Guest Room — Neutral minimalist sleeping area with bespoke headboard."
      },
      {
        url: "/uploads/projects/hardik-bhai/guest-room-02.webp",
        caption: "Guest Room — Full-height wardrobe joinery and dressing mirror."
      },
      {
        url: "/uploads/projects/hardik-bhai/guest-room-03.webp",
        caption: "Guest Room — Diagonal spatial overview with natural daylight filtering."
      },
      {
        url: "/uploads/projects/hardik-bhai/guest-room-04.webp",
        caption: "Guest Room — Study desk niche with floating shelf storage."
      },
      {
        url: "/uploads/projects/hardik-bhai/master-bedroom-01.webp",
        caption: "Master Bedroom — Monolithic fluted wall backdrop and king bed suite."
      },
      {
        url: "/uploads/projects/hardik-bhai/master-bedroom-02.webp",
        caption: "Master Bedroom — Dressing area with bronze-tinted glass shutter wardrobe."
      },
      {
        url: "/uploads/projects/hardik-bhai/master-bedroom-03.webp",
        caption: "Master Bedroom — Lounge armchair corner with expansive window view."
      },
      {
        url: "/uploads/projects/hardik-bhai/master-bedroom-04.webp",
        caption: "Master Bedroom — Architectural media wall and floating dresser console."
      },
      {
        url: "/uploads/projects/hardik-bhai/master-bedroom-05.webp",
        caption: "Master Bedroom — Comprehensive room overview across main spatial axis."
      }
    ],
    tags: ["Hardikbhai", "Residential", "Fluted Timber", "Private Residence", "Ahmedabad"]
  },
  {
    id: "project-01",
    slug: "residence-01",
    title: "Residence 01",
    subtitle: "Minimalist Haven with Natural Travertine & Raw Oak",
    location: "Ahmedabad",
    year: "2026",
    category: "RESIDENTIAL",
    type: "Private Residence",
    area: "6,400 sq.ft",
    featured: true,
    isDemo: true,
    description: "A serene residential interior exploring monolithic spatial volumes, warm lime plaster textures, and bespoke Japanese joinery. The design harmonizes soft daylight filtering through floor-to-ceiling fenestrations with organic travertine stone accents and quiet contemplation alcoves.",
    coverImage: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=85",
    aspectRatio: "wide",
    gridSpan: "hero",
    hasVideo: true,
    video: {
      url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
      poster: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=85",
      caption: "Spatial walkthrough of the central living pavilion and garden lightwell."
    },
    images: [
      {
        url: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=85",
        caption: "Main living gallery featuring monolithic hearth and bespoke linen lounge."
      },
      {
        url: "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1600&q=85",
        caption: "Culinary studio with fluted travertine island and concealed joinery."
      },
      {
        url: "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1600&q=85",
        caption: "Primary suite highlighting limewashed planes and morning sunlight."
      },
      {
        url: "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1600&q=85",
        caption: "Bath sanctuary carved from split-face sandstone with concealed perimeter illumination."
      }
    ],
    tags: ["Travertine", "Raw Timber", "Lime Plaster", "Zen Garden"]
  },
  {
    id: "project-02",
    slug: "villa-02",
    title: "Villa 02",
    subtitle: "Coastal Sanctuary Framed in Tactile Earth & Teak",
    location: "Alibaug",
    year: "2025",
    category: "RESIDENTIAL",
    type: "Coastal Retreat",
    area: "8,200 sq.ft",
    featured: false,
    isDemo: true,
    description: "Nestled between coastal groves and saline breezes, Villa 02 utilizes rammed earth tones, reclaimed Burma teak timber, and generous open-air colonnades to create a tranquil sanctuary where interior and landscape dissolve effortlessly.",
    coverImage: "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "portrait",
    gridSpan: "medium-tall",
    hasVideo: false,
    images: [
      {
        url: "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1600&q=85",
        caption: "Enclosed courtyard gallery framing local coastal flora."
      },
      {
        url: "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1600&q=85",
        caption: "Dining colonnade finished in textured lime wash and hand-rubbed teak."
      },
      {
        url: "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1600&q=85",
        caption: "Reading salon with custom low-slung upholstery and brushed brass fixtures."
      }
    ],
    tags: ["Coastal", "Rammed Earth", "Burma Teak", "Courtyard"]
  },
  {
    id: "project-03",
    slug: "apartment-03",
    title: "Apartment 03",
    subtitle: "Urban Penthouse with Refined Architectural Lines",
    location: "Mumbai",
    year: "2025",
    category: "RESIDENTIAL",
    type: "High-Rise Penthouse",
    area: "3,800 sq.ft",
    featured: false,
    isDemo: true,
    description: "An elevated urban dwelling designed as a tranquil counterpoint to city density. The layout leverages floating micro-cement partitions, dark stained walnut cabinetry, and bronze-framed glazing to capture uninterrupted skyline panoramas.",
    coverImage: "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "landscape",
    gridSpan: "medium-wide",
    hasVideo: true,
    video: {
      url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
      poster: "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1400&q=85",
      caption: "Twilight sequence showing the interplay of indirect lighting and walnut panelling."
    },
    images: [
      {
        url: "https://images.unsplash.com/photo-1600585152220-90363fe7e115?auto=format&fit=crop&w=1600&q=85",
        caption: "Open living composition with integrated cantilevered credenza."
      },
      {
        url: "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1600&q=85",
        caption: "Master dressing suite clad in smoked oak and textured linen screens."
      },
      {
        url: "https://images.unsplash.com/photo-1600565193348-f74bd3c7ccdf?auto=format&fit=crop&w=1600&q=85",
        caption: "Minimalist kitchen workspace with seamless induction integration."
      }
    ],
    tags: ["Penthouse", "Walnut", "Bronze", "Micro-Cement"]
  },
  {
    id: "project-04",
    slug: "restaurant-04",
    title: "Restaurant 04",
    subtitle: "Intimate Fine Dining Architecture of Shadow & Stone",
    location: "New Delhi",
    year: "2024",
    category: "HOSPITALITY",
    type: "Fine Dining Space",
    area: "4,500 sq.ft",
    featured: false,
    isDemo: true,
    description: "An experiential culinary journey centered around atmospheric chiaroscuro. Raw volcanic basalt stone, acoustic wool baffle ceilings, and pin-spot illuminating tables create intimate social enclaves within a generous vaulted volume.",
    coverImage: "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "landscape",
    gridSpan: "large-wide",
    hasVideo: false,
    images: [
      {
        url: "https://images.unsplash.com/photo-1550966871-3ed3cdb5ed0c?auto=format&fit=crop&w=1600&q=85",
        caption: "The central dining nave with sculptural basalt banquet tables."
      },
      {
        url: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1600&q=85",
        caption: "Private wine cellar lounge lined with blackened steel vitrines."
      },
      {
        url: "https://images.unsplash.com/photo-1559339352-11d035aa65de?auto=format&fit=crop&w=1600&q=85",
        caption: "Omakase counter showcasing a single unbroken slab of honed black granite."
      }
    ],
    tags: ["Basalt", "Chiaroscuro", "Blackened Steel", "Hospitality"]
  },
  {
    id: "project-05",
    slug: "office-space-05",
    title: "Office Space 05",
    subtitle: "Biophilic Creative Headquarters with Acoustic Timber Enclosures",
    location: "Bengaluru",
    year: "2025",
    category: "OFFICE",
    type: "Design Studio & Headquarters",
    area: "12,000 sq.ft",
    featured: false,
    isDemo: true,
    description: "A forward-thinking workspace that challenges corporate orthodoxy. Through modular acoustic timber pods, cascading indoor botanical gardens, and ambient diffused skylights, the environment fosters quiet concentration alongside collaborative cross-pollination.",
    coverImage: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "portrait",
    gridSpan: "medium-tall",
    hasVideo: true,
    video: {
      url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
      poster: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1400&q=85",
      caption: "Exploration of modular meeting volumes and diffused light ceiling canopy."
    },
    images: [
      {
        url: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1600&q=85",
        caption: "Collaborative atrium with custom terrazzo amphitheater seating."
      },
      {
        url: "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1600&q=85",
        caption: "Executive think-tank enclosed in curved reeded glass partitions."
      },
      {
        url: "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1600&q=85",
        caption: "Material library and prototyping benches finished in untreated birch plywood."
      }
    ],
    tags: ["Workplace", "Birch Plywood", "Reeded Glass", "Acoustics"]
  },
  {
    id: "project-06",
    slug: "residence-06",
    title: "Residence 06",
    subtitle: "Tropical Vernacular Villa Clad in Hand-Chiseled Laterite",
    location: "Goa",
    year: "2024",
    category: "RESIDENTIAL",
    type: "Tropical Residence",
    area: "5,800 sq.ft",
    featured: false,
    isDemo: true,
    description: "Rooted in Goa's rich architectural legacy, Residence 06 pairs traditional deep verandas and hand-cut red laterite stone with razor-sharp modernist geometry. Polished IPS cement floors and terracotta louvers allow monsoon winds to naturally cool every wing.",
    coverImage: "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "landscape",
    gridSpan: "medium-standard",
    hasVideo: false,
    images: [
      {
        url: "https://images.unsplash.com/photo-1613977257363-707ba9348227?auto=format&fit=crop&w=1600&q=85",
        caption: "Transition veranda connecting the living pavilion to the reflection pond."
      },
      {
        url: "https://images.unsplash.com/photo-1600585154526-990dced4db0d?auto=format&fit=crop&w=1600&q=85",
        caption: "Open-plan dining space featuring hand-cast terrazzo dining suite."
      },
      {
        url: "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1600&q=85",
        caption: "Outdoor courtyard shower surrounded by lush philodendrons and laterite masonry."
      }
    ],
    tags: ["Laterite", "Tropical Modernism", "IPS Flooring", "Veranda"]
  },
  {
    id: "project-07",
    slug: "villa-07",
    title: "Villa 07",
    subtitle: "Courtyard Palace Reimagined in White Makrana Marble",
    location: "Udaipur",
    year: "2025",
    category: "RESIDENTIAL",
    type: "Lakeside Estate",
    area: "9,500 sq.ft",
    featured: false,
    isDemo: true,
    description: "An estate celebrating the timeless dignity of stone craftsmanship. Overlooking calm waters, the residence interprets classical jali screens as dynamic kinetic bronze louvers that throw intricate shadow tapestries across white Makrana marble floors.",
    coverImage: "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "portrait",
    gridSpan: "medium-tall",
    hasVideo: true,
    video: {
      url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyBlazes.mp4",
      poster: "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1400&q=85",
      caption: "Afternoon sun casting dynamic geometry across the marble courtyard arcade."
    },
    images: [
      {
        url: "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1600&q=85",
        caption: "The grand portico showcasing double-height fluted marble colonnades."
      },
      {
        url: "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1600&q=85",
        caption: "Drawing room featuring bespoke bouclé seating and antique brass hardware."
      },
      {
        url: "https://images.unsplash.com/photo-1600566753376-12c8ab7fb75b?auto=format&fit=crop&w=1600&q=85",
        caption: "Private morning terrace framing the Aravali mountain silhouette."
      }
    ],
    tags: ["Makrana Marble", "Kinetic Screens", "Colonnades", "Lakeside"]
  },
  {
    id: "project-08",
    slug: "cafe-08",
    title: "Cafe 08",
    subtitle: "Artisanal Roastery in Terracotta, Lime, & Cast Bronze",
    location: "Jaipur",
    year: "2024",
    category: "HOSPITALITY",
    type: "Specialty Cafe & Roastery",
    area: "2,200 sq.ft",
    featured: false,
    isDemo: true,
    description: "Honoring Jaipur's terracotta pottery heritage, Cafe 08 features a sculptural central counter cast entirely from indigenous pink terracotta clay. Curved lime-plaster arches and unlacquered bronze details create a sensory haven for specialty coffee enthusiasts.",
    coverImage: "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "landscape",
    gridSpan: "medium-standard",
    hasVideo: false,
    images: [
      {
        url: "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1600&q=85",
        caption: "Sculptural terracotta brew bar with custom brass pour-over fittings."
      },
      {
        url: "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=1600&q=85",
        caption: "Seating alcoves recessed into arched lime plaster niches."
      },
      {
        url: "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?auto=format&fit=crop&w=1600&q=85",
        caption: "Sunlit rear courtyard with hand-thrown ceramic planters and olive trees."
      }
    ],
    tags: ["Terracotta", "Arches", "Specialty Coffee", "Brass"]
  },
  {
    id: "project-09",
    slug: "apartment-09",
    title: "Apartment 09",
    subtitle: "Monochromatic Sanctuary Defined by Silence and Form",
    location: "Pune",
    year: "2026",
    category: "RESIDENTIAL",
    type: "Duplex Residence",
    area: "4,100 sq.ft",
    featured: false,
    isDemo: true,
    description: "Conceived as an exercise in architectural reduction. A strictly controlled palette of warm chalk tones, raw silk upholstery, and smoked Belgian oak floors allows subtle gradations of natural sunlight to define the spatial boundaries throughout the day.",
    coverImage: "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "landscape",
    gridSpan: "medium-standard",
    hasVideo: false,
    images: [
      {
        url: "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?auto=format&fit=crop&w=1600&q=85",
        caption: "Double-height living volume with monolithic floating fireplace."
      },
      {
        url: "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?auto=format&fit=crop&w=1600&q=85",
        caption: "Study mezzanine overlooking the internal courtyard garden."
      },
      {
        url: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=85",
        caption: "Minimalist entry foyer with recessed shadow-gap reveals."
      }
    ],
    tags: ["Monochrome", "Belgian Oak", "Raw Silk", "Chalk Plaster"]
  },
  {
    id: "project-10",
    slug: "studio-10",
    title: "Studio 10",
    subtitle: "Curated Fashion & Object Atelier with Sculptural Volumes",
    location: "Ahmedabad",
    year: "2025",
    category: "RETAIL",
    type: "Flagship Atelier & Gallery",
    area: "3,100 sq.ft",
    featured: false,
    isDemo: true,
    description: "An architectural retail concept designed like an art archive. Garments and artisanal objects are displayed on custom cast-concrete plinths against hand-scraped lime plaster walls, transforming the shopping experience into a serene gallery walkthrough.",
    coverImage: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1400&q=85",
    aspectRatio: "portrait",
    gridSpan: "medium-tall",
    hasVideo: true,
    video: {
      url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
      poster: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1400&q=85",
      caption: "Spatial walkthrough showcasing cast-concrete plinths and suspended light channels."
    },
    images: [
      {
        url: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1600&q=85",
        caption: "Main gallery displaying curated textiles on monolithic cast-concrete blocks."
      },
      {
        url: "https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1600&q=85",
        caption: "Accessory display niche with warm directional fiber-optic lighting."
      },
      {
        url: "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1600&q=85",
        caption: "Private client salon furnished in hand-stitched saddle leather and sandblasted glass."
      }
    ],
    tags: ["Retail Architecture", "Cast Concrete", "Atelier", "Gallery"]
  }
];

const PLACEHOLDER_SECTIONS = {
  "3d": {
    code: "02",
    title: "3D VISUALIZATION",
    navLabel: "3D",
    description: "This section of Studio Desire is currently being prepared.",
    note: "Spatial renderings, photorealistic atmospheric lighting studies, and CGI architecture archives will be showcased here.",
    expectedFeatures: ["Interactive 3D Walkthroughs", "Atmospheric Lighting Studies", "CGI Material Archives"]
  },
  "blueprint": {
    code: "03",
    title: "BLUEPRINTS & DRAWINGS",
    navLabel: "Blueprint",
    description: "This section of Studio Desire is currently being prepared.",
    note: "Architectural floor plans, spatial sections, structural joinery details, and technical documentation will be presented here.",
    expectedFeatures: ["Vector Floor Plans", "Joinery & Millwork Details", "Spatial Sections"]
  },
  "planning": {
    code: "04",
    title: "SPATIAL PLANNING",
    navLabel: "Planning",
    description: "This section of Studio Desire is currently being prepared.",
    note: "Interior zoning frameworks, circulation studies, ergonomic programming, and space allocation archives will be documented here.",
    expectedFeatures: ["Circulation Layouts", "Zoning Matrices", "Feasibility Analyses"]
  },
  "products": {
    code: "05",
    title: "BESPOKE PRODUCTS",
    navLabel: "Products",
    description: "This section of Studio Desire is currently being prepared.",
    note: "Custom furniture collections, handcrafted architectural hardware, tactile textiles, and limited edition luminaires will be curated here.",
    expectedFeatures: ["Custom Furniture Editions", "Architectural Hardware", "Limited Luminaires"]
  },
  "about": {
    code: "06",
    title: "ABOUT STUDIO DESIRE",
    navLabel: "About",
    description: "This section of Studio Desire is currently being prepared.",
    note: "Our design ethos, studio philosophy, material research practice, and lead architectural profile will be articulated here.",
    expectedFeatures: ["Design Ethos & Philosophy", "Material Research Practice", "Leadership & Team"]
  },
  "contact": {
    code: "07",
    title: "CONTACT & INQUIRIES",
    navLabel: "Contact",
    description: "This section of Studio Desire is currently being prepared.",
    note: "Client project commissioning, architectural consultation bookings, and studio appointment information will be available here.",
    expectedFeatures: ["Project Commissioning", "Consultation Bookings", "Studio Coordinates"]
  }
};

// Expose universally on window for direct file:// or standard script usage
if (typeof window !== "undefined") {
  window.StudioDesireData = {
    CATEGORIES,
    MEDIA_TYPES,
    PROJECTS,
    PLACEHOLDER_SECTIONS
  };
}

// Also export for ES module environments
export { CATEGORIES, MEDIA_TYPES, PROJECTS, PLACEHOLDER_SECTIONS };
