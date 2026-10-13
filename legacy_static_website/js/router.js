/**
 * STUDIO DESIRE — CLIENT-SIDE ROUTER & VIEW CONTROLLER
 */

(function () {
  const getData = () => window.StudioDesireData || {};
  const getGallery = () => window.StudioDesireGallery;

  class Router {
    constructor() {
      this.projectsView = document.getElementById("projectsView");
      this.placeholderView = document.getElementById("placeholderView");

      // Placeholder View Elements
      this.placeholderCode = document.getElementById("placeholderCode");
      this.placeholderTitle = document.getElementById("placeholderTitle");
      this.placeholderDesc = document.getElementById("placeholderDesc");
      this.placeholderNote = document.getElementById("placeholderNote");
      this.placeholderFeaturesList = document.getElementById("placeholderFeaturesList");

      // Nav Links
      this.navLinks = document.querySelectorAll(".nav-link, .mobile-nav-link, .footer-link");

      this.init();
    }

    init() {
      window.addEventListener("hashchange", () => this.handleRoute());
      // Initial routing on page load
      this.handleRoute();
    }

    handleRoute() {
      const data = getData();
      const gallery = getGallery();
      const rawHash = window.location.hash.slice(1).toLowerCase();
      const cleanHash = rawHash || "projects";

      // Handle Project Detail deep link: #project/residence-01 or #project/project-01
      if (cleanHash.startsWith("project/")) {
        const slugOrId = cleanHash.replace("project/", "");
        this.showProjectsView();
        this.updateActiveNav("projects");
        if (gallery) {
          gallery.openProjectDetail(slugOrId);
        }
        return;
      }

      // Check if route is a Coming Soon placeholder
      const placeholderSections = data.PLACEHOLDER_SECTIONS || {};
      if (placeholderSections[cleanHash]) {
        this.showPlaceholderView(cleanHash);
        this.updateActiveNav(cleanHash);
        if (gallery) {
          gallery.closeProjectDetail();
        }
        return;
      }

      // Default to Projects View
      this.showProjectsView();
      this.updateActiveNav("projects");
      if (gallery) {
        gallery.closeProjectDetail();
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    showProjectsView() {
      if (this.projectsView) this.projectsView.style.display = "block";
      if (this.placeholderView) this.placeholderView.classList.remove("active");
    }

    showPlaceholderView(sectionKey) {
      const data = getData();
      const section = (data.PLACEHOLDER_SECTIONS || {})[sectionKey];
      if (!section) return;

      if (this.projectsView) this.projectsView.style.display = "none";
      if (this.placeholderView) this.placeholderView.classList.add("active");

      if (this.placeholderCode) this.placeholderCode.textContent = section.code || "00";
      if (this.placeholderTitle) this.placeholderTitle.textContent = section.title;
      if (this.placeholderDesc) this.placeholderDesc.textContent = section.description;
      if (this.placeholderNote) this.placeholderNote.textContent = section.note;

      if (this.placeholderFeaturesList && section.expectedFeatures) {
        this.placeholderFeaturesList.innerHTML = section.expectedFeatures
          .map(
            (feat) => `
            <li style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.8125rem; color: var(--text-secondary);">
              <span style="display: inline-block; width: 4px; height: 4px; background: var(--accent-warm); border-radius: 50%;"></span>
              <span>${feat}</span>
            </li>
          `
          )
          .join("");
      }

      window.scrollTo({ top: 0, behavior: "smooth" });
    }

    updateActiveNav(activeKey) {
      // Refresh navLinks reference in case DOM was updated
      this.navLinks = document.querySelectorAll(".nav-link, .mobile-nav-link, .footer-link");
      this.navLinks.forEach((link) => {
        const routeAttr = link.getAttribute("data-route");
        if (routeAttr === activeKey) {
          link.classList.add("active");
          link.setAttribute("aria-current", "page");
        } else {
          link.classList.remove("active");
          link.removeAttribute("aria-current");
        }
      });
    }
  }

  const router = new Router();
  window.StudioDesireRouter = router;
})();
