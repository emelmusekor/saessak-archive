/* 연도별 프로그램 페이지 렌더러. data/programs-YYYY.js 가 window.PROGRAM_YEAR 를,
   (있으면) data/schools-YYYY.js 가 window.SCHOOL_YEAR 를 채운다. */
(function () {
  var D = window.PROGRAM_YEAR;
  if (!D) return;
  var PH = ["진입기", "도약기", "성장기", "완성기"];
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function fmt(n) { return Number(n).toLocaleString("ko-KR"); }
  function hasHangul(s) { return /[ㄱ-힝]/.test(s); }
  function ranges(ph) {
    var out = [], start = 1;
    ph.forEach(function (n) { out.push(n === 1 ? start + "차시" : start + "~" + (start + n - 1) + "차시"); start += n; });
    return out;
  }

  /* 첫머리: 프로그램 이름을 그대로 크게 */
  var lineup = document.getElementById("lineup");
  if (lineup) {
    lineup.innerHTML =
      (D.seriesLabel ? '<p class="lineup-label">' + esc(D.seriesLabel) + "</p>" : "") +
      '<p class="lineup-words">' + D.programs.map(function (p, i) {
        var half = p.half && (i === 0 || D.programs[i - 1].half !== p.half) ? '<span class="lineup-half">' + esc(p.half) + "</span>" : "";
        return half + '<a href="#' + p.id + '" style="--pc:' + p.color + '"' + (hasHangul(p.word) ? ' class="kr"' : "") + ">" + esc(p.word) + "</a>";
      }).join("") + "</p>" +
      '<dl class="lineup-facts">' + D.facts.map(function (f) { return "<div><dt>" + esc(f[0]) + "</dt><dd>" + esc(f[1]) + "</dd></div>"; }).join("") + "</dl>";
  }

  var sub = document.getElementById("subnav");
  if (sub) sub.innerHTML = D.programs.map(function (p) { return '<li><a href="#' + p.id + '">' + esc(p.word) + "</a></li>"; }).join("");

  /* 프로그램별 수업 학교 수 (참여 학교 자료가 있을 때) */
  var S = window.SCHOOL_YEAR, perProg = {};
  if (S && S.schools && !S.partial) S.schools.forEach(function (s) { (s.programs || []).forEach(function (id) { perProg[id] = (perProg[id] || 0) + 1; }); });

  /* 수업 사진 (data/photos-YYYY.js 가 있을 때) */
  var PHOTOS = window.PROGRAM_PHOTOS || {};
  function photoStrip(p) {
    var list = PHOTOS[p.id];
    if (!list || !list.length) return "";
    var shown = list.slice(0, 4);
    return '<div class="container prog-photos"><ul style="--n:' + shown.length + '">' + shown.map(function (ph) {
      return '<li><a href="' + esc(ph.file) + '" target="_blank" rel="noopener"><img src="' + esc(ph.small || ph.file) + '" alt="' + esc(ph.alt || "") + '" loading="lazy"></a></li>';
    }).join("") + "</ul></div>";
  }

  document.getElementById("programs").innerHTML = D.programs.map(function (p) {
    var r = ranges(p.phases);
    var steps = p.steps.map(function (s, i) {
      return "<li><b>" + PH[i] + '</b><span class="n">' + r[i] + "</span><span>" + esc(s) + "</span></li>";
    }).join("");
    var actions = "";
    var mats = ((window.MATERIALS && window.MATERIALS.items) || []).filter(function (m) { return String(m.year) === String(D.year) && m.program_id === p.id; });
    ["수업 PPT", "교안", "부록 교재"].forEach(function (type) {
      var m = mats.filter(function (x) { return x.type === type; })[0];
      if (m) actions += '<a class="btn btn-navy" href="' + esc(m.file) + '" target="_blank" rel="noopener">' + type + ' 보기 <span class="arr" aria-hidden="true">↗</span></a>';
    });
    if (p.activities && p.activities.length) {
      var href = p.activities.length === 1 ? p.activities[0][0] : "try.html";
      var label = p.activities.length === 1 ? p.activities[0][2] + " 열기" : "웹 활동지 열기";
      actions += '<a class="btn btn-outline" href="' + esc(href) + '">' + esc(label) + ' <span class="arr" aria-hidden="true">→</span></a>';
    }
    (p.links || []).slice(0, 2).forEach(function (l) {
      actions += '<a class="btn btn-outline" href="' + esc(l[1]) + '" target="_blank" rel="noopener">' + esc(l[0]) + ' <span class="arr" aria-hidden="true">↗</span></a>';
    });
    var sessions = "";
    if (p.flow && p.flow.length) {
      var rows = [];
      p.flow.forEach(function (items) { items.forEach(function (it) { rows.push('<li><span class="n">' + esc(it[0]) + "차시</span><span>" + esc(it[1]) + "</span></li>"); }); });
      sessions = '<details class="sessions"><summary>차시별 수업 보기</summary><ol>' + rows.join("") + "</ol></details>";
    }
    var big = hasHangul(p.label) ? ' kr' : "";
    return '<section class="prog" id="' + p.id + '" style="--pc:' + p.color + '" aria-labelledby="' + p.id + '-t">' +
      '<div class="container prog-grid">' +
        '<div class="poster" aria-hidden="true">' +
          '<div class="poster-top"><span class="poster-tag">' + esc((p.half ? p.half + " · " : "") + p.track) + '</span><span class="poster-meta">' + esc(p.levelLabel) + " · " + p.sessions + "차시</span></div>" +
          '<div class="poster-art"><svg viewBox="0 0 48 48">' + p.icon + "</svg></div>" +
          '<div><strong class="poster-verb' + big + '">' + esc(p.label) + '</strong>' + (p.title !== p.label ? '<span class="poster-name">' + esc(p.title) + "</span>" : "") + "</div>" +
        "</div>" +
        '<div class="prog-info">' +
          '<p class="prog-kicker"><span class="tag-sprout">' + esc(p.literacy) + '</span>' +
            (p.participants ? '<span class="prog-count"><b>' + fmt(p.participants) + "</b>명" + (p.participantsPlus ? " 이상" : "") + " 참여</span>" : "") +
            (perProg[p.id] ? '<span class="prog-count"><b>' + perProg[p.id] + "</b>곳에서 수업</span>" : "") + "</p>" +
          '<h2 id="' + p.id + '-t">' + esc(p.tagline) + "</h2>" +
          '<p class="prog-name"><span class="v' + (hasHangul(p.label) ? " kr" : "") + '">' + esc(p.label) + "</span>" + (p.title !== p.label ? esc(p.title) : "") + "</p>" +
          '<p class="prog-desc">' + esc(p.intro) + "</p>" +
          '<ol class="steps">' + steps + "</ol>" +
          (p.made ? '<p class="made"><b>학생 결과물</b><span>' + esc(p.made) + "</span></p>" : "") +
          (actions ? '<div class="prog-actions">' + actions + "</div>" : "") +
          (mats.length ? '<a class="mat-all" href="library.html#' + D.year + "-" + p.id + '">이 프로그램 자료 ' + mats.length + '개 모두 보기 <span aria-hidden="true">→</span></a>' : "") +
          sessions +
        "</div>" +
      "</div>" + photoStrip(p) + "</section>";
  }).join("");

  /* 참여 학교 */
  var box = document.getElementById("schools");
  if (S && box && S.schools && S.schools.length) {
    var order = ["초", "중", "고", "특수", "기관"];
    var names = { "초": "초등학교", "중": "중학교", "고": "고등학교", "특수": "특수학교", "기관": "기관·센터" };
    var groups = {};
    S.schools.forEach(function (s) { (groups[s.level] = groups[s.level] || []).push(s); });
    var total = S.totalLabel ? '<b>' + esc(S.totalLabel.replace(/곳$/, "")) + "</b>곳" : "<b>" + fmt(S.schools.length) + "</b>곳";
    var html = '<div class="school-head"><p class="school-total">' + total +
      (S.participantsLabel ? "<span>학생 <b>" + esc(S.participantsLabel) + "</b></span>" : "") + "</p>" +
      '<p class="school-note">' + (S.partial ? "수업 기록이 남은 " + fmt(S.schools.length) + "곳" + (S.note ? " · " : "") : "") + esc(S.note || "") + "</p></div>";
    order.forEach(function (lv) {
      var list = groups[lv];
      if (!list || !list.length) return;
      var bare = function (n) { return n.replace(/^(서울|인천|경기|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)/, ""); };
      list.sort(function (a, b) { return bare(a.name).localeCompare(bare(b.name), "ko"); });
      html += '<div class="school-group"><h3>' + names[lv] + ' <span>' + list.length + "</span></h3><ul class=\"school-grid\">" +
        list.map(function (s) {
          var mark = s.logo ? '<img src="' + esc(s.logo) + '" alt="" loading="lazy">' : '<span class="school-initial" aria-hidden="true">' + esc(bare(s.name).charAt(0)) + "</span>";
          return '<li><span class="school-logo">' + mark + '</span><span class="school-name">' + esc(s.name) + "</span></li>";
        }).join("") + "</ul></div>";
    });
    box.innerHTML = html;
    box.closest("section").hidden = false;
  }

  /* 보고 있는 프로그램 표시 */
  var links = Array.prototype.slice.call(document.querySelectorAll("#subnav a"));
  if (links.length && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) {
          var on = a.getAttribute("href") === "#" + en.target.id;
          a.classList.toggle("is-active", on);
          if (on) {
            var ul = a.closest("ul");
            if (ul && ul.scrollWidth > ul.clientWidth) ul.scrollTo({ left: a.offsetLeft - (ul.clientWidth - a.offsetWidth) / 2, behavior: "smooth" });
          }
        });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    document.querySelectorAll(".prog").forEach(function (s) { io.observe(s); });
  }

  if (location.hash) {
    var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target) requestAnimationFrame(function () { target.scrollIntoView({ behavior: "instant", block: "start" }); });
  }
})();
