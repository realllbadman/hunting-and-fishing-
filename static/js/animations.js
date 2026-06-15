/* ════════════════════════════════════════════════════════════════════
   Hunting & Fishing Supply Co — Animation System (vanilla JS)
   Navbar scroll state · IntersectionObserver scroll reveal · hero particles
   All motion respects prefers-reduced-motion. No inline styles for
   reveal/navbar — only class toggles. (Particles need randomized inline
   geometry by nature.)
   ════════════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Mark that JS is active so reveal elements may start hidden. If this script
  // never runs, the class is absent and .reveal content stays visible.
  document.documentElement.classList.add("anim-ready");

  /* ── 1. Sticky navbar: add .scrolled past 60px ── */
  var nav = document.querySelector(".bar-nav");
  if (nav) {
    var setNavState = function () {
      nav.classList.toggle("scrolled", window.scrollY > 60);
    };
    setNavState();
    window.addEventListener("scroll", setNavState, { passive: true });
  }

  /* ── 3. Scroll reveal (fade + slide up), fire once ── */
  var reveals = document.querySelectorAll(".reveal");
  if (reveals.length) {
    if (reduceMotion || !("IntersectionObserver" in window)) {
      // No motion / no support: show everything immediately.
      reveals.forEach(function (el) { el.classList.add("visible"); });
    } else {
      var observer = new IntersectionObserver(
        function (entries, obs) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              obs.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.12 }
      );
      reveals.forEach(function (el) { observer.observe(el); });
    }
  }

  /* ── Page-leave transition: fade current content out, then navigate ── */
  function leaveTo(href) {
    if (reduceMotion) { window.location.href = href; return; }
    document.body.classList.add("page-leaving");
    window.setTimeout(function () { window.location.href = href; }, 200);
  }
  // Exposed so inline handlers (e.g. product cards) can use the same transition.
  window.navTo = leaveTo;

  // Clear the leave-state when the page is shown again — critical for the
  // browser Back button / bfcache restore, otherwise the restored page stays
  // faded out (blank). pageshow fires on both fresh loads and bfcache restores.
  window.addEventListener("pageshow", function () {
    document.body.classList.remove("page-leaving");
  });

  // Fix blank page on Back: the browser restores the page from its
  // back/forward cache with body.page-leaving still set (main = opacity 0).
  // Clear it whenever the page is shown (initial load or bfcache restore).
  window.addEventListener("pageshow", function () {
    document.body.classList.remove("page-leaving");
  });

  if (!reduceMotion) {
    document.addEventListener("click", function (e) {
      if (e.defaultPrevented || e.button !== 0 ||
          e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest ? e.target.closest("a") : null;
      if (!a) return;
      var href = a.getAttribute("href");
      if (!href) return;
      if (a.target && a.target !== "_self") return;       // new tab/window
      if (a.hasAttribute("download")) return;
      if (a.hasAttribute("data-no-transition")) return;
      if (href.charAt(0) === "#") return;                 // in-page anchor
      if (/^(mailto:|tel:|javascript:)/i.test(href)) return;
      var url;
      try { url = new URL(href, window.location.href); } catch (err) { return; }
      if (url.origin !== window.location.origin) return;  // external
      e.preventDefault();
      leaveTo(url.href);
    });
  }

  /* ── 8. Floating particles in the hero (once, on load) ── */
  var hero = document.querySelector(".hero");
  if (hero && !reduceMotion) {
    var COUNT = 18;
    var fragment = document.createDocumentFragment();
    for (var i = 0; i < COUNT; i++) {
      var p = document.createElement("div");
      p.className = "hero-particle";
      var size = (2 + Math.random() * 4).toFixed(1);     // 2–6px
      p.style.width = size + "px";
      p.style.height = size + "px";
      p.style.left = (Math.random() * 100).toFixed(2) + "%";
      p.style.animationDuration = (8 + Math.random() * 12).toFixed(1) + "s"; // 8–20s
      p.style.animationDelay = (-Math.random() * 20).toFixed(1) + "s";       // desync
      fragment.appendChild(p);
    }
    hero.appendChild(fragment);
  }
})();
