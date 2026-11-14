"""materials/manifest.json(자료 정리 결과) → docs/materials/ 복사 + docs/data/materials.js 생성.
usage: python -I make_materials_js.py <materials_dir> <site_dir>
"""
import json
import re
import shutil
import sys
from pathlib import Path

mat, site = Path(sys.argv[1]), Path(sys.argv[2])
items = json.loads((mat / "manifest.json").read_text(encoding="utf-8"))

# 프로그램 표시 정보: 2026·2025는 프로그램 데이터에서, 나머지는 여기서
programs = {}
for year in (2026, 2025):
    js = (site / "data" / f"programs-{year}.js").read_text(encoding="utf-8")
    body = js[js.index("{"): js.rindex("}") + 1]
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = None
    if data:
        for p in data["programs"]:
            programs[f"{year}:{p['id']}"] = {"word": p["label"], "name": p["title"], "color": p["color"]}
    else:  # 2025 파일은 JS 객체 리터럴이라 정규식으로 읽는다
        for m in re.finditer(r'id: "([^"]+)", label: "([^"]+)", word: "[^"]+", title: "([^"]+)"[\s\S]*?color: "([^"]+)"', js):
            programs[f"{year}:{m.group(1)}"] = {"word": m.group(2), "name": m.group(3), "color": m.group(4)}
programs.update({
    "2024:moveit": {"word": "MOVE IT!", "name": "움직인 대로 생각하는 모션 코딩", "color": "#2F6FD0"},
    "2024:makeit": {"word": "MAKE IT!", "name": "모두를 위한 반응형 책 만들기", "color": "#C2582B"},
    "2024:gotit": {"word": "GOT IT!", "name": "데이터로 지키는 지구", "color": "#1F8A63"},
    "2024:connectit": {"word": "Connect IT!", "name": "나만의 미래 모빌리티: 꼬꼬무 체인리액션", "color": "#5A4FC8"},
})
for it in items:  # 2023 등 목록에 없는 프로그램은 manifest의 이름을 쓴다
    key = f"{it['year']}:{it['program_id']}"
    programs.setdefault(key, {"word": "", "name": it.get("program") or it["program_id"], "color": "#265297"})

dst = site / "materials"
if dst.exists():
    shutil.rmtree(dst)
out_items, total = [], 0
for it in items:
    rec = dict(it)
    for key in ("file", "thumb"):
        rel = it.get(key)
        if not rel:
            continue
        src = mat / rel
        if not src.exists():
            rec[key] = None
            continue
        target = dst / rel.replace("out/", "files/", 1)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, target)
        total += target.stat().st_size
        rec[key] = "materials/" + target.relative_to(dst).as_posix()
    if rec.get("file"):
        out_items.append(rec)

order = {"수업 PPT": 0, "교안": 1, "활동지": 2, "부록 교재": 3, "영상": 4, "예제 파일": 5}
out_items.sort(key=lambda r: (-int(r["year"]), r["program_id"], order.get(r["type"], 9), r["title"]))
payload = {"programs": programs, "items": out_items}
(site / "data" / "materials.js").write_text(
    "/* 자료실 목록 (tools/make_materials_js.py 로 생성) */\nwindow.MATERIALS = " + json.dumps(payload, ensure_ascii=False, indent=1) + ";\n",
    encoding="utf-8")
print("items", len(out_items), "copied MB", round(total / 1048576, 1))
