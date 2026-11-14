"""Rebuild the Make! 클래스 마켓 web worksheets with the archive's activity design.
Keeps each original's markup and logic; swaps the stylesheet and header, and applies small usability fixes."""
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])          # 원본 폴더 (03.(초고)Make! 클래스 마켓)
OUT = Path(sys.argv[2])          # site/try

FILES = [
    ("1~2차시) 나만의 QR코드 픽셀아트 그리기.html", "qr-pixel-art.html", "1~2차시", "진입기",
     "나만의 QR코드 픽셀아트",
     "QR코드는 검은 칸과 흰 칸으로 정보를 담아요. 21×21 칸을 칠해 픽셀아트를 만들고, 내가 쓴 글자를 진짜 QR코드로 바꿔 봐요."),
    ("1~2차시) 바코드_비밀_암호_해독_작전_게임모드.html", "barcode-binary.html", "1~2차시", "진입기",
     "바코드 비밀 암호 해독 작전",
     "검은 칸은 1, 흰 칸은 0이에요. 오른쪽 자리부터 1, 2, 4, 8처럼 두 배씩 커지는 자릿값을 더해 이진수 바코드를 해독해요."),
    ("3~4차시) 학급 마켓 공정 거래 서약서 및 약관.html", "market-terms.html", "3~4차시", "도약기",
     "학급 마켓 공정 거래 서약서",
     "우리 반 마켓에서 지킬 거래 규칙과 환불 약관을 학급 회의로 정하고, 약관에 동의하면 서명해요."),
    ("5~6차시) 합리적 소비를 위한 지출 계획서.html", "spending-plan.html", "5~6차시", "성장기",
     "합리적 소비를 위한 지출 계획서",
     "예산과 사고 싶은 물건을 적고 우선순위를 정하면, 순서대로 샀을 때 남는 코인이 자동으로 계산돼요."),
    ("5~6차시) 중고 상품 정보 등록 계획서.html", "item-listing.html", "5~6차시", "성장기",
     "중고 상품 정보 등록 계획서",
     "팔 물건의 상태를 진단하고 알맞은 가격과 설명을 정리해 마켓 등록 카드를 완성해요."),
    ("7~8차시) 사이버 범죄 모의 신고서 작성.html", "cyber-report.html", "7~8차시", "성장기",
     "사이버 범죄 모의 신고서",
     "온라인 거래에서 피해를 당했다고 상상하고 신고서를 써 봐요. 언제 얼마를 잃었는지, 어떤 증거가 남았는지 빠짐없이 적어요."),
    ("7~8차시) 나의 디지털 생애곡선 그리기 학습지.html", "life-curve.html", "7~8차시", "성장기",
     "나의 디지털 생애곡선",
     "어릴 때부터 노년까지 나의 자산이 어떻게 달라질지 마우스나 손가락으로 곡선을 그리고, 자산관리 약속을 세워요."),
]

LEAF = ('<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 29V15" fill="none" stroke="#1F8048" '
        'stroke-width="2.4" stroke-linecap="round"/><path fill="#1F8048" d="M16 17C16 10 11 5.5 3.5 5.5 3.5 12.5 8.5 17 16 17Z"/>'
        '<path fill="#56B47B" d="M16 14.5C16 8.5 20.5 4 28.5 4c0 6.5-4.5 10.5-12.5 10.5Z"/></svg>')

HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} | 디지털새싹 수업 체험</title>
<link rel="icon" href="../assets/img/kaaie-mark.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700;800&family=Noto+Sans+KR:wght@400;500;700&family=Nanum+Pen+Script&display=swap">
<link rel="stylesheet" href="../assets/activity.css">
</head>
<body>
<header class="a-head">
  <div class="a-in">
    <a class="a-brand" href="../index.html" aria-label="디지털새싹 홈"><img src="../assets/img/kaaie-logo.png" alt="한국인공지능교육학회" width="284" height="53"><span class="sep" aria-hidden="true"></span><span class="name">디지털새싹</span></a>
    <nav class="a-nav" aria-label="이동"><a href="../2026.html#make">Make! 클래스 마켓</a><a href="../try.html">웹 활동지 목록</a></nav>
  </div>
</header>
<section class="a-hero">
  <div class="a-in">
    <p class="a-kicker"><span class="v">Make!</span><span>클래스 마켓 · 초등 5~6학년</span><span class="ses">{session} · {phase}</span></p>
    <h1>{title}</h1>
    <p class="sub">{sub}</p>
  </div>
