#!/usr/bin/env python3
"""
Deterministic Integrity & Completeness Test Suite for Kids' Own Stories (`just test`).
Fails with non-zero exit code if ANY story in `stories.yaml` (or on disk) is missing:
- Raw & converted audio (`audio_originale.mp3`, `audio_originale.ogg`, `archive_audio`)
- Hover WOW assets (`hover_preview.mp4`, `title_it.mp3`, `title_en.mp3`)
- Bilingual studio narrated audiobooks (`narrated_it.mp3`, `narrated_en.mp3`)
- Whisper word-level karaoke timings (`karaoke_it.json`, `karaoke_en.json`)
- 40-second full-story movie (`video_*.mp4`, duration >= 35s)
- 16:9 horizontal illustrations for every page (`width > height`)
- 5-language storyteller prose (`it`, `en`, `fr`, `de`, `pt`)
"""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parent.parent


def has_valid_audio_magic(path: Path, ext_key: str) -> bool:
    try:
        with path.open("rb") as fh:
            hdr = fh.read(4)
    except OSError:
        return False
    if ext_key == "audio_mp3":
        return hdr.startswith(b"ID3") or (len(hdr) >= 2 and hdr[0] == 0xFF and (hdr[1] & 0xE0) == 0xE0)
    if ext_key == "audio_ogg":
        return hdr.startswith(b"OggS")
    return True


