"""앨범 데이터 생성: data/photos-YYYY.js + assets/photos/pool/pool.json → data/album.js
usage: python make_album.py <docs_dir>"""
import json, sys
from pathlib import Path

DOCS = Path(sys.argv[1])
def load(js, var):
    p = DOCS / js
    if not p.exists(): return None
    t = p.read_text(encoding="utf-8")
    try: return json.loads(t[t.index("{"): t.rindex("}") + 1])
    except ValueError: return None

groups, photos = [], []
for year in (2026, 2025, 2024, 2023):
    ph = load(f"data/photos-{year}.js", "PROGRAM_PHOTOS") or {}
    prog = {p["id"]: p for p in (load(f"data/programs-{year}.js", "PROGRAM_YEAR") or {"programs": []})["programs"]}
    n = 0
    for pid in prog:  # 프로그램 순서대로
        for x in ph.get(pid, []):
            p = prog[pid]
            name = p["title"] if p.get("half") else (p["label"] + " " + p["title"])
            photos.append({"file": x["file"], "small": x.get("small"), "alt": x.get("alt", ""), "group": str(year), "caption": f"{year} {name}"})
            n += 1
    if n: groups.append({"key": str(year), "label": str(year)})
pool = DOCS / "assets/photos/pool/pool.json"
if pool.exists():
    items = json.loads(pool.read_text(encoding="utf-8"))
    for x in items:
        kind = x.get("kind", "class")
        g = "teachers" if kind in ("teachers", "event") else "class"
        photos.append({"file": x["file"], "small": x.get("small"), "alt": x.get("alt", ""), "group": g, "caption": ""})
    if any(p["group"] == "teachers" for p in photos): groups.append({"key": "teachers", "label": "교사 연수·개발"})
    if any(p["group"] == "class" for p in photos): groups.append({"key": "class", "label": "수업 현장"})
# 연도가 섞이도록 번갈아 배치 (전체 보기에서 한 해만 몰려 보이지 않게)
buckets = {}
for p in photos: buckets.setdefault(p["group"], []).append(p)
mixed, i = [], 0
while any(buckets.values()):
    for k in list(buckets):
        if buckets[k]: mixed.append(buckets[k].pop(0))
(DOCS / "data/album.js").write_text("/* 앨범 사진 (tools/make_album.py 로 생성). 아이 얼굴이 보이지 않는 사진만 씀 */\nwindow.ALBUM = " +
    json.dumps({"groups": groups, "photos": mixed}, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
print("album", len(mixed), [g["key"] for g in groups])
