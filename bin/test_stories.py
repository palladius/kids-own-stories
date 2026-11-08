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
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parent.parent


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

    print("-" * 110)
    if errors:
        print(f"\n❌ TEST SUITE FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"\n✅ ALL {len(stories)} STORIES PASSED 100% DETERMINISTIC INTEGRITY CHECKS!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
