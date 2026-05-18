(function () {
  "use strict";

  const state = {
    marketingReady: true,
    activeSection: "hero",
  };
  window.marketingReady = state.marketingReady;

  const header = document.querySelector("[data-elevate]");
  const navLinks = Array.from(document.querySelectorAll(".site-nav a"));
  const sections = navLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  function updateHeader() {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 8);
  }

  function activateNav(sectionId) {
    state.activeSection = sectionId;
    navLinks.forEach((link) => {
      link.classList.toggle("active", link.getAttribute("href") === `#${sectionId}`);
    });
  }

  if ("IntersectionObserver" in window) {
    const sectionObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) activateNav(visible.target.id);
      },
      { threshold: [0.18, 0.35, 0.55], rootMargin: "-12% 0px -48% 0px" },
    );
    sections.forEach((section) => sectionObserver.observe(section));

    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -7% 0px" },
    );
    document.querySelectorAll(".scene").forEach((section) => revealObserver.observe(section));
  } else {
    document.querySelectorAll(".scene").forEach((section) => section.classList.add("is-visible"));
  }

  navLinks.forEach((link) => {
    link.addEventListener("click", () => {
      const target = link.getAttribute("href")?.replace("#", "");
      if (target) activateNav(target);
    });
  });

  window.addEventListener("scroll", updateHeader, { passive: true });
  updateHeader();

  document.querySelectorAll(".candidate").forEach((candidate) => {
    candidate.addEventListener("click", () => {
      document.querySelectorAll(".candidate").forEach((item) => item.classList.remove("active"));
      candidate.classList.add("active");
    });
  });

  const gateButtons = document.querySelectorAll(".gate-actions button:not(.review)");
  gateButtons.forEach((button) => {
    button.addEventListener("click", () => {
      button.classList.toggle("confirmed");
      button.textContent = button.classList.contains("confirmed")
        ? button.textContent.replace("确认", "已确认")
        : button.textContent.replace("已确认", "确认");
    });
  });
})();
