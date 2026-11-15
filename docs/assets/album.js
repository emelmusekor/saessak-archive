/* 앨범: data/album.js 의 window.ALBUM = {groups:[{key,label}], photos:[{file,small,alt,group,caption}]} */
(function () {
  var A = window.ALBUM;
  var box = document.getElementById("album");
  if (!A || !box) return;
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var current = "all", shown = [];

  var filter = document.getElementById("album-filter");
  filter.innerHTML = [{ key: "all", label: "전체" }].concat(A.groups).map(function (g) {
    return '<button type="button" data-k="' + esc(g.key) + '"' + (g.key === "all" ? ' aria-pressed="true"' : ' aria-pressed="false"') + ">" + esc(g.label) + "</button>";
  }).join("");
  filter.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) return;
    current = b.getAttribute("data-k");
    [].forEach.call(filter.children, function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    render();
  });

  function render() {
    shown = A.photos.filter(function (p) { return current === "all" || p.group === current; });
    box.innerHTML = shown.map(function (p, i) {
      return '<li><button type="button" data-i="' + i + '"><img src="' + esc(p.small || p.file) + '" alt="' + esc(p.alt) + '" loading="lazy"></button></li>';
    }).join("");
  }
  render();

  var lb = document.getElementById("lightbox"), img = lb.querySelector("img"), cap = lb.querySelector(".lb-cap"), idx = 0;
  function show(i) {
    idx = (i + shown.length) % shown.length;
    var p = shown[idx];
    img.src = p.file; img.alt = p.alt;
    cap.textContent = (p.caption ? p.caption + " · " : "") + p.alt;
  }
  box.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-i]");
    if (!b) return;
    show(+b.getAttribute("data-i"));
    if (lb.showModal) lb.showModal(); else lb.setAttribute("open", "");
  });
  lb.querySelector(".lb-close").addEventListener("click", function () { lb.close(); });
  lb.querySelector(".lb-prev").addEventListener("click", function () { show(idx - 1); });
  lb.querySelector(".lb-next").addEventListener("click", function () { show(idx + 1); });
  lb.addEventListener("click", function (e) { if (e.target === lb) lb.close(); });
  document.addEventListener("keydown", function (e) {
    if (!lb.open) return;
    if (e.key === "ArrowLeft") show(idx - 1);
    if (e.key === "ArrowRight") show(idx + 1);
  });
})();
