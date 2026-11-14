"""fetch_logos.py 결과(report.csv) 중 믿을 수 있는 교표만 골라 docs/assets/schools/ 에 넣고 logos.json 을 쓴다.

채택: status=ok, 또는 status=review 이면서 kind=emblem 이고 사유가 '저해상도'뿐인 것.
제외: 동명 학교로 모호한 것(ambiguous), 약한 일치(weak), banner/favicon, 파일 없음.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

run, site = Path(sys.argv[1]), Path(sys.argv[2])
skip_names = set(sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else set()
rows = list(csv.DictReader(open(run / "report.csv", encoding="utf-8-sig")))
dst = site / "assets" / "schools"
dst.mkdir(parents=True, exist_ok=True)
for old in dst.glob("*.png"):
    old.unlink()

mapping, stats = {}, Counter()
for r in rows:
    name, st, kind = r["name"], r.get("status", ""), r.get("kind", "")
    notes = (r.get("notes") or "").lower()
    if name in skip_names:
        stats["manual skip"] += 1
        continue
    if kind != "emblem" or not r.get("file"):
        stats[f"skip {st}/{kind or 'none'}"] += 1
        continue
    if st == "review" and ("ambiguous" in notes or "weak" in notes or "low-res" not in notes):
        stats["skip review(ambiguous/weak)"] += 1
        continue
    if st not in ("ok", "review"):
        stats[f"skip {st}"] += 1
        continue
    src = run / r["file"]
    if not src.exists():
        stats["missing file"] += 1
        continue
    code = r.get("neis_code") or str(abs(hash(name)))
    im = Image.open(src).convert("RGBA")
    im.thumbnail((128, 128), Image.LANCZOS)
    out = f"{code}.png"
    im.save(dst / out, optimize=True)
    mapping[name] = out
    stats["used " + st] += 1

(dst / "logos.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=1), encoding="utf-8")
total = sum(p.stat().st_size for p in dst.glob("*.png"))
print(dict(stats))
print("logos:", len(mapping), "size:", round(total / 1024), "KB")