def probe_media(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration,size:stream=codec_type,width,height",
        "-of", "json",
        str(path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return {}
    try:
        return json.loads(res.stdout)
    except Exception:
        return {}


def main() -> int:
    yaml_path = ROOT / "stories.yaml"
    if not yaml_path.exists():
        print("❌ FAIL: stories.yaml not found", file=sys.stderr)
        return 1

    catalog = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    stories = catalog.get("stories", [])
    errors: list[str] = []

    if not stories:
        errors.append("No stories found in stories.yaml")

    # 1. Check for orphan story directories on disk not registered in stories.yaml
    registered_folders = {s.get("folder") for s in stories}
    if "le-petit-prince" in {s.get("slug") for s in stories}:
        errors.append("Constitution violation: 'le-petit-prince' must NOT appear in stories.yaml (Layer 2 book only)")
    for author_dir in (ROOT / "stories").iterdir():
        if not author_dir.is_dir():
            continue
        for story_dir in author_dir.iterdir():
            if not story_dir.is_dir():
                continue
            rel = str(story_dir.relative_to(ROOT))
            if rel not in registered_folders:
                errors.append(f"Orphan story folder on disk not in stories.yaml: {rel}")

    # 2. Validate every story in stories.yaml
    print(f"🔍 Auditing {len(stories)} stories in stories.yaml...\n")
    print(f"{'#':<3} {'Slug':<48} {'Author':<11} {'Status':<10} {'Video':<8} {'Hover+Title':<13} {'Karaoke'}")
    print("-" * 110)

    for idx, st in enumerate(stories, 1):
        slug = st.get("slug", f"story-{idx}")
        author = st.get("author", "unknown")
        status = st.get("status", "unknown")
        assets = st.get("assets", {})
        pages = assets.get("pages", [])

        if status != "complete":
            errors.append(f"[{slug}] status is '{status}' (expected 'complete')")
        if st.get("missing_assets"):
            errors.append(f"[{slug}] has non-empty missing_assets: {st.get('missing_assets')}")

        # Check top-level localized titles & quotes
        for lang in ("en", "fr", "de", "pt"):
            if not st.get(f"title_{lang}"):
                errors.append(f"[{slug}] missing title_{lang}")
            if not st.get(f"short_title_{lang}"):
                errors.append(f"[{slug}] missing short_title_{lang}")
            if not st.get(f"quote_{lang}"):
                errors.append(f"[{slug}] missing quote_{lang}")

        # Required file paths
        required_files = {
            "archive_audio.mp3": assets.get("archive_audio", {}).get("mp3"),
            "archive_audio.ogg": assets.get("archive_audio", {}).get("ogg"),
            "story_audio.mp3": assets.get("story_audio", {}).get("mp3"),
            "story_audio.ogg": assets.get("story_audio", {}).get("ogg"),
            "narrated_audio.it": assets.get("narrated_audio", {}).get("it"),
            "narrated_audio.en": assets.get("narrated_audio", {}).get("en"),
            "karaoke_timings.it": assets.get("karaoke_timings", {}).get("it"),
            "karaoke_timings.en": assets.get("karaoke_timings", {}).get("en"),
            "title_audio.it (Hover IT Title TTS)": assets.get("title_audio", {}).get("it"),
            "title_audio.en (Hover EN Title TTS)": assets.get("title_audio", {}).get("en"),
            "hover_video (Hover 5s Video)": assets.get("hover_video"),
            "readme": assets.get("readme"),
            "web_page": assets.get("web_page"),
            "video.file (40s Full Movie)": assets.get("video", {}).get("file"),
        }

        for label, rel_path in required_files.items():
            if not rel_path:
                errors.append(f"[{slug}] missing asset declaration in stories.yaml: {label}")
                continue
            fp = ROOT / rel_path
            if not fp.exists():
                errors.append(f"[{slug}] missing file on disk for {label}: {rel_path}")
            elif fp.stat().st_size < 512:
                errors.append(f"[{slug}] file too small/corrupt ({fp.stat().st_size} B) for {label}: {rel_path}")

        # Check Hover Video + Title Audio durations
        hover_ok = False
        hover_rel = assets.get("hover_video")
        title_it_rel = assets.get("title_audio", {}).get("it")
        title_en_rel = assets.get("title_audio", {}).get("en")
        if hover_rel and (ROOT / hover_rel).exists():
            info = probe_media(ROOT / hover_rel)
            dur = float(info.get("format", {}).get("duration", 0) or 0)
            if dur < 3.0:
                errors.append(f"[{slug}] hover_video duration too short ({dur:.1f}s): {hover_rel}")
            else:
                hover_ok = True
        if title_it_rel and (ROOT / title_it_rel).exists():
            info = probe_media(ROOT / title_it_rel)
            dur = float(info.get("format", {}).get("duration", 0) or 0)
            if dur < 5.0:
                errors.append(f"[{slug}] title_audio.it duration too short ({dur:.1f}s < 5.0s): {title_it_rel}")
                hover_ok = False
        else:
            hover_ok = False
        if title_en_rel and (ROOT / title_en_rel).exists():
            info = probe_media(ROOT / title_en_rel)
            dur = float(info.get("format", {}).get("duration", 0) or 0)
            if dur < 5.0:
                errors.append(f"[{slug}] title_audio.en duration too short ({dur:.1f}s < 5.0s): {title_en_rel}")
                hover_ok = False
        else:
            hover_ok = False

        # Check 40s Full Movie duration
        video_dur_str = "MISSING"
        video_rel = assets.get("video", {}).get("file")
        if video_rel and (ROOT / video_rel).exists():
            info = probe_media(ROOT / video_rel)
            dur = float(info.get("format", {}).get("duration", 0) or 0)
            video_dur_str = f"{dur:.1f}s"
            if dur < 35.0:
                errors.append(f"[{slug}] full story video must be ~40s (got {dur:.1f}s): {video_rel}")

        # Check Karaoke JSON page count & words
        karaoke_ok = True
        for klang in ("it", "en"):
            krel = assets.get("karaoke_timings", {}).get(klang)
            if not krel or not (ROOT / krel).exists():
                karaoke_ok = False
                continue
            try:
                kdata = json.loads((ROOT / krel).read_text(encoding="utf-8"))
                kpages = kdata.get("pages", [])
                if len(kpages) != len(pages):
                    errors.append(
                        f"[{slug}] karaoke_{klang}.json has {len(kpages)} pages, expected {len(pages)}"
                    )
                    karaoke_ok = False
            except Exception as e:
                errors.append(f"[{slug}] invalid JSON in {krel}: {e}")
                karaoke_ok = False

        # Check pages, 16:9 horizontal illustrations, and 5-language paragraphs
        if len(pages) < 3:
            errors.append(f"[{slug}] has only {len(pages)} pages (expected >= 3)")

        for p in pages:
            pnum = p.get("page")
            img_rel = p.get("image")
            if not img_rel or not (ROOT / img_rel).exists():
                errors.append(f"[{slug} p.{pnum}] missing illustration: {img_rel}")
            else:
                info = probe_media(ROOT / img_rel)
                streams = info.get("streams", [])
                w = streams[0].get("width", 0) if streams else 0
                h = streams[0].get("height", 0) if streams else 0
                if w <= h:
                    errors.append(
                        f"[{slug} p.{pnum}] illustration is not horizontal 16:9 ({w}x{h}): {img_rel}"
                    )

            for plang in ("it", "en", "fr", "de", "pt"):
                paras = p.get(f"paragraphs_{plang}", [])
                if not isinstance(paras, list) or len(paras) < 2:
                    errors.append(
                        f"[{slug} p.{pnum}] missing or incomplete paragraphs_{plang} (got {len(paras) if isinstance(paras, list) else 0} paragraphs)"
                    )

        print(
            f"{idx:<3} {slug:<48} {author:<11} {status:<10} {video_dur_str:<8} "
            f"{'✅ OK' if hover_ok else '❌ FAIL':<13} {'✅ OK' if karaoke_ok else '❌ FAIL'}"
        )

    # 3. Validate Layer 2 Illustrated Watercolor Books (sardegna 16p + le-petit-prince 26p),
    #    kids_books_catalog.js parity, zero-EN-audio Constitution, docs/CONSTITUTION.md & /books/
    cat_js = ROOT / "kids_books_catalog.js"
    catalog_books: dict = {}
    if not cat_js.exists():
        errors.append("Missing kids_books_catalog.js")
    else:
        cat_raw = cat_js.read_text(encoding="utf-8").strip()
        prefix = "window.KIDS_BOOKS_CATALOG ="
        if not cat_raw.startswith(prefix):
            errors.append("kids_books_catalog.js does not start with 'window.KIDS_BOOKS_CATALOG ='")
        else:
            json_body = cat_raw[len(prefix):].strip().rstrip(";").strip()
            try:
                catalog_books = json.loads(json_body)
            except Exception as e:
                errors.append(f"kids_books_catalog.js invalid JSON payload: {e}")

    kids_books_specs = [
        {
            "label": "Sardegna",
            "story_id": "storia-sardegna-cala-gonone-arbatax-famiglia",
            "json_path": ROOT / "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/kids_book_data.json",
            "audio_dir": ROOT / "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/kids_audio",
            "expected_pages": 16,
            "json_levels": ("seby", "ale"),
            "quiz_pages": set(range(1, 17)),
            "require_en_tr": False,
            "require_default_lang": None,
        },
        {
            "label": "LePetitPrince",
            "story_id": "le-petit-prince",
            "json_path": ROOT / "books/petit-prince/kids_book_data.json",
            "audio_dir": ROOT / "books/petit-prince/kids_audio",
            "expected_pages": 26,
            "json_levels": ("seby", "ale", "emma"),
            "quiz_pages": set(range(2, 27, 2)),
            "require_en_tr": True,
            "require_default_lang": "fr",
        },
    ]

    for spec in kids_books_specs:
        lbl = spec["label"]
        sid = spec["story_id"]
        kb_json = spec["json_path"]
        if not kb_json.exists():
            errors.append(f"[{lbl}] Missing {kb_json.relative_to(ROOT)}")
            continue

        kb = json.loads(kb_json.read_text(encoding="utf-8"))
        kb_pages = kb.get("pages", [])
        sup_langs = kb.get("supported_langs", [])
        def_lang = kb.get("default_lang")

        if set(sup_langs) != {"fr", "it", "de"} or "en" in sup_langs:
            errors.append(f"[{lbl}] supported_langs must be {{'fr','it','de'}} without 'en', got {sup_langs}")
        if def_lang == "en":
            errors.append(f"[{lbl}] default_lang must NEVER be 'en'")
        if spec["require_default_lang"] and def_lang != spec["require_default_lang"]:
            errors.append(f"[{lbl}] default_lang expected {spec['require_default_lang']!r}, got {def_lang!r}")
        if kb.get("total_pages") != spec["expected_pages"] or len(kb_pages) != spec["expected_pages"]:
            errors.append(
                f"[{lbl}] expected {spec['expected_pages']} pages, got total_pages={kb.get('total_pages')} len(pages)={len(kb_pages)}"
            )

        # Cross-check kids_books_catalog.js parity
        cat_entry = catalog_books.get(sid)
        if not cat_entry:
            errors.append(f"[{lbl}] missing entry {sid!r} in kids_books_catalog.js")
        else:
            if cat_entry.get("pages") != kb_pages:
                errors.append(f"[{lbl}] kids_books_catalog.js pages differ from {kb_json.relative_to(ROOT)}")
            if cat_entry.get("total_pages") != spec["expected_pages"]:
                errors.append(f"[{lbl}] kids_books_catalog.js total_pages={cat_entry.get('total_pages')} != {spec['expected_pages']}")
            if cat_entry.get("supported_langs") != sup_langs:
                errors.append(f"[{lbl}] kids_books_catalog.js supported_langs={cat_entry.get('supported_langs')} != {sup_langs}")

        # Zero EN studio audio files in book's kids_audio/ (recursive)
        audio_dir = spec["audio_dir"]
        if audio_dir.exists():
            en_files = [
                str(p.relative_to(ROOT))
                for p in audio_dir.rglob("*")
                if p.is_file() and p.name.startswith("en_") and p.suffix.lower() in (".mp3", ".ogg")
            ]
            if en_files:
                errors.append(f"[{lbl}] Constitution violation: EN audio files found in {audio_dir.relative_to(ROOT)}: {en_files[:5]}")

        if sid == "le-petit-prince":
            en_gloss = kb.get("en_gloss") or {}
            if not isinstance(en_gloss, dict) or len(en_gloss) == 0:
                errors.append(f"[{lbl}] missing or empty en_gloss map")
            if (ROOT / "books/petit-prince/wc_p01_xray.jpg").exists():
                errors.append(f"[{lbl}] obsolete books/petit-prince/wc_p01_xray.jpg must not exist (X-ray moved to wc_p03_xray.jpg)")
            if audio_dir.exists():
                orphan_p01 = [p.name for p in audio_dir.glob("*_p01.*") if p.is_file()]
                if orphan_p01:
                    errors.append(f"[{lbl}] orphan frontispiece audio files found on disk: {orphan_p01[:5]}")

        for idx_p, kp in enumerate(kb_pages, 1):
            pno = kp.get("page")
            if pno != idx_p:
                errors.append(f"[{lbl}] page index mismatch at slot {idx_p}: got page={pno}")
                continue
            expected_patch = "bottom" if pno % 2 == 1 else "top"
            if kp.get("patch_pos") != expected_patch:
                errors.append(f"[{lbl} p.{pno}] patch_pos={kp.get('patch_pos')!r} != expected {expected_patch!r}")

            w_img = kp.get("image", "")
            img_path = ROOT / w_img
            if not w_img.endswith(f"wc_p{pno:02d}.jpg") or not img_path.exists():
                errors.append(f"[{lbl} p.{pno}] missing watercolor image wc_p{pno:02d}.jpg: {w_img}")
            elif img_path.stat().st_size < 512:
                errors.append(f"[{lbl} p.{pno}] watercolor image too small ({img_path.stat().st_size} B): {w_img}")
            else:
                try:
                    with Image.open(img_path) as im:
                        if im.size != (896, 1200) or im.mode != "RGB" or im.format != "JPEG":
                            errors.append(
                                f"[{lbl} p.{pno}] expected 896x1200 RGB JPEG, got {im.size} {im.mode} {im.format}: {w_img}"
                            )
                except Exception as e:
                    errors.append(f"[{lbl} p.{pno}] invalid image {w_img}: {e}")

            xray_img = kp.get("hover_reveal_image")
            if sid == "le-petit-prince" and pno == 1:
                if kp.get("is_frontispiece") is not True or kp.get("display_page") != 0:
                    errors.append(f"[{lbl} p.1] expected is_frontispiece=True and display_page=0")
                if xray_img is not None:
                    errors.append(f"[{lbl} p.1] frontispiece must NOT have hover_reveal_image: {xray_img!r}")
            if sid == "le-petit-prince" and pno == 3:
                if xray_img != "books/petit-prince/wc_p03_xray.jpg":
                    errors.append(f"[{lbl} p.3] expected hover_reveal_image='books/petit-prince/wc_p03_xray.jpg', got {xray_img!r}")
            if xray_img is not None:
                xray_str = str(xray_img).strip()
                xray_path = ROOT / xray_str
                if not xray_str or not xray_path.exists():
                    errors.append(f"[{lbl} p.{pno}] missing hover_reveal_image: {xray_img}")
                elif xray_path.stat().st_size < 512:
                    errors.append(f"[{lbl} p.{pno}] hover_reveal_image too small ({xray_path.stat().st_size} B): {xray_img}")
                else:
                    try:
                        with Image.open(xray_path) as im:
                            if im.size != (896, 1200) or im.mode != "RGB" or im.format != "JPEG":
                                errors.append(
                                    f"[{lbl} p.{pno}] hover_reveal_image expected 896x1200 RGB JPEG, got {im.size} {im.mode} {im.format}: {xray_img}"
                                )
                    except Exception as e:
                        errors.append(f"[{lbl} p.{pno}] invalid hover_reveal_image {xray_img}: {e}")

            is_front = bool(kp.get("is_frontispiece"))
            for lvl in spec["json_levels"]:
                if "en" in (kp.get("levels", {}).get(lvl) or {}):
                    errors.append(f"[{lbl} p.{pno} {lvl}] Constitution violation: 'en' must NOT exist inside page.levels.{lvl}")

            if not is_front:
                for klang in ("fr", "it", "de"):
                    for lvl in spec["json_levels"]:
                        ldata = kp.get("levels", {}).get(lvl, {}).get(klang, {})
                        if not ldata.get("text") or not ldata.get("tokens"):
                            errors.append(f"[{lbl} p.{pno} {lvl} {klang}] missing text or tokens")
                        for ext_key in ("audio_mp3", "audio_ogg"):
                            arel = ldata.get(ext_key)
                            afp = (ROOT / arel) if arel else None
                            if not arel or not afp or not afp.exists() or afp.stat().st_size < 512:
                                errors.append(f"[{lbl} p.{pno} {lvl} {klang}] missing/small {ext_key}: {arel}")
                            elif not has_valid_audio_magic(afp, ext_key):
                                errors.append(f"[{lbl} p.{pno} {lvl} {klang}] invalid {ext_key} magic header: {arel}")

                        # Strict word-audio coverage for EVERY book (Sardegna + Le Petit Prince),
                        # EVERY level, and EVERY non-punctuation word token across FR/IT/DE.
                        # Minimum 1500B MP3 / 500B OGG catches 720B silent edge-tts stubs immediately!
                        for tok in ldata.get("tokens") or []:
                            w_txt = str(tok.get("w") or "")
                            if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]", w_txt):
                                continue
                            for w_ext, min_sz in (("audio_mp3", 1500), ("audio_ogg", 500)):
                                w_rel = tok.get(w_ext)
                                w_fp = (ROOT / w_rel) if w_rel else None
                                if not w_rel or not w_fp or not w_fp.exists() or w_fp.stat().st_size < min_sz:
                                    sz = w_fp.stat().st_size if (w_fp and w_fp.exists()) else 0
                                    errors.append(
                                        f"[{lbl} p.{pno} {lvl} {klang}] token {w_txt!r} missing/tiny/silent {w_ext} ({sz}B < {min_sz}B): {w_rel}"
                                    )
                                elif not has_valid_audio_magic(w_fp, w_ext):
                                    errors.append(
                                        f"[{lbl} p.{pno} {lvl} {klang}] token {w_txt!r} invalid {w_ext} magic header: {w_rel}"
                                    )

                        if sid == "le-petit-prince":
                            words_cnt = len(str(ldata.get("text") or "").split())
                            if lvl == "seby":
                                w_min, w_max = 14, 25
                            elif lvl == "ale":
                                w_min, w_max = 26, 42
                            else:
                                w_min, w_max = (40, 55) if expected_patch == "top" else (40, 64)
                            if not (w_min <= words_cnt <= w_max):
                                errors.append(
                                    f"[{lbl} p.{pno} {lvl} {klang}] CEFR word count {words_cnt} outside [{w_min}, {w_max}] ({expected_patch})"
                                )

                            sep_groups: dict[str, list[dict]] = {}
                            for tok in ldata.get("tokens") or []:
                                sg = tok.get("sep_group")
                                if sg:
                                    sep_groups.setdefault(sg, []).append(tok)
                            for sg, sg_toks in sep_groups.items():
                                roles = sorted(str(t.get("sep_role") or "") for t in sg_toks)
                                if roles != ["prefix", "stem"]:
                                    errors.append(f"[{lbl} p.{pno} {lvl} {klang}] sep_group {sg!r} roles={roles} != ['prefix', 'stem']")
                                for t in sg_toks:
                                    if not str(t.get("sep_inf") or "").strip() or not str(t.get("sep_pair") or "").strip():
                                        errors.append(
                                            f"[{lbl} p.{pno} {lvl} {klang}] sep_group {sg!r} missing sep_inf/sep_pair on {t.get('w')!r}"
                                        )

            sb = kp.get("speech_bubble") or {}
            if isinstance(sb, dict):
                for klang in ("fr", "it", "de"):
                    sb_lang = sb.get(klang)
                    if isinstance(sb_lang, dict) and sb_lang.get("text"):
                        for ext_key in ("audio_mp3", "audio_ogg"):
                            arel = sb_lang.get(ext_key)
                            afp = (ROOT / arel) if arel else None
                            if not arel or not afp or not afp.exists() or afp.stat().st_size < 512:
                                errors.append(f"[{lbl} p.{pno} bubble {klang}] missing/small {ext_key}: {arel}")
                            elif not has_valid_audio_magic(afp, ext_key):
                                errors.append(f"[{lbl} p.{pno} bubble {klang}] invalid {ext_key} magic header: {arel}")
                sb_en = sb.get("en")
                if isinstance(sb_en, dict) and (sb_en.get("audio_mp3") or sb_en.get("audio_ogg")):
                    errors.append(f"[{lbl} p.{pno}] Constitution violation: speech_bubble.en must NOT declare studio audio")

            tr_en = (kp.get("translations") or {}).get("en") or {}
            if spec["require_en_tr"] and not is_front:
                for lvl in ("seby", "ale", "emma"):
                    tr_entry = tr_en.get(lvl) or {}
                    if not str(tr_entry.get("text") or "").strip():
                        errors.append(f"[{lbl} p.{pno} {lvl}] missing translations.en text")
                    if tr_entry.get("audio_mp3") or tr_entry.get("audio_ogg"):
                        errors.append(f"[{lbl} p.{pno} {lvl}] Constitution violation: translations.en must NOT declare studio audio")

            qmap = kp.get("questions") or {}
            if "en" in qmap:
                errors.append(f"[{lbl} p.{pno}] Constitution violation: 'en' must NOT exist inside page.questions")
            if pno in spec["quiz_pages"]:
                for klang in ("fr", "it", "de"):
                    qs = qmap.get(klang, [])
                    if len(qs) != 3:
                        errors.append(f"[{lbl} p.{pno} {klang}] expected 3 Antolin questions, got {len(qs)}")
            else:
                if qmap:
                    errors.append(f"[{lbl} p.{pno}] expected empty/null questions on non-quiz page, got {list(qmap.keys())}")

    # Global zero-EN-words-audio check (French assets/words_audio/fr/n_en.* is valid French, NOT EN!)
    if (ROOT / "assets/words_audio/en").exists():
        errors.append("Constitution violation: assets/words_audio/en directory must NOT exist")

    books_dir = ROOT / "books"
    if books_dir.exists():
        en_books_audio = [
            str(p.relative_to(ROOT))
            for p in books_dir.rglob("*")
            if p.is_file() and p.name.startswith("en_") and p.suffix.lower() in (".mp3", ".ogg")
        ]
        if en_books_audio:
            errors.append(f"Constitution violation: recursive books/ EN audio files found: {en_books_audio[:5]}")

    # Version, cache-busters (?v=<VERSION>), and README copyright transparency check
    version_path = ROOT / "VERSION"
    if not version_path.exists():
        errors.append("Missing VERSION file")
    else:
        repo_version = version_path.read_text(encoding="utf-8").strip()
        index_html_path = ROOT / "index.html"
        if index_html_path.exists():
            idx_src = index_html_path.read_text(encoding="utf-8")
            m_app_ver = re.search(r"const\s+APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", idx_src)
            if not m_app_ver or m_app_ver.group(1) != repo_version:
                errors.append(
                    f"VERSION ({repo_version!r}) != APP_VERSION in index.html ({m_app_ver.group(1) if m_app_ver else None!r})"
                )
            for cat_script in ("stories_catalog.js", "kids_books_catalog.js"):
                expected_tag = f"{cat_script}?v={repo_version}"
                if expected_tag not in idx_src:
                    errors.append(f"index.html missing cache-busted catalog script {expected_tag!r}")
        books_index_path = ROOT / "books/index.html"
        if books_index_path.exists():
            bidx_src = books_index_path.read_text(encoding="utf-8")
            expected_tag = f"kids_books_catalog.js?v={repo_version}"
            if expected_tag not in bidx_src:
                errors.append(f"books/index.html missing cache-busted catalog script {expected_tag!r}")

    readme_path = ROOT / "README.md"
    if not readme_path.exists():
        errors.append("Missing README.md")
    else:
        readme_txt = readme_path.read_text(encoding="utf-8")
        if "2015" not in readme_txt or "2032" not in readme_txt:
            errors.append("README.md missing CH/EU (2015) / France (2032) public-domain transparency note")

    # Docs, Bookshelf & Cover plate checks
    const_path = ROOT / "docs/CONSTITUTION.md"
    if not const_path.exists() or const_path.stat().st_size < 512:
        errors.append("Missing or incomplete docs/CONSTITUTION.md")
    else:
        const_txt = const_path.read_text(encoding="utf-8")
        for tok in ("FR", "IT", "DE", "en-GB"):
            if tok not in const_txt:
                errors.append(f"docs/CONSTITUTION.md missing required token: {tok}")

    books_index = ROOT / "books/index.html"
    if not books_index.exists() or books_index.stat().st_size < 512:
        errors.append("Missing or incomplete books/index.html")

    for cover_rel in ("books/covers/sardegna.jpg", "books/covers/petit-prince.jpg"):
        cp = ROOT / cover_rel
        if not cp.exists() or cp.stat().st_size < 512:
            errors.append(f"Missing or incomplete bookshelf cover: {cover_rel}")
        else:
            try:
                with Image.open(cp) as im:
                    if im.size != (896, 1200) or im.mode != "RGB" or im.format != "JPEG":
                        errors.append(f"Cover {cover_rel} expected 896x1200 RGB JPEG, got {im.size} {im.mode} {im.format}")
            except Exception as e:
                errors.append(f"Invalid cover image {cover_rel}: {e}")

    # 4. Validate standalone story pages (stories/*/*/index.html): audio player non-collapse CSS, direct src, valid media, and JS syntax
    standalone_htmls = sorted((ROOT / "stories").glob("*/*/index.html"))
    for shp in standalone_htmls:
        rel_shp = shp.relative_to(ROOT)
        sh_src = shp.read_text(encoding="utf-8")
        if 'http-equiv="refresh"' in sh_src.lower():
            continue
        if ".audio-lang-item" not in sh_src or "min-width" not in sh_src:
            errors.append(f"[{rel_shp}] missing .audio-lang-item / min-width anti-collapse CSS for <audio> controls")
        if 'preload="none"' in sh_src:
            errors.append(f"[{rel_shp}] <audio> uses preload=\"none\" (causes 0:00 / 0:00 display)")
        audio_tags = re.findall(r"<audio\b[^>]*>", sh_src)
        if len(audio_tags) < 3:
            errors.append(f"[{rel_shp}] expected >= 3 narrated <audio> tags (IT/en-GB/FR), got {len(audio_tags)}")
        for atag in audio_tags:
            m_src = re.search(r'\bsrc="([^"]+)"', atag)
            if not m_src:
                errors.append(f"[{rel_shp}] <audio> tag missing direct src=\"...\" attribute: {atag}")
                continue
            media_path = shp.parent / m_src.group(1)
            if not media_path.exists() or media_path.stat().st_size < 1024:
                errors.append(f"[{rel_shp}] <audio src=\"{m_src.group(1)}\"> missing or empty on disk")
        if "HOSTED_BASE" not in sh_src:
            errors.append(f"[{rel_shp}] missing HOSTED_BASE fallback script for non-HTTP local HTML viewers")

    # 5. Validate JavaScript syntax in index.html, netflix.html, ring.html, books/index.html, standalone story pages, and kids_books_catalog.js via `node --check`
    all_html_targets = [ROOT / n for n in ("index.html", "netflix.html", "ring.html", "books/index.html")] + standalone_htmls
    for hp in all_html_targets:
        if not hp.exists():
            continue
        rel_name = hp.relative_to(ROOT)
        html_src = hp.read_text(encoding="utf-8")
        scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", html_src, re.S)
        for s_idx, script_body in enumerate(scripts):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
                tf.write(script_body)
                tmp_js = Path(tf.name)
            chk = subprocess.run(["node", "--check", str(tmp_js)], capture_output=True, text=True)
            tmp_js.unlink(missing_ok=True)
            if chk.returncode != 0:
                errors.append(f"[{rel_name} inline script #{s_idx}] JS SyntaxError:\n{chk.stderr.strip()}")

    if cat_js.exists():
        chk = subprocess.run(["node", "--check", str(cat_js)], capture_output=True, text=True)
        if chk.returncode != 0:
            errors.append(f"[kids_books_catalog.js] JS SyntaxError:\n{chk.stderr.strip()}")

    print("-" * 110)
    if errors:
        print(f"\n❌ TEST SUITE FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"\n✅ ALL {len(stories)} STORIES + 16-PAGE SARDEGNA + 26-PAGE LE PETIT PRINCE WATERCOLOR BOOKS (FR/IT/DE) PASSED 100% DETERMINISTIC CHECKS!"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
