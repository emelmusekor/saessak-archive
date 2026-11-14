/* 자료실: data/materials.js 의 window.MATERIALS 를 연도 → 프로그램 순으로 그린다. */
(function () {
  var M = window.MATERIALS;
  var root = document.getElementById("library");
  if (!M || !root || !(M.items || []).length) return;
  var sec = document.getElementById("library-section");
  if (sec) sec.hidden = false;
  var items = M.items || [];
  var programs = M.programs || {};          // { "2026:make": {name, word, color} }
  var TYPES = ["수업 PPT", "교안", "활동지", "부록 교재", "영상", "예제 파일"];
  var state = { year: "all", type: "all" };

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function size(b) { if (!b) return ""; return b >= 1048576 ? (b / 1048576).toFixed(1) + "MB" : Math.max(1, Math.round(b / 1024)) + "KB"; }
  function years() { var y = {}; items.forEach(function (i) { y[i.year] = 1; }); return Object.keys(y).sort().reverse(); }

  function filters() {
    var yb = ['<button type="button" class="chip-btn" data-k="year" data-v="all">전체</button>'].concat(
      years().map(function (y) { return '<button type="button" class="chip-btn" data-k="year" data-v="' + y + '">' + y + "</button>"; })).join("");
    var present = TYPES.filter(function (t) { return items.some(function (i) { return i.type === t; }); });
    var tb = ['<button type="button" class="chip-btn" data-k="type" data-v="all">모든 자료</button>'].concat(
      present.map(function (t) { return '<button type="button" class="chip-btn" data-k="type" data-v="' + esc(t) + '">' + esc(t) + "</button>"; })).join("");
    return '<div class="lib-filters"><div class="lib-filter" role="group" aria-label="연도">' + yb + '</div><div class="lib-filter" role="group" aria-label="자료 종류">' + tb + '</div><p class="lib-count" id="lib-count" aria-live="polite"></p></div>';
  }

  function card(i) {
    var thumb = i.thumb ? '<img src="' + esc(i.thumb) + '" alt="" loading="lazy">' : '<span class="lib-ext">' + esc((i.ext || "").toUpperCase()) + "</span>";
    var meta = [(i.ext || "").toUpperCase(), i.pages ? i.pages + "쪽" : "", i.sessions || "", size(i.size_bytes)].filter(Boolean).join(" · ");
    var viewable = /^(pdf|mp4|html|png|jpg)$/i.test(i.ext || "");
    return '<li class="lib-card" data-year="' + i.year + '" data-type="' + esc(i.type) + '">' +
      '<a class="lib-thumb" href="' + esc(i.file) + '" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true">' + thumb + "</a>" +
      '<div class="lib-body"><span class="lib-type">' + esc(i.type) + "</span>" +
      "<b>" + esc(i.title) + "</b><span class=\"lib-meta\">" + esc(meta) + "</span>" +
      '<span class="lib-actions">' +
        (viewable ? '<a href="' + esc(i.file) + '" target="_blank" rel="noopener">보기</a>' : "") +
        '<a href="' + esc(i.file) + '" download>내려받기</a>' +
      "</span></div></li>";
  }

  function render() {
    var html = filters();
    years().forEach(function (y) {
      var inYear = items.filter(function (i) { return String(i.year) === y; });
      var groups = [];
      inYear.forEach(function (i) { if (groups.indexOf(i.program_id) < 0) groups.push(i.program_id); });
      html += '<section class="lib-year" data-year="' + y + '"><h2 class="lib-year-h">' + y + '<span>' + inYear.length + "개 자료</span></h2>";
      groups.forEach(function (pid) {
        var p = programs[y + ":" + pid] || { name: (inYear.find(function (i) { return i.program_id === pid; }) || {}).program || pid };
        var list = inYear.filter(function (i) { return i.program_id === pid; });
        html += '<div class="lib-prog" id="' + y + "-" + esc(pid) + '" style="--pc:' + esc(p.color || "#265297") + '">' +
          '<h3><span class="w' + (/[ㄱ-힝]/.test(p.word || "") ? " kr" : "") + '">' + esc(p.word || "") + "</span>" + esc(p.name || "") + "</h3>" +
          '<ul class="lib-grid">' + list.map(card).join("") + "</ul></div>";
      });
      html += "</section>";
    });
    root.innerHTML = html;
    root.querySelectorAll(".chip-btn").forEach(function (b) {
      b.addEventListener("click", function () { state[b.dataset.k] = b.dataset.v; apply(); });
    });
    apply();
  }

  function apply() {
    var shown = 0;
    root.querySelectorAll(".chip-btn").forEach(function (b) { b.setAttribute("aria-pressed", String(state[b.dataset.k] === b.dataset.v)); });
    root.querySelectorAll(".lib-card").forEach(function (c) {
      var ok = (state.year === "all" || c.dataset.year === state.year) && (state.type === "all" || c.dataset.type === state.type);
      c.hidden = !ok; if (ok) shown++;
    });
    root.querySelectorAll(".lib-prog").forEach(function (g) { g.hidden = !g.querySelector(".lib-card:not([hidden])"); });
    root.querySelectorAll(".lib-year").forEach(function (g) { g.hidden = !g.querySelector(".lib-prog:not([hidden])"); });
    var cnt = document.getElementById("lib-count");
    if (cnt) cnt.textContent = "자료 " + shown + "개";
  }

  render();
  if (location.hash) {
    var t = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (t) requestAnimationFrame(function () { t.scrollIntoView({ behavior: "instant", block: "start" }); });
  }
})();
