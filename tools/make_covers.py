"""프로그램 표지 이미지 생성: 프로그램 카드용(assets/covers/<year>-<id>.jpg)과 수업 PPT 자료 썸네일용(assets/covers/items/...).
PDF 첫 장은 글꼴이 바뀌어 보여서, 같은 틀로 표지를 새로 그린다.
usage: python make_covers.py <docs_dir> <work_dir>   (Chrome 헤드리스로 렌더링)
"""
import json, re, subprocess, sys
from pathlib import Path

DOCS, WORK = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def load(js):
    t = (DOCS / js).read_text(encoding="utf-8")
    return json.loads(t[t.index("{"): t.rindex("}") + 1])

jobs = []
mats = load("data/materials.js")["items"]
for year in (2026, 2025, 2024, 2023):
    D = load(f"data/programs-{year}.js")
    for p in D["programs"]:
        half = p.get("half")
        base = {"year": year, "half": half or "", "color": p["color"],
                "label": "" if half else p["label"], "title": p["title"],
                "meta": f"{p['levelLabel']} · {p['sessions']}차시"}
        jobs.append(dict(base, tag="", out=f"assets/covers/{year}-{p['id']}.jpg"))
        for it in mats:
            if str(it["year"]) == str(year) and it["program_id"] == p["id"] and it["type"] == "수업 PPT":
                m = re.search(r"\(([^)]*)\)\s*$", it["title"])
                tag = "수업 PPT" + (" · " + m.group(1) if m else (" · " + it["sessions"] if it.get("sessions") else ""))
                name = Path(it["thumb"]).name if it.get("thumb") else Path(it["file"]).stem + ".jpg"
                jobs.append(dict(base, tag=tag, out=f"assets/covers/items/{name}", item=it["file"]))

TPL = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Noto+Sans+KR:wght@400;500;700;800&display=block" rel="stylesheet">
<style>
html,body{margin:0;width:1280px;height:720px;overflow:hidden;background:#fff;font-family:'Noto Sans KR',sans-serif;color:#15284A}
.c{position:relative;box-sizing:border-box;width:1280px;height:720px;padding:64px 96px 0;background:color-mix(in srgb,VAR 7%,#fff)}
.top{display:flex;justify-content:space-between;align-items:center}
.top img{height:48px}
.top span{font-size:26px;color:#68707F;font-weight:500;letter-spacing:-.02em}
.mid{position:absolute;left:96px;right:96px;top:50%;transform:translateY(-58%)}
.lab{margin:0 0 16px;font:800 76px/1.05 Montserrat,'Noto Sans KR';letter-spacing:-.03em;color:VAR}
.lab.kr{font-family:'Noto Sans KR';font-size:52px;letter-spacing:-.05em}
h1{margin:0;font-size:66px;line-height:1.25;font-weight:800;letter-spacing:-.05em;word-break:keep-all;max-width:1000px}
h1.sm{font-size:54px}
.bot{position:absolute;left:96px;right:96px;bottom:70px;display:flex;justify-content:space-between;align-items:center}
.meta{font-size:30px;color:#4A5262;font-weight:500}
.tag{font-size:24px;font-weight:700;color:VAR;border:2px solid VAR;padding:6px 18px}
.bar{position:absolute;left:0;right:0;bottom:0;height:18px;background:VAR}
.side{position:absolute;right:0;top:0;width:18px;height:100%;background:VAR;opacity:.18}
</style></head><body><div class="c">
<div class="top"><img src="LOGO"><span>YEARLINE</span></div>
<div class="mid">LABEL<h1 class="HCLS">TITLE</h1></div>
<div class="bot"><span class="meta">META</span>TAG</div>
<div class="bar"></div></div></body></html>"""

def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;")
logo = (DOCS / "assets/img/kaaie-logo.png").as_uri()
WORK.mkdir(parents=True, exist_ok=True)
prof = WORK / "chrome-prof"
for i, j in enumerate(jobs):
    kr = bool(re.search("[가-힣]", j["label"]))
    html = (TPL.replace("VAR", j["color"]).replace("LOGO", logo)
            .replace("YEARLINE", f"{j['year']} 디지털새싹" + (f" {j['half']}" if j["half"] else ""))
            .replace("LABEL", f'<p class="lab{" kr" if kr else ""}">{esc(j["label"])}</p>' if j["label"] else "")
            .replace("HCLS", "sm" if len(j["title"]) > 22 else "")
            .replace("TITLE", esc(j["title"])).replace("META", esc(j["meta"]))
            .replace("TAG", f'<span class="tag">{esc(j["tag"])}</span>' if j["tag"] else ""))
    src = WORK / f"c{i}.html"; src.write_text(html, encoding="utf-8")
    png = WORK / f"c{i}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    f"--user-data-dir={prof}", "--virtual-time-budget=4000", "--window-size=1280,720",
                    f"--screenshot={png}", src.as_uri()], capture_output=True)
    from PIL import Image
    out = DOCS / j["out"]; out.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(png).convert("RGB")
    im.resize((960, 540), Image.LANCZOS).save(out, quality=86, optimize=True)
    j["png"] = str(png)
(WORK / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=1), encoding="utf-8")
print("covers", len(jobs))
