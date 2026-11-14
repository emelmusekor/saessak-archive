#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_logos.py - fetch official school emblems (교표) for Korean schools from their official names.

Pipeline (per school)
  1. NEIS Open API `schoolInfo` (open.neis.go.kr): official name, NEIS code, 교육청, homepage URL.
     Works without a key (sample mode: max 5 rows per call, which is enough for one-name lookups);
     pass --neis-key / env NEIS_API_KEY for bulk/ambiguous names (1000 rows per call).
  2. School homepage (follows JS/meta redirects) -> header logo (<h1> img / *logo* img).
     On the 시도교육청 standard platforms (*.icees.kr, *.icems.kr, *.sen.es.kr, *.goe*.kr ...) this
     is a "banner": emblem on the left + school name text. The banner is saved, and the emblem is
     cropped from its left side (always available, but only ~35-42 px tall).
  3. Menu links "학교상징 / 교표 / 학교CI" -> content images:
       - the header emblem located inside a (composite) "학교상징" / CI image by multi-scale masked
         normalised cross-correlation (shape) + hue-histogram similarity (colour), then cropped at
         that image's (higher) resolution, or
       - an image explicitly labelled 교표 (alt / file name / heading) that is a standalone mark.
  4. Normalise: RGBA -> trim (also peels thin card frames) -> max N px (never upscaled) -> PNG.

Input CSV : column `name` (required). Optional: `region` (인천 / 서울 / 경기 / E10 ...),
            `homepage` (override NEIS), `logo_url` (manual override: direct image URL).
            A name like "박문중학교(인천)" is also understood as name + region.
Output    : OUT/<NEIS code>_<official name>.png       best image (see report.kind)
            OUT/<NEIS code>_<official name>_banner.png header banner (when found)
            OUT/report.csv  name,status,source_url,kind,notes,+details
            OUT_cache/      raw HTTP cache next to OUT (untrusted data, not for publishing;
                            makes re-runs free and polite; --cache to move it, safe to delete)
Status    : ok      = emblem found, >= --min-ok px
            review  = low-res emblem, banner/favicon only, weak match, or ambiguous NEIS match
            fail    = nothing usable (see notes)
Kind      : emblem | banner | favicon | none
Method    : symbol_page / ci_page          whole image from the 학교상징 / 학교CI page
            symbol_page_crop / ci_page_crop emblem cut out of a composite image on that page
            *_label / *_label_blob          labelled 교표 image that did not match the header emblem
            header_crop                     emblem cut from the header banner (low-res fallback)
            header / favicon / manual
Match     : "ncc/colour" agreement of the chosen image with the header emblem (accepted when
            ncc >= --match-min, colour >= 0.5 and ncc + colour >= --accept; review below --confident)
Resumable : schools whose report row is ok/review and whose file exists are skipped
            (use --force to redo, --retry-review to redo only 'review' rows).

Requires Pillow + numpy. PyMuPDF (fitz) is optional and only used to rasterise SVG logos.
Downloaded data is only decoded as images / parsed as text, never executed.

Example
  python -I fetch_logos.py schools.csv --out out --sheet out/sample_sheet.png
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

try:  # optional, for SVG logos only
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

Image.MAX_IMAGE_PIXELS = 40_000_000

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
NEIS_URL = "https://open.neis.go.kr/hub/schoolInfo"

REGION_PREFIXES = [  # longest prefixes first where they overlap
    ("충청북", "M10"), ("충청남", "N10"), ("전라북", "P10"), ("전라남", "Q10"),
    ("경상북", "R10"), ("경상남", "S10"),
    ("서울", "B10"), ("부산", "C10"), ("대구", "D10"), ("인천", "E10"), ("광주", "F10"),
    ("대전", "G10"), ("울산", "H10"), ("세종", "I10"), ("경기", "J10"), ("강원", "K10"),
    ("충북", "M10"), ("충남", "N10"), ("전북", "P10"), ("전남", "Q10"), ("경북", "R10"),
    ("경남", "S10"), ("제주", "T10"),
]
CODE_SHORT = {"B10": "서울", "C10": "부산", "D10": "대구", "E10": "인천", "F10": "광주",
              "G10": "대전", "H10": "울산", "I10": "세종", "J10": "경기", "K10": "강원",
              "M10": "충북", "N10": "충남", "P10": "전북", "Q10": "전남", "R10": "경북",
              "S10": "경남", "T10": "제주"}

REPORT_FIELDS = ["name", "status", "source_url", "kind", "notes",
                 "method", "official_name", "edu_office", "neis_code", "homepage",
                 "file", "banner_file", "src_w", "src_h", "out_w", "out_h", "match"]


# --------------------------------------------------------------------------- HTTP

@dataclass
class Resp:
    url: str
    final: str
    status: int
    ctype: str = ""
    body: bytes = b""
    error: str = ""
    insecure: bool = False

    @property
    def ok(self) -> bool:
        return self.status == 200 and bool(self.body)


def iri_to_uri(url: str) -> str:
    """Percent-encode non-ASCII / spaces in path and query, keep existing escapes."""
    p = urllib.parse.urlsplit(url.strip())
    netloc = p.netloc
    if any(ord(c) > 127 for c in netloc):
        netloc = netloc.encode("idna").decode("ascii")
    path = urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=-._~")
    query = urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?-._~")
    return urllib.parse.urlunsplit((p.scheme, netloc, path, query, ""))


class Fetcher:
    """Sequential, polite HTTP client with an on-disk cache (only 200 responses are cached)."""

    def __init__(self, cache_dir: str, delay: float = 1.5, min_gap: float = 1.0,
                 timeout: float = 25, max_bytes: int = 20_000_000, verbose: bool = False):
        self.cache_dir = cache_dir
        self.delay, self.min_gap, self.timeout, self.max_bytes = delay, min_gap, timeout, max_bytes
        self.verbose = verbose
        self.ctx = ssl.create_default_context()
        self.ctx_insecure = ssl._create_unverified_context()  # fallback for broken school cert chains
        self.host_last: dict[str, float] = {}
        self.any_last = 0.0
        self.requests = 0
        self.cache_hits = 0
        os.makedirs(cache_dir, exist_ok=True)

    def _paths(self, url):
        k = hashlib.sha1(url.encode("utf-8")).hexdigest()
        d = os.path.join(self.cache_dir, k[:2])
        return d, os.path.join(d, k + ".bin"), os.path.join(d, k + ".json")

    def _throttle(self, host: str):
        now = time.monotonic()
        wait = max(self.host_last.get(host, -1e9) + self.delay - now, self.any_last + self.min_gap - now, 0)
        if wait > 0:
            time.sleep(wait)
        t = time.monotonic()
        self.host_last[host] = t
        self.any_last = t

    def get(self, url: str, referer: str | None = None, cache: bool = True) -> Resp:
        url = iri_to_uri(url)
        d, bp, mp = self._paths(url)
        if cache and os.path.exists(mp) and os.path.exists(bp):
            try:
                meta = json.load(open(mp, encoding="utf-8"))
                self.cache_hits += 1
                return Resp(body=open(bp, "rb").read(), **meta)
            except Exception:
                pass
        r = self._do(url, referer)
        if cache and r.ok:
            os.makedirs(d, exist_ok=True)
            with open(bp, "wb") as fh:
                fh.write(r.body)
            json.dump({"url": r.url, "final": r.final, "status": r.status, "ctype": r.ctype,
                       "error": r.error, "insecure": r.insecure}, open(mp, "w", encoding="utf-8"),
                      ensure_ascii=False)
        return r

    def _do(self, url: str, referer: str | None) -> Resp:
        headers = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
                   "Accept": "text/html,application/xhtml+xml,image/*,*/*;q=0.8"}
        if referer:
            headers["Referer"] = referer
        insecure = False
        for _ in range(2):
            self._throttle(urllib.parse.urlsplit(url).hostname or "")
            self.requests += 1
            if self.verbose:
                print(f"      GET {url}", flush=True)
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout,
                                            context=self.ctx_insecure if insecure else self.ctx) as r:
                    body = r.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        return Resp(url, r.geturl(), -1, "", b"", "response too large", insecure)
                    return Resp(url, r.geturl(), r.status, r.headers.get("Content-Type", ""), body, "",
                                insecure)
            except urllib.error.HTTPError as e:
                return Resp(url, url, e.code, "", b"", f"HTTP {e.code}", insecure)
            except Exception as e:  # URLError, ssl errors, timeouts, resets
                reason = getattr(e, "reason", e)
                if not insecure and ("CERTIFICATE_VERIFY_FAILED" in str(e) or isinstance(reason, ssl.SSLError)):
                    insecure = True
                    continue
                return Resp(url, url, -1, "", b"", f"{type(reason).__name__}: {reason}"[:200], insecure)
        return Resp(url, url, -1, "", b"", "unreachable", insecure)


