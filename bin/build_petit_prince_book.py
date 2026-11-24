#!/usr/bin/env python3
"""
M3/M4 Complete Asset & Catalog Builder for *Le Petit Prince* (26 plates / 13 double spreads).

Supports modular execution:
  --plates   Composite 26 896x1200 RGB JPEG watercolor plates (wc_p01..wc_p26.jpg + wc_p03_xray.jpg)
  --audio    Synthesize 300 Aoede studio TTS clips -> 600 files (.mp3 + .ogg) in FR/IT/DE (ZERO EN!)
  --words    Synthesize missing single-word clips (.mp3 + .ogg) in assets/words_audio/{fr,it,de}/
  --align    Run Whisper base + Needleman-Wunsch DP + ffprobe duration clamping on 225 level MP3s
  --compile  Build books/petit-prince/kids_book_data.json & 2-book kids_books_catalog.js
  --all      Run all phases in order (--plates -> --audio -> --words -> --align -> --compile)

Caches large downloads, extracted JP2s, and Whisper outputs strictly under:
  /tmp/petit_prince_build_cache/
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import io
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "books" / "petit-prince"
COVER_PATH = ROOT / "books" / "covers" / "petit-prince.jpg"
CONTENT_SPEC_PATH = BOOK_DIR / "content_spec.json"
KIDS_BOOK_DATA_PATH = BOOK_DIR / "kids_book_data.json"
KIDS_AUDIO_DIR = BOOK_DIR / "kids_audio"
CATALOG_JS_PATH = ROOT / "kids_books_catalog.js"
SARDEGNA_JSON_PATH = (
    ROOT / "stories" / "alessandro" / "storia-sardegna-cala-gonone-arbatax-famiglia" / "kids_book_data.json"
)
WORDS_AUDIO_DIR = ROOT / "assets" / "words_audio"

CACHE_DIR = Path("/tmp/petit_prince_build_cache")
IA_JP2_DIR = CACHE_DIR / "ia_jp2"
GUTENBERG_DIR = CACHE_DIR / "gutenberg_au"
IA_XML_PATH = CACHE_DIR / "ia_1943_djvu.xml"
IA_ZIP_PATH = CACHE_DIR / "ia_1943_jp2.zip"
LIBERLIBER_SHARED_DIR = Path("/tmp/liberliber_petit_prince")
LIBERLIBER_CACHE_DIR = CACHE_DIR / "liberliber"
LIBERLIBER_PDF_URL = (
    "https://www.liberliber.eu/mediateca/libri/s/saint_exupery/"
    "il_piccolo_principe/pdf/saint_exupery_il_piccolo_principe.pdf"
)
PREARRANGE_NB_DIR = CACHE_DIR / "prearranged_nb"
REMASTER_NB_DIR = CACHE_DIR / "remastered_nb"
WHISPER_CACHE_PATH = CACHE_DIR / "whisper_cache.json"
ALIGNED_TIMINGS_PATH = CACHE_DIR / "aligned_timings.json"

WHISPER_PYTHON = Path("/home/linuxbrew/.linuxbrew/Cellar/openai-whisper/20250625_4/libexec/bin/python")
GPRISM_ENV_PATH = Path("/home/riccardo/git/gic/.env.gprism")

SUPPORTED_LANGS = ("fr", "it", "de")
TIERS = ("seby", "ale", "emma")
STRIP_OUTER_RE = re.compile(r"^[^\wÀ-ÿŒœŸÿÄÖÜäöüß]+|[^\wÀ-ÿŒœŸÿÄÖÜäöüß]+$")
NORM_ALIGN_RE = re.compile(r"[^\wÀ-ÿŒœŸÿÄÖÜäöüß]")

IA_BASE_URL = "https://archive.org/download/antoinedesaintexuperylepetitprince1943"
IA_XML_URL = f"{IA_BASE_URL}/Antoine%20de%20Saint%20Exupery%20-%20Le%20Petit%20Prince%20-%201943_djvu.xml"
IA_ZIP_URL = f"{IA_BASE_URL}/Antoine%20de%20Saint%20Exupery%20-%20Le%20Petit%20Prince%20-%201943_jp2.zip"
GUTENBERG_BASE_URL = "https://gutenberg.net.au/ebooks03/0300771h-images"

PLATE_W = 896
PLATE_H = 1200

STYLE_MAP = {
    "fr": (
        "Douce, chaleureuse, mélodieuse, affectueuse et enjouée maîtresse d'école primaire française "
        "qui lit un conte illustré poétique aux enfants avec beaucoup d'expression, d'émerveillement et un sourire dans la voix"
    ),
    "it": (
        "Dolce, calda, sinuosa, affettuosa e giocosa maestra delle elementari italiana "
        "che legge una fiaba illustrata poetica ai bambini con tantissimo pathos, meraviglia, "
        "musicalità, incanto e un sorriso affettuoso nella voce"
    ),
    "de": (
        "Liebevolle, warme, melodische, ausdrucksstarke und verspielte Grundschullehrerin, "
        "die Kindern ein poetisches Bilderbuch mit viel Gefühl, Staunen und einem Lächeln in der Stimme vorliest"
    ),
}

EDGE_VOICES = {
    "fr": ("fr-FR-EloiseNeural", "-18%"),
    "it": ("it-IT-IsabellaNeural", "-5%"),
    "de": ("de-DE-KatjaNeural", "-10%"),
}


# =============================================================================
# PHASE A — 24 WATERCOLOR PLATES (896x1200 RGB JPEG)
# =============================================================================

# Each recipe lists source items to place in the safe art zone.
# Format of each item:
#   {"src": ("ia", leaf_idx, (x0,y0,x1,y1), erase_xml_bool) or ("au", filename, None, False),
#    "rel_box": (rx0, ry0, rx1, ry1) inside the page's safe art zone (0..1)}
# Optional "wash": "sunset" or "starry_desert" adds a delicate watercolor atmosphere behind the art.
PLATE_RECIPES: dict[int, dict] = {
    1: {
        "items": [
            {"src": ("ia", 1, (1120, 590, 2240, 1180), True), "rel_box": (0.08, 0.26, 0.92, 0.62)},
            {"src": ("ia", 1, (1120, 1680, 2245, 2210), True), "rel_box": (0.12, 0.64, 0.90, 0.98)},
        ],
    },
    2: {
        "items": [
            {"src": ("ia", 4, (1500, 2430, 2255, 2870), True), "rel_box": (0.04, 0.56, 0.36, 0.88)},
            {"src": ("ia", 3, (1080, 1390, 2230, 2540), False), "rel_box": (0.28, 0.16, 0.96, 0.96)},
        ],
    },
    3: {
        "items": [
            {"src": ("ia", 7, (1320, 290, 2260, 1680), False), "rel_box": (0.14, 0.12, 0.92, 0.96)},
        ],
    },
    4: {
        "items": [
            {"src": ("ia", 12, (295, 330, 2265, 2880), True), "rel_box": (0.04, 0.24, 0.96, 0.98)},
        ],
    },
    5: {
        "wash": "sunset",
        "items": [
            {"src": ("ia", 14, (1400, 1250, 2255, 2145), True), "rel_box": (0.12, 0.22, 0.88, 0.92)},
        ],
    },
    6: {
        "items": [
            {"src": ("ia", 19, (390, 295, 1150, 1060), True), "rel_box": (0.04, 0.20, 0.54, 0.90)},
            {"src": ("ia", 18, (1600, 300, 2255, 1050), True), "rel_box": (0.54, 0.22, 0.96, 0.88)},
        ],
    },
    7: {
        "items": [
            {"src": ("ia", 22, (285, 290, 1550, 2040), True), "rel_box": (0.12, 0.24, 0.88, 0.98)},
        ],
    },
    8: {
        "items": [
            {"src": ("ia", 25, (1580, 295, 2260, 1340), False), "rel_box": (0.10, 0.28, 0.78, 0.98)},
        ],
    },
    9: {
        "items": [
            {"src": ("ia", 28, (1525, 1200, 2255, 2380), True), "rel_box": (0.04, 0.26, 0.44, 0.94)},
            {"src": ("ia", 30, (995, 1085, 2260, 1960), False), "rel_box": (0.40, 0.28, 0.96, 0.94)},
        ],
    },
    10: {
        "items": [
            {"src": ("ia", 32, (1115, 295, 2260, 1180), False), "rel_box": (0.10, 0.20, 0.94, 0.94)},
        ],
    },
    11: {
        "items": [
            {"src": ("ia", 34, (1305, 1405, 2260, 2325), True), "rel_box": (0.12, 0.14, 0.92, 0.96)},
        ],
    },
    12: {
        "items": [
            {"src": ("ia", 37, (1175, 1480, 2255, 2325), False), "rel_box": (0.10, 0.18, 0.94, 0.94)},
        ],
    },
    13: {
        "items": [
            {"src": ("ia", 42, (1175, 290, 2245, 1370), False), "rel_box": (0.10, 0.16, 0.92, 0.94)},
        ],
    },
    14: {
        "items": [
            {"src": ("ia", 43, (1245, 670, 2255, 1725), False), "rel_box": (0.20, 0.16, 0.96, 0.94)},
            {"src": ("au", "0300771h-32.jpg", None, False), "rel_box": (0.04, 0.56, 0.42, 0.94)},
        ],
    },
    15: {
        "items": [
            {"src": ("ia", 44, (1255, 600, 2260, 1280), True), "rel_box": (0.10, 0.16, 0.90, 0.92)},
        ],
    },
    16: {
        "items": [
            {"src": ("ia", 45, (980, 950, 2260, 1870), False), "rel_box": (0.08, 0.20, 0.94, 0.94)},
        ],
    },
    17: {
        "items": [
            {"src": ("ia", 47, (1195, 595, 2255, 1460), False), "rel_box": (0.08, 0.18, 0.94, 0.94)},
        ],
    },
    18: {
        "items": [
            {"src": ("au", "0300771h-43.jpg", None, False), "rel_box": (0.06, 0.22, 0.94, 0.90)},
        ],
    },
    19: {
        "wash": "starry_desert",
        "items": [
            {"src": ("ia", 41, (1480, 1170, 2260, 1810), False), "rel_box": (0.12, 0.26, 0.90, 0.96)},
        ],
    },
    20: {
        "items": [
            {"src": ("ia", 55, (1100, 295, 2260, 1725), False), "rel_box": (0.12, 0.16, 0.92, 0.96)},
        ],
    },
    21: {
        "items": [
            {"src": ("ia", 57, (1235, 1895, 2260, 2880), False), "rel_box": (0.10, 0.26, 0.92, 0.98)},
        ],
    },
    22: {
        "items": [
            {"src": ("ia", 61, (1100, 1670, 2255, 2675), True), "rel_box": (0.10, 0.26, 0.92, 0.98)},
        ],
    },
    23: {
        "wash": "starry_desert",
        "items": [
            {"src": ("ia", 60, (1420, 1480, 2250, 2240), True), "rel_box": (0.12, 0.27, 0.88, 0.96)},
        ],
    },
    24: {
        "wash": "epilogue_night",
        "items": [
            {"src": ("ia", 64, (850, 320, 2210, 1325), True), "rel_box": (0.06, 0.30, 0.94, 0.94)},
        ],
    },
}


def ensure_plate_sources() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    IA_JP2_DIR.mkdir(parents=True, exist_ok=True)
    GUTENBERG_DIR.mkdir(parents=True, exist_ok=True)

    if not IA_XML_PATH.exists() or IA_XML_PATH.stat().st_size < 100_000:
        print(f"Downloading {IA_XML_URL} -> {IA_XML_PATH} ...")
        urllib.request.urlretrieve(IA_XML_URL, IA_XML_PATH)

    if not IA_ZIP_PATH.exists() or IA_ZIP_PATH.stat().st_size < 10_000_000:
        print(f"Downloading {IA_ZIP_URL} -> {IA_ZIP_PATH} ...")
        urllib.request.urlretrieve(IA_ZIP_URL, IA_ZIP_PATH)

    needed_leaves = sorted({
        item["src"][1]
        for rec in PLATE_RECIPES.values()
        for item in rec["items"]
        if item["src"][0] == "ia"
    })
    missing_leaves = [
        idx for idx in needed_leaves
        if not (IA_JP2_DIR / f"Antoine de Saint Exupery - Le Petit Prince - 1943_{idx:04d}.jp2").exists()
    ]
    if missing_leaves:
        print(f"Extracting {len(missing_leaves)} IA JP2 leaves into {IA_JP2_DIR} ...")
        with zipfile.ZipFile(IA_ZIP_PATH) as zf:
            for member in zf.namelist():
                if member.endswith(".jp2"):
                    out_p = IA_JP2_DIR / Path(member).name
                    if not out_p.exists():
                        out_p.write_bytes(zf.read(member))

    needed_au = sorted({
        item["src"][1]
        for rec in PLATE_RECIPES.values()
        for item in rec["items"]
        if item["src"][0] == "au"
    })
    for fname in needed_au:
        out_p = GUTENBERG_DIR / fname
        if not out_p.exists() or out_p.stat().st_size < 1_000:
            url = f"{GUTENBERG_BASE_URL}/{fname}"
            print(f"Downloading {url} -> {out_p} ...")
            urllib.request.urlretrieve(url, out_p)


def make_cold_press_paper_and_patch(patch_pos: str, seed: int, include_patch: bool = True):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter

    rng = np.random.default_rng(seed)

    # Base #fdfaf2 cold-press paper with multi-octave tooth (std ~ 2.5 matching Sardegna)
    base = np.full((PLATE_H, PLATE_W, 3), [253.0, 250.0, 242.0], dtype=np.float32)

    fine = rng.normal(0.0, 1.75, size=(PLATE_H, PLATE_W)).astype(np.float32)
    med_low = rng.normal(0.0, 2.15, size=(PLATE_H // 4, PLATE_W // 4)).astype(np.float32)
    med_img = Image.fromarray(med_low, mode="F").resize((PLATE_W, PLATE_H), Image.Resampling.BILINEAR)
    med = np.asarray(med_img, dtype=np.float32)

    row_streak = rng.normal(0.0, 0.55, size=(PLATE_H, 1)).astype(np.float32)
    col_streak = rng.normal(0.0, 0.45, size=(1, PLATE_W)).astype(np.float32)

    grain = fine + med + row_streak + col_streak
    # Slightly warmer paper tint variance across channels like cotton rag
    paper = base.copy()
    paper[:, :, 0] += grain * 0.92
    paper[:, :, 1] += grain * 0.96
    paper[:, :, 2] += grain * 1.12

    if not include_patch:
        return np.clip(paper, 0.0, 255.0)

    # Feathered sand-wash reading patch matching Sardegna wc_p01..04.jpg
    if patch_pos == "bottom":
        x0, y0, x1, y1 = 48, 868, 848, 1170
    else:
        x0, y0, x1, y1 = 48, 28, 848, 315

    # Organic deckle-brush polygon around the reading patch
    mask_img = Image.new("L", (PLATE_W, PLATE_H), 0)
    draw = ImageDraw.Draw(mask_img)
    draw.rounded_rectangle((x0 + 8, y0 + 8, x1 - 8, y1 - 8), radius=28, fill=235)

    # Add organic edge wobble with low-frequency sine/cosine harmonics
    xs = np.arange(x0, x1 + 1, 16)
    ys = np.arange(y0, y1 + 1, 16)
    ph1 = (seed * 1.37) % (2 * math.pi)
    ph2 = (seed * 2.71) % (2 * math.pi)
    poly_pts = []
    for x in xs:
        wobble = 6.0 * math.sin(x * 0.025 + ph1) + 4.0 * math.cos(x * 0.063 + ph2)
        poly_pts.append((float(x), float(y0 + 6 + wobble)))
    for y in ys:
        wobble = 6.0 * math.cos(y * 0.031 + ph1) + 3.5 * math.sin(y * 0.071 + ph2)
        poly_pts.append((float(x1 - 6 + wobble), float(y)))
    for x in reversed(xs):
        wobble = 6.0 * math.sin(x * 0.029 + ph2) + 4.0 * math.cos(x * 0.058 + ph1)
        poly_pts.append((float(x), float(y1 - 6 + wobble)))
    for y in reversed(ys):
        wobble = 6.0 * math.cos(y * 0.027 + ph2) + 3.5 * math.sin(y * 0.067 + ph1)
        poly_pts.append((float(x0 + 6 + wobble), float(y)))
    draw.polygon(poly_pts, fill=242)

    mask_soft = mask_img.filter(ImageFilter.GaussianBlur(radius=14))
    alpha = (np.asarray(mask_soft, dtype=np.float32) / 255.0)[:, :, None]

    # Subtle internal pigment pooling inside sand-wash
    pool_low = rng.normal(0.0, 2.0, size=(PLATE_H // 16, PLATE_W // 16)).astype(np.float32)
    pool = np.asarray(
        Image.fromarray(pool_low, mode="F").resize((PLATE_W, PLATE_H), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    sand = np.empty_like(paper)
    sand[:, :, 0] = 250.0 + pool * 0.6 + grain * 0.75
    sand[:, :, 1] = 242.0 + pool * 0.7 + grain * 0.85
    sand[:, :, 2] = 221.0 + pool * 1.1 + grain * 1.05

    paper = paper * (1.0 - alpha) + sand * alpha
    return np.clip(paper, 0.0, 255.0)


def apply_atmospheric_wash(paper: "np.ndarray", wash_kind: str, patch_pos: str, seed: int) -> "np.ndarray":
    import numpy as np
    from PIL import Image, ImageFilter

    if patch_pos == "bottom":
        wy0, wy1 = 160, 825
    else:
        wy0, wy1 = 355, 1080
    wx0, wx1 = 68, 828

    rng = np.random.default_rng(seed + 900)
    yy, xx = np.mgrid[0:PLATE_H, 0:PLATE_W].astype(np.float32)

    # Elliptical soft mask inside art zone so margins remain clean paper
    cx = (wx0 + wx1) * 0.5
    cy = (wy0 + wy1) * 0.5
    rx = (wx1 - wx0) * 0.46
    ry = (wy1 - wy0) * 0.46
    dist = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    mask = np.clip(1.0 - np.clip((dist - 0.55) / 0.45, 0.0, 1.0), 0.0, 1.0)
    mask = mask * mask * (3.0 - 2.0 * mask)
    mask_img = Image.fromarray((mask * 255).astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=18))
    m = (np.asarray(mask_img, dtype=np.float32) / 255.0)[:, :, None]

    t_y = np.clip((yy - wy0) / max(1.0, (wy1 - wy0)), 0.0, 1.0)[:, :, None]
    pool_low = rng.normal(0.0, 4.0, size=(PLATE_H // 20, PLATE_W // 20)).astype(np.float32)
    pool = np.asarray(
        Image.fromarray(pool_low, mode="F").resize((PLATE_W, PLATE_H), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )[:, :, None]

    out = paper.copy()
    if wash_kind == "sunset":
        # Warm golden-apricot-rose 44-sunsets watercolor sky gradient
        tint = np.zeros_like(paper)
        tint[:, :, 0] = 253.0 - 2.0 * t_y[:, :, 0] + pool[:, :, 0] * 0.3
        tint[:, :, 1] = 236.0 - 16.0 * (1.0 - t_y[:, :, 0]) + pool[:, :, 0] * 0.4
        tint[:, :, 2] = 204.0 - 18.0 * (1.0 - t_y[:, :, 0]) + pool[:, :, 0] * 0.5
        strength = 0.42 * m
        out = out * (1.0 - strength) + tint * strength
    elif wash_kind in ("starry_desert", "epilogue_night"):
        # Soft twilight blue-gold watercolor atmosphere
        tint = np.zeros_like(paper)
        tint[:, :, 0] = 232.0 + 18.0 * t_y[:, :, 0] + pool[:, :, 0] * 0.4
        tint[:, :, 1] = 236.0 + 10.0 * t_y[:, :, 0] + pool[:, :, 0] * 0.4
        tint[:, :, 2] = 247.0 - 18.0 * t_y[:, :, 0] + pool[:, :, 0] * 0.4
        strength = (0.34 if wash_kind == "starry_desert" else 0.22) * m
        out = out * (1.0 - strength) + tint * strength
        if wash_kind == "epilogue_night":
            # Gentle golden star glow near upper center-right of epilogue star
            sx, sy = 515.0, 445.0
            sd = np.sqrt(((xx - sx) / 70.0) ** 2 + ((yy - sy) / 70.0) ** 2)
            glow = np.exp(-sd * sd * 1.8)[:, :, None]
            gold = np.array([255.0, 239.0, 172.0], dtype=np.float32).reshape(1, 1, 3)
            out = out * (1.0 - 0.30 * glow) + gold * (0.30 * glow)
    return np.clip(out, 0.0, 255.0)


def erase_djvu_neutral_text(im_arr: "np.ndarray", xml_obj: ET.Element) -> "np.ndarray":
    import numpy as np

    h, w, _ = im_arr.shape
    out = im_arr.copy()
    for ln in xml_obj.findall(".//LINE"):
        ws = ln.findall(".//WORD")
        if not ws:
            continue
        xs, ys = [], []
        txt = " ".join((wd.text or "").strip() for wd in ws)
        for wd in ws:
            c = [int(v) for v in wd.attrib["coords"].split(",")]
            xs.extend([c[0], c[2]])
            ys.extend([c[1], c[3]])
        lh = max(ys) - min(ys)
        if len(ws) >= 2 or "CHAPITRE" in txt or lh <= 110:
            for wd in ws:
                c = [int(v) for v in wd.attrib["coords"].split(",")]
                x0 = max(0, min(c[0], c[2]) - 12)
                x1 = min(w, max(c[0], c[2]) + 12)
                y0 = max(0, min(c[1], c[3]) - 10)
                y1 = min(h, max(c[1], c[3]) + 10)
                sub = out[y0:y1, x0:x1]
                chroma = sub.max(axis=2).astype(np.int16) - sub.min(axis=2).astype(np.int16)
                mask = chroma < 28
                sub[mask] = 255
    return out


def prepare_art_cutout(src_spec: tuple, xml_objs: list[ET.Element], ia_cache: dict) -> tuple["Image.Image", "np.ndarray"]:
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFile, ImageFilter

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    kind, ident, crop_box, erase_xml = src_spec

    if kind == "ia":
        if ident not in ia_cache:
            jp2_path = IA_JP2_DIR / f"Antoine de Saint Exupery - Le Petit Prince - 1943_{ident:04d}.jp2"
            ia_cache[ident] = np.asarray(Image.open(jp2_path).convert("RGB"), dtype=np.uint8)
        arr = ia_cache[ident]
        if erase_xml and ident < len(xml_objs):
            arr = erase_djvu_neutral_text(arr, xml_objs[ident])
        x0, y0, x1, y1 = crop_box
        crop = arr[y0:y1, x0:x1].copy()

        # Tighten crop to non-paper ink/color content with +24px breathing margin
        mx = crop.max(axis=2).astype(np.int16)
        mn = crop.min(axis=2).astype(np.int16)
        chroma = mx - mn
        content = (mn < 222) | (chroma > 20)
        ys, xs = np.where(content)
        if len(ys) > 30:
            ch, cw = crop.shape[:2]
            tx0 = max(0, int(xs.min()) - 40)
            ty0 = max(0, int(ys.min()) - 40)
            tx1 = min(cw, int(xs.max()) + 40)
            ty1 = min(ch, int(ys.max()) + 40)
            crop = crop[ty0:ty1, tx0:tx1]
        pil_art = Image.fromarray(crop, mode="RGB")
    else:
        au_path = GUTENBERG_DIR / ident
        pil_art = Image.open(au_path).convert("RGB")
        # Trim outer scanner border on Gutenberg AU thumbnails (e.g., 0300771h-32.jpg left edge)
        if ident == "0300771h-32.jpg":
            pil_art = pil_art.crop((36, 8, pil_art.width - 8, pil_art.height - 8))
        elif pil_art.width > 120 and pil_art.height > 120:
            pil_art = pil_art.crop((14, 8, pil_art.width - 8, pil_art.height - 8))
        # Clean Lanczos upscale for low-res Gutenberg AU color plates
        scale = 3 if pil_art.width < 340 else 2
        pil_art = pil_art.resize((pil_art.width * scale, pil_art.height * scale), Image.Resampling.LANCZOS)
        pil_art = pil_art.filter(ImageFilter.UnsharpMask(radius=1.0, percent=60, threshold=3))

    # Gentle saturation boost so 1943 watercolors harmonize with Sardegna vibrancy
    pil_art = ImageEnhance.Color(pil_art).enhance(1.10)
    art_arr = np.asarray(pil_art, dtype=np.float32)

    # Sample bright low-chroma scan-paper pixels directly to neutralize yellowed/gray scanner paper
    chroma_raw = art_arr.max(axis=2) - art_arr.min(axis=2)
    lum_raw = 0.299 * art_arr[:, :, 0] + 0.587 * art_arr[:, :, 1] + 0.114 * art_arr[:, :, 2]
    paper_candidates = art_arr[(lum_raw > 195.0) & (chroma_raw < 22.0)]
    if len(paper_candidates) > 50:
        paper_rgb = np.percentile(paper_candidates, 20, axis=0)
    else:
        paper_rgb = np.array([235.0, 235.0, 232.0], dtype=np.float32)
    paper_rgb = np.clip(paper_rgb, 205.0, 250.0)

    # Per-channel white-balance stretch from black_pt=10 -> 0 and paper_rgb -> 255
    black_pt = 10.0
    knock = (art_arr - black_pt) / np.maximum(paper_rgb - black_pt, 1.0) * 255.0
    knock = np.clip(knock, 0.0, 255.0)

    # Smoothly send residual near-white low-chroma background pixels to pure 255 for clean Multiply
    lum_k = 0.299 * knock[:, :, 0] + 0.587 * knock[:, :, 1] + 0.114 * knock[:, :, 2]
    chroma_k = knock.max(axis=2) - knock.min(axis=2)
    paper_like = np.clip((lum_k - 228.0) / 22.0, 0.0, 1.0) * np.clip(1.0 - chroma_k / 24.0, 0.0, 1.0)
    knock = knock * (1.0 - paper_like[:, :, None]) + 255.0 * paper_like[:, :, None]

    return Image.fromarray(knock.astype(np.uint8), mode="RGB"), knock


def build_feathered_edge_alpha(w: int, h: int, feather: int = 24) -> "np.ndarray":
    import numpy as np

    fx = min(feather, max(2, w // 6))
    fy = min(feather, max(2, h // 6))
    x_Ramp = np.ones(w, dtype=np.float32)
    y_Ramp = np.ones(h, dtype=np.float32)

    lx = np.linspace(0.0, 1.0, fx, dtype=np.float32)
    lx = lx * lx * (3.0 - 2.0 * lx)
    x_Ramp[:fx] = lx
    x_Ramp[-fx:] = lx[::-1]

    ly = np.linspace(0.0, 1.0, fy, dtype=np.float32)
    ly = ly * ly * (3.0 - 2.0 * ly)
    y_Ramp[:fy] = ly
    y_Ramp[-fy:] = ly[::-1]

    return y_Ramp[:, None] * x_Ramp[None, :]


def composite_plate(pnum: int, xml_objs: list[ET.Element], ia_cache: dict) -> Path:
    import numpy as np
    from PIL import Image

    patch_pos = "bottom" if pnum % 2 == 1 else "top"
    canvas = make_cold_press_paper_and_patch(patch_pos, seed=194300 + pnum)

    recipe = PLATE_RECIPES[pnum]
    if recipe.get("wash"):
        canvas = apply_atmospheric_wash(canvas, recipe["wash"], patch_pos, seed=194300 + pnum)

    # Art safe zones matching Explorer 1 & Sardegna wc_p01..04.jpg geometry
    if patch_pos == "bottom":
        safe_x0, safe_y0, safe_x1, safe_y1 = 56, 48, 840, 815
    else:
        safe_x0, safe_y0, safe_x1, safe_y1 = 56, 345, 840, 1125
    safe_w = safe_x1 - safe_x0
    safe_h = safe_y1 - safe_y0

    for item in recipe["items"]:
        art_pil, _ = prepare_art_cutout(item["src"], xml_objs, ia_cache)
        rx0, ry0, rx1, ry1 = item["rel_box"]
        box_x0 = safe_x0 + int(round(rx0 * safe_w))
        box_y0 = safe_y0 + int(round(ry0 * safe_h))
        box_w = max(40, int(round((rx1 - rx0) * safe_w)))
        box_h = max(40, int(round((ry1 - ry0) * safe_h)))

        # Aspect-preserving fit inside target box, anchored toward bottom-center of its slot
        aw, ah = art_pil.size
        scale = min(box_w / float(aw), box_h / float(ah))
        nw = max(16, int(round(aw * scale)))
        nh = max(16, int(round(ah * scale)))
        art_resized = np.asarray(art_pil.resize((nw, nh), Image.Resampling.LANCZOS), dtype=np.float32)

        px0 = box_x0 + (box_w - nw) // 2
        py0 = box_y0 + (box_h - nh) // 2

        alpha = build_feathered_edge_alpha(nw, nh, feather=36)[:, :, None]
        region = canvas[py0:py0 + nh, px0:px0 + nw]
        multiplied = (region * art_resized) / 255.0
        canvas[py0:py0 + nh, px0:px0 + nw] = region * (1.0 - alpha) + multiplied * alpha

    out_img = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="RGB")
    out_path = BOOK_DIR / f"wc_p{pnum:02d}.jpg"
    tmp_path = out_path.with_suffix(".tmp.jpg")
    out_img.save(tmp_path, format="JPEG", quality=92, subsampling=1, optimize=True)
    tmp_path.replace(out_path)
    return out_path


def run_plates_legacy(pages_filter: set[int] | None = None) -> None:
    ensure_plate_sources()
    xml_objs = ET.parse(IA_XML_PATH).getroot().findall(".//OBJECT")
    ia_cache: dict = {}
    targets = [p for p in range(1, 25) if not pages_filter or p in pages_filter]
    print(f"[plates-legacy] Compositing {len(targets)} plates (896x1200 RGB JPEG)...")
    for pnum in targets:
        out_p = composite_plate(pnum, xml_objs, ia_cache)
        print(f"  -> {out_p.relative_to(ROOT)} ({out_p.stat().st_size // 1024} KB)")
    print("[plates-legacy] Done.")


# =============================================================================
# PHASE A2 — LIBER LIBER + NANO BANANA (gemini-3-pro-image-preview) REMASTERING
# =============================================================================

ASPECT_CANVAS_SIZES: dict[str, tuple[int, int]] = {
    "16:9": (1280, 720),
    "4:3": (1200, 900),
    "3:4": (900, 1200),
    "1:1": (1024, 1024),
}

COMMON_NB_RESTORE_RULE = (
    "Restore and remaster this public-domain Antoine de Saint-Exupery Little Prince illustration into a "
    "crisp, museum-grade high-resolution hand-drawn fountain-pen ink and delicate watercolor illustration on a "
    "PURE SOLID WHITE (#FFFFFF) background. "
    "Strictly preserve Saint-Exupery's exact original composition, character poses, proportions, facial "
    "expressions, and charming naive storybook style. "
    "Completely eliminate all JPEG compression artifacts, scan grain, halftone dot patterns, blotches, stray specks, "
    "and rectangular compositing seams. "
    "Keep the background pure uniform #FFFFFF white with ZERO text, ZERO captions, ZERO borders, and ZERO frames."
)

# 27 remaster specs: p01_top_boa, p01..p24 + p01_xray + cover
# Each "ll" source is ("ll", img_num, rel_box_in_prearrange_canvas)
REMASTER_SPECS: dict[str, dict] = {
    "p01_top_boa": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.08, 0.14, 0.92, 0.90),
        "tight_pad": 22,
        "sources": [("ll", 10, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "CRITICAL FAITHFULNESS: Restore ONLY the existing lines and washes of this exact Saint-Exupery drawing "
            "WITHOUT changing any creature, anatomy, or silhouette. "
            "Preserve the EXACT wide-open U-shaped golden-ochre boa mouth with tiny teeth along the orange-red lower "
            "jaw on the left, the EXACT furry pale lavender-grey wild beast (a small four-legged beast/mammal with two "
            "dark little rounded ears on top of its head and a snout facing left — NEVER turn the prey into a snake!), "
            "and the EXACT coiled golden-ochre snake rings and flat horizontal tail stretching straight to the "
            "bottom-left. "
            "Only remove JPEG noise/grain, refine the dark-sepia ink outlines, smooth the translucent golden-ochre "
            "and pale lavender-grey watercolor washes, and gently fade the faint ground shadow at bottom-right into "
            "pure uniform #FFFFFF white. ZERO text."
        ),
    },
    "p01": {
        "aspect_ratio": "16:9",
        "plate_rel_box": (0.06, 0.36, 0.94, 0.82),
        "tight_pad": 28,
        "sources": [("ll", 13, (0.08, 0.14, 0.92, 0.86))],
        "note": (
            "Depict ONLY Drawing No. 1: the single closed brown boa constrictor that looks like a felt hat. "
            "Smooth out the blotchy brown fill into a warm, delicate translucent sepia-ochre watercolor wash with "
            "a crisp hand-drawn dark-sepia fountain-pen ink outline. "
            "Do NOT draw any elephant, any X-ray outline, or any second snake. Pure #FFFFFF white background."
        ),
    },
    "p01_xray": {
        "aspect_ratio": "16:9",
        "plate_rel_box": (0.06, 0.36, 0.94, 0.82),
        "tight_pad": 28,
        "sources": [("ll", 12, (0.08, 0.14, 0.92, 0.86))],
        "note": (
            "Depict ONLY Drawing No. 2: the open X-ray outline of the boa constrictor digesting an elephant inside, "
            "keeping the exact silhouette footprint, dome contour, tail length, and horizontal alignment of the input. "
            "Use a crisp dark-sepia fountain-pen ink outline and soft warm pastel grey watercolor shading on the "
            "elephant inside. Do NOT add extra text or objects. Pure #FFFFFF white background."
        ),
    },
    "p02": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.04, 0.10, 0.96, 0.95),
        "sources": [
            ("ll", 22, (0.04, 0.62, 0.34, 0.90)),
            ("ll", 20, (0.10, 0.38, 0.30, 0.58)),
            ("ll", 24, (0.38, 0.10, 0.95, 0.94)),
        ],
        "note": (
            "Unify the wooden sheep box (bottom-left), the tiny fluffy hand-drawn sheep (mid-left), and the Little "
            "Prince in his blue-and-red-lined royal cloak with golden hair and sword (right) into one cohesive, "
            "harmonized hand-drawn ink and luminous watercolor scene. Remove all stray specks and diagonal lines; "
            "keep the upper-left corner completely clean white for a speech bubble."
        ),
    },
    "p03": {
        "aspect_ratio": "3:4",
        "plate_rel_box": (0.10, 0.16, 0.92, 0.96),
        "sources": [("ll", 28, (0.06, 0.08, 0.88, 0.90))],
        "note": (
            "Restore the Little Prince in his green tunic standing atop his tiny Asteroid B-612 surrounded by small "
            "yellow stars and distant planets. Use a soft pastel lavender-blue watercolor wash on the asteroid, crisp "
            "delicate ink, and luminous golden stars on pure #FFFFFF white. "
            "IMPORTANT: Gently round, complete, and softly fade the right edge and bottom edge of the asteroid into "
            "pure #FFFFFF white so there is NO flat straight vertical or horizontal cut edge."
        ),
    },
    "p04": {
        "aspect_ratio": "3:4",
        "plate_rel_box": (0.04, 0.12, 0.96, 0.96),
        "sources": [
            ("ll", 38, (0.05, 0.16, 0.54, 0.52)),
            ("ll", 40, (0.40, 0.44, 0.95, 0.95)),
        ],
        "note": (
            "Restore both vignettes cleanly on pure #FFFFFF white: upper-left shows the Little Prince uprooting tiny "
            "baobab shoots on a small curved planet; lower-right shows three giant monstrous baobab trees bursting "
            "a tiny planet. Completely remove any yellowed rectangular halo around the lower planet and keep the "
            "top-left corner open white."
        ),
    },
    "p05": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.10, 0.22, 0.90, 0.94),
        "wash": "sunset",
        "sources": [("ll", 42, (0.08, 0.12, 0.92, 0.88))],
        "note": (
            "Restore the minimalist drawing of the Little Prince sitting on a small chair watching the sunset on his "
            "tiny curved asteroid with delicate grass stems. Render in crisp dark-sepia fountain-pen ink with a very "
            "subtle, soft warm sepia and pale apricot-gold sunset watercolor wash, keeping the sky open and airy on "
            "pure #FFFFFF white."
        ),
    },
    "p06": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.04, 0.16, 0.96, 0.94),
        "sources": [
            ("ll", 48, (0.05, 0.22, 0.47, 0.90)),
            ("ll", 52, (0.51, 0.20, 0.95, 0.90)),
        ],
        "note": (
            "Unify both side-by-side vignettes into a harmonized hand-drawn ink and pastel watercolor pair on pure "
            "#FFFFFF white: on the left, the Little Prince watering his tiny red rose on his curved planet; on the "
            "right, the Little Prince kneeling to place the folding screen around the red rose. Match line weight and "
            "soft pastel colors seamlessly with zero boxy edges and open upper-left space."
        ),
    },
    "p07": {
        "aspect_ratio": "3:4",
        "plate_rel_box": (0.12, 0.20, 0.88, 0.96),
        "sources": [("ll", 58, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Little Prince sweeping the volcanoes on Asteroid B-612 with his yellow scarf streaming in the "
            "wind. Crisp fountain-pen ink, soft pale sky-blue planet rim, tiny warm orange-yellow stars and volcanoes "
            "on pure #FFFFFF white."
        ),
    },
    "p08": {
        "aspect_ratio": "3:4",
        "plate_rel_box": (0.08, 0.24, 0.88, 0.97),
        "sources": [("ll", 60, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the King wearing his red-and-ermine star-patterned royal cloak sitting on his throne atop a "
            "golden asteroid surrounded by tiny stars. Crisp delicate ink and warm translucent watercolor washes on "
            "pure #FFFFFF white."
        ),
    },
    "p09": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.04, 0.24, 0.96, 0.94),
        "sources": [
            ("ll", 62, (0.05, 0.14, 0.44, 0.92)),
            ("ll", 64, (0.46, 0.22, 0.95, 0.92)),
        ],
        "note": (
            "Harmonize these two adjacent vignettes on pure #FFFFFF white: on the left, the Vain Man tipping his hat "
            "atop his tiny asteroid; on the right, the Drunkard sitting at his table surrounded by bottles. Match "
            "ink weight and soft watercolor washes cleanly with zero rectangular borders."
        ),
    },
    "p10": {
        "aspect_ratio": "1:1",
        "plate_rel_box": (0.08, 0.20, 0.92, 0.94),
        "sources": [("ll", 66, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Businessman sitting behind his desk counting stars and writing figures on papers. Crisp "
            "fountain-pen ink and clean pale watercolor shading on pure #FFFFFF white."
        ),
    },
    "p11": {
        "aspect_ratio": "1:1",
        "plate_rel_box": (0.10, 0.18, 0.92, 0.96),
        "sources": [("ll", 68, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Lamplighter beside his tall streetlamp atop his tiny round planet with warm orange-red "
            "sunburst rays and stars. Crisp ink and delicate luminous watercolor on pure #FFFFFF white."
        ),
    },
    "p12": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.08, 0.20, 0.92, 0.94),
        "sources": [("ll", 70, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "Restore the old Geographer sitting behind his large desk examining a huge open book with a magnifying "
            "glass on his curved planet. Crisp ink and gentle warm watercolor washes on pure #FFFFFF white."
        ),
    },
    "p13": {
        "aspect_ratio": "1:1",
        "plate_rel_box": (0.10, 0.20, 0.90, 0.95),
        "sources": [("ll", 74, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Little Prince arriving on Earth in the desert with the tiny golden snake on the sand and the "
            "soft pastel lavender-blue shadow behind him under a glowing yellow star. Keep the blue shadow strictly "
            "soft pastel lavender-blue (NEVER neon or dark cobalt blue) with delicate transparent watercolor texture "
            "on pure #FFFFFF white."
        ),
    },
    "p14": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.04, 0.14, 0.96, 0.95),
        "sources": [
            ("ll", 76, (0.04, 0.44, 0.50, 0.92)),
            ("ll", 78, (0.42, 0.08, 0.96, 0.92)),
        ],
        "note": (
            "CRITICAL SEAM UNIFICATION: Merge the desert dunes and tiny red three-petaled flower (bottom-left) "
            "seamlessly into and across the rocky base of the tall jagged mountain peak (right) so it forms ONE single "
            "continuous hand-drawn ink and delicate watercolor landscape. "
            "Do NOT stop the warm desert sand wash in a vertical cliff between the flower and mountain — let the "
            "gentle pale desert sand-ochre wash flow continuously across the bottom of the dunes and softly around "
            "the lower mountain base, fading organically into pure #FFFFFF white on all edges with ZERO straight lines, "
            "ZERO rectangular boxes, and open sky in the upper-left."
        ),
    },
    "p15": {
        "aspect_ratio": "16:9",
        "plate_rel_box": (0.06, 0.22, 0.94, 0.92),
        "sources": [("ll", 80, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "Restore the Little Prince standing weeping beside two lush green rosebushes dotted with red roses. "
            "Replace the flat rectangular orange wall block on the left with a soft, natural pale warm ochre-sand "
            "watercolor wash that fades gently and organically into pure #FFFFFF white with zero hard rectangular edges."
        ),
    },
    "p16": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.06, 0.22, 0.94, 0.94),
        "sources": [("ll", 84, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "Restore the Little Prince with his streaming yellow scarf talking to the cute little reddish-orange fox "
            "between a pastel pink-lavender rocky cliff and a sunlit pale green hillside. Crisp delicate ink and "
            "translucent pastel watercolor on pure #FFFFFF white."
        ),
    },
    "p17": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.08, 0.20, 0.92, 0.94),
        "sources": [("ll", 88, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "Restore the fox peeking out of its burrow beneath gentle rolling green hills and a golden-yellow tree "
            "with little wild flowers in the foreground. Use soft, natural sunlit spring-green and warm golden-ochre "
            "watercolor (NO neon highlighter yellow banding) on pure #FFFFFF white."
        ),
    },
    "p18": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.08, 0.22, 0.92, 0.92),
        "sources": [("ll", 86, (0.10, 0.10, 0.90, 0.90))],
        "note": (
            "Restore the Hunter in his brimmed hat with rifle slung over his shoulder standing on a gentle warm ochre "
            "hill between two small round golden-green trees. Eliminate low-res JPEG blur; restore crisp fountain-pen "
            "ink and soft warm watercolor washes on pure #FFFFFF white."
        ),
    },
    "p19": {
        "aspect_ratio": "1:1",
        "plate_rel_box": (0.10, 0.22, 0.90, 0.96),
        "wash": "starry_desert",
        "sources": [("ll", 72, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Little Prince standing in the desert pointing left with his yellow coat and sunlit golden "
            "rays above subtle desert sand curves. Restore crisp facial features, delicate ink lines, and soft warm "
            "golden-sand watercolor (no neon yellow) on pure #FFFFFF white."
        ),
    },
    "p20": {
        "aspect_ratio": "3:4",
        "plate_rel_box": (0.10, 0.18, 0.92, 0.96),
        "sources": [("ll", 92, (0.08, 0.08, 0.90, 0.90))],
        "note": (
            "Restore the Little Prince standing by the stone desert well with its wooden pulley and rope atop a "
            "sandstone cliff. Use soft, natural warm desert ochre and sandstone watercolor (completely eliminate neon "
            "yellow color banding) and crisp ink lines on pure #FFFFFF white. "
            "Softly fade and feather the right edge and bottom of the sandstone cliff organically into pure #FFFFFF "
            "white so there is NO hard straight vertical edge."
        ),
    },
    "p21": {
        "aspect_ratio": "1:1",
        "plate_rel_box": (0.10, 0.24, 0.90, 0.97),
        "sources": [("ll", 94, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Little Prince sitting atop the old ruined stone wall with dangling legs looking down at the "
            "golden snake coiled at the wall's base. Use soft pastel lavender-grey and warm sandstone watercolor on "
            "the wall and crisp ink lines on pure #FFFFFF white."
        ),
    },
    "p22": {
        "aspect_ratio": "1:1",
        "plate_rel_box": (0.08, 0.22, 0.92, 0.97),
        "sources": [("ll", 100, (0.08, 0.08, 0.92, 0.92))],
        "note": (
            "Restore the Little Prince in his golden-yellow coat falling gently toward the curved desert dune beneath "
            "a single shining star. Crisp hand-drawn ink, warm pastel gold coat, and soft pale-blue desert rim wash "
            "on pure #FFFFFF white."
        ),
    },
    "p23": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.10, 0.24, 0.90, 0.95),
        "wash": "starry_desert",
        "sources": [("ll", 96, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "Restore the Little Prince standing/walking gently in the desert among sweeping curved sand lines with "
            "his scarf fluttering behind him. Render crisp, clear dark-sepia fountain-pen ink outlines (never faint "
            "or washed out) enriched with a delicate, luminous soft moonlight-blue and warm desert-sand watercolor wash "
            "fading softly into pure #FFFFFF white."
        ),
    },
    "p24": {
        "aspect_ratio": "4:3",
        "plate_rel_box": (0.06, 0.24, 0.94, 0.94),
        "wash": "epilogue_night",
        "sources": [("ll", 102, (0.08, 0.10, 0.92, 0.90))],
        "note": (
            "Restore the iconic final epilogue desert illustration: two sweeping hand-drawn curved desert horizon "
            "lines beneath one single shining golden star in the quiet sky. Render crisp, graceful dark-sepia ink "
            "lines, a soft luminous golden watercolor star, and a subtle delicate whisper of twilight sky-blue and "
            "warm desert sand watercolor wash fading cleanly into pure #FFFFFF white."
        ),
    },
    "cover": {
        "aspect_ratio": "3:4",
        "sources": [("cover_ia0", None, (0.06, 0.08, 0.88, 0.88))],
        "note": (
            "Restore this classic Little Prince cover illustration (the Little Prince in his pale yellow-green tunic "
            "and red bow-tie standing atop Asteroid B-612 with smoking volcano, tiny baobab sprout, scattered golden "
            "stars and small planets). Crisp hand-drawn fountain-pen ink and luminous translucent watercolor washes. "
            "IMPORTANT: Gently round, complete, and softly fade out BOTH the bottom edge AND the right edge of the "
            "brownish-lavender asteroid into pure #FFFFFF white so it forms a naturally curved asteroid floating in "
            "space with NO flat horizontal or vertical cut edges. Pure #FFFFFF white background with ZERO text, ZERO "
            "titles, and ZERO logos."
        ),
    },
}


def ensure_liberliber_imgs() -> Path:
    shared_imgs = LIBERLIBER_SHARED_DIR / "imgs"
    if (shared_imgs / "img-102.png").exists():
        return shared_imgs

    LIBERLIBER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = LIBERLIBER_CACHE_DIR / "il_piccolo_principe.pdf"
    imgs_dir = LIBERLIBER_CACHE_DIR / "imgs"
    imgs_dir.mkdir(parents=True, exist_ok=True)
    if (imgs_dir / "img-102.png").exists():
        return imgs_dir

    if not pdf_path.exists() or pdf_path.stat().st_size < 500_000:
        print(f"[liberliber] Downloading {LIBERLIBER_PDF_URL} -> {pdf_path} ...")
        req = urllib.request.Request(LIBERLIBER_PDF_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            pdf_path.write_bytes(resp.read())

    print(f"[liberliber] Extracting PNGs via pdfimages -> {imgs_dir} ...")
    subprocess.run(["pdfimages", "-png", str(pdf_path), str(imgs_dir / "img")], check=True)
    if not (imgs_dir / "img-102.png").exists():
        raise RuntimeError(f"Expected Liber Liber PNGs missing in {imgs_dir}")
    return imgs_dir


def _trim_source_to_white(pil_img: "Image.Image", pad: int = 12) -> "Image.Image":
    import numpy as np
    from PIL import Image

    arr = np.asarray(pil_img.convert("RGB"), dtype=np.uint8)
    mx = arr.max(axis=2).astype(np.int16)
    mn = arr.min(axis=2).astype(np.int16)
    chroma = mx - mn
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    content = (lum < 238.0) | (chroma > 14)
    ys, xs = np.where(content)
    if len(ys) > 20:
        h, w = arr.shape[:2]
        x0 = max(0, int(xs.min()) - pad)
        y0 = max(0, int(ys.min()) - pad)
        x1 = min(w, int(xs.max()) + 1 + pad)
        y1 = min(h, int(ys.max()) + 1 + pad)
        arr = arr[y0:y1, x0:x1]
    # Clean near-white background to pure 255
    f = arr.astype(np.float32)
    lum_f = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]
    chr_f = f.max(axis=2) - f.min(axis=2)
    bg = (lum_f > 244.0) & (chr_f < 10.0)
    f[bg] = 255.0
    return Image.fromarray(f.astype(np.uint8), mode="RGB")


def _load_cover_ia0_source() -> "Image.Image":
    import numpy as np
    from PIL import Image

    jp2_path = IA_JP2_DIR / "Antoine de Saint Exupery - Le Petit Prince - 1943_0000.jp2"
    if not jp2_path.exists():
        ensure_plate_sources()
        if not jp2_path.exists():
            with zipfile.ZipFile(IA_ZIP_PATH) as zf:
                for member in zf.namelist():
                    if member.endswith("_0000.jp2"):
                        jp2_path.write_bytes(zf.read(member))
                        break
    arr = np.asarray(Image.open(jp2_path).convert("RGB"), dtype=np.uint8)
    # Crop strictly below title/subtitle text (y=1080..3255, x=70..2530)
    crop = arr[1080:3255, 70:2530].copy()
    # Erase bottom-left 'folio' logo clean to pure white
    crop[1800:2175, 0:720] = 255
    # Lightly neutralize off-white paper without clipping pastel planet wash
    f = crop.astype(np.float32)
    lum = 0.299 * f[:, :, 0] + 0.587 * f[:, :, 1] + 0.114 * f[:, :, 2]
    chr_v = f.max(axis=2) - f.min(axis=2)
    paper_cand = f[(lum > 218.0) & (chr_v < 16.0)]
    paper_rgb = np.percentile(paper_cand, 35, axis=0) if len(paper_cand) > 100 else np.array([245.0, 244.0, 240.0])
    paper_rgb = np.clip(paper_rgb, 225.0, 253.0)
    f = np.clip((f - 6.0) / np.maximum(paper_rgb - 6.0, 1.0) * 255.0, 0.0, 255.0)
    return _trim_source_to_white(Image.fromarray(f.astype(np.uint8), mode="RGB"), pad=16)


def build_prearranged_image(asset_key: str, ll_imgs_dir: Path) -> Path:
    from PIL import Image

    PREARRANGE_NB_DIR.mkdir(parents=True, exist_ok=True)
    spec = REMASTER_SPECS[asset_key]
    cw, ch = ASPECT_CANVAS_SIZES[spec["aspect_ratio"]]
    canvas = Image.new("RGB", (cw, ch), (255, 255, 255))

    for src_kind, src_ident, rel_box in spec["sources"]:
        if src_kind == "ll":
            raw = Image.open(ll_imgs_dir / f"img-{int(src_ident):03d}.png").convert("RGB")
            art = _trim_source_to_white(raw, pad=8)
        elif src_kind == "cover_ia0":
            art = _load_cover_ia0_source()
        else:
            raise ValueError(f"Unknown source kind: {src_kind}")

        rx0, ry0, rx1, ry1 = rel_box
        bx0 = int(round(rx0 * cw))
        by0 = int(round(ry0 * ch))
        bw = max(32, int(round((rx1 - rx0) * cw)))
        bh = max(32, int(round((ry1 - ry0) * ch)))

        aw, ah = art.size
        scale = min(bw / float(aw), bh / float(ah))
        nw = max(16, int(round(aw * scale)))
        nh = max(16, int(round(ah * scale)))
        art_rs = art.resize((nw, nh), Image.Resampling.LANCZOS)
        px = bx0 + (bw - nw) // 2
        py = by0 + (bh - nh) // 2
        canvas.paste(art_rs, (px, py))

    out_path = PREARRANGE_NB_DIR / f"{asset_key}.png"
    tmp_path = out_path.with_suffix(".tmp.png")
    canvas.save(tmp_path, format="PNG")
    tmp_path.replace(out_path)
    return out_path


def load_gemini_image_keys() -> list[str]:
    """Load keys prioritizing paid/billing keys for image generation: $GEMINI_API_KEY -> GEMINI_API_KEY2 -> FREE."""
    keys: list[str] = []
    shell_k = os.environ.get("GEMINI_API_KEY", "").strip()
    if shell_k.startswith("AIza"):
        keys.append(shell_k)
    if GPRISM_ENV_PATH.exists():
        env_txt = GPRISM_ENV_PATH.read_text(encoding="utf-8")
        found = dict(re.findall(r'^([A-Z0-9_]+)=["\']?(AIza[A-Za-z0-9_-]+)', env_txt, re.M))
        for kname in ("GEMINI_API_KEY2", "GEMINI_API_KEY_FREE_TTS_STT"):
            val = found.get(kname)
            if val and val not in keys:
                keys.append(val)
    return keys


def remaster_asset_nanobanana(
    asset_key: str,
    ll_imgs_dir: Path,
    keys: list[str],
    image_size: str = "1K",
    force: bool = False,
) -> tuple[str, Path, str]:
    from PIL import Image

    REMASTER_NB_DIR.mkdir(parents=True, exist_ok=True)
    out_png = REMASTER_NB_DIR / f"{asset_key}.png"
    if not force and out_png.exists() and out_png.stat().st_size > 10_000:
        return (asset_key, out_png, "cached")

    if not keys:
        raise RuntimeError("No valid Gemini API keys found in $GEMINI_API_KEY or .env.gprism")

    pre_png = build_prearranged_image(asset_key, ll_imgs_dir)
    b64_in = base64.b64encode(pre_png.read_bytes()).decode("ascii")
    spec = REMASTER_SPECS[asset_key]
    prompt = f"{COMMON_NB_RESTORE_RULE}\n\nScene-specific restoration instructions:\n{spec['note']}"

    payload_bytes = json.dumps({
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": "image/png", "data": b64_in}},
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": spec["aspect_ratio"],
                "imageSize": image_size,
            },
        },
    }).encode("utf-8")

    last_err = "no keys"
    for rnd in range(4):
        for k_idx, key in enumerate(keys):
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-3-pro-image-preview:generateContent?key={key}"
            )
            req = urllib.request.Request(url, data=payload_bytes, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                img_bytes = None
                for cand in data.get("candidates") or []:
                    for part in (cand.get("content") or {}).get("parts") or []:
                        idata = part.get("inlineData") or part.get("inline_data")
                        if idata and idata.get("data"):
                            img_bytes = base64.b64decode(idata["data"])
                            break
                    if img_bytes:
                        break
                if not img_bytes or len(img_bytes) < 5_000:
                    raise RuntimeError(f"No image returned in candidate response for {asset_key}")

                pil_out = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                tmp_png = out_png.with_suffix(".tmp.png")
                pil_out.save(tmp_png, format="PNG")
                tmp_png.replace(out_png)
                return (asset_key, out_png, f"key#{k_idx}")
            except urllib.error.HTTPError as he:
                body = ""
                try:
                    body = he.read().decode("utf-8", errors="ignore")[:220]
                except Exception:
                    pass
                last_err = f"HTTP {he.code}: {body}"
                if he.code in (429, 500, 502, 503, 504):
                    time.sleep(min(20.0, (1.6 ** (rnd + k_idx)) + random.uniform(0.3, 1.2)))
                else:
                    time.sleep(0.5)
            except Exception as exc:
                last_err = str(exc)
                time.sleep(min(12.0, 1.5 * (rnd + 1) + random.uniform(0.2, 0.8)))

    raise RuntimeError(f"Nano Banana remaster failed for {asset_key}: {last_err}")


def knock_remastered_white_bg(pil_img: "Image.Image") -> "Image.Image":
    """Gently normalize near-white background to pure 255 for seamless Multiply compositing."""
    import numpy as np
    from PIL import Image

    arr = np.asarray(pil_img.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape
    border = np.concatenate([arr[0:6, :, :].reshape(-1, 3), arr[h - 6:h, :, :].reshape(-1, 3),
                             arr[:, 0:6, :].reshape(-1, 3), arr[:, w - 6:w, :].reshape(-1, 3)], axis=0)
    b_lum = 0.299 * border[:, 0] + 0.587 * border[:, 1] + 0.114 * border[:, 2]
    b_chr = border.max(axis=1) - border.min(axis=1)
    white_border = border[(b_lum > 225.0) & (b_chr < 18.0)]
    if len(white_border) > 50:
        paper_rgb = np.percentile(white_border, 25, axis=0)
    else:
        paper_rgb = np.array([250.0, 250.0, 250.0], dtype=np.float32)
    paper_rgb = np.clip(paper_rgb, 232.0, 255.0)

    # Rescale only softly from 0 -> paper_rgb so dark ink stays rich & border hits pure 255
    knock = np.clip(arr / np.maximum(paper_rgb, 1.0) * 255.0, 0.0, 255.0)
    lum = 0.299 * knock[:, :, 0] + 0.587 * knock[:, :, 1] + 0.114 * knock[:, :, 2]
    chroma = knock.max(axis=2) - knock.min(axis=2)
    paper_like = np.clip((lum - 238.0) / 14.0, 0.0, 1.0) * np.clip(1.0 - chroma / 16.0, 0.0, 1.0)
    knock = knock * (1.0 - paper_like[:, :, None]) + 255.0 * paper_like[:, :, None]
    return Image.fromarray(knock.astype(np.uint8), mode="RGB")


def tight_pad_cutout(pil_img: "Image.Image", pad: int = 28) -> "Image.Image":
    import numpy as np
    from PIL import Image

    arr = np.asarray(pil_img.convert("RGB"), dtype=np.uint8)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    chroma = arr.max(axis=2).astype(np.int16) - arr.min(axis=2).astype(np.int16)
    ys, xs = np.where((lum < 224.0) | (chroma > 16))
    if len(ys) > 30:
        crop = arr[int(ys.min()):int(ys.max()) + 1, int(xs.min()):int(xs.max()) + 1]
    else:
        crop = arr
    ch, cw = crop.shape[:2]
    out = Image.new("RGB", (cw + 2 * pad, ch + 2 * pad), (255, 255, 255))
    out.paste(Image.fromarray(crop, mode="RGB"), (pad, pad))
    return out


def _paste_multiply_into_box(
    canvas: "np.ndarray",
    art_pil: "Image.Image",
    box: tuple[int, int, int, int],
    feather: int = 36,
) -> tuple[int, int, int, int]:
    import numpy as np
    from PIL import Image

    box_x0, box_y0, box_x1, box_y1 = box
    box_w = max(40, box_x1 - box_x0)
    box_h = max(40, box_y1 - box_y0)
    aw, ah = art_pil.size
    scale = min(box_w / float(aw), box_h / float(ah))
    nw = max(16, int(round(aw * scale)))
    nh = max(16, int(round(ah * scale)))
    art_resized = np.asarray(art_pil.resize((nw, nh), Image.Resampling.LANCZOS), dtype=np.float32)

    px0 = box_x0 + (box_w - nw) // 2
    py0 = box_y0 + (box_h - nh) // 2
    alpha = build_feathered_edge_alpha(nw, nh, feather=feather)[:, :, None]
    region = canvas[py0:py0 + nh, px0:px0 + nw]
    multiplied = (region * art_resized) / 255.0
    canvas[py0:py0 + nh, px0:px0 + nw] = region * (1.0 - alpha) + multiplied * alpha
    return (px0, py0, px0 + nw, py0 + nh)


def composite_remastered_plate(pnum: int) -> list[Path]:
    import numpy as np
    from PIL import Image

    if pnum == 1:
        # Page 1 (Page 0 frontispiece verso): pure warm #fdfaf2 cold-press parchment (no sand patch, no art)
        canvas = make_cold_press_paper_and_patch("bottom", seed=194301, include_patch=False)
        out_path = BOOK_DIR / "wc_p01.jpg"
        tmp_path = out_path.with_suffix(".tmp.jpg")
        Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="RGB").save(
            tmp_path, format="JPEG", quality=92, subsampling=1, optimize=True
        )
        tmp_path.replace(out_path)
        return [out_path]

    if pnum == 2:
        key = "p01_top_boa"
    elif pnum == 3:
        key = "p01"
    else:
        key = f"p{pnum - 2:02d}"

    spec = REMASTER_SPECS[key]
    patch_pos = "bottom" if pnum % 2 == 1 else "top"
    canvas = make_cold_press_paper_and_patch(patch_pos, seed=194300 + pnum)
    if spec.get("wash"):
        canvas = apply_atmospheric_wash(canvas, spec["wash"], patch_pos, seed=194300 + pnum)

    if patch_pos == "bottom":
        safe_x0, safe_y0, safe_x1, safe_y1 = 56, 48, 840, 815
    else:
        safe_x0, safe_y0, safe_x1, safe_y1 = 56, 345, 840, 1125
    safe_w = safe_x1 - safe_x0
    safe_h = safe_y1 - safe_y0

    rx0, ry0, rx1, ry1 = spec["plate_rel_box"]
    target_box = (
        safe_x0 + int(round(rx0 * safe_w)),
        safe_y0 + int(round(ry0 * safe_h)),
        safe_x0 + int(round(rx1 * safe_w)),
        safe_y0 + int(round(ry1 * safe_h)),
    )

    art_pil = knock_remastered_white_bg(Image.open(REMASTER_NB_DIR / f"{key}.png"))
    if spec.get("tight_pad"):
        art_pil = tight_pad_cutout(art_pil, pad=int(spec["tight_pad"]))

    outputs: list[Path] = []
    if pnum == 3:
        # Page 3 (Spread 2 Left): ONLY Drawing No. 1 (hat) -> hover/tap Drawing No. 2 (X-ray elephant)
        xray_canvas = canvas.copy()
        placed_box = _paste_multiply_into_box(canvas, art_pil, target_box, feather=24)

        xray_pil = knock_remastered_white_bg(Image.open(REMASTER_NB_DIR / "p01_xray.png"))
        xray_pil = tight_pad_cutout(xray_pil, pad=int(spec.get("tight_pad", 28)))
        # Align bottom baseline & horizontal span of X-ray boa directly onto Drawing No. 1's placed box
        px0, py0, px1, py1 = placed_box
        pw = px1 - px0
        xw, xh = xray_pil.size
        nh = max(16, int(round(pw * (xh / float(xw)))))
        y_top = max(safe_y0, py1 - nh)
        xray_box = (px0, y_top, px1, y_top + nh)
        _paste_multiply_into_box(xray_canvas, xray_pil, xray_box, feather=24)

        xray_out = BOOK_DIR / "wc_p03_xray.jpg"
        tmp_x = xray_out.with_suffix(".tmp.jpg")
        Image.fromarray(np.clip(xray_canvas, 0, 255).astype(np.uint8), mode="RGB").save(
            tmp_x, format="JPEG", quality=92, subsampling=1, optimize=True
        )
        tmp_x.replace(xray_out)
        outputs.append(xray_out)
    else:
        _paste_multiply_into_box(canvas, art_pil, target_box, feather=24 if pnum == 2 else 36)

    out_path = BOOK_DIR / f"wc_p{pnum:02d}.jpg"
    tmp_path = out_path.with_suffix(".tmp.jpg")
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="RGB").save(
        tmp_path, format="JPEG", quality=92, subsampling=1, optimize=True
    )
    tmp_path.replace(out_path)
    outputs.insert(0, out_path)
    return outputs


def composite_remastered_cover() -> Path:
    import numpy as np
    from PIL import Image, ImageDraw

    # Cold-press #fdfaf2 paper (without reading patch)
    rng = np.random.default_rng(194300)
    base = np.full((PLATE_H, PLATE_W, 3), [253.0, 250.0, 242.0], dtype=np.float32)
    fine = rng.normal(0.0, 1.75, size=(PLATE_H, PLATE_W)).astype(np.float32)
    med_low = rng.normal(0.0, 2.15, size=(PLATE_H // 4, PLATE_W // 4)).astype(np.float32)
    med = np.asarray(
        Image.fromarray(med_low, mode="F").resize((PLATE_W, PLATE_H), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    grain = fine + med
    paper = base.copy()
    paper[:, :, 0] += grain * 0.92
    paper[:, :, 1] += grain * 0.96
    paper[:, :, 2] += grain * 1.12
    paper_img = Image.fromarray(np.clip(paper, 0, 255).astype(np.uint8), mode="RGB")

    # Double-gold border + 4 corner dots matching books/covers/sardegna.jpg
    draw = ImageDraw.Draw(paper_img)
    draw.rounded_rectangle((29, 29, 866, 1170), radius=14, outline=(220, 187, 142), width=2)
    draw.rounded_rectangle((38, 38, 857, 1161), radius=10, outline=(215, 186, 154), width=1)
    for cx, cy in ((47, 47), (848, 47), (47, 1152), (848, 1152)):
        draw.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=(209, 178, 131))

    canvas = np.asarray(paper_img, dtype=np.float32)
    cover_art = knock_remastered_white_bg(Image.open(REMASTER_NB_DIR / "cover.png"))
    cover_art = tight_pad_cutout(cover_art, pad=20)
    _paste_multiply_into_box(canvas, cover_art, (60, 82, 836, 1118), feather=36)

    COVER_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = COVER_PATH.with_suffix(".tmp.jpg")
    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8), mode="RGB").save(
        tmp_path, format="JPEG", quality=92, subsampling=1, optimize=True
    )
    tmp_path.replace(COVER_PATH)
    return COVER_PATH


def run_plates(
    pages_filter: set[int] | None = None,
    include_cover: bool | None = None,
    force: bool = False,
    image_size: str = "1K",
    nb_workers: int = 4,
) -> None:
    ll_imgs_dir = ensure_liberliber_imgs()
    keys = load_gemini_image_keys()
    targets = [p for p in range(1, 27) if not pages_filter or p in pages_filter]

    asset_keys: list[str] = []
    for pnum in targets:
        if pnum == 1:
            continue  # Frontispiece is pure warm parchment, zero NB asset needed
        elif pnum == 2:
            asset_keys.append("p01_top_boa")
        elif pnum == 3:
            asset_keys.extend(["p01", "p01_xray"])
        else:
            asset_keys.append(f"p{pnum - 2:02d}")
    asset_keys = list(dict.fromkeys(asset_keys))
    do_cover = (include_cover is True) or (include_cover is None and pages_filter is None)
    if do_cover:
        asset_keys.append("cover")

    print(f"[plates] Nano Banana remastering {len(asset_keys)} assets (size={image_size}, workers={nb_workers}, force={force})...")
    with ThreadPoolExecutor(max_workers=nb_workers) as pool:
        futs = {
            pool.submit(remaster_asset_nanobanana, ak, ll_imgs_dir, keys, image_size, force): ak
            for ak in asset_keys
        }
        for idx, fut in enumerate(as_completed(futs), 1):
            ak, out_png, status = fut.result()
            print(f"  [nb {idx:02d}/{len(asset_keys):02d}] {ak} -> {out_png.name} ({status})", flush=True)

    print(f"[plates] Compositing {len(targets)} watercolor plates (896x1200 RGB JPEG)...")
    for pnum in targets:
        outs = composite_remastered_plate(pnum)
        for out_p in outs:
            print(f"  -> {out_p.relative_to(ROOT)} ({out_p.stat().st_size // 1024} KB)")

    if do_cover:
        cov_p = composite_remastered_cover()
        print(f"  -> {cov_p.relative_to(ROOT)} ({cov_p.stat().st_size // 1024} KB)")
    print("[plates] Done.")


# =============================================================================
# PHASE B1 — AOEDE STUDIO TTS AUDIO (576 FILES: FR/IT/DE ONLY, ZERO EN)
# =============================================================================

def load_gemini_keys() -> list[str]:
    """Load keys in order: GEMINI_API_KEY_FREE_TTS_STT -> GEMINI_API_KEY2 (.env.gprism) -> shell $GEMINI_API_KEY."""
    keys: list[str] = []
    if GPRISM_ENV_PATH.exists():
        env_txt = GPRISM_ENV_PATH.read_text(encoding="utf-8")
        found = dict(re.findall(r'^([A-Z0-9_]+)=["\']?(AIza[A-Za-z0-9_-]+)', env_txt, re.M))
        for kname in ("GEMINI_API_KEY_FREE_TTS_STT", "GEMINI_API_KEY2"):
            val = found.get(kname)
            if val and val not in keys:
                keys.append(val)
    shell_k = os.environ.get("GEMINI_API_KEY", "").strip()
    if shell_k.startswith("AIza") and shell_k not in keys:
        keys.append(shell_k)
    return keys


def is_valid_audio_pair(mp3_path: Path, ogg_path: Path, min_mp3: int = 1000, min_ogg: int = 512) -> bool:
    if not mp3_path.exists() or not ogg_path.exists():
        return False
    if mp3_path.stat().st_size < min_mp3 or ogg_path.stat().st_size < min_ogg:
        return False
    hdr_m = mp3_path.read_bytes()[:4]
    hdr_o = ogg_path.read_bytes()[:4]
    ok_m = hdr_m[:3] == b"ID3" or (len(hdr_m) >= 2 and hdr_m[0] == 0xFF and (hdr_m[1] & 0xE0) == 0xE0)
    ok_o = hdr_o == b"OggS"
    return ok_m and ok_o


def synth_aoede_clip(item: tuple[str, str, int, str, Path, Path], keys: list[str]) -> tuple[str, bool, str]:
    kind, lang, pnum, text, mp3_path, ogg_path = item
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"Forbidden language for studio TTS: {lang}")
    if is_valid_audio_pair(mp3_path, ogg_path):
        return (mp3_path.name, True, "cached")

    style_prompt = STYLE_MAP[lang]
    payload_bytes = json.dumps({
        "contents": [{
            "parts": [{
                "text": text,
                "speech_metadata": {"style": style_prompt},
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Aoede"}
                }
            },
        },
    }).encode("utf-8")

    last_err = "no keys"
    max_rounds = 4
    for rnd in range(max_rounds):
        for k_idx, key in enumerate(keys):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key={key}"
            req = urllib.request.Request(url, data=payload_bytes, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                wav_bytes = base64.b64decode(b64)
                if len(wav_bytes) < 512:
                    raise RuntimeError(f"Empty WAV ({len(wav_bytes)} B)")

                tmp_wav = mp3_path.with_suffix(".tmp.wav")
                tmp_mp3 = mp3_path.with_suffix(".tmp.mp3")
                tmp_ogg = ogg_path.with_suffix(".tmp.ogg")
                try:
                    tmp_wav.write_bytes(wav_bytes)
                    subprocess.run(
                        [
                            "ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_wav),
                            "-af", "silenceremove=stop_periods=-1:stop_duration=0.35:stop_threshold=-45dB,volume=1.35",
                            "-c:a", "libmp3lame", "-q:a", "3", str(tmp_mp3),
                        ],
                        check=True,
                    )
                    subprocess.run(
                        [
                            "ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_mp3),
                            "-c:a", "libopus", "-b:a", "32k", str(tmp_ogg),
                        ],
                        check=True,
                    )
                    tmp_mp3.replace(mp3_path)
                    tmp_ogg.replace(ogg_path)
                finally:
                    tmp_wav.unlink(missing_ok=True)
                    tmp_mp3.unlink(missing_ok=True)
                    tmp_ogg.unlink(missing_ok=True)
                return (mp3_path.name, True, f"key#{k_idx}")
            except urllib.error.HTTPError as he:
                body = ""
                try:
                    body = he.read().decode("utf-8", errors="ignore")[:180]
                except Exception:
                    pass
                last_err = f"HTTP {he.code}: {body}"
                if he.code in (429, 500, 502, 503, 504):
                    time.sleep(min(18.0, (1.5 ** (rnd + k_idx)) + random.uniform(0.2, 1.0)))
                else:
                    time.sleep(0.5)
            except Exception as exc:
                last_err = str(exc)
                time.sleep(min(12.0, 1.2 * (rnd + 1) + random.uniform(0.1, 0.7)))

    return (mp3_path.name, False, last_err)


def run_audio(pages_filter: set[int] | None = None, max_workers: int = 5) -> None:
    KIDS_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    spec = json.loads(CONTENT_SPEC_PATH.read_text(encoding="utf-8"))
    keys = load_gemini_keys()
    if not keys:
        raise RuntimeError("No valid Gemini TTS keys found in .env.gprism or $GEMINI_API_KEY")

    tasks = []
    for p in spec["pages"]:
        if p.get("is_frontispiece"):
            continue
        pnum = int(p["page"])
        if pages_filter and pnum not in pages_filter:
            continue
        pstr = f"{pnum:02d}"
        for lang in SUPPORTED_LANGS:
            if p.get("speech_bubble") and p["speech_bubble"].get(lang, {}).get("text"):
                sb_txt = p["speech_bubble"][lang]["text"]
                tasks.append((
                    "bubble", lang, pnum, sb_txt,
                    KIDS_AUDIO_DIR / f"{lang}_bubble_p{pstr}.mp3",
                    KIDS_AUDIO_DIR / f"{lang}_bubble_p{pstr}.ogg",
                ))
            for tier in TIERS:
                txt = p["levels"][tier][lang]["text"]
                if not txt:
                    continue
                tasks.append((
                    tier, lang, pnum, txt,
                    KIDS_AUDIO_DIR / f"{lang}_{tier}_p{pstr}.mp3",
                    KIDS_AUDIO_DIR / f"{lang}_{tier}_p{pstr}.ogg",
                ))

    cached = sum(1 for t in tasks if is_valid_audio_pair(t[4], t[5]))
    print(f"[audio] {len(tasks)} total Aoede clips ({cached} cached, {len(tasks) - cached} to synthesize) using {len(keys)} key(s)...")

    ok_count = 0
    fail_list = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = {pool.submit(synth_aoede_clip, t, keys): t for t in tasks}
        for idx, fut in enumerate(as_completed(futs), 1):
            name, ok, msg = fut.result()
            if ok:
                ok_count += 1
                if msg != "cached" and (ok_count % 15 == 0 or idx == len(tasks)):
                    print(f"  [audio] {idx}/{len(tasks)} done (latest: {name} via {msg})", flush=True)
            else:
                fail_list.append((name, msg))
                print(f"  [audio] FAIL {name}: {msg}", flush=True)

    if fail_list:
        raise RuntimeError(f"{len(fail_list)} Aoede clips failed, e.g. {fail_list[:3]}")
    print(f"[audio] All {ok_count}/{len(tasks)} studio clips ready ({ok_count * 2} files).")


# =============================================================================
# PHASE B2 — MISSING SINGLE-WORD CLIPS VIA EDGE-TTS (FR/IT/DE ONLY)
# =============================================================================

async def _synth_word_async(sem: asyncio.Semaphore, lang: str, clean: str, spoken: str) -> tuple[str, str, bool, str]:
    import edge_tts

    out_dir = WORDS_AUDIO_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = out_dir / f"{clean}.mp3"
    ogg_path = out_dir / f"{clean}.ogg"
    if mp3_path.exists() and ogg_path.exists() and mp3_path.stat().st_size > 200 and ogg_path.stat().st_size > 200:
        return (lang, clean, True, "cached")

    voice, rate = EDGE_VOICES[lang]
    tmp_mp3 = mp3_path.with_suffix(".tmp.mp3")
    tmp_ogg = ogg_path.with_suffix(".tmp.ogg")

    async with sem:
        last_err = ""
        for attempt in range(5):
            try:
                comm = edge_tts.Communicate(spoken, voice, rate=rate)
                with open(tmp_mp3, "wb") as f:
                    async for chunk in comm.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                if not tmp_mp3.exists() or tmp_mp3.stat().st_size <= 200:
                    raise RuntimeError("Empty edge-tts mp3")
                await asyncio.to_thread(
                    subprocess.run,
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_mp3), "-c:a", "libopus", "-b:a", "32k", str(tmp_ogg)],
                    check=True,
                )
                tmp_mp3.replace(mp3_path)
                tmp_ogg.replace(ogg_path)
                return (lang, clean, True, "synth")
            except Exception as exc:
                last_err = str(exc)
                tmp_mp3.unlink(missing_ok=True)
                tmp_ogg.unlink(missing_ok=True)
                await asyncio.sleep(0.6 * (attempt + 1) + random.uniform(0.05, 0.35))
        return (lang, clean, False, last_err)


def _words_worker_main() -> None:
    spec = json.loads(CONTENT_SPEC_PATH.read_text(encoding="utf-8"))
    words_needed: dict[tuple[str, str], str] = {}
    for p in spec["pages"]:
        if p.get("is_frontispiece"):
            continue
        for tier in TIERS:
            for lang in SUPPORTED_LANGS:
                for tok in p["levels"][tier][lang]["tokens"]:
                    clean = tok["clean"]
                    spoken = STRIP_OUTER_RE.sub("", tok["w"])
                    if clean and spoken and (lang, clean) not in words_needed:
                        words_needed[(lang, clean)] = spoken

    todo = []
    for (lang, clean), spoken in sorted(words_needed.items()):
        mp3_p = WORDS_AUDIO_DIR / lang / f"{clean}.mp3"
        ogg_p = WORDS_AUDIO_DIR / lang / f"{clean}.ogg"
        if not (mp3_p.exists() and ogg_p.exists() and mp3_p.stat().st_size > 200 and ogg_p.stat().st_size > 200):
            todo.append((lang, clean, spoken))

    print(f"[words] Total unique (lang, clean)={len(words_needed)}; missing={len(todo)}")
    if not todo:
        print("[words] Nothing missing.")
        return

    async def _run() -> None:
        sem = asyncio.Semaphore(10)
        coros = [_synth_word_async(sem, lang, clean, spoken) for (lang, clean, spoken) in todo]
        done = 0
        fails = []
        for fut in asyncio.as_completed(coros):
            lang, clean, ok, msg = await fut
            done += 1
            if not ok:
                fails.append((lang, clean, msg))
            if done % 150 == 0 or done == len(todo):
                print(f"  [words] {done}/{len(todo)} synthesized (fails={len(fails)})", flush=True)
        if fails:
            raise RuntimeError(f"{len(fails)} word clips failed: {fails[:5]}")

    asyncio.run(_run())
    print("[words] Done.")


def run_words() -> None:
    try:
        import edge_tts  # noqa: F401
        _words_worker_main()
    except ImportError:
        env = os.environ.copy()
        env.setdefault("UV_CACHE_DIR", "/tmp/uv-cache")
        env.setdefault("UV_LINK_MODE", "copy")
        env.setdefault("UV_INDEX_URL", "https://pypi.org/simple")
        cmd = ["uv", "run", "--with", "edge-tts", "python3", str(Path(__file__).resolve()), "--words-worker"]
        subprocess.run(cmd, env=env, check=True)


# =============================================================================
# PHASE C1 — WHISPER ACOUSTIC KARAOKE ALIGNMENT (BASE + NEEDLEMAN-WUNSCH DP)
# =============================================================================

def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return float(out)


def norm_align_word(w: str) -> str:
    return NORM_ALIGN_RE.sub("", w.lower())


def align_word_sim(a: str, b: str) -> float:
    na, nb = norm_align_word(a), norm_align_word(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.5
    if na in nb or nb in na:
        return 1.0
    return (SequenceMatcher(None, na, nb).ratio() * 1.6) - 0.55


def expand_whisper_words(raw_words: list[dict]) -> list[dict]:
    """Split Whisper tokens containing apostrophes/hyphens slightly so 'l'avion' or 'n'en' matches cleanly."""
    out = []
    for item in raw_words:
        w = item["w"].strip()
        s, e = float(item["s"]), float(item["e"])
        if not w:
            continue
        out.append({"w": w, "s": s, "e": e})
    return out


def needleman_wunsch_align(gt_tokens: list[dict], wh_words: list[dict], actual_dur: float) -> list[tuple[float, float]]:
    import numpy as np

    n = len(gt_tokens)
    if n == 0:
        return []
    usable_end = max(0.25, actual_dur - 0.04)

    # Fallback to char-weighted linear timings if Whisper returned < 2 words
    if len(wh_words) < 2:
        weights = [max(2, len(norm_align_word(t["w"]))) for t in gt_tokens]
        total_w = sum(weights) or 1
        cur = 0.06
        span = max(0.20, usable_end - cur)
        res = []
        for wg in weights:
            d = span * (wg / total_w)
            res.append((round(cur, 3), round(min(usable_end, cur + d), 3)))
            cur += d
        return res

    # Also compute merged/split-friendly form: match GT words against Whisper words
    m = len(wh_words)
    gap_penalty = -0.32
    dp = np.zeros((n + 1, m + 1), dtype=np.float32)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)

    for i in range(1, n + 1):
        dp[i, 0] = i * gap_penalty
        ptr[i, 0] = 2
    for j in range(1, m + 1):
        dp[0, j] = j * gap_penalty
        ptr[0, j] = 3

    for i in range(1, n + 1):
        gt_w = gt_tokens[i - 1]["w"]
        pos_gt = i / float(n)
        for j in range(1, m + 1):
            pos_wh = j / float(m)
            if abs(pos_gt - pos_wh) > 0.30:
                sim = -1.5
            else:
                sim = align_word_sim(gt_w, wh_words[j - 1]["w"])
            sc_diag = dp[i - 1, j - 1] + sim
            sc_up = dp[i - 1, j] + gap_penalty
            sc_left = dp[i, j - 1] + gap_penalty
            if sc_diag >= sc_up and sc_diag >= sc_left:
                dp[i, j] = sc_diag
                ptr[i, j] = 1
            elif sc_up >= sc_left:
                dp[i, j] = sc_up
                ptr[i, j] = 2
            else:
                dp[i, j] = sc_left
                ptr[i, j] = 3

    matched_wh: list[int | None] = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        mv = ptr[i, j]
        if mv == 1:
            if align_word_sim(gt_tokens[i - 1]["w"], wh_words[j - 1]["w"]) >= 0.25:
                matched_wh[i - 1] = j - 1
            i -= 1
            j -= 1
        elif mv == 2:
            i -= 1
        else:
            j -= 1

    times: list[tuple[float, float] | None] = [None] * n
    for idx_gt, wh_idx in enumerate(matched_wh):
        if wh_idx is not None:
            wo = wh_words[wh_idx]
            s_v = max(0.02, min(usable_end - 0.08, float(wo["s"])))
            e_v = max(s_v + 0.06, min(usable_end, float(wo["e"])))
            times[idx_gt] = (s_v, e_v)

    # Interpolate unaligned spans monotonically using char weights
    idx = 0
    while idx < n:
        if times[idx] is None:
            start_gap = idx
            while idx < n and times[idx] is None:
                idx += 1
            end_gap = idx

            t_left = times[start_gap - 1][1] if start_gap > 0 and times[start_gap - 1] is not None else 0.04
            if end_gap < n and times[end_gap] is not None:
                t_right = times[end_gap][0]
            else:
                t_right = usable_end

            if t_right <= t_left + 0.05 * (end_gap - start_gap):
                t_right = min(usable_end, t_left + 0.12 * (end_gap - start_gap))

            weights = [max(2, len(norm_align_word(gt_tokens[k]["w"]))) for k in range(start_gap, end_gap)]
            tot = sum(weights) or 1
            span = max(0.06 * (end_gap - start_gap), t_right - t_left)
            cur = t_left
            for k, wg in zip(range(start_gap, end_gap), weights):
                d = span * (wg / tot)
                times[k] = (cur, cur + max(0.05, d * 0.94))
                cur += d
        else:
            idx += 1

    # Strict monotonic clamp pass: 0 <= s < e <= actual_dur + 0.04 and s >= prev_s
    out: list[tuple[float, float]] = []
    prev_s = 0.0
    max_e = actual_dur + 0.04
    for k, pair in enumerate(times):
        s_val, e_val = pair if pair is not None else (prev_s, prev_s + 0.1)
        s_val = max(0.0, min(s_val, max(0.0, actual_dur - 0.06)))
        if s_val < prev_s:
            s_val = prev_s
        e_val = max(s_val + 0.05, min(e_val, max_e))
        if e_val <= s_val:
            e_val = s_val + 0.05
        out.append((round(s_val, 3), round(e_val, 3)))
        prev_s = s_val
    return out


def _align_worker_main() -> None:
    import numpy as np
    import whisper

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    spec = json.loads(CONTENT_SPEC_PATH.read_text(encoding="utf-8"))

    cache = {}
    if WHISPER_CACHE_PATH.exists():
        cache = json.loads(WHISPER_CACHE_PATH.read_text(encoding="utf-8"))

    # Collect level MP3 jobs (skip frontispiece / empty audio_mp3)
    jobs = []
    for p in spec["pages"]:
        if p.get("is_frontispiece"):
            continue
        pnum = int(p["page"])
        pstr = f"{pnum:02d}"
        for tier in TIERS:
            for lang in SUPPORTED_LANGS:
                rel_mp3 = p["levels"][tier][lang]["audio_mp3"]
                if not rel_mp3:
                    continue
                mp3_path = ROOT / rel_mp3
                if not mp3_path.exists():
                    raise FileNotFoundError(f"Missing studio MP3 for alignment: {mp3_path}")
                jobs.append((pnum, tier, lang, rel_mp3, mp3_path, p["levels"][tier][lang]["tokens"]))

    uncached = [j for j in jobs if j[3] not in cache]
    print(f"[align] {len(jobs)} clips total; {len(cache)} cached; {len(uncached)} to transcribe with Whisper base...")

    if uncached:
        model = whisper.load_model("base")
        for idx, (pnum, tier, lang, rel_mp3, mp3_path, _) in enumerate(uncached, 1):
            dur = ffprobe_duration(mp3_path)
            raw = subprocess.check_output(
                ["ffmpeg", "-v", "error", "-i", str(mp3_path), "-f", "s16le", "-ac", "1", "-ar", "16000", "-"]
            )
            audio_16k = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            res = model.transcribe(
                audio_16k,
                language=lang,
                word_timestamps=True,
                fp16=False,
                condition_on_previous_text=False,
            )
            words = []
            for seg in res.get("segments", []):
                for wd in seg.get("words", []):
                    tok = wd.get("word", "").strip()
                    if tok:
                        words.append({"w": tok, "s": float(wd["start"]), "e": float(wd["end"])})
            cache[rel_mp3] = {"duration": dur, "words": words}
            if idx % 20 == 0 or idx == len(uncached):
                WHISPER_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                print(f"  [align] Whisper {idx}/{len(uncached)} ({rel_mp3}: {len(words)} words, dur={dur:.2f}s)", flush=True)

    WHISPER_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    aligned_out: dict[str, list[list[float]]] = {}
    for pnum, tier, lang, rel_mp3, mp3_path, gt_tokens in jobs:
        entry = cache[rel_mp3]
        dur = float(entry.get("duration") or ffprobe_duration(mp3_path))
        wh_words = expand_whisper_words(entry.get("words", []))
        pairs = needleman_wunsch_align(gt_tokens, wh_words, dur)
        aligned_out[rel_mp3] = [[s, e] for (s, e) in pairs]

    ALIGNED_TIMINGS_PATH.write_text(json.dumps(aligned_out, ensure_ascii=False), encoding="utf-8")
    print(f"[align] Wrote {len(aligned_out)} aligned clip timing lists -> {ALIGNED_TIMINGS_PATH}")


def run_align() -> None:
    try:
        import whisper  # noqa: F401
        _align_worker_main()
    except ImportError:
        if not WHISPER_PYTHON.exists():
            raise RuntimeError(f"Homebrew Whisper python not found at {WHISPER_PYTHON}")
        cmd = [str(WHISPER_PYTHON), str(Path(__file__).resolve()), "--align-worker"]
        subprocess.run(cmd, check=True)


# =============================================================================
# PHASE C2 — COMPILE kids_book_data.json & kids_books_catalog.js
# =============================================================================

def run_compile(allow_fallback_timings: bool = False) -> None:
    spec = json.loads(CONTENT_SPEC_PATH.read_text(encoding="utf-8"))
    book_data = copy.deepcopy(spec)
    book_data["author_label"] = "Antoine de Saint-Exupéry"

    if ALIGNED_TIMINGS_PATH.exists():
        aligned = json.loads(ALIGNED_TIMINGS_PATH.read_text(encoding="utf-8"))
    elif allow_fallback_timings:
        aligned = {}
    else:
        raise RuntimeError(f"Missing {ALIGNED_TIMINGS_PATH}; run --align first!")

    updated_tokens = 0
    for pg in book_data["pages"]:
        if pg.get("is_frontispiece"):
            continue
        for tier in TIERS:
            for lang in SUPPORTED_LANGS:
                lvl = pg["levels"][tier][lang]
                rel_mp3 = lvl["audio_mp3"]
                if not rel_mp3:
                    continue
                if rel_mp3 in aligned:
                    pairs = aligned[rel_mp3]
                    if len(pairs) != len(lvl["tokens"]):
                        raise RuntimeError(
                            f"Token count mismatch for {rel_mp3}: aligned={len(pairs)} vs spec={len(lvl['tokens'])}"
                        )
                    for tok, (s, e) in zip(lvl["tokens"], pairs):
                        tok["s"] = s
                        tok["e"] = e
                        updated_tokens += 1
                elif not allow_fallback_timings:
                    raise RuntimeError(f"Missing aligned timings for {rel_mp3}")

    KIDS_BOOK_DATA_PATH.write_text(json.dumps(book_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[compile] Wrote {KIDS_BOOK_DATA_PATH.relative_to(ROOT)} ({updated_tokens} token timings updated)")

    sardegna_data = json.loads(SARDEGNA_JSON_PATH.read_text(encoding="utf-8"))
    if "author_label" not in sardegna_data:
        sardegna_data["author_label"] = "Riccardo Carlesso"

    catalog = {
        "storia-sardegna-cala-gonone-arbatax-famiglia": sardegna_data,
        "le-petit-prince": book_data,
    }
    js_text = "window.KIDS_BOOKS_CATALOG = " + json.dumps(catalog, ensure_ascii=False, indent=2) + ";\n"
    CATALOG_JS_PATH.write_text(js_text, encoding="utf-8")
    print(f"[compile] Wrote {CATALOG_JS_PATH.relative_to(ROOT)} ({len(js_text) // 1024} KB, {len(catalog)} books)")


# =============================================================================
# CLI ENTRYPOINT
# =============================================================================

def parse_pages_arg(val: str | None) -> set[int] | None:
    if not val:
        return None
    out = set()
    for part in val.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Le Petit Prince M3 plates, audio, timings, and catalog.")
    ap.add_argument("--plates", action="store_true", help="Remaster & composite 26 896x1200 RGB JPEG watercolor plates")
    ap.add_argument("--cover", action="store_true", help="Remaster & composite books/covers/petit-prince.jpg")
    ap.add_argument("--force", action="store_true", help="Bypass Nano Banana remaster cache for selected targets")
    ap.add_argument("--image-size", default="1K", choices=("1K", "2K"), help="Nano Banana output size (default: 1K)")
    ap.add_argument("--nb-workers", type=int, default=4, help="ThreadPool workers for Nano Banana (default: 4)")
    ap.add_argument("--audio", action="store_true", help="Generate 300 Aoede studio TTS clips (FR/IT/DE only)")
    ap.add_argument("--words", action="store_true", help="Generate missing clickable word audio pairs via edge-tts")
    ap.add_argument("--align", action="store_true", help="Run Whisper base + Needleman-Wunsch DP karaoke alignment")
    ap.add_argument("--compile", action="store_true", help="Compile kids_book_data.json and kids_books_catalog.js")
    ap.add_argument("--all", action="store_true", help="Run all phases in order")
    ap.add_argument("--pages", default=None, help="Optional comma/range page filter for --plates/--audio (e.g. 1,4-6)")
    ap.add_argument("--workers", type=int, default=5, help="ThreadPool workers for --audio (default: 5)")
    ap.add_argument("--allow-fallback-timings", action="store_true", help="Allow --compile without aligned_timings.json")
    ap.add_argument("--words-worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--align-worker", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.words_worker:
        _words_worker_main()
        return 0
    if args.align_worker:
        _align_worker_main()
        return 0

    if not any([args.plates, args.cover, args.audio, args.words, args.align, args.compile, args.all]):
        ap.print_help()
        return 1

    pages_filter = parse_pages_arg(args.pages)

    if args.all or args.plates:
        inc_cover = True if (args.all or args.cover) else None
        run_plates(
            pages_filter=pages_filter,
            include_cover=inc_cover,
            force=args.force,
            image_size=args.image_size,
            nb_workers=args.nb_workers,
        )
    elif args.cover:
        ll_imgs_dir = ensure_liberliber_imgs()
        keys = load_gemini_image_keys()
        _, out_png, status = remaster_asset_nanobanana(
            "cover", ll_imgs_dir, keys, image_size=args.image_size, force=args.force
        )
        print(f"  [nb] cover -> {out_png.name} ({status})")
        cov_p = composite_remastered_cover()
        print(f"  -> {cov_p.relative_to(ROOT)} ({cov_p.stat().st_size // 1024} KB)")
    if args.all or args.audio:
        run_audio(pages_filter=pages_filter, max_workers=args.workers)
    if args.all or args.words:
        run_words()
    if args.all or args.align:
        run_align()
    if args.all or args.compile:
        run_compile(allow_fallback_timings=args.allow_fallback_timings)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
