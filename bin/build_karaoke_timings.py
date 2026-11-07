#!/usr/bin/env python3
"""
Builds high-precision word-by-word Karaoke timing JSON files (`karaoke_it.json`, `karaoke_en.json`)
for Kids' Own Stories by analyzing the pure 24kHz unmixed voice WAV tracks (or filtered MP3s),
detecting exact page boundaries, sentence/phrase pauses (VAD), and syllable-weighted word intervals.

Also adds optional support for FR, DE, PT-BR when unlocked by Story Vote >= 8/10.
"""

import json
import math
import re
import struct
import subprocess
import wave
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
INTRO_DELAY_SEC = 1.20  # adelay=1200|1200 applied during mix_voice_with_piano


def load_pcm_24k_mono(wav_or_mp3: Path) -> list[float]:
    """Loads 24kHz mono float samples [-1.0, 1.0] from WAV or MP3."""
    if wav_or_mp3.suffix.lower() == ".wav" and wav_or_mp3.exists():
        with wave.open(str(wav_or_mp3), "rb") as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
            ints = struct.unpack(f"<{n}h", raw)
            return [x / 32768.0 for x in ints]
    # Fallback: decode mp3 via ffmpeg to 24kHz mono s16le
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(wav_or_mp3),
        "-f", "s16le", "-ac", "1", "-ar", "24000", "-"
    ]
    raw = subprocess.check_output(cmd)
    n = len(raw) // 2
    ints = struct.unpack(f"<{n}h", raw)
    return [x / 32768.0 for x in ints]


def compute_rms_envelope(samples: list[float], sample_rate: int = 24000, win_ms: int = 10) -> list[float]:
    """Computes RMS energy per 10ms frame."""
    step = int(sample_rate * win_ms / 1000)
    n_frames = len(samples) // step
    rms = []
    for i in range(n_frames):
        chunk = samples[i * step:(i + 1) * step]
        s = sum(x * x for x in chunk)
        rms.append(math.sqrt(s / len(chunk)))
    return rms


def estimate_word_weight(word: str) -> float:
    """Estimates spoken duration weight of a word based on vowel nuclei, length, and punctuation."""
    clean = re.sub(r"[^\wÀ-ÿ]", "", word)
    if not clean:
        return 0.4
    vowels = len(re.findall(r"[aeiouyàèéìòóùäöüãõâêîôû]+", clean.lower()))
    syllables = max(1, vowels)
    weight = syllables * 0.65 + len(clean) * 0.09
    # Add natural micro-pause weight if word ends with punctuation
    if re.search(r"[.!?…»”]$", word):
        weight += 0.45
    elif re.search(r"[,;:—–]$", word):
        weight += 0.22
    return weight


def split_page_boundaries(rms: list[float], pages: list[dict], lang: str, win_sec: float = 0.01) -> list[tuple[float, float]]:
    """
    Finds the N-1 page boundaries in the voice track by locating the longest silence gaps
    near the expected cumulative character/word ratios of the pages.
    """
    total_frames = len(rms)
    total_dur = total_frames * win_sec

    # Trim leading and trailing silence in the raw voice track
    thresh = 0.008
    first_voiced = 0
    while first_voiced < total_frames and rms[first_voiced] < thresh:
        first_voiced += 1
    last_voiced = total_frames - 1
    while last_voiced > first_voiced and rms[last_voiced] < thresh:
        last_voiced -= 1

    # Compute expected weight of each page (including story title on page 1)
    page_weights = []
    for idx, p in enumerate(pages):
        title_txt = p.get("title_en" if lang == "en" else f"title_{lang}" if lang != "it" else "title", p.get("title", ""))
        paras = p.get(f"paragraphs_{lang}", [])
        full_txt = f"{title_txt} " + " ".join(paras)
        words = full_txt.split()
        w = sum(estimate_word_weight(tok) for tok in words)
        if idx == 0:
            w += 3.5  # Story main title spoken before page 1 title
        page_weights.append(w)

    total_w = sum(page_weights)
    cum_w = 0.0
    boundaries = [first_voiced * win_sec]

    # Find silence runs (consecutive frames below threshold)
    is_silent = [1 if r < thresh else 0 for r in rms]

    for i in range(len(pages) - 1):
        cum_w += page_weights[i]
        expected_ratio = cum_w / total_w
        expected_sec = (first_voiced * win_sec) + expected_ratio * ((last_voiced - first_voiced) * win_sec)
        expected_frame = int(expected_sec / win_sec)

        # Search window: +/- 18% of total duration around expected_frame
        search_radius = int(0.18 * total_frames)
        lo = max(first_voiced + 50, expected_frame - search_radius)
        hi = min(last_voiced - 50, expected_frame + search_radius)

        # Find all silence intervals in [lo, hi]
        best_mid_frame = expected_frame
        best_score = -1.0
        idx_f = lo
        while idx_f < hi:
            if is_silent[idx_f]:
                start_f = idx_f
                while idx_f < hi and is_silent[idx_f]:
                    idx_f += 1
                end_f = idx_f
                dur_frames = end_f - start_f
                mid_f = (start_f + end_f) // 2
                # Prefer silence gaps >= 55 frames (0.55s, matching our 0.65s inter-page silence)
                # weighted by proximity to expected_frame
                dist_penalty = abs(mid_f - expected_frame) / float(search_radius + 1)
                score = (dur_frames * win_sec) * (1.35 - 0.65 * dist_penalty)
                if score > best_score:
                    best_score = score
                    best_mid_frame = mid_f
            else:
                idx_f += 1

        boundaries.append(best_mid_frame * win_sec)

    boundaries.append(last_voiced * win_sec)

    # Convert to (start_sec, end_sec) per page, trimming silence at edges of each page
    page_spans = []
    for i in range(len(pages)):
        s_frame = int(boundaries[i] / win_sec)
        e_frame = int(boundaries[i + 1] / win_sec)
        while s_frame < e_frame and rms[s_frame] < thresh:
            s_frame += 1
        while e_frame > s_frame and rms[e_frame - 1] < thresh:
            e_frame -= 1
        page_spans.append((s_frame * win_sec, e_frame * win_sec))

    return page_spans