# --------------------------------------------------------------------------- HTML

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}


class PageParser(HTMLParser):
    """Collects images (with ancestor context + preceding text), links (with text), icons, metas."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str, str]] = []
        self.imgs: list[dict] = []
        self.links: list[tuple[str, str]] = []
        self.icons: list[str] = []
        self.metas: list[dict] = []
        self._a = None
        self._skip = 0
        self._text_since_img: list[str] = []

    def _ctx(self):
        return " ".join(f"{t}#{i}.{c}" for t, i, c in self.stack).lower()

    def handle_starttag(self, tag, attrs, selfclosing=False):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in ("script", "style", "noscript", "template"):
            if not selfclosing:
                self._skip += 1
            return
        if tag == "img":
            src = a.get("src") or a.get("data-src") or a.get("data-original") or ""
            self.imgs.append({"src": src.strip(), "alt": a.get("alt", "").strip(),
                              "title": a.get("title", "").strip(), "ctx": self._ctx(),
                              "cls": (a.get("class", "") + " " + a.get("id", "")).lower(),
                              "before": " ".join(self._text_since_img)[-120:], "idx": len(self.imgs)})
            self._text_since_img = []
            if self._a is not None and a.get("alt"):
                self._a[1].append(a.get("alt"))
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link" and "icon" in a.get("rel", "").lower() and a.get("href"):
            self.icons.append(a["href"].strip())
        elif tag == "a":
            self._a = [a.get("href", "").strip(), []]
        if tag not in VOID and not selfclosing:
            self.stack.append((tag, a.get("id", ""), a.get("class", "")))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, selfclosing=True)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template"):
            self._skip = max(0, self._skip - 1)
            return
        if tag == "a" and self._a is not None:
            self.links.append((self._a[0], re.sub(r"\s+", " ", " ".join(self._a[1])).strip()))
            self._a = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._skip:
            return
        t = data.strip()
        if not t:
            return
        self._text_since_img.append(t)
        if len(self._text_since_img) > 40:
            self._text_since_img = self._text_since_img[-40:]
        if self._a is not None:
            self._a[1].append(t)


def parse_html(text: str) -> PageParser:
    p = PageParser()
    try:
        p.feed(text)
        p.close()
    except Exception:
        pass
    return p


def decode_html(body: bytes, ctype: str) -> str:
    cands = []
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
    if m:
        cands.append(m.group(1))
    m = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
    if m:
        cands.append(m.group(1).decode("ascii", "ignore"))
    cands += ["utf-8", "cp949"]
    for enc in cands:
        enc = "cp949" if enc.lower().replace("_", "-") in ("euc-kr", "ks-c-5601-1987", "x-windows-949") else enc
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


JS_REDIRECT = re.compile(r"""(?:window\.|document\.|top\.|self\.|parent\.)?location(?:\.href)?\s*"""
                         r"""(?:=|\.replace\(|\.assign\()\s*['"]([^'"]+)['"]""")
META_REFRESH = re.compile(r"""<meta[^>]+http-equiv\s*=\s*['"]?refresh['"]?[^>]*?content\s*=\s*['"]?\s*\d*\s*;?"""
                          r"""\s*url\s*=\s*['"]?([^'">\s]+)""", re.I)


def fetch_page(f: Fetcher, url: str, referer: str | None = None) -> tuple[Resp, str]:
    """GET a page, following meta-refresh and (on small stub pages) JS location redirects."""
    seen = {url}
    r, text = Resp(url, url, -1, error="not fetched"), ""
    for _ in range(4):
        r = f.get(url, referer=referer)
        if not r.ok:
            return r, ""
        text = decode_html(r.body, r.ctype)
        stripped = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        m = META_REFRESH.search(stripped)
        if not m and len(stripped) < 30000:
            m = JS_REDIRECT.search(stripped)
        if not m:
            return r, text
        nxt = urllib.parse.urljoin(r.final, html.unescape(m.group(1).strip()))
        if nxt in seen or not nxt.startswith("http"):
            return r, text
        seen.add(nxt)
        referer, url = r.final, nxt
    return r, text


def homepage_candidates(hp: str) -> list[str]:
    hp = hp.strip().strip("\"'")
    if not hp:
        return []
    if not re.match(r"https?://", hp, re.I):
        return ["https://" + hp, "http://" + hp]
    other = re.sub(r"^https?://", "http://" if hp.lower().startswith("https") else "https://", hp, flags=re.I)
    return [hp, other]


# --------------------------------------------------------------------------- NEIS

def region_code(region: str) -> str:
    r = (region or "").strip()
    if not r:
        return ""
    if re.fullmatch(r"[A-Z]\d0", r.upper()):
        return r.upper()
    for pre, code in REGION_PREFIXES:
        if r.startswith(pre):
            return code
    return ""


def split_paren(name: str) -> tuple[str, str]:
    m = re.match(r"^\s*(.+?)\s*[\(（]\s*([^)）]+?)\s*[\)）]\s*$", name)
    if m:
        return m.group(1), m.group(2)
    return name.strip(), ""


def neis_lookup(f: Fetcher, name: str, region: str, key: str, prefer: list[str]) -> tuple[dict | None, list[str]]:
    """Return (row, notes). row has SCHUL_NM, SD_SCHUL_CODE, ATPT_OFCDC_SC_CODE, HMPG_ADRES ..."""
    notes = []
    code = region_code(region)
    if region and not code:
        notes.append(f"unknown region '{region}' ignored")

    def call(nm, rc):
        params = {"Type": "json", "pIndex": 1, "pSize": 1000 if key else 100, "SCHUL_NM": nm}
        if key:
            params["KEY"] = key
        if rc:
            params["ATPT_OFCDC_SC_CODE"] = rc
        r = f.get(NEIS_URL + "?" + urllib.parse.urlencode(params), cache=True)
        if not r.ok:
            return None, f"NEIS error: {r.error or r.status}"
        try:
            d = json.loads(r.body.decode("utf-8"))
        except Exception:
            return None, "NEIS: bad JSON"
        if "schoolInfo" not in d:
            res = d.get("RESULT", {})
            if res.get("CODE") == "INFO-200":
                return [], ""
            return None, f"NEIS {res.get('CODE')}: {res.get('MESSAGE')}"
        head = d["schoolInfo"][0]["head"]
        rows = d["schoolInfo"][1]["row"]
        total = head[0].get("list_total_count", len(rows))
        if total > len(rows):
            return rows, f"NEIS returned {len(rows)}/{total} rows (keyless sample mode caps at 5; add --neis-key or a region)"
        return rows, ""

    tries = [name]
    short = name
    for pre, _ in REGION_PREFIXES:
        if name.startswith(pre) and len(name) > len(pre) + 3:
            short = name[len(pre):]
            break
    if short != name:
        tries.append(short)  # e.g. given "인천송림초등학교" but official is "송림초등학교"
    rows = None
    for nm in tries:
        rows, err = call(nm, code)
        if err:
            notes.append(err)
        if rows:
            break
    if not rows:
        if rows is None:
            return None, notes
        notes.append("not found in NEIS" + (f" (region {CODE_SHORT.get(code, code)})" if code else ""))
        return None, notes

    def prefixed(r):
        return r["SCHUL_NM"] == CODE_SHORT.get(r["ATPT_OFCDC_SC_CODE"], "") + name

    exact = [r for r in rows if r["SCHUL_NM"] == name]
    pref = [r for r in rows if prefixed(r)]
    cands = exact or pref or rows
    if len(cands) > 1:
        order = {c: i for i, c in enumerate(prefer)}
        cands.sort(key=lambda r: order.get(r["ATPT_OFCDC_SC_CODE"], 99))
    alts = [r for r in rows if r is not cands[0]]
    if len(cands) > 1 or (not exact and not pref and len(rows) > 1):
        notes.append("ambiguous NEIS match; picked {} ({}); others: {}".format(
            cands[0]["SCHUL_NM"], CODE_SHORT.get(cands[0]["ATPT_OFCDC_SC_CODE"], ""),
            ", ".join(f"{r['SCHUL_NM']}({CODE_SHORT.get(r['ATPT_OFCDC_SC_CODE'], '')})" for r in alts[:5])))
        notes.append("AMBIGUOUS")
    elif not exact and not pref:
        notes.append(f"partial name match -> {cands[0]['SCHUL_NM']}")
    return cands[0], notes


# --------------------------------------------------------------------------- images

def load_image(data: bytes) -> Image.Image | None:
    """Decode bytes (png/jpg/gif/bmp/webp/ico/svg) to RGBA, or None."""
    head = data[:2048].lstrip().lower()
    if head.startswith(b"<?xml") or head.startswith(b"<svg") or b"<svg" in head:
        if fitz is None:
            return None
        try:
            doc = fitz.open(stream=data, filetype="svg")
            page = doc[0]
            zoom = max(1.0, 512 / max(page.rect.width, page.rect.height, 1))
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
            return Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
        except Exception:
            return None
    try:
        im = Image.open(io.BytesIO(data))
        if im.format == "ICO":
            try:
                im.size = max(im.info.get("sizes", [im.size]))
            except Exception:
                pass
        if getattr(im, "is_animated", False):
            im.seek(0)
        im.load()
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass
        if im.mode == "P" and "transparency" in im.info:
            im = im.convert("RGBA")
        return im.convert("RGBA")
    except Exception:
        return None


def bg_color(a: np.ndarray):
    """Background colour from the image border: None = transparent, else RGB int array."""
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    if (border[:, 3] < 32).mean() > 0.4:
        return None
    opaque = border[border[:, 3] >= 32][:, :3].astype(int)
    return np.median(opaque, axis=0)


def fg_mask(a: np.ndarray, bg, tol: int = 38) -> np.ndarray:
    alpha = a[..., 3]
    if bg is None:
        return alpha > 40
    d = np.abs(a[..., :3].astype(int) - bg).max(axis=2)
    return (alpha > 40) & (d > tol)


def runs(profile: np.ndarray, min_gap: int) -> list[tuple[int, int]]:
    """Runs of True (half-open), merging runs separated by gaps shorter than min_gap."""
    idx = np.flatnonzero(profile)
    if idx.size == 0:
        return []
    out, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev > min_gap:
            out.append((s, prev + 1))
            s = i
        prev = i
    out.append((s, prev + 1))
    return out


def content_box(img: Image.Image, tol: int = 38):
    a = np.asarray(img)
    m = fg_mask(a, bg_color(a), tol)
    rows, cols = np.flatnonzero(m.any(1)), np.flatnonzero(m.any(0))
    if rows.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def _peel_frame(img: Image.Image, tol: int = 38):
    """If the image is a 'card' (thin frame line, then background, then content) return inner box."""
    a = np.asarray(img)
    H, W = a.shape[:2]
    if H < 24 or W < 24:
        return None
    # frame line colour = median of the outermost ring
    ring = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    fc = np.median(ring[:, :3].astype(int), axis=0)
    near = lambda x: (np.abs(x[..., :3].astype(int) - fc).max(axis=-1) <= tol) & (x[..., 3] > 40)
    if min(near(a[0]).mean(), near(a[-1]).mean(), near(a[:, 0]).mean(), near(a[:, -1]).mean()) < 0.6:
        return None
    lim = max(3, int(0.12 * min(H, W)))
    # walk inward from each side until a line is mostly NOT frame colour and fairly uniform
    def depth(lines):
        for k in range(1, lim):
            ln = lines(k)
            if near(ln).mean() < 0.3:
                return k
        return None
    t = [depth(lambda k: a[k]), depth(lambda k: a[-1 - k]), depth(lambda k: a[:, k]), depth(lambda k: a[:, -1 - k])]
    if any(v is None for v in t):
        return None
    inner = img.crop((t[2], t[0], W - t[3], H - t[1]))
    ia = np.asarray(inner)
    ib = bg_color(ia)
    if ib is None:
        return None
    # inner border must be mostly background (otherwise it is a solid badge, not a frame)
    ring2 = np.concatenate([ia[0], ia[-1], ia[:, 0], ia[:, -1]])
    if (np.abs(ring2[:, :3].astype(int) - ib).max(axis=1) <= tol).mean() < 0.8:
        return None
    return t[2], t[0], W - t[3], H - t[1]


def main_box(img: Image.Image, tol: int = 38):
    """Content box keeping only the heaviest run of rows / columns (drops e.g. the rounded corner
    arcs left over after peeling a card frame)."""
    a = np.asarray(img)
    m = fg_mask(a, bg_color(a), tol)
    if not m.any():
        return None
    out = []
    for axis in (0, 1):  # columns, then rows
        prof = m.sum(axis)
        rs = runs(prof > 0, max(2, int(0.02 * prof.size)))
        r0, r1 = max(rs, key=lambda r: prof[r[0]:r[1]].sum())
        out.append((int(r0), int(r1)))
    (x0, x1), (y0, y1) = out
    return x0, y0, x1, y1


def trim(img: Image.Image, tol: int = 38, peel: bool = True) -> Image.Image:
    box = content_box(img, tol)
    if box:
        img = img.crop(box)
    if peel:
        for _ in range(2):
            fb = _peel_frame(img, tol)
            if not fb:
                break
            img = img.crop(fb)
            box = main_box(img, tol)
            if box:
                img = img.crop(box)
    return img


def split_banner(img: Image.Image, tol: int = 38):
    """Header banner -> (emblem crop | None, info). Emblem = leftmost dense, square-ish blob,
    separated from the name text by >= 2 empty columns or (if touching) by a profile valley."""
    a = np.asarray(img)
    bg = bg_color(a)
    m = fg_mask(a, bg, tol)
    rows = np.flatnonzero(m.any(1))
    if rows.size == 0:
        return None, "empty"
    m = m[rows[0]:rows[-1] + 1]
    ac = a[rows[0]:rows[-1] + 1]
    ch, W = m.shape
    prof = m.sum(0)
    cols = np.flatnonzero(prof)
    x0, xe = int(cols[0]), int(cols[-1]) + 1
    if xe - x0 <= 1.6 * ch:  # the header logo is already just an emblem
        return trim(img, tol), "square header logo"

    def same_colour_as_text(c1):
        """A lone glyph of the school name only has the text colour (plus anti-aliasing blends
        towards the background); an emblem has other colours too."""
        rest = m[:, c1:]
        if rest.sum() < 20:
            return False
        rp = ac[:, c1:][rest].astype(float)
        bp = ac[:, x0:c1][m[:, x0:c1]].astype(float)
        if bp.size == 0:
            return False
        if bg is None:  # transparent banner: anti-aliasing lives in alpha, RGB stays the text colour
            solid = rp[rp[:, 3] >= 200]
            tc = np.median((solid if len(solid) >= 10 else rp)[:, :3], axis=0)
            return (np.abs(bp[:, :3] - tc).max(axis=1) <= 60).mean() >= 0.8
        b = np.asarray(bg, dtype=float)
        far = np.abs(rp[:, :3] - b).max(axis=1)
        tc = np.median(rp[far >= np.percentile(far, 70)][:, :3], axis=0)
        v = tc - b
        vv = float((v * v).sum())
        if vv < 1:
            return False
        t = np.clip(((bp[:, :3] - b) @ v) / vv, 0, 1)
        d = np.abs(bp[:, :3] - (b + t[:, None] * v)).max(axis=1)
        return (d <= 40).mean() >= 0.85

    def accept(c1, relaxed=False):
        sub = m[:, x0:c1]
        rr = np.flatnonzero(sub.any(1))
        if rr.size == 0:
            return None
        h, w = rr[-1] - rr[0] + 1, c1 - x0
        fill = prof[x0:c1].max() / ch  # emblems fill (almost) whole columns, glyph strokes do not
        ink = sub.sum() / float(w * h)
        if relaxed:  # cleanly separated blob: allow hollow / wider marks, but not a lone sparse glyph
            good = 0.55 <= w / h <= 2.0 and h >= 0.7 * ch and w >= 0.6 * ch and fill >= 0.6 and ink >= 0.35
        else:
            good = 0.55 <= w / h <= 1.8 and h >= 0.75 * ch and w >= 0.5 * ch and fill >= 0.75
        if good and not same_colour_as_text(c1):
            y0 = rows[0] + rr[0]
            return img.crop((x0, int(y0), c1, int(y0 + h)))
        return None

    segs = runs(prof > 0, 2)  # split at >= 2 empty columns
    if len(segs) >= 2:
        crop = accept(int(segs[0][1]), relaxed=True)
        if crop is not None:
            return crop, f"left blob {crop.width}x{crop.height} (gap) of banner {img.width}x{img.height}"
    dense = np.flatnonzero(prof >= 0.75 * ch)
    if dense.size and dense[0] - x0 <= 0.5 * ch:  # text touches the emblem: cut at first valley
        for c in range(max(int(x0 + 0.5 * ch), int(dense[0]) + 1), min(W - 1, int(x0 + 1.8 * ch))):
            if prof[c] <= 0.35 * ch and prof[c] <= prof[c - 1] and prof[c] <= prof[c + 1]:
                crop = accept(c)
                if crop is not None:
                    return crop, f"left blob {crop.width}x{crop.height} (valley) of banner {img.width}x{img.height}"
                break
    return None, "no emblem-like blob at the left of the header logo"


def _rgb(img: Image.Image) -> Image.Image:
    base = Image.new("RGBA", img.size, (255, 255, 255, 255))
    base.alpha_composite(img.convert("RGBA"))
    return base.convert("RGB")


def _filled_mask(img: Image.Image, tol: int = 38) -> np.ndarray:
    a = np.asarray(img)
    m = fg_mask(a, bg_color(a), tol)
    rf = np.zeros_like(m)
    cf = np.zeros_like(m)
    for i in range(m.shape[0]):
        j = np.flatnonzero(m[i])
        if j.size:
            rf[i, j[0]:j[-1] + 1] = True
    for i in range(m.shape[1]):
        j = np.flatnonzero(m[:, i])
        if j.size:
            cf[j[0]:j[-1] + 1, i] = True
    M = rf & cf
    if M.mean() < 0.25:
        M = np.ones_like(M)
    return M.astype(np.float64)


try:  # scipy.fft is faster (threads); numpy.fft is the fallback
    from scipy import fft as _sfft

    def _rfft2(x, s=None):
        return _sfft.rfft2(x, s=s, workers=-1)

    def _irfft2(x, s):
        return _sfft.irfft2(x, s=s, workers=-1)
except Exception:  # pragma: no cover
    def _rfft2(x, s=None):
        return np.fft.rfft2(x, s=s)

    def _irfft2(x, s):
        return np.fft.irfft2(x, s=s)


def _masked_ncc(C: np.ndarray, T: np.ndarray, M: np.ndarray) -> np.ndarray:
    """Joint-RGB masked normalised cross-correlation (valid positions) via FFT.
    C: HxWx3, T: hxwx3, M: hxw {0,1}. Returns (H-h+1)x(W-w+1) scores in [-1, 1]."""
    H, W, _ = C.shape
    h, w = M.shape
    n = float(M.sum())
    C = C.astype(np.float32)
    flip = lambda k: np.ascontiguousarray(k[::-1, ::-1], dtype=np.float32)
    FM = _rfft2(flip(M), s=(H, W))
    num_f = 0
    s1sq = np.zeros((H - h + 1, W - w + 1), dtype=np.float64)
    tss = 0.0
    for ch in range(3):
        t = T[..., ch]
        t0 = (t - (t * M).sum() / n) * M
        tss += float((t0.astype(np.float64) ** 2).sum())
        Fc = _rfft2(C[..., ch])
        num_f = num_f + Fc * _rfft2(flip(t0), s=(H, W))  # sum over channels in the frequency domain
        s1 = _irfft2(Fc * FM, s=(H, W))[h - 1:, w - 1:].astype(np.float64)
        s1sq += s1 * s1
    num = _irfft2(num_f, s=(H, W))[h - 1:, w - 1:].astype(np.float64)
    s2 = _irfft2(_rfft2((C * C).sum(axis=2)) * FM, s=(H, W))[h - 1:, w - 1:].astype(np.float64)
    var = s2 - s1sq / n
    if tss <= 1e-6:
        return np.zeros_like(num)
    ok = var > n * 3 * 16.0  # ignore flat windows (std < ~4 grey levels)
    out = np.zeros_like(num)
    out[ok] = num[ok] / np.sqrt(var[ok] * tss)
    return np.clip(out, -1, 1)


def find_template(big: Image.Image, tpl: Image.Image, min_ratio: float = 1.15, step: float = 1.09,
                  work: int = 40):
    """Locate tpl inside big at scales where it appears >= min_ratio x the template size.
    Returns (score, (x0, y0, x1, y1) in big coords) or (-1, None)."""
    t = tpl
    if max(t.size) > work:
        t = t.resize((max(8, round(t.width * work / max(t.size))), max(8, round(t.height * work / max(t.size)))),
                     Image.LANCZOS)
    T = np.asarray(_rgb(t), dtype=np.float64)
    M = _filled_mask(t)
    h, w = M.shape
    tmax = max(h, w)
    BW, BH = big.size
    base = _rgb(big)
    e = max(tpl.width, tpl.height) * min_ratio  # emblem size (px, in big) at the first scale
    e_max = min(BW * tmax / w, BH * tmax / h)
    best = (-1.0, None)
    while e <= e_max * 1.0001:
        fct = tmax / e
        sw, sh = max(w, round(BW * fct)), max(h, round(BH * fct))
        C = np.asarray(base.resize((sw, sh), Image.LANCZOS, reducing_gap=3.0), dtype=np.float64)
        ncc = _masked_ncc(C, T, M)
        i = int(np.argmax(ncc))
        y, x = divmod(i, ncc.shape[1])
        sc = float(ncc.flat[i])
        if sc > best[0]:
            best = (sc, (x / fct, y / fct, (x + w) / fct, (y + h) / fct))
        e *= step
    return best


def _hue_hist(x: np.ndarray) -> np.ndarray:
    """15-bin colour signature: 12 (softened) hue bins for chromatic pixels + dark/mid/light greys.
    Hue-based, so the same emblem rendered navy in one place and royal blue in another still agrees."""
    px = x.reshape(-1, 3) / 255.0
    mx, mn = px.max(1), px.min(1)
    d = np.maximum(mx - mn, 1e-6)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6.0
    chrom = (s > 0.25) & (mx > 0.15)
    bins = np.zeros(15)
    np.add.at(bins, np.floor(h[chrom] * 12).astype(int) % 12, 1)
    v = mx[~chrom]
    bins[12], bins[13], bins[14] = (v < 0.35).sum(), ((v >= 0.35) & (v < 0.85)).sum(), (v >= 0.85).sum()
    hb = bins[:12].copy()
    bins[:12] = 0.5 * hb + 0.25 * np.roll(hb, 1) + 0.25 * np.roll(hb, -1)
    return bins / max(1.0, bins.sum())


def colour_similarity(crop: Image.Image, tpl: Image.Image) -> float:
    """Histogram intersection (0..1) of hue signatures of crop vs template, compared at the template's
    size inside its shape mask. The NCC is shape-dominated (round badges all look alike at 40 px);
    this separates e.g. a green emblem from a navy one."""
    M = _filled_mask(tpl) > 0
    a = np.asarray(_rgb(tpl).filter(ImageFilter.GaussianBlur(0.8)), dtype=float)
    b = np.asarray(_rgb(crop.resize(tpl.size, Image.LANCZOS)).filter(ImageFilter.GaussianBlur(0.8)), dtype=float)
    return float(np.minimum(_hue_hist(a[M]), _hue_hist(b[M])).sum())


def _connected(seed: np.ndarray, mask: np.ndarray, max_side: int = 240) -> np.ndarray:
    """Pixels of `mask` 8-connected to `seed` (geodesic reconstruction). Large masks are processed on
    a block-pooled grid so that the numpy-only loop stays fast."""
    k = max(1, int(np.ceil(max(mask.shape) / max_side)))
    H, W = mask.shape
    if k > 1:
        Hp, Wp = -(-H // k) * k, -(-W // k) * k
        pool = lambda x: np.pad(x, ((0, Hp - H), (0, Wp - W))).reshape(Hp // k, k, Wp // k, k).any(axis=(1, 3))
        ms, cur = pool(mask), pool(seed)
    else:
        ms, cur = mask, seed.copy()
    cur &= ms
    while True:
        g = cur.copy()
        g[1:] |= cur[:-1]; g[:-1] |= cur[1:]; g[:, 1:] |= cur[:, :-1]; g[:, :-1] |= cur[:, 1:]
        g[1:, 1:] |= cur[:-1, :-1]; g[:-1, :-1] |= cur[1:, 1:]; g[1:, :-1] |= cur[:-1, 1:]; g[:-1, 1:] |= cur[1:, :-1]
        g &= ms
        if np.array_equal(g, cur):
            break
        cur = g
    if k > 1:
        cur = np.repeat(np.repeat(cur, k, axis=0), k, axis=1)[:H, :W] & mask
    return cur


def shape_iou(crop: Image.Image, tpl: Image.Image) -> float:
    """IoU of the filled foreground shapes of crop (resized to the template) and template."""
    a = _filled_mask(tpl) > 0
    b = _filled_mask(crop.resize(tpl.size, Image.LANCZOS)) > 0
    return float((a & b).sum() / max(1, (a | b).sum()))


def agreement(crop: Image.Image, tpl: Image.Image) -> float:
    return shape_iou(crop, tpl) + colour_similarity(crop, tpl)


def crop_match(big: Image.Image, box, tol: int = 38, grow: float = 0.35, tpl: Image.Image | None = None) -> Image.Image:
    """Turn a matched box into a tight emblem crop: shrink to the foreground inside the box, then grow
    outward through touching foreground (the header version of an emblem can have a slightly different
    aspect ratio) until a whitespace gap, by at most `grow` x the box size per side."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    # pad with the background colour so that an emblem touching the image edge still has a clean border
    pad = int(grow * max(bw, bh)) + 2
    bgc = bg_color(np.asarray(big))
    canvas = Image.new("RGBA", (big.width + 2 * pad, big.height + 2 * pad),
                       (0, 0, 0, 0) if bgc is None else tuple(int(v) for v in bgc) + (255,))
    canvas.paste(big, (pad, pad))
    big = canvas
    x0, y0, x1, y1 = x0 + pad, y0 + pad, x1 + pad, y1 + pad
    box = (x0, y0, x1, y1)
    W, H = big.size
    win = (int(max(0, x0 - grow * bw)), int(max(0, y0 - grow * bh)),
           int(min(W, x1 + grow * bw)), int(min(H, y1 + grow * bh)))
    reg = big.crop(win)
    a = np.asarray(reg)
    bg = bg_color(a)
    m = fg_mask(a, bg, tol)
    border = np.concatenate([m[0], m[-1], m[:, 0], m[:, -1]])
    clean = bg is None or border.mean() <= 0.15  # plain background around the match -> safe to grow
    # 1. shrink: foreground bbox inside the matched box (+3%)
    cx0, cy0 = max(0, int(x0 - win[0] - 0.03 * bw)), max(0, int(y0 - win[1] - 0.03 * bh))
    cx1, cy1 = int(x1 - win[0] + 0.03 * bw), int(y1 - win[1] + 0.03 * bh)
    core = m[cy0:cy1, cx0:cx1]
    rows, cols = np.flatnonzero(core.any(1)), np.flatnonzero(core.any(0))
    if rows.size == 0:
        return big.crop(tuple(int(round(v)) for v in box))
    X0, Y0, X1, Y1 = cx0 + cols[0], cy0 + rows[0], cx0 + cols[-1] + 1, cy0 + rows[-1] + 1
    # 2. grow: add foreground *connected* to the centre of the match (so a decorative circle or
    #    neighbouring text that merely passes through the box is not swallowed)
    if clean:
        seed = np.zeros_like(m)
        mx0, my0 = int(x0 - win[0]), int(y0 - win[1])
        seed[my0 + int(0.25 * bh):my0 + int(0.75 * bh), mx0 + int(0.25 * bw):mx0 + int(0.75 * bw)] = True
        comp = _connected(seed & m, m)
        rr, cc = np.flatnonzero(comp.any(1)), np.flatnonzero(comp.any(0))
        if rr.size and cc.size:
            X0, Y0 = min(X0, int(cc[0])), min(Y0, int(rr[0]))
            X1, Y1 = max(X1, int(cc[-1]) + 1), max(Y1, int(rr[-1]) + 1)
    tw, th = X1 - X0, Y1 - Y0
    if 0.6 <= tw / max(1, th) <= 1.7 and 0.7 * bw <= tw <= 1.6 * bw and 0.7 * bh <= th <= 1.6 * bh:
        out = reg.crop((int(X0), int(Y0), int(X1), int(Y1)))
        if clean and bg is not None and rr.size and tpl is not None:
            # small fragments touching the crop edge that are not connected to the matched centre are
            # either a decoration around the emblem (e.g. a circle frame) or the emblem's own outer
            # ring: keep whichever version agrees better with the header emblem
            other = m[Y0:Y1, X0:X1] & ~comp[Y0:Y1, X0:X1]
            edge = np.zeros_like(other)
            edge[0], edge[-1], edge[:, 0], edge[:, -1] = other[0], other[-1], other[:, 0], other[:, -1]
            frag = _connected(edge, other)
            if 0 < frag.sum() <= 0.08 * frag.size:
                arr = np.array(out)
                arr[frag] = tuple(int(v) for v in bg) + (255,)
                alt = trim(Image.fromarray(arr, "RGBA"), peel=False)
                if agreement(alt, tpl) > agreement(trim(out, peel=False), tpl) + 0.02:
                    out = alt
        return out
    # growth ran into neighbouring content: fall back to the shrunken core box
    return reg.crop((int(cx0 + cols[0]), int(cy0 + rows[0]), int(cx0 + cols[-1] + 1), int(cy0 + rows[-1] + 1)))


def xy_blob(img: Image.Image, tol: int = 38, depth: int = 4):
    """Recursive whitespace cut; return the largest square-ish leaf (for labelled composites)."""
    a = np.asarray(img)
    m = fg_mask(a, bg_color(a), tol)
    gap = max(3, int(0.02 * max(m.shape)))
    leaves = []

    def cut(x0, y0, x1, y1, d):
        sub = m[y0:y1, x0:x1]
        rows, cols = np.flatnonzero(sub.any(1)), np.flatnonzero(sub.any(0))
        if rows.size == 0:
            return
        x0, x1, y0, y1 = x0 + cols[0], x0 + cols[-1] + 1, y0 + rows[0], y0 + rows[-1] + 1
        if d > 0:
            sub = m[y0:y1, x0:x1]
            for axis in (0, 1):
                rs = runs(sub.any(axis), gap)
                if len(rs) > 1:
                    for r0, r1 in rs:
                        if axis == 0:
                            cut(x0 + r0, y0, x0 + r1, y1, d - 1)
                        else:
                            cut(x0, y0 + r0, x1, y0 + r1, d - 1)
                    return
        leaves.append((int(x0), int(y0), int(x1), int(y1)))

    cut(0, 0, m.shape[1], m.shape[0], depth)
    good = [b for b in leaves if 0.6 <= (b[2] - b[0]) / max(1, b[3] - b[1]) <= 1.7 and min(b[2] - b[0], b[3] - b[1]) >= 40]
    if not good:
        return None
    b = max(good, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
    return img.crop(b)


def is_squareish(img: Image.Image, lo: float = 0.6, hi: float = 1.7) -> bool:
    return lo <= img.width / max(1, img.height) <= hi


def finalize(img: Image.Image, max_px: int, transparent: bool = False) -> tuple[Image.Image, tuple[int, int]]:
    """-> (output image, native size after trimming)."""
    img = trim(img.convert("RGBA"))
    native = img.size
    if transparent:
        img = knock_out_background(img)
    if max(img.size) > max_px:
        s = max_px / max(img.size)
        img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    return img, native


def knock_out_background(img: Image.Image, tol: int = 38) -> Image.Image:
    """Make the background region connected to the border transparent (flood fill)."""
    a = np.array(img)
    bg = bg_color(a)
    if bg is None:
        return img
    cand = ~fg_mask(a, bg, tol)
    reach = np.zeros_like(cand)
    reach[0], reach[-1], reach[:, 0], reach[:, -1] = cand[0], cand[-1], cand[:, 0], cand[:, -1]
    while True:
        grown = reach.copy()
        grown[1:] |= reach[:-1]
        grown[:-1] |= reach[1:]
        grown[:, 1:] |= reach[:, :-1]
        grown[:, :-1] |= reach[:, 1:]
        grown &= cand
        if (grown == reach).all():
            break
        reach = grown
    a[reach, 3] = 0
    return Image.fromarray(a, "RGBA")


# --------------------------------------------------------------------------- page heuristics

CHROME_SRC = re.compile(r"bannerimg|popupimg|/popup/|/banner|/btn|btn_|/ico|ico_|icon|bullet|blank\.|"
                        r"arrow|/common/(?!.*logo)|loading|spacer|/quick|sns_|search|noimages|menuimg|"
                        r"selectdesignimageview|visual|/main/|kakao|facebook|youtube|instagram|blog_|"
                        r"/tit_|title_|/titimg|sub_?top|subtop", re.I)
CHROME_CTX = re.compile(r"(^|[ #.])(header|footer|gnb|lnb|snb|nav|quick|banner|popup|util|sitemap|"
                        r"top_menu|topmenu|foot|bottom|left_menu|leftmenu|location)", re.I)
SYMBOL_LINKS = [(re.compile(r"교표"), 6), (re.compile(r"학교\s*CI|^\s*CI\s*$|학교\s*UI|^\s*UI\s*$"), 6),
                (re.compile(r"상징"), 5), (re.compile(r"심[벌볼]|엠블[럼렘]|학교\s*마크"), 4),
                (re.compile(r"교목|교화|교가"), 2)]
LABEL_POS = re.compile(r"교\s*표|엠블[럼렘]|emblem|학교\s*마크|심[벌볼]\s*마크|symbol[\s_-]*(mark|logo|ci)", re.I)
LABEL_NEG = re.compile(r"교목|교화|교조|교가|교훈|나무|꽃|캐릭터|마스코트|전경|건물|약도|지도|배치도|"
                       r"character|mascot|tree|flower|bird|song|map|photo|교복|교기", re.I)
FILE_POS = re.compile(r"교표|emblem|symbol[_-]?(ci|logo|mark)|kyopyo|gyopyo|schoollogo|school_logo|"
                      r"(^|[_-])logo|(^|[_-])mark|(^|[_-])ci([_.-]|$)", re.I)


def header_logo_candidates(p: PageParser, names: list[str]) -> list[dict]:
    out = []
    for im in p.imgs:
        src, alt, ctx = im["src"], im["alt"], im["ctx"]
        if not src or src.startswith("data:"):
            continue
        fname = urllib.parse.unquote(src.rsplit("/", 1)[-1].split("?")[0])
        s = 0
        if re.search(r"(^| )h1#", ctx):
            s += 3
        if re.search(r"logo|school_mark|header_school|site_?name|brand", ctx + " " + im["cls"]):
            s += 3
        if re.search(r"(^| )(header|div)#(header|top|head)|[ .]header", ctx):
            s += 1
        if re.search(r"logo|emblem|(^|[_-])ci([_.-]|$)|mark", fname, re.I) or "/logo/" in src.lower():
            s += 2
        if any(n and n in alt for n in names):
            s += 2
        if "로고" in alt or "logo" in alt.lower():
            s += 1
        if re.search(r"footer|foot|bottom|copyright", ctx):
            s -= 3
        if re.search(r"banner|popup|slide|visual|quick|sns|search|btn_|menu", src.lower()) or \
                re.search(r"banner|popup|slide|visual|quick|sns|search", ctx):
            s -= 2
        if s >= 4:
            out.append({**im, "score": s})
    out.sort(key=lambda d: (-d["score"], d["idx"]))
    seen, uniq = set(), []
    for d in out:
        if d["src"] not in seen:
            seen.add(d["src"])
            uniq.append(d)
    return uniq


def symbol_links(p: PageParser, base_url: str) -> list[tuple[int, str, str]]:
    host = urllib.parse.urlsplit(base_url).hostname or ""
    found = {}
    for href, text in p.links:
        if not href or not text or href.startswith(("#", "mailto:", "tel:")):
            continue
        if href.lower().startswith("javascript"):
            m = re.search(r"['\"](/[^'\"]+)['\"]", href)
            if not m:
                continue
            href = m.group(1)
        url = urllib.parse.urljoin(base_url, html.unescape(href))
        if (urllib.parse.urlsplit(url).hostname or "") != host:
            continue
        score = max([sc for rx, sc in SYMBOL_LINKS if rx.search(text)] or [0])
        if score and len(text) <= 30:
            if url not in found or found[url][0] < score:
                found[url] = (score, url, text)
    return sorted(found.values(), key=lambda t: -t[0])


def content_images(p: PageParser, page_url: str, exclude: set[str]) -> list[dict]:
    out = []
    for im in p.imgs:
        src = im["src"]
        if not src or src.startswith("data:"):
            continue
        url = urllib.parse.urljoin(page_url, src)
        if url in exclude or CHROME_SRC.search(src) or CHROME_CTX.search(im["ctx"]):
            continue
        fname = urllib.parse.unquote(src.rsplit("/", 1)[-1].split("?")[0])
        text = f"{im['alt']} {im['title']}"
        s = 0
        if LABEL_POS.search(text):
            s += 4
        if FILE_POS.search(fname):
            s += 3
        if re.search(r"교\s*표", im["before"][-40:]):
            s += 2
        if LABEL_NEG.search(text + " " + fname) and not LABEL_POS.search(text + " " + fname):
            s -= 4
        out.append({**im, "url": url, "label": s})
    return out


# --------------------------------------------------------------------------- per-school

@dataclass
class Candidate:
    img: Image.Image
    url: str
    method: str
    score: float  # ranking score
    match: float = -1.0  # NCC with the header emblem (-1 = not matched)
    colour: float = -1.0  # hue-signature similarity with the header emblem
    notes: list = field(default_factory=list)

    @property
    def conf(self) -> float:
        return self.match + self.colour if self.match >= 0 else -1.0


def safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", s).strip("._")
    return s[:80] or "school"


def get_image(f: Fetcher, url: str, referer: str | None, min_side: int = 8):
    r = f.get(url, referer=referer)
    if not r.ok:
        return None, r
    im = load_image(r.body)
    if im is None or min(im.size) < min_side:
        return None, r
    return im, r


def process(row: dict, f: Fetcher, args, out_dir: str) -> dict:
    t0 = time.time()
    name_in = (row.get("name") or "").strip()
    name, hint = split_paren(name_in)
    region = (row.get("region") or "").strip() or hint
    rec = {k: "" for k in REPORT_FIELDS}
    rec.update(name=name_in, status="fail", kind="none")
    notes: list[str] = []

    # 1. NEIS --------------------------------------------------------------
    info, n = neis_lookup(f, name, region, args.neis_key, args.prefer)
    notes += [x for x in n if x != "AMBIGUOUS"]
    ambiguous = "AMBIGUOUS" in n
    official = info["SCHUL_NM"] if info else name
    if info:
        rec.update(official_name=official, edu_office=info.get("ATPT_OFCDC_SC_NM", ""),
                   neis_code=info.get("SD_SCHUL_CODE", ""))
    base = safe_name(f"{rec['neis_code']}_{official}" if rec["neis_code"] else official)
    homepage = (row.get("homepage") or "").strip() or ((info or {}).get("HMPG_ADRES") or "").strip()
    rec["homepage"] = homepage

    def save(img: Image.Image, suffix: str = "") -> tuple[str, dict]:
        """Write the normalised PNG; return (file name, size fields for the report)."""
        fin, native = finalize(img, args.max_px, args.transparent)
        fn = base + suffix + ".png"
        fin.save(os.path.join(out_dir, fn), optimize=True)
        return fn, {"file": fn, "src_w": native[0], "src_h": native[1], "out_w": fin.width, "out_h": fin.height}

    # 0. manual override ---------------------------------------------------
    if (row.get("logo_url") or "").strip():
        im, r = get_image(f, row["logo_url"].strip(), None)
        if im is None:
            notes.append(f"logo_url failed: {r.error or r.status}")
        else:
            fn, sz = save(im)
            kind = (row.get("kind") or "emblem").strip()
            rec.update(status="ok", kind=kind, method="manual", source_url=r.final, **sz)
            rec["notes"] = "; ".join(notes + ["manual logo_url"])
            return rec

    if not homepage:
        why = ("check the name / region, or add a homepage or logo_url column" if info is None else
               "NEIS has no homepage (HMPG_ADRES empty) - add a homepage or logo_url column")
        rec["notes"] = "; ".join(notes + [why])
        return rec

    # 2. homepage ------------------------------------------------------------
    resp, text = Resp(homepage, homepage, -1, error="?"), ""
    for cand_url in homepage_candidates(homepage):
        resp, text = fetch_page(f, cand_url)
        if resp.ok and text:
            break
    if not (resp.ok and text):
        rec["notes"] = "; ".join(notes + [f"homepage unreachable: {resp.error or resp.status}"])
        return rec
    if resp.insecure:
        notes.append("TLS certificate not verifiable (fetched without verification)")
    main_url = resp.final
    p = parse_html(text)
    short = re.sub(r"^(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)", "", official)
    core = re.sub(r"(초등학교|중학교|고등학교|학교|초|중|고)$", "", short)
    names = [x for x in {official, short, core} if len(x) >= 2]

    # 3. header banner -------------------------------------------------------
    banner = banner_url = None
    hdr_emblem = None
    hdr_cands = header_logo_candidates(p, names)
    for c in hdr_cands[:3]:
        u = urllib.parse.urljoin(main_url, c["src"])
        im, r = get_image(f, u, main_url)
        if im is not None and max(im.size) >= 24:
            banner, banner_url = im, r.final
            break
    if banner is not None:
        hdr_emblem, why = split_banner(banner)
        if hdr_emblem is None:
            notes.append(f"header logo: {why}")
        fn, _ = save(banner, "_banner")
        rec["banner_file"] = fn
    else:
        notes.append("no header logo found")

    # 4. symbol / CI pages -------------------------------------------------
    cands: list[Candidate] = []
    links = symbol_links(p, main_url)
    pages = [lk for lk in links if lk[0] >= 4][:args.max_pages] or [lk for lk in links if lk[0] >= 2][:1]
    exclude = {urllib.parse.urljoin(main_url, c["src"]) for c in hdr_cands}  # header/tablet/footer logos
    if banner_url:
        exclude.add(banner_url)
    tried = 0

    big_enough = max(120, 2 * max(hdr_emblem.size)) if hdr_emblem is not None else 120

    def strong(c: Candidate) -> bool:  # good enough to stop downloading more candidates
        return max(c.img.size) >= big_enough and (c.conf >= args.confident or c.method.endswith("_label"))

    for _, purl, ptext in pages:
        if any(strong(c) for c in cands):
            break  # spare the server
        if purl.split("#")[0] == main_url.split("#")[0]:
            continue
        pr, ptxt = fetch_page(f, purl, referer=main_url)
        if not (pr.ok and ptxt):
            notes.append(f"symbol page failed ({ptext}): {pr.error or pr.status}")
            continue
        pp = parse_html(ptxt)
        exclude |= {urllib.parse.urljoin(pr.final, c["src"]) for c in header_logo_candidates(pp, names)
                    if re.search(r"(^| )h1#|logo|header|school_mark", c["ctx"] + " " + c["cls"])}
        imgs = content_images(pp, pr.final, exclude)
        imgs.sort(key=lambda d: (-d["label"], d["idx"]))
        for ci in imgs:
            if tried >= args.max_images or any(strong(c) for c in cands):
                break
            if ci["label"] < 3 and hdr_emblem is None:
                continue  # no header emblem to match against, and not labelled 교표: cannot be judged
            if ci["label"] <= -4:
                continue
            exclude.add(ci["url"])
            im, r = get_image(f, ci["url"], pr.final, min_side=24)
            tried += 1
            if im is None:
                continue
            labelled = ci["label"] >= 3
            where = "ci_page" if re.search(r"CI|UI", ptext) else "symbol_page"
            tr = trim(im)  # also removes card frames, which would otherwise disturb the crop
            # (a) locate the header emblem inside it
            if hdr_emblem is not None and max(tr.size) >= 1.15 * max(hdr_emblem.size):
                sc, box = find_template(tr, hdr_emblem)
                if box is not None and sc >= args.match_min:
                    crop = crop_match(tr, box, tpl=hdr_emblem)
                    col = colour_similarity(crop, hdr_emblem)
                    if (col >= 0.5 and sc + col >= args.accept) or sc >= 0.85:
                        if labelled and is_squareish(tr) and crop.width * crop.height >= 0.5 * tr.width * tr.height:
                            crop = tr  # the page labels this image as the 교표: keep all of it (outer rings etc.)
                        whole = (crop.width >= 0.85 * tr.width and crop.height >= 0.85 * tr.height)
                        meth = f"{where}{'' if whole else '_crop'}"
                        cands.append(Candidate(crop, r.final, meth, 2.0 + (sc + col) / 2 + (0.5 if labelled else 0) +
                                               min(max(crop.size), 400) / 1000, sc, col))
                        continue
                if labelled and box is not None:
                    notes.append(f"labelled 교표 image does not match header emblem (ncc {sc:.2f})")
            # (b) explicitly labelled standalone mark
            if labelled:
                if is_squareish(tr) and min(tr.size) >= 40:
                    cands.append(Candidate(tr, r.final, f"{where}_label", 1.5 + min(max(tr.size), 400) / 1000))
                else:
                    blob = xy_blob(im)
                    if blob is not None:
                        cands.append(Candidate(blob, r.final, f"{where}_label_blob", 1.0 + min(max(blob.size), 400) / 1000))

    # 5. decide ------------------------------------------------------------
    best = max(cands, key=lambda c: c.score) if cands else None
    if best is not None and hdr_emblem is not None and max(best.img.size) < 1.2 * max(hdr_emblem.size):
        best = None  # no better than the header crop
    if best is not None:
        fn, sz = save(best.img)
        rec.update(kind="emblem", method=best.method, source_url=best.url, **sz,
                   match=f"{best.match:.2f}/{best.colour:.2f}" if best.match >= 0 else "")
        if 0 <= best.conf < args.confident:
            notes.append(f"weak match (ncc {best.match:.2f} + colour {best.colour:.2f}) - check")
            ambiguous = True
        if best.match < 0 and hdr_emblem is not None:
            notes.append("labelled 교표 image used; it differs from the header emblem - check")
            ambiguous = True
    elif hdr_emblem is not None:
        fn, sz = save(hdr_emblem)
        rec.update(kind="emblem", method="header_crop", source_url=banner_url, **sz)
        notes.append(f"emblem cropped from header banner ({max(hdr_emblem.size)}px) - low-res; "
                     f"banner also saved")
    elif banner is not None:
        fn, sz = save(banner)
        rec.update(kind="banner", method="header", source_url=banner_url, **sz)
        notes.append("header banner only (emblem + school name text)")
    else:
        icons = [urllib.parse.urljoin(main_url, u) for u in p.icons] + [urllib.parse.urljoin(main_url, "/favicon.ico")]
        for u in icons[:2]:
            im, r = get_image(f, u, main_url, min_side=16)
            if im is not None:
                fn, sz = save(im)
                rec.update(kind="favicon", method="favicon", source_url=r.final, **sz)
                notes.append("favicon only (may be a generic platform icon)")
                break

    if rec["kind"] == "emblem":
        big_enough = max(int(rec["src_w"] or 0), int(rec["src_h"] or 0)) >= args.min_ok
        rec["status"] = "ok" if big_enough and not ambiguous else "review"
    elif rec["kind"] in ("banner", "favicon"):
        rec["status"] = "review"
    else:
        notes.append("no logo found")
    rec["notes"] = "; ".join(notes)
    rec["_secs"] = round(time.time() - t0, 1)
    return rec


# --------------------------------------------------------------------------- contact sheet

def load_font(size: int):
    for fp in [r"C:\Windows\Fonts\malgun.ttf", "/System/Library/Fonts/AppleSDGothicNeo.ttc",
               "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def contact_sheet(rows: list[dict], out_dir: str, path: str, cols: int = 4):
    cw, ch = 300, 330
    n = max(1, len(rows))
    sheet = Image.new("RGB", (cols * cw, ((n + cols - 1) // cols) * ch), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    f1, f2 = load_font(15), load_font(12)
    colors = {"ok": (22, 128, 60), "review": (190, 120, 0), "fail": (200, 40, 40)}
    for i, r in enumerate(rows):
        x, y = (i % cols) * cw, (i // cols) * ch
        d.rectangle([x + 4, y + 4, x + cw - 5, y + ch - 5], outline=(210, 210, 210), fill=(255, 255, 255))
        # checkerboard behind the main image so transparency / white padding is visible
        bx0, by0, bw, bh = x + 50, y + 12, 200, 190
        for cy in range(by0, by0 + bh, 10):
            for cx in range(bx0, bx0 + bw, 10):
                if ((cx - bx0) // 10 + (cy - by0) // 10) % 2:
                    d.rectangle([cx, cy, min(cx + 9, bx0 + bw - 1), min(cy + 9, by0 + bh - 1)], fill=(236, 236, 236))
        for key, box in (("file", (bw, bh)), ("banner_file", (270, 46))):
            fn = r.get(key)
            if not fn or not os.path.exists(os.path.join(out_dir, fn)):
                continue
            if key == "banner_file" and fn == r.get("file"):
                continue
            im = Image.open(os.path.join(out_dir, fn)).convert("RGBA")
            im.thumbnail(box, Image.LANCZOS)
            if key == "file":
                px, py = bx0 + (bw - im.width) // 2, by0 + (bh - im.height) // 2
            else:
                px, py = x + (cw - im.width) // 2, y + 210
            sheet.paste(im, (px, py), im)
        label = r.get("official_name") or r.get("name")
        d.text((x + 10, y + 262), label[:22], fill=(20, 20, 20), font=f1)
        st = r.get("status", "")
        d.text((x + 10, y + 284), f"{st} · {r.get('kind', '')} · {r.get('method', '')}", fill=colors.get(st, (0, 0, 0)), font=f2)
        info = f"src {r.get('src_w')}x{r.get('src_h')} → {r.get('out_w')}x{r.get('out_h')}"
        if r.get("match"):
            info += f" · ncc {r['match']}"
        d.text((x + 10, y + 302), info if r.get("src_w") else (r.get("notes", "")[:40]), fill=(90, 90, 90), font=f2)
    sheet.save(path, optimize=True)


# --------------------------------------------------------------------------- main

def read_input(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "name" not in rows[0]:
        sys.exit("input CSV needs a 'name' column")
    return [r for r in rows if (r.get("name") or "").strip()]


def load_report(path: str) -> dict[str, dict]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {r["name"]: r for r in csv.DictReader(fh)}


def write_report(path: str, rows: list[dict]):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=REPORT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    try:
        os.replace(tmp, path)
    except PermissionError:  # e.g. report.csv is open in Excel
        alt = path[:-4] + ".pending.csv"
        os.replace(tmp, alt)
        print(f"  ! {path} is locked (open in Excel?) - wrote {alt} instead", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="input CSV with a 'name' column (optional: region, homepage, logo_url)")
    ap.add_argument("--out", default="out", help="output folder (default: out)")
    ap.add_argument("--cache", default="", help="HTTP cache folder (default: <out>_cache next to the output "
                                                 "folder; raw downloads - do not publish, safe to delete)")
    ap.add_argument("--neis-key", default=os.environ.get("NEIS_API_KEY", ""), help="NEIS API key (or env NEIS_API_KEY)")
    ap.add_argument("--prefer", default="인천,서울,경기", help="region preference for ambiguous names (default 인천,서울,경기)")
    ap.add_argument("--delay", type=float, default=1.5, help="min seconds between requests to the same host (default 1.5)")
    ap.add_argument("--max-px", type=int, default=256, help="max output size in px; never upscales (default 256)")
    ap.add_argument("--min-ok", type=int, default=64, help="emblems smaller than this (source px) are 'review' (default 64)")
    ap.add_argument("--match-min", type=float, default=0.5, help="NCC floor for a template match (default 0.5)")
    ap.add_argument("--accept", type=float, default=1.3, help="accept a match if NCC + colour >= this (default 1.3)")
    ap.add_argument("--confident", type=float, default=1.4, help="matches below this NCC + colour are 'review' (default 1.4)")
    ap.add_argument("--max-pages", type=int, default=3, help="max symbol/CI pages per school (default 3)")
    ap.add_argument("--max-images", type=int, default=6, help="max candidate images downloaded per school (default 6)")
    ap.add_argument("--transparent", action="store_true", help="make the outer background transparent")
    ap.add_argument("--force", action="store_true", help="redo every school")
    ap.add_argument("--retry-review", action="store_true", help="redo schools whose status is 'review'")
    ap.add_argument("--limit", type=int, default=0, help="only process the first N schools")
    ap.add_argument("--sheet", default="", help="write a labelled contact sheet PNG to this path")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    args.prefer = [region_code(x) for x in args.prefer.split(",") if region_code(x)]

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    report_path = os.path.join(out_dir, "report.csv")
    prev = load_report(report_path)
    rows = read_input(args.csv)
    if args.limit:
        rows = rows[:args.limit]
    cache_dir = args.cache or os.path.abspath(out_dir).rstrip("\\/") + "_cache"
    f = Fetcher(cache_dir, delay=args.delay, verbose=args.verbose)

    results = []
    t_start = time.time()
    for i, row in enumerate(rows, 1):
        nm = row["name"].strip()
        old = prev.get(nm)
        keep = (old and not args.force and old.get("status") in ("ok", "review")
                and old.get("file") and os.path.exists(os.path.join(out_dir, old["file"]))
                and not (args.retry_review and old.get("status") == "review"))
        if keep:
            results.append(old)
            print(f"[{i}/{len(rows)}] {nm}: skip (already {old['status']})", flush=True)
            continue
        try:
            rec = process(row, f, args, out_dir)
        except Exception as e:  # never let one school stop the batch
            rec = {k: "" for k in REPORT_FIELDS}
            rec.update(name=nm, status="fail", kind="none", notes=f"error: {type(e).__name__}: {e}")
        results.append(rec)
        print(f"[{i}/{len(rows)}] {nm}: {rec['status']} {rec['kind']} {rec.get('method', '')} "
              f"{rec.get('src_w', '')}x{rec.get('src_h', '')} {rec.get('match', '')} ({rec.get('_secs', '?')}s) "
              f"{rec['notes'][:150]}", flush=True)
        write_report(report_path, results + [prev[r["name"].strip()] for r in rows[i:] if r["name"].strip() in prev])
    write_report(report_path, results)
    cnt = {}
    for r in results:
        cnt[r["status"]] = cnt.get(r["status"], 0) + 1
    print(f"\ndone: {cnt}  requests={f.requests} cache_hits={f.cache_hits}  {time.time() - t_start:.0f}s")
    print(f"report: {report_path}")
    if args.sheet:
        contact_sheet(results, out_dir, args.sheet)
        print(f"sheet: {args.sheet}")


if __name__ == "__main__":
    main()
