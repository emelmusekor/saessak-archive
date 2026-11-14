"""Write the year pages (2026.html, 2025.html) from one template so they stay identical in structure."""
import sys
from pathlib import Path

SITE = Path(sys.argv[1])
YEARS = [
    # year, page title, english kicker, sub-visual image, description, og image
    (2026, "2026 프로그램", "PROGRAM", "assets/img/slide-view.jpg",
     "Create! PLAY! Make! Design! Insight! Move! Link! 한국인공지능교육학회 교사들이 만든 2026 디지털새싹 프로그램."),
    (2025, "2025 프로그램", "ARCHIVE", "assets/img/storyboard.jpg",
     "한국인공지능교육학회의 2025 디지털새싹 ‘나도 ○○!’ 6개 프로그램. 학생 6,837명이 참여했습니다."),
]
ALL_YEARS = [2026, 2025]

HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} | 한국인공지능교육학회 디지털새싹</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title} | 한국인공지능교육학회 디지털새싹">
<meta property="og:image" content="https://emelmusekor.github.io/saessak-archive/{img}">
<link rel="icon" href="assets/img/kaaie-mark.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&family=Noto+Sans+KR:wght@300;400;500;700;800&display=swap">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
"""

def header(active):
    def cur(key):
        return ' aria-current="page"' if key == active else ""
    return f"""
<div class="topbar">
  <div class="container">
    <span class="en">Korean Association of Artificial Intelligence Education</span>
    <a href="http://aied.or.kr/" target="_blank" rel="noopener">한국인공지능교육학회 홈페이지 ↗</a>
  </div>
</div>

<header class="header">
  <div class="container">
    <a class="brand" href="index.html" aria-label="디지털새싹 홈">
      <img src="assets/img/kaaie-logo.png" alt="한국인공지능교육학회" width="284" height="53">
      <span class="brand-sep" aria-hidden="true"></span>
      <span class="brand-name">디지털새싹</span>
    </a>
    <nav class="gnb" id="gnb" aria-label="주요 메뉴">
      <a href="2026.html"{cur('2026')}>프로그램</a>
      <a href="2025.html"{cur('past')}>지난 프로그램</a>
      <a href="library.html"{cur('lib')}>자료실</a>
      <a class="ext" href="http://aied.or.kr/" target="_blank" rel="noopener">학회 소개<span>↗</span></a>
    </nav>
    <button class="menu-btn" type="button" aria-label="메뉴 열기" aria-controls="gnb" aria-expanded="false"><i></i><i></i><i></i></button>
  </div>
</header>
"""

FOOTER = """
<footer class="footer">
  <div class="container">
    <nav class="footer-links" aria-label="바닥글 메뉴">
      <a href="2026.html">2026 프로그램</a>
      <a href="2025.html">지난 프로그램</a>
      <a href="library.html">자료실</a>
      <a href="http://aied.or.kr/" target="_blank" rel="noopener">한국인공지능교육학회</a>
    </nav>
    <div class="footer-info">
      <p>한국인공지능교육학회 디지털새싹 프로그램</p>
      <p>디지털새싹 주관기관 ㈜조은에듀테크 · 협력기관 (사)한국인공지능교육학회</p>
      <p class="en">Korean Association of Artificial Intelligence Education · Digital Saessak</p>
    </div>
  </div>
</footer>
"""

for year, title, en, img, desc in YEARS:
    tabs = "".join(
        f'<a href="{y}.html"{" aria-current=\"page\"" if y == year else ""}>{y}</a>' for y in ALL_YEARS
    )
    body = f"""
<main>
  <section class="sub-visual" style="background-image:url('{img}')">
    <div class="container">
      <p class="en">{en}</p>
      <h1>{title}</h1>
      <nav class="visual-years" aria-label="연도">{tabs}</nav>
    </div>
  </section>

  <nav class="subnav" aria-label="프로그램 바로가기">
    <ul id="subnav"></ul>
  </nav>

  <div class="container lineup" id="lineup"></div>

  <div id="programs"></div>

  <section class="section soft" id="schools-section" hidden>
    <div class="container">
      <div class="sec-head">
        <h2><span class="en">Schools</span><span class="kr">{year} 참여 학교</span></h2>
      </div>
      <div id="schools"></div>
    </div>
  </section>
</main>
"""
    scripts = f"""
<script src="data/programs-{year}.js"></script>
<script src="data/schools-{year}.js" onerror="this.remove()"></script>
<script src="data/materials.js" onerror="this.remove()"></script>
<script src="assets/programs.js" defer></script>
<script src="assets/site.js" defer></script>
</body>
</html>
"""
    html = HEAD.format(title=title, desc=desc, img=img) + header("2026" if year == 2026 else "past") + body + FOOTER + scripts
    (SITE / f"{year}.html").write_text(html, encoding="utf-8")
    print("wrote", f"{year}.html", len(html))
