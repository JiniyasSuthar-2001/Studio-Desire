/**
 * STUDIO DESIRE — MAIN APPLICATION LOGIC
 */

(function () {
  const getData = () => window.StudioDesireData || { CATEGORIES: [], MEDIA_TYPES: [], PROJECTS: [] };
  const API_BASE_URL = "http://localhost:8000/api";

  class App {
    constructor() {
      this.activeCategory = "ALL";
      this.activeMediaType = "all"; // "all" | "photos" | "videos"
      this.apiProjects = null;

      // Cache Elements
      this.featuredContainer = document.getElementById("featuredProjectContainer");
      this.categoryFiltersList = document.getElementById("categoryFiltersList");
      this.mediaFiltersContainer = document.getElementById("mediaFiltersContainer");
      this.editorialGrid = document.getElementById("editorialGrid");
      this.projectCounter = document.getElementById("projectCounter");

      // Mobile Navigation Drawer
      this.mobileNavToggle = document.getElementById("mobileNavToggle");
      this.mobileDrawer = document.getElementById("mobileDrawer");

      this.init();
    }

    async init() {
      await this.fetchLiveApiData();
      this.renderFeaturedProject();
      this.renderCategoryFilters();
      this.renderMediaFilters();
      this.renderProjectGrid();
      this.initMobileNav();
    }

    async fetchLiveApiData() {
      try {
        const res = await fetch(`${API_BASE_URL}/projects`);
        if (res.ok) {
          const json = await res.json();
          if (json && json.projects) {
            // Map backend schema to format expected by UI
            this.apiProjects = json.projects.map((p) => ({
              id: `project-${String(p.id).padStart(2, "0")}`,
              dbId: p.id,
              slug: p.slug,
              title: p.title,
              subtitle: p.subtitle,
              location: p.location,
              year: String(p.year),
              category: p.category.toUpperCase(),
              type: p.project_type,
              area: p.area,
              featured: p.featured,
              isDemo: p.is_demo,
              description: p.description,
              coverImage: p.cover_image,
              hasVideo: p.has_video,
              gridSpan: p.grid_span,
              aspectRatio: p.aspect_ratio
            }));
          }
        }
      } catch {
        // Fallback gracefully to bundled StudioDesireData
      }
    }

    /* --------------------------------------------------------------------------
       FEATURED PROJECT HERO
       -------------------------------------------------------------------------- */
    renderFeaturedProject() {
      if (!this.featuredContainer) return;
      const data = getData();
      const projects = this.apiProjects || data.PROJECTS || [];
      const featured = projects.find((p) => p.featured) || projects[0];
      if (!featured) return;

      this.featuredContainer.innerHTML = `
        <div class="featured-label-bar">
          <div class="featured-flag">01 FEATURED PROJECT</div>
          <div class="featured-index">${featured.id.toUpperCase()}</div>
        </div>
        <div class="featured-card" data-project-id="${featured.id}" role="button" tabindex="0" aria-label="View featured project: ${featured.title}">
          <div class="featured-media-container">
            <img src="${featured.coverImage}" alt="${featured.title} — ${featured.location}" class="featured-image" loading="eager" />
            <div class="demo-tag">DEMO PROJECT</div>
            <div class="featured-overlay">
              <div class="featured-info">
                <div class="featured-title-group">
                  <h2>${featured.title}</h2>
                  <div class="featured-meta">
                    <span>${featured.location}</span>
                    <span>·</span>
                    <span>${featured.category}</span>
                    <span>·</span>
                    <span>${featured.year}</span>
                  </div>
                </div>
                <div class="featured-action">
                  <span>View Project</span>
                  <span aria-hidden="true">→</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;

      const card = this.featuredContainer.querySelector(".featured-card");
      if (card) {
        const openDetail = () => {
          window.location.hash = `#project/${featured.slug}`;
        };
        card.addEventListener("click", openDetail);
        card.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openDetail();
          }
        });
      }
    }

    /* --------------------------------------------------------------------------
       CATEGORY FILTERS
       -------------------------------------------------------------------------- */
    renderCategoryFilters() {
      if (!this.categoryFiltersList) return;
      const data = getData();
      const categories = data.CATEGORIES || [];

      this.categoryFiltersList.innerHTML = categories
        .map(
          (cat) => `
        <li>
          <button 
            class="filter-btn ${cat === this.activeCategory ? "active" : ""}" 
            data-category="${cat}"
            role="tab"
            aria-selected="${cat === this.activeCategory ? "true" : "false"}"
          >
            ${cat}
          </button>
        </li>
      `
        )
        .join("");

      const buttons = this.categoryFiltersList.querySelectorAll(".filter-btn");
      buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const cat = btn.getAttribute("data-category");
          if (cat === this.activeCategory) return;

          this.activeCategory = cat;
          buttons.forEach((b) => {
            b.classList.remove("active");
            b.setAttribute("aria-selected", "false");
          });
          btn.classList.add("active");
          btn.setAttribute("aria-selected", "true");

          this.renderProjectGrid();
        });
      });
    }

    /* --------------------------------------------------------------------------
       MEDIA TYPE SWITCHER (ALL / PHOTOS / VIDEOS)
       -------------------------------------------------------------------------- */
    renderMediaFilters() {
      if (!this.mediaFiltersContainer) return;
      const data = getData();
      const mediaTypes = data.MEDIA_TYPES || [];

      this.mediaFiltersContainer.innerHTML = mediaTypes
        .map(
          (m) => `
        <button 
          class="media-filter-btn ${m.id === this.activeMediaType ? "active" : ""}" 
          data-media="${m.id}"
        >
          ${m.label}
        </button>
      `
        )
        .join("");

      const buttons = this.mediaFiltersContainer.querySelectorAll(".media-filter-btn");
      buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
          const media = btn.getAttribute("data-media");
          if (media === this.activeMediaType) return;

          this.activeMediaType = media;
          buttons.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");

          this.renderProjectGrid();
        });
      });
    }

    /* --------------------------------------------------------------------------
       ASYMMETRIC EDITORIAL PROJECT GRID
       -------------------------------------------------------------------------- */
    getFilteredProjects() {
      const data = getData();
      const projects = this.apiProjects || data.PROJECTS || [];

      return projects.filter((proj) => {
        // Category Match
        const matchesCategory =
          this.activeCategory === "ALL" || proj.category.toUpperCase() === this.activeCategory.toUpperCase();

        // Media Type Match
        let matchesMedia = true;
        if (this.activeMediaType === "photos") {
          matchesMedia = !proj.hasVideo || proj.images.length > 0;
        } else if (this.activeMediaType === "videos") {
          matchesMedia = proj.hasVideo === true;
        }

        return matchesCategory && matchesMedia;
      });
    }

    renderProjectGrid() {
      if (!this.editorialGrid) return;

      const filtered = this.getFilteredProjects();
      const data = getData();

      // Update Counter
      if (this.projectCounter) {
        this.projectCounter.textContent = `[ ${filtered.length} ${filtered.length === 1 ? "Space" : "Spaces"} Indexed ]`;
      }

      if (filtered.length === 0) {
        this.editorialGrid.innerHTML = `
          <div class="grid-empty-state">
            <h3>No Projects Located</h3>
            <p>There are currently no spaces matching the selected "${this.activeCategory}" archive criteria.</p>
          </div>
        `;
        return;
      }

      // Map projects with architectural rhythmic layout spans
      this.editorialGrid.innerHTML = filtered
        .map((proj, idx) => {
          const spanClass = this.getEditorialSpan(idx, filtered.length);
          const ratioClass = this.getEditorialRatio(idx);

          return `
          <article 
            class="project-card ${spanClass}" 
            data-project-id="${proj.id}"
            role="button"
            tabindex="0"
            aria-label="View project dossier: ${proj.title}, ${proj.location}"
          >
            <div class="card-media-wrapper ${ratioClass}">
              <img 
                src="${proj.coverImage}" 
                alt="${proj.title} — ${proj.location} Architectural Interior" 
                class="card-img" 
                loading="lazy" 
              />
              <span class="demo-tag">DEMO PROJECT</span>
              ${
                proj.hasVideo
                  ? `
                <div class="video-indicator" title="Includes architectural spatial video">
                  <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                  <span>Motion</span>
                </div>
              `
                  : ""
              }
            </div>
            <div class="card-header-row">
              <h3 class="card-title">${proj.title}</h3>
              <span class="card-arrow" aria-hidden="true">→</span>
            </div>
            <div class="card-meta-row">
              <span class="card-location">${proj.location}</span>
              <span class="card-category-year">${proj.category} · ${proj.year}</span>
            </div>
          </article>
        `;
        })
        .join("");

      // Attach click listeners to cards
      const cards = this.editorialGrid.querySelectorAll(".project-card");
      cards.forEach((card) => {
        const projId = card.getAttribute("data-project-id");
        const proj = (data.PROJECTS || []).find((p) => p.id === projId);
        if (!proj) return;

        const triggerOpen = () => {
          window.location.hash = `#project/${proj.slug}`;
        };

        card.addEventListener("click", triggerOpen);
        card.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            triggerOpen();
          }
        });
      });
    }

    /**
     * Generates asymmetric column rhythm for editorial magazine composition
     */
    getEditorialSpan(index, total) {
      const patterns = [
        "span-7",  // Asymmetric Left dominant
        "span-5",  // Asymmetric Right support
        "span-4",  // Triad 1
        "span-4",  // Triad 2
        "span-4",  // Triad 3
        "span-12", // Full-width panoramic break
        "span-5",  // Flipped rhythm: Left narrow
        "span-7",  // Flipped rhythm: Right wide
        "span-6",  // Balanced dual
        "span-6"   // Balanced dual
      ];
      return patterns[index % patterns.length] || "span-6";
    }

    getEditorialRatio(index) {
      const ratios = [
        "ratio-landscape",
        "ratio-portrait",
        "ratio-standard",
        "ratio-standard",
        "ratio-standard",
        "ratio-hero",
        "ratio-portrait",
        "ratio-landscape",
        "ratio-standard",
        "ratio-landscape"
      ];
      return ratios[index % ratios.length] || "ratio-standard";
    }

    /* --------------------------------------------------------------------------
       MOBILE NAVIGATION DRAWER
       -------------------------------------------------------------------------- */
    initMobileNav() {
      if (!this.mobileNavToggle || !this.mobileDrawer) return;

      this.mobileNavToggle.addEventListener("click", () => {
        const isOpen = this.mobileDrawer.classList.contains("open");
        if (isOpen) {
          this.closeMobileNav();
        } else {
          this.openMobileNav();
        }
      });

      // Close when clicking any link inside mobile drawer
      const drawerLinks = this.mobileDrawer.querySelectorAll(".mobile-nav-link");
      drawerLinks.forEach((link) => {
        link.addEventListener("click", () => this.closeMobileNav());
      });
    }

    openMobileNav() {
      this.mobileDrawer.classList.add("open");
      this.mobileNavToggle.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
    }

    closeMobileNav() {
      this.mobileDrawer.classList.remove("open");
      this.mobileNavToggle.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    }
  }

  // Auto-initialize
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => new App());
  } else {
    new App();
  }
})();