def align_words_in_span(
    rms: list[float],
    span_start_sec: float,
    span_end_sec: float,
    segments_words: list[list[str]],
    win_sec: float = 0.01,
    offset_sec: float = INTRO_DELAY_SEC,
) -> list[list[dict]]:
    """
    Given a voice time span [span_start_sec, span_end_sec] and a list of segments
    (e.g. [story_title_words, page_title_words, para1_words, para2_words, para3_words]),
    detects natural phrase pauses in the RMS envelope to anchor segment boundaries
    and distributes words within each voiced phrase using syllable-weighted energy alignment.
    """
    s_frame = int(span_start_sec / win_sec)
    e_frame = int(span_end_sec / win_sec)
    thresh = 0.008

    # First, find K-1 pause boundaries for the K segments (title + paragraphs)
    # using cumulative voiced energy so expected positions are immune to silence skew
    seg_weights = [max(0.5, sum(estimate_word_weight(w) for w in seg)) for seg in segments_words]
    total_seg_w = sum(seg_weights)

    page_voiced_cum = [0.0]
    for f in range(s_frame, e_frame):
        page_voiced_cum.append(page_voiced_cum[-1] + (1.0 if rms[f] >= thresh else 0.08))
    total_page_voiced = page_voiced_cum[-1] or 1.0

    def page_voiced_to_frame(v_target: float) -> int:
        lo_i, hi_i = 0, len(page_voiced_cum) - 1
        while lo_i < hi_i:
            mid_i = (lo_i + hi_i) // 2
            if page_voiced_cum[mid_i] < v_target:
                lo_i = mid_i + 1
            else:
                hi_i = mid_i
        return s_frame + lo_i

    seg_frames = [s_frame]
    cum_w = 0.0

    for k in range(len(segments_words) - 1):
        cum_w += seg_weights[k]
        target_v = (cum_w / total_seg_w) * total_page_voiced
        exp_f = page_voiced_to_frame(target_v)
        # Tight search window: +/- 1.2s for short titles, +/- 2.4s for full paragraphs
        radius = 120 if len(segments_words[k]) <= 14 else 240
        lo = max(seg_frames[-1] + 20, exp_f - radius)
        hi = min(e_frame - 20, exp_f + radius)

        # Find best pause in [lo, hi]
        best_f = exp_f
        best_score = -1.0
        f = lo
        while f < hi:
            if rms[f] < thresh:
                st = f
                while f < hi and rms[f] < thresh:
                    f += 1
                en = f
                dur = en - st
                mid = (st + en) // 2
                dist = abs(mid - exp_f) / float(radius + 1)
                sc = min(dur, 65) * (1.35 - 0.75 * dist)
                if sc > best_score:
                    best_score = sc
                    best_f = mid
            else:
                f += 1
        seg_frames.append(best_f)

    seg_frames.append(e_frame)

    # Now align words inside each segment using voiced frames
    aligned_segments = []
    for k, words in enumerate(segments_words):
        if not words:
            aligned_segments.append([])
            continue
        k_start = seg_frames[k]
        k_end = seg_frames[k + 1]
        while k_start < k_end and rms[k_start] < thresh:
            k_start += 1
        while k_end > k_start and rms[k_end - 1] < thresh:
            k_end -= 1

        #Now align words inside each segment by mapping words ONLY onto voiced frames
        # and skipping natural breath/punctuation pauses (>= 100ms of silence)!
        voiced_mask = []
        f_idx = k_start
        while f_idx < k_end:
            if rms[f_idx] < thresh:
                s_run = f_idx
                while f_idx < k_end and rms[f_idx] < thresh:
                    f_idx += 1
                run_len = f_idx - s_run
                # If silence run >= 10 frames (100ms), it's a breath/phrase pause (weight 0.02)
                # Shorter dips (< 100ms) are plosive consonants inside words (weight 0.5)
                w_val = 0.02 if run_len >= 10 else 0.5
                voiced_mask.extend([w_val] * run_len)
            else:
                # Weight voiced frames slightly by energy + constant speech rate
                voiced_mask.append(1.0)
                f_idx += 1

        if not voiced_mask:
            voiced_mask = [1.0]
            k_end = k_start + 1

        # Build cumulative voiced progress array over [k_start, k_end]
        cum_voiced = [0.0]
        for v in voiced_mask:
            cum_voiced.append(cum_voiced[-1] + v)
        total_voiced = cum_voiced[-1] or 1.0

        # Pure phonetic weight (without punctuation pause padding, since pauses are in voiced_mask!)
        def pure_word_weight(w_tok: str) -> float:
            clean = re.sub(r"[^\wÀ-ÿ]", "", w_tok)
            if not clean:
                return 0.35
            vowels = len(re.findall(r"[aeiouyàèéìòóùäöüãõâêîôû]+", clean.lower()))
            return max(1, vowels) * 0.68 + len(clean) * 0.08

        weights = [pure_word_weight(w) for w in words]
        w_sum = sum(weights) or 1.0

        def voiced_target_to_sec(v_target: float) -> float:
            # Binary search in cum_voiced
            lo_i, hi_i = 0, len(voiced_mask)
            while lo_i < hi_i:
                mid_i = (lo_i + hi_i) // 2
                if cum_voiced[mid_i] < v_target:
                    lo_i = mid_i + 1
                else:
                    hi_i = mid_i
            return (k_start + lo_i) * win_sec + offset_sec

        cur_v = 0.0
        word_items = []
        for w_idx, w_str in enumerate(words):
            w_v = total_voiced * (weights[w_idx] / w_sum)
            nxt_v = cur_v + w_v
            # Snap word start to the first actually voiced frame if cur_v falls inside a breath pause
            s_sec = voiced_target_to_sec(cur_v + w_v * 0.04)
            e_sec = voiced_target_to_sec(nxt_v - w_v * 0.02)
            if e_sec <= s_sec:
                e_sec = round(s_sec + 0.12, 2)
            word_items.append({
                "w": w_str,
                "s": round(s_sec, 2),
                "e": round(e_sec, 2),
            })
            cur_v = nxt_v
        aligned_segments.append(word_items)

    return aligned_segments