</section>
<div class="wrap">
"""

HELPERS = r"""
function a11yLabels(){
  document.querySelectorAll('.fieldline').forEach(function(row){
    var lab=row.querySelector('label'), el=row.querySelector('input,textarea,select');
    if(lab && el && !el.closest('label')){ if(!el.id) el.id='f-'+Math.random().toString(36).slice(2,8); lab.htmlFor=el.id; }
  });
  document.querySelectorAll('table').forEach(function(tb){
    var heads=[].map.call(tb.querySelectorAll('thead th'),function(th){return th.textContent.trim();});
    [].forEach.call(tb.querySelectorAll('tbody tr'),function(tr,ri){
      [].forEach.call(tr.children,function(td,ci){
        td.querySelectorAll('input,textarea,select').forEach(function(el){
          if(!el.getAttribute('aria-label') && !el.closest('label')) el.setAttribute('aria-label',((heads[ci]||'')+' '+(ri+1)).trim());
        });
      });
    });
  });
  document.querySelectorAll('.inline-write').forEach(function(el,i){ if(!el.getAttribute('aria-label')) el.setAttribute('aria-label','빈칸 '+(i+1)); });
  document.querySelectorAll('input[placeholder],textarea[placeholder]').forEach(function(el){
    var named=el.getAttribute('aria-label')||el.closest('label')||(el.id&&document.querySelector('label[for="'+el.id+'"]'));
    if(!named) el.setAttribute('aria-label',el.placeholder);
  });
}
setTimeout(a11yLabels,0);
function escHtml(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function showExport(canvas,label){
  const out=document.getElementById('exportOut'); if(!out) return;
  out.innerHTML='';
  const img=new Image(); img.alt=label+' 완성 이미지'; img.src=canvas.toDataURL('image/png');
  const cap=document.createElement('p'); cap.className='small muted';
  cap.textContent='완성된 이미지입니다. 이미지를 길게 누르거나 마우스 오른쪽 버튼을 눌러 저장하세요.';
  out.append(img,cap); out.hidden=false;
  out.scrollIntoView({behavior:'smooth',block:'nearest'});
}
"""

QR_POINTER = r"""(function(){
  const paint=document.getElementById('paint'); let mode=null;
  function cellFrom(el){ return el && el.dataset && el.dataset.cell!==undefined && paint.contains(el) ? Number(el.dataset.cell) : null; }
  function setCell(i){ if(i===null||painted[i]===mode) return; painted[i]=mode; const b=paint.querySelector('[data-cell="'+i+'"]'); if(b) b.classList.toggle('on',mode); }
  paint.addEventListener('pointerdown',e=>{ const i=cellFrom(e.target); if(i===null) return; e.preventDefault(); mode = e.button===2 ? false : !painted[i]; setCell(i); });
  paint.addEventListener('pointermove',e=>{ if(mode===null) return; setCell(cellFrom(document.elementFromPoint(e.clientX,e.clientY))); });
  function end(){ if(mode===null) return; mode=null; renderPaint(); }
  window.addEventListener('pointerup',end); window.addEventListener('pointercancel',end);
  paint.addEventListener('click',e=>{ if(e.detail!==0) return; const i=cellFrom(e.target); if(i===null) return; painted[i]=!painted[i]; renderPaint(); const b=paint.querySelector('[data-cell="'+i+'"]'); if(b) b.focus(); });
})();"""


def must_replace(text, old, new, label):
    if old not in text:
        raise SystemExit(f"[{label}] 바꿀 문자열을 찾지 못함: {old[:60]}")
    return text.replace(old, new)


def number_h2(body):
    n = 0
    def rep(m):
        nonlocal n
        n += 1
        return f'<h2><span class="step">{n}</span>'
    return re.sub(r'<h2>(?!<span)', rep, body)


for src_name, out_name, session, phase, title, sub in FILES:
    text = (SRC / src_name).read_text(encoding="utf-8")
    hero = re.search(r'<header class="hero">.*?</header>', text, re.S)
    script_at = text.find("<script>", hero.end())
    body = text[hero.end():script_at].rstrip()
    body = re.sub(r'\s*</div>\s*$', '', body)            # .wrap 닫는 태그 제거
    script = text[script_at + len("<script>"):text.rfind("</script>")]

    # 공통: 표는 좁은 화면에서 가로로 스크롤
    body = body.replace('<table class="table">', '<div class="table-scroll"><table class="table">').replace('</table>', '</table></div>')

    if out_name == "qr-pixel-art.html":
        body = must_replace(body, '<h2>QR 픽셀아트 입력판</h2>',
                            '<h2><span class="step">1</span>QR 픽셀아트 입력판</h2>\n    <p class="hint">칸을 누르거나 끌어서 칠해요. 칠한 칸에서 시작하면 지우개가 돼요. 아래 버튼으로 QR의 기본 패턴을 먼저 채워 볼 수도 있어요.</p>', out_name)
        body = must_replace(body, '<h2>결과 입력 → QR코드 생성</h2>', '<h2><span class="step">2</span>글자를 QR코드로 바꾸기</h2>', out_name)
        body = must_replace(body, '<div class="row" style="margin-top:14px">\n      <button class="secondary" id="fillFinders"',
                            '<div class="qr-tools">\n      <button class="secondary" id="fillFinders"', out_name)
        script = must_replace(script,
            "document.getElementById('paint').addEventListener('mousedown',e=>{const c=e.target.dataset.cell;if(c===undefined)return;e.preventDefault();painted[Number(c)]=e.button===2?false:true;renderPaint();});",
            QR_POINTER, out_name)
    elif out_name == "barcode-binary.html":
        script = must_replace(script,
            "t.answer=(e.target.value||'').replace(/[^0-9]/g,'').slice(0,2); render(); });",
            "t.answer=(e.target.value||'').replace(/[^0-9]/g,'').slice(0,2); render(); const el=byId('tasks').querySelector('[data-answer=\"'+id+'\"]'); if(el){ el.focus(); const n=el.value.length; el.setSelectionRange(n,n); } });",
            out_name)
        body = body.replace("자리값", "자릿값")
        script = script.replace("자리값", "자릿값")
        body = must_replace(body, '<h2>이진수 바코드 예시표</h2>', '<h2><span class="step">1</span>이진수 바코드 예시표</h2>', out_name)
        body = must_replace(body, '<h2 style="margin:0">게임 모드: 이진수 바코드 해독</h2>', '<h2 style="margin:0"><span class="step">2</span>게임 모드: 이진수 바코드 해독</h2>', out_name)
        body = must_replace(body, '<h2 style="margin:0">미션 8문제</h2>', '<h2 style="margin:0"><span class="step">3</span>미션 8문제</h2>', out_name)
    elif out_name == "market-terms.html":
        body = number_h2(body)
        body = body.replace("중고 거래(계약)을", "중고 거래(계약)를").replace("고장나 있었다", "고장 나 있었다")
        script = must_replace(script, "window.addEventListener('resize',fitSign); fitSign();",
            "let lastW=0; function refit(){ const w=canvas.getBoundingClientRect().width; if(Math.abs(w-lastW)<1) return; const tmp=document.createElement('canvas'); tmp.width=canvas.width; tmp.height=canvas.height; tmp.getContext('2d').drawImage(canvas,0,0); fitSign(); lastW=w; ctx.save(); ctx.setTransform(1,0,0,1,0,0); ctx.drawImage(tmp,0,0); ctx.restore(); } window.addEventListener('resize',refit); fitSign(); lastW=canvas.getBoundingClientRect().width;",
            out_name)
    elif out_name == "item-listing.html":
        body = re.sub(r'<h2>STEP (\d)\. ', r'<h2><span class="step">\1</span>', body)
        body = must_replace(body, '<button id="export">이미지로 내보내기(PNG)</button></div></section>',
                            '<button id="export">등록 카드 이미지 만들기</button></div><div id="exportOut" class="export-out" hidden></div></section>', out_name)
        script = must_replace(script, "downloadCanvas(c,'중고_상품_정보_등록_계획서.png');", "showExport(c,'중고 상품 정보 등록 계획서');", out_name)
    elif out_name == "cyber-report.html":
        body = number_h2(body)
        body = must_replace(body, '<button id="export">이미지로 내보내기(PNG)</button></div></section>',
                            '<button id="export">신고서 이미지 만들기</button></div><div id="exportOut" class="export-out" hidden></div></section>', out_name)
        script = must_replace(script, "downloadCanvas(c,'사이버_범죄_모의_신고서.png');", "showExport(c,'사이버 범죄 모의 신고서');", out_name)
    elif out_name == "spending-plan.html":
        body = number_h2(body)
        script = must_replace(script, '${label}</option>', '${escHtml(label)}</option>', out_name)
        script = must_replace(script, '<td>${names[sel]}</td>', '<td>${escHtml(names[sel])}</td>', out_name)
    else:
        body = number_h2(body)

    if 'onclick="window.print()"' in body:
        raise SystemExit(f"[{out_name}] 인쇄 버튼이 본문에 남아 있음")

    html = HEAD.format(title=title, sub=sub, session=session, phase=phase, leaf=LEAF)
    html += body.strip() + "\n</div>\n<script>" + HELPERS + script.rstrip() + "\n</script>\n</body>\n</html>\n"
    (OUT / out_name).write_text(html, encoding="utf-8")
    print("built", out_name, len(html))
