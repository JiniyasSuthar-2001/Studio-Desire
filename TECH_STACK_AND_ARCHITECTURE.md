# Studio Desire — Technology Stack, File Extensions & Architecture Guide

This document explains the technical architecture, programming languages, file extensions, and key concepts used to build the **Studio Desire** interior design studio web platform.

---

## 1. High-Level Technology Stack

Studio Desire is built with a **modern decoupled architecture** consisting of:

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend Framework** | **React 18** | Interactive UI components, reactive state management, and page transitions |
| **Frontend Language** | **TypeScript** | Static typing, compile-time safety, and structured data interfaces |
| **Frontend Build Tool** | **Vite 5** | High-speed development server with Hot Module Replacement (HMR) and optimized production bundler |
| **Styling System** | **Vanilla CSS3** | Custom architectural design system (CSS Grid, Flexbox, custom design tokens, responsive breakpoints) |
| **Backend Framework** | **FastAPI** | High-performance Python REST API framework with automatic OpenAPI/Swagger documentation |
| **Backend Language** | **Python 3.10+** | Server-side routing, data validation, database interaction, and automation scripts |
| **Database ORM** | **SQLAlchemy 2.0** | Object-Relational Mapping (ORM) connecting Python classes to database tables |
| **Database Engine** | **SQLite** | Self-contained, zero-configuration relational database stored locally in `backend/studio_desire.db` |
| **Data Validation** | **Pydantic v2** | Request validation, payload schema definition, and serialization |
| **Development Launcher** | **Python Subprocess (`start_up.py`)** | Single-command orchestrator starting both frontend and backend concurrently |

---

## 2. File Extensions Used & What Each Does

In this codebase, you will encounter the following file extensions:

### `.tsx` (TypeScript XML / React Component)
- **What it is**: A TypeScript file that contains JSX (syntax that combines HTML markup and JavaScript/TypeScript logic).
- **Where it is used**: Inside `frontend/src/pages/` and `frontend/src/components/`.
- **Examples**:
  - `frontend/src/pages/ProjectsPage.tsx` — Projects archive page
  - `frontend/src/pages/ProductsPage.tsx` — Design objects & furniture concepts page
  - `frontend/src/pages/AboutPage.tsx` — Studio editorial profile & team section
  - `frontend/src/pages/ContactPage.tsx` — Inquiry form with inline validation
  - `frontend/src/components/Header.tsx` — Site navigation and mobile drawer
  - `frontend/src/components/ProductDetail.tsx` — Dossier modal & minimal image viewer

### `.ts` (Pure TypeScript)
- **What it is**: Standard TypeScript code without JSX. Used for data models, type definitions, and API client services.
- **Where it is used**: Inside `frontend/src/types/` and `frontend/src/services/`.
- **Examples**:
  - `frontend/src/types/product.ts` — TypeScript interfaces for products and media
  - `frontend/src/types/contact.ts` — Data contracts for inquiry submissions
  - `frontend/src/services/productService.ts` — API fetch calls to `GET /api/products`
  - `frontend/src/services/contactService.ts` — Submits inquiry form to `POST /api/contact`

### `.py` (Python Script)
- **What it is**: Python source code executing on the server or as a CLI tool.
- **Where it is used**: Inside `backend/` and at the project root.
- **Examples**:
  - `start_up.py` — Root development launcher script
  - `backend/app/main.py` — FastAPI application entry point, CORS config, and router mounting
  - `backend/app/models/product.py` — SQLAlchemy database table definitions
  - `backend/app/schemas/contact.py` — Pydantic request/response validation schemas
  - `backend/app/api/products.py` — REST API endpoints for product queries and category filtering
  - `backend/seed.py` — Database seeder populating demo projects and design concepts

### `.css` (Cascading Style Sheets)
- **What it is**: The visual styling language controlling colors, typography, layout grids, spacing, transitions, and responsive behavior.
- **Where it is used**: `frontend/src/styles/editorial.css`.
- **Why Vanilla CSS**: Allows 100% fine-grained control over the bespoke Studio Desire editorial aesthetic (hairline borders, warm off-white palette, asymmetric CSS Grid) without generic utility-library overhead.

### `.db` (SQLite Database)
- **What it is**: A binary relational database file managed by SQLite.
- **Where it is used**: `backend/studio_desire.db`.
- **Contains tables**:
  - `projects` & `project_media` — Architectural project archives and media items
  - `products` & `product_media` — Bespoke design objects, concepts, and specifications
  - `contact_inquiries` — Received client consultation requests

### `.json` (JavaScript Object Notation)
- **What it is**: Human-readable data configuration format.
- **Where it is used**:
  - `frontend/package.json` — Node.js dependencies, scripts (`npm run dev`, `npm run build`)
  - `frontend/tsconfig.json` — TypeScript compiler settings