def build_karaoke_for_story_lang(story: dict, lang: str):
    slug = story["slug"]
    folder = ROOT / story["folder"]
    raw_wav = Path(f"/tmp/{slug}_voice_{lang}.wav")
    narrated_mp3 = folder / f"narrated_{lang}.mp3"

    source_audio = raw_wav if raw_wav.exists() else narrated_mp3
    if not source_audio.exists():
        print(f"⚠️ Skipping {slug} [{lang}] — no audio found at {source_audio}")
        return None

    is_raw_wav = (source_audio == raw_wav)
    offset = INTRO_DELAY_SEC if is_raw_wav else 0.0

    samples = load_pcm_24k_mono(source_audio)
    rms = compute_rms_envelope(samples, 24000, win_ms=10)

    pages = story["assets"]["pages"]
    page_spans = split_page_boundaries(rms, pages, lang, win_sec=0.01)

    story_title = story.get("title_en" if lang == "en" else f"title_{lang}" if lang != "it" else "title", story["title"])

    pages_out = []
    for idx, p in enumerate(pages):
        p_start, p_end = page_spans[idx]
        page_title = p.get("title_en" if lang == "en" else f"title_{lang}" if lang != "it" else "title", p["title"])
        paras = p.get(f"paragraphs_{lang}", [])

        segments_words = []
        if idx == 0:
            segments_words.append(story_title.split())
        segments_words.append(page_title.split())
        for para in paras:
            segments_words.append(para.split())

        aligned = align_words_in_span(rms, p_start, p_end, segments_words, win_sec=0.01, offset_sec=offset)

        if idx == 0:
            story_title_aligned = aligned[0]
            page_title_aligned = aligned[1]
            paras_aligned = aligned[2:]
        else:
            story_title_aligned = []
            page_title_aligned = aligned[0]
            paras_aligned = aligned[1:]

        pages_out.append({
            "page": p["page"],
            "start": round(p_start + offset, 2),
            "end": round(p_end + offset, 2),
            "story_title_words": story_title_aligned,
            "title_words": page_title_aligned,
            "paragraphs": paras_aligned,
        })

    out_data = {
        "story_slug": slug,
        "lang": lang,
        "intro_delay_sec": INTRO_DELAY_SEC,
        "pages": pages_out,
    }

    out_json = folder / f"karaoke_{lang}.json"
    out_json.write_text(json.dumps(out_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Saved Karaoke timings: {out_json.relative_to(ROOT)} ({len(pages_out)} pages, source={source_audio.name})")
    return out_json


def main():
    catalog = yaml.safe_load((ROOT / "stories.yaml").read_text(encoding="utf-8"))
    for story in catalog.get("stories", []):
        for lang in ("it", "en"):
            build_karaoke_for_story_lang(story, lang)


if __name__ == "__main__":
    main()
