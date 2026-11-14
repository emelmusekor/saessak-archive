(function () {
  /* header: shadow on scroll, mobile menu */
  var header = document.querySelector(".header");
  if (header) {
    var onScroll = function () { header.classList.toggle("is-scrolled", window.scrollY > 4); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    var btn = header.querySelector(".menu-btn");
    if (btn) {
      var setOpen = function (open) {
        header.classList.toggle("menu-open", open);
        btn.setAttribute("aria-expanded", String(open));
        btn.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
      };
      btn.addEventListener("click", function () { setOpen(!header.classList.contains("menu-open")); });
      header.querySelectorAll(".gnb a").forEach(function (a) { a.addEventListener("click", function () { setOpen(false); }); });
      document.addEventListener("keydown", function (e) { if (e.key === "Escape") setOpen(false); });
    }
  }

  /* year tabs (archive board) */
  document.querySelectorAll("[data-tabs]").forEach(function (root) {
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
    var label = root.querySelector("[data-year-label]");
    var sub = root.querySelector("[data-year-sub]");
    function select(tab) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        var panel = document.getElementById(t.getAttribute("aria-controls"));
        if (panel) panel.hidden = !on;
      });
      if (label) label.textContent = tab.dataset.label || "";
      if (sub) sub.textContent = tab.dataset.sub || "";
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(t); });
      t.addEventListener("keydown", function (e) {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        e.preventDefault();
        var next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        next.focus();
        select(next);
      });
    });
  });

  /* respect reduced motion for the hero video */
  var video = document.querySelector(".hero-video");
  if (video && window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    video.removeAttribute("autoplay");
    try { video.pause(); } catch (e) { /* ignore */ }
  }
})();
