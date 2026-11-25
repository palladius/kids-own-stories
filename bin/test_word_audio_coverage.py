#!/usr/bin/env python3
"""
Strict acoustic unit test verifying 100% clickable word-audio coverage across
ALL watercolor books (Sardegna + Le Petit Prince), ALL CEFR tiers, and ALL
3 learning languages (FR, IT, DE).

Checks for every non-punctuation word token:
  1. Both audio_mp3 and audio_ogg fields exist and point to files on disk
  2. File sizes >= 1500B (MP3) and >= 500B (OGG)
  3. Acoustic verification via ffmpeg volumedetect: duration >= 0.16s and
     max_volume >= -35.0 dB (catches silent 720B edge-tts stubs like belva.mp3!)
"""

import concurrent.futures
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG_JS = ROOT / "kids_books_catalog.js"


def load_books_catalog() -> dict:
    raw = subprocess.check_output(
        ["node", "-e", "const window={}; require(process.argv[1]); console.log(JSON.stringify(window.KIDS_BOOKS_CATALOG));", str(CATALOG_JS)],
        text=True,
    )
    return json.loads(raw)


def audit_audio_file(rel: str) -> tuple[str, list[str]] | None:
    mp3 = ROOT / rel
    ogg = mp3.with_suffix(".ogg")
    issues: list[str] = []
    if not mp3.exists():
        return (rel, ["MISSING_MP3"])
    if not ogg.exists() or ogg.stat().st_size < 500:
        sz_ogg = ogg.stat().st_size if ogg.exists() else 0
        issues.append(f"MISSING_OR_TINY_OGG({sz_ogg}B)")
    sz_mp3 = mp3.stat().st_size
    if sz_mp3 < 1500:
        issues.append(f"TINY_MP3({sz_mp3}B)")

    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(mp3), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True, check=False,
    )
    out = res.stderr or ""
    m_max = re.search(r"max_volume:\s*([-\d.]+)\s*dB", out)
    m_dur = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out)
    max_db = float(m_max.group(1)) if m_max else -999.0
    dur = (
        int(m_dur.group(1)) * 3600 + int(m_dur.group(2)) * 60 + float(m_dur.group(3))
        if m_dur
        else 0.0
    )
    if max_db < -35.0:
        issues.append(f"SILENT(max={max_db}dB)")
    if dur < 0.16:
        issues.append(f"TOO_SHORT({dur:.2f}s)")
    return (rel, issues) if issues else None


def main() -> int:
    token_count = 0
    missing_fields: list[str] = []
    unique_mp3s: set[str] = set()

    catalog = load_books_catalog()
    for label, data in catalog.items():
        for pg in data.get("pages") or []:
            if pg.get("is_frontispiece"):
                continue
            pno = pg.get("page")
            for lvl, langs in (pg.get("levels") or {}).items():
                for lang, obj in (langs or {}).items():
                    if lang not in ("fr", "it", "de"):
                        continue
                    for tok in obj.get("tokens") or []:
                        w = str(tok.get("w") or "")
                        if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]", w):
                            continue
                        token_count += 1
                        mp3 = tok.get("audio_mp3")
                        ogg = tok.get("audio_ogg")
                        if not mp3 or not ogg:
                            missing_fields.append(f"[{label} p.{pno} {lvl} {lang}] {w!r}")
                        else:
                            unique_mp3s.add(mp3)

    print(
        f"🔊 Auditing {len(unique_mp3s)} unique word audio files across {token_count} clickable tokens (FR/IT/DE)..."
    )
    broken: list[tuple[str, list[str]]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for res in pool.map(audit_audio_file, sorted(unique_mp3s)):
            if res:
                broken.append(res)

    if missing_fields or broken:
        print(
            f"❌ WORD AUDIO COVERAGE FAILED: {len(missing_fields)} missing fields, {len(broken)} broken/silent files",
            file=sys.stderr,
        )
        for m in missing_fields[:20]:
            print(f"  - MISSING FIELD: {m}", file=sys.stderr)
        for rel, issues in broken[:30]:
            print(f"  - {rel}: {', '.join(issues)}", file=sys.stderr)
        return 1

    print(
        f"✅ 100% WORD AUDIO COVERAGE VERIFIED: {len(unique_mp3s)}/{len(unique_mp3s)} files audible (>= -35dB, >= 0.16s, >= 1500B MP3 / 500B OGG) across {token_count} tokens!"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
