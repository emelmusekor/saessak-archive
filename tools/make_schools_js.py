"""schools.json(에이전트 결과) → docs/data/schools-YYYY.js. 로고가 assets/schools/<file> 에 있으면 연결."""
import json, sys, re
from pathlib import Path

src, site, year = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
logo_map = {}
lm = site / "assets" / "schools" / "logos.json"          # {"학교명": "파일명.png"}
if lm.exists():
    logo_map = json.loads(lm.read_text(encoding="utf-8"))

PROG = {"create": "Create!", "play": "Play!", "make": "Make!", "design": "Design!", "insight": "Insight!", "move": "Move!", "link": "Link!"}
def prog_id(name):
    for k, v in PROG.items():
        if name.lower().startswith(v.lower()):
            return k
    return None

data = json.loads(src.read_text(encoding="utf-8"))[year]
out = []
for s in data["schools"]:
    item = {"name": s["name"], "level": s.get("level") or "기관", "region": (s.get("region") or "").split(" ")[0],
            "programs": sorted({p for p in (prog_id(x) for x in (s.get("programs") or [])) if p})}
    if s["name"] in logo_map:
        item["logo"] = "assets/schools/" + logo_map[s["name"]]
    out.append(item)
out.sort(key=lambda x: x["name"])
payload = {"year": int(year), "participantsLabel": sys.argv[4] if len(sys.argv) > 4 else None,
           "note": "교표 출처: 각 학교 누리집" if any("logo" in x for x in out) else None, "schools": out}
js = "/* " + year + " 참여 학교. 출처: 운영기관이 정리한 결과보고용 수업 사진 폴더(학교별). */\nwindow.SCHOOL_YEAR = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n"
(site / "data" / f"schools-{year}.js").write_text(js, encoding="utf-8")
print("schools", len(out), "with logo", sum(1 for x in out if "logo" in x))
