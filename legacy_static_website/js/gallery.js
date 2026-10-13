/**
 * STUDIO DESIRE — PROJECT DETAIL & GALLERY CONTROLLER
 */

(function () {
  const getProjects = () => (window.StudioDesireData ? window.StudioDesireData.PROJECTS : []);

  class GalleryController {
    constructor() {
      this.currentProject = null;
      this.currentImageIndex = 0;
      this.galleryImages = [];

      // Cache DOM Elements
      this.modalBackdrop = document.getElementById("projectDetailModal");
      this.modalContainer = document.getElementById("modalContainer");
      this.modalCloseBtn = document.getElementById("modalCloseBtn");
      this.modalPrevBtn = document.getElementById("modalPrevBtn");
      this.modalNextBtn = document.getElementById("modalNextBtn");

      // Modal Content Elements
      this.modalCategoryBadge = document.getElementById("modalCategoryBadge");
      this.modalIndexBadge = document.getElementById("modalIndexBadge");
      this.modalTitle = document.getElementById("modalTitle");
      this.modalSubtitle = document.getElementById("modalSubtitle");
      this.specLocation = document.getElementById("specLocation");
      this.specCategory = document.getElementById("specCategory");
      this.specYear = document.getElementById("specYear");
      this.specArea = document.getElementById("specArea");
      this.modalDescription = document.getElementById("modalDescription");
      this.modalVideoSection = document.getElementById("modalVideoSection");
      this.modalVideoContainer = document.getElementById("modalVideoContainer");
      this.modalGalleryStack = document.getElementById("modalGalleryStack");

      // Lightbox Elements
      this.lightboxBackdrop = document.getElementById("lightboxModal");
      this.lightboxCloseBtn = document.getElementById("lightboxCloseBtn");
      this.lightboxPrevBtn = document.getElementById("lightboxPrevBtn");
      this.lightboxNextBtn = document.getElementById("lightboxNextBtn");
      this.lightboxImage = document.getElementById("lightboxImage");
      this.lightboxCaption = document.getElementById("lightboxCaption");
      this.lightboxCounter = document.getElementById("lightboxCounter");

      this.initEventListeners();
    }

    initEventListeners() {
      // Modal Close
      if (this.modalCloseBtn) {
        this.modalCloseBtn.addEventListener("click", () => this.closeProjectDetail());
      }

      if (this.modalBackdrop) {
        this.modalBackdrop.addEventListener("click", (e) => {
          if (e.target === this.modalBackdrop) {
            this.closeProjectDetail();
          }
        });
      }

      // Modal Pagination
      if (this.modalPrevBtn) {
        this.modalPrevBtn.addEventListener("click", () => this.navigateAdjacentProject(-1));
      }
      if (this.modalNextBtn) {
        this.modalNextBtn.addEventListener("click", () => this.navigateAdjacentProject(1));
      }

      // Lightbox Controls
      if (this.lightboxCloseBtn) {
        this.lightboxCloseBtn.addEventListener("click", () => this.closeLightbox());
      }
      if (this.lightboxPrevBtn) {
        this.lightboxPrevBtn.addEventListener("click", () => this.navigateLightbox(-1));
      }
      if (this.lightboxNextBtn) {
        this.lightboxNextBtn.addEventListener("click", () => this.navigateLightbox(1));
      }

      if (this.lightboxBackdrop) {
        this.lightboxBackdrop.addEventListener("click", (e) => {
          if (e.target === this.lightboxBackdrop) {
            this.closeLightbox();
          }
        });
      }

      // Keyboard Shortcuts (Esc, Arrow keys)
      window.addEventListener("keydown", (e) => {
        if (this.lightboxBackdrop && this.lightboxBackdrop.classList.contains("open")) {
          if (e.key === "Escape") this.closeLightbox();
          if (e.key === "ArrowLeft") this.navigateLightbox(-1);
          if (e.key === "ArrowRight") this.navigateLightbox(1);
          return;
        }

        if (this.modalBackdrop && this.modalBackdrop.classList.contains("open")) {
          if (e.key === "Escape") this.closeProjectDetail();
          if (e.key === "ArrowLeft") this.navigateAdjacentProject(-1);
          if (e.key === "ArrowRight") this.navigateAdjacentProject(1);
        }
      });
    }

    openProjectDetail(projectId) {
      const projects = getProjects();
      const project = projects.find((p) => p.id === projectId || p.slug === projectId);
      if (!project) return;

      this.currentProject = project;
      this.galleryImages = project.images || [];

      // Populate Headers & Badges
      if (this.modalCategoryBadge) this.modalCategoryBadge.textContent = `${project.category} · ${project.year}`;
      if (this.modalIndexBadge) this.modalIndexBadge.textContent = project.id.toUpperCase();
      if (this.modalTitle) this.modalTitle.textContent = project.title;
      if (this.modalSubtitle) this.modalSubtitle.textContent = project.subtitle || "";

      // Populate Specs
      if (this.specLocation) this.specLocation.textContent = project.location;
      if (this.specCategory) this.specCategory.textContent = project.category;
      if (this.specYear) this.specYear.textContent = project.year;
      if (this.specArea) this.specArea.textContent = project.area || "N/A";

      // Populate Narrative
      if (this.modalDescription) this.modalDescription.textContent = project.description;

      // Handle Video Section
      if (this.modalVideoSection && this.modalVideoContainer) {
        if (project.hasVideo && project.video) {
          this.modalVideoSection.style.display = "block";
          this.modalVideoContainer.innerHTML = `
            <div class="video-frame-wrapper">
              <video controls preload="metadata" poster="${project.video.poster || project.coverImage}">
                <source src="${project.video.url}" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
            ${project.video.caption ? `<p class="video-caption">${project.video.caption}</p>` : ""}
          `;
        } else {
          this.modalVideoSection.style.display = "none";
          this.modalVideoContainer.innerHTML = "";
        }
      }

      // Populate Gallery Stack
      if (this.modalGalleryStack) {
        this.modalGalleryStack.innerHTML = this.galleryImages
          .map(
            (img, idx) => `
            <figure class="gallery-item" data-index="${idx}">
              <div class="gallery-item-image-wrapper">
                <img src="${img.url}" alt="${project.title} - Space Detail ${idx + 1}" loading="lazy" />
              </div>
              <figcaption class="gallery-caption">
                <span>${img.caption || `${project.title} — Detail view`}</span>
                <span class="gallery-index">0${idx + 1} / 0${this.galleryImages.length}</span>
              </figcaption>
            </figure>
          `
          )
          .join("");

        // Attach click handlers to open lightbox
        const galleryItems = this.modalGalleryStack.querySelectorAll(".gallery-item");
        galleryItems.forEach((item) => {
          item.addEventListener("click", () => {
            const idx = parseInt(item.getAttribute("data-index"), 10);
            this.openLightbox(idx);
          });
        });
      }

      // Show Modal
      if (this.modalBackdrop) this.modalBackdrop.classList.add("open");
      document.body.style.overflow = "hidden";

      // Scroll modal container to top
      if (this.modalContainer) {
        this.modalContainer.scrollTop = 0;
      }
    }

    closeProjectDetail() {
      // Pause any playing videos
      if (this.modalVideoContainer) {
        const vid = this.modalVideoContainer.querySelector("video");
        if (vid) vid.pause();
      }

      if (this.modalBackdrop) this.modalBackdrop.classList.remove("open");
      document.body.style.overflow = "";

      // Clear hash if it was pointing to project
      if (window.location.hash.startsWith("#project/")) {
        history.replaceState(null, "", "#projects");
      }
    }

    navigateAdjacentProject(direction) {
      const projects = getProjects();
      if (!this.currentProject || projects.length === 0) return;
      const currentIndex = projects.findIndex((p) => p.id === this.currentProject.id);
      let newIndex = currentIndex + direction;

      if (newIndex < 0) newIndex = projects.length - 1;
      if (newIndex >= projects.length) newIndex = 0;

      const nextProject = projects[newIndex];
      this.openProjectDetail(nextProject.id);
      history.replaceState(null, "", `#project/${nextProject.slug}`);
    }

    /* Lightbox Methods */
    openLightbox(index) {
      if (!this.galleryImages || this.galleryImages.length === 0) return;
      this.currentImageIndex = index;
      this.updateLightboxDisplay();

      if (this.lightboxBackdrop) this.lightboxBackdrop.classList.add("open");
    }

    closeLightbox() {
      if (this.lightboxBackdrop) this.lightboxBackdrop.classList.remove("open");
    }

    navigateLightbox(direction) {
      if (!this.galleryImages || this.galleryImages.length === 0) return;
      this.currentImageIndex += direction;

      if (this.currentImageIndex < 0) {
        this.currentImageIndex = this.galleryImages.length - 1;
      } else if (this.currentImageIndex >= this.galleryImages.length) {
        this.currentImageIndex = 0;
      }

      this.updateLightboxDisplay();
    }

    updateLightboxDisplay() {
      const item = this.galleryImages[this.currentImageIndex];
      if (!item) return;

      if (this.lightboxImage) {
        this.lightboxImage.src = item.url;
        this.lightboxImage.alt = item.caption || "Studio Desire Gallery Image";
      }

      if (this.lightboxCaption) {
        this.lightboxCaption.textContent = item.caption || `${this.currentProject ? this.currentProject.title : "Project"} Archival Plate`;
      }

      if (this.lightboxCounter) {
        this.lightboxCounter.textContent = `0${this.currentImageIndex + 1} / 0${this.galleryImages.length}`;
      }
    }
  }

  // Instantiate and bind to window
  const galleryController = new GalleryController();
  window.StudioDesireGallery = galleryController;
})();
