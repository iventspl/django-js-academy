/* Django Handbook — chapter table-of-contents highlighting and target flash. */
(function () {
  "use strict";

  const root = document.querySelector("[data-handbook-chapter]");
  if (!root) return;

  const sections = Array.from(root.querySelectorAll(".hb-section[id]"));
  const links = Array.from(
    document.querySelectorAll(
      '.hb-toc nav a[href^="#"], .hb-mobile-toc nav a[href^="#"]',
    ),
  );
  if (!sections.length || !links.length) return;

  const linkById = new Map();
  links.forEach((link) => {
    linkById.set(link.getAttribute("href").slice(1), link);
  });

  const setActive = (id) => {
    links.forEach((link) => {
      const active = link.getAttribute("href") === `#${id}`;
      link.classList.toggle("is-active", active);
      if (active) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    });
  };

  const flash = (id) => {
    const target = document.getElementById(id);
    if (!target) return;
    target.classList.remove("is-target");
    // Restart the animation when the same link is clicked twice.
    void target.offsetWidth;
    target.classList.add("is-target");
    window.setTimeout(() => target.classList.remove("is-target"), 2400);
  };

  const goToHash = () => {
    const id = window.location.hash.slice(1);
    if (!id) return;
    setActive(id);
    flash(id);
    const target = document.getElementById(id);
    if (target) target.scrollIntoView({ block: "start" });
  };

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length) setActive(visible[0].target.id);
      },
      { rootMargin: "-12% 0px -68% 0px", threshold: [0, 0.2, 0.6] },
    );
    sections.forEach((section) => observer.observe(section));
  }

  links.forEach((link) => {
    link.addEventListener("click", () => {
      const id = link.getAttribute("href").slice(1);
      setActive(id);
      flash(id);
    });
  });

  if (window.location.hash) {
    window.setTimeout(goToHash, 50);
  }
  window.addEventListener("hashchange", goToHash);
})();