### `.md` (Markdown Documentation)
- **What it is**: Structured text documentation formatted for easy reading on GitHub and IDEs.
- **Where it is used**: Project guides, implementation plans, and walkthrough logs.

---

## 3. What Kind of Code Is Written?

### A. Frontend Code Style
1. **Functional React Components with Hooks**:
   - `useState` manages active categories, modal popups, lightbox indexes, and form input states.
   - `useEffect` handles asynchronous API data fetching and window hash route listening (`#projects`, `#products`, `#about`, `#contact`).
   - `useRef` handles DOM reference control and scroll resets.
2. **Strict Static Typing**:
   - Every API response is strictly mapped to TypeScript interfaces, eliminating runtime `undefined` property errors.
3. **Vanilla CSS Design System Tokens**:
   - Variables like `--bg-primary: #f9f8f6;`, `--text-primary: #141413;`, `--border-hairline: #e6e3dc;`, and serif font families (`Cormorant Garamond`).
   - Asymmetric 12-column CSS Grid (`grid-template-columns: repeat(12, 1fr)`) with alternating spans (`span-7`, `span-5`, `span-12`, `span-6`).
4. **Client-Side Hash Routing**:
   - Smooth navigation between pages (`#products`, `#about`, `#contact`, `#projects`) and deep modal links (`#product/modular-lounge-chair`) without requiring extra routing libraries or server page reloads.

### B. Backend Code Style
1. **Modular Layered Architecture**:
   - **Models** (`backend/app/models/`): Define SQLite database tables using SQLAlchemy Declarative Base.
   - **Schemas** (`backend/app/schemas/`): Define Pydantic validation models ensuring strict input/output shapes.
   - **API Endpoints** (`backend/app/api/`): Clean FastAPI route controllers handling HTTP requests and responses.
   - **Database Session** (`backend/app/database/`): Connection pooling and session lifecycle management via `get_db` dependency injection.
2. **Safe Input Validation**:
   - Contact form uses Pydantic's `EmailStr` and field constraints to validate data before persisting to SQLite.
3. **RESTful Architecture**:
   - Predictable HTTP methods (`GET`, `POST`) and standardized status codes (`200 OK`, `201 Created`, `404 Not Found`, `422 Unprocessable Entity`).

---

## 4. Key Architectural Features & Important Notes

### 1. Centralized Startup (`python start_up.py`)
- You do **not** need to open two separate command terminals.
- Running `python start_up.py` from the project root automatically:
  1. Validates the Python interpreter, FastAPI directory, and npm binary.
  2. Launches Uvicorn (FastAPI) on `http://127.0.0.1:8000` with auto-reloading.
  3. Launches Vite dev server on `http://localhost:5173`.
  4. Merges and color-codes logs (`[BACKEND]` in cyan, `[FRONTEND]` in green).
  5. Terminates the entire child process tree cleanly when you press `Ctrl+C`.

### 2. Architectural Editorial Design Direction
- **Atmosphere**: Calm, quiet, minimal, image-driven, and sophisticated.
- **Palette**: Warm off-white background (`#f9f8f6`), near-black typography (`#141413`), subtle sand surfaces (`#f3f1ec`), hairline border accents (`#e6e3dc`).
- **Typography**:
  - Headings: *Cormorant Garamond* (editorial architectural serif)
  - Body & Metadata: *Plus Jakarta Sans* (clean geometric sans-serif)
- **Deliberately Avoided**: Large colorful gradients, SaaS cards, heavy drop-shadows, spinning gimmicky animations, or generic agency marketing sections.

### 3. Separation of Concerns for Upcoming Pages
- **Products Page**: An archival design portfolio displaying custom furniture and interior concepts. **NOT** an ecommerce store (no cart, no checkout, no pricing, no purchase flow).
- **About Page**: A studio and people profile answering *"Who is Studio Desire?"* (concise practice story, collaborator roster, capabilities, and approach statement).
- **Planning, 3D & Blueprint**: Kept as clean `Coming Soon` placeholders until future development phases.
- **Contact Inquiries**: Stored directly in SQLite table `contact_inquiries` with initial status `new`. No real emails are sent during the client prototype stage.

---

## 5. Summary Cheat Sheet for Development

| Action | Command | Where to run |
| :--- | :--- | :--- |
| **Start entire project (Frontend + Backend)** | `python start_up.py` | Project root (`/`) |
| **Re-seed database (Projects & Products)** | `py backend/seed.py` | Project root (`/`) |
| **Typecheck & compile Frontend** | `npm run build` | `frontend/` directory |
| **Run Frontend alone** | `npm run dev` | `frontend/` directory |
| **Run Backend alone** | `uvicorn app.main:app --reload` | `backend/` directory |
| **View Interactive API Documentation** | Browse `http://127.0.0.1:8000/docs` | Any web browser |
| **View Website Application** | Browse `http://localhost:5173` | Any web browser |
