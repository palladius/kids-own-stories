#!/home/linuxbrew/.linuxbrew/Cellar/openai-whisper/20250625_4/libexec/bin/python
"""
Builds high-precision acoustic word-by-word Karaoke timing JSON files (`karaoke_it.json`, `karaoke_en.json`)
for Kids' Own Stories by combining:
1. Exact digital-zero inter-page splice detection (`0.65s` zero-sample gaps inserted between pages).
2. Acoustic word timestamp extraction via OpenAI Whisper (`word_timestamps=True`) per page.
3. Needleman-Wunsch dynamic programming sequence alignment between the ground-truth story text
   (story title, chapter title, and paragraphs) and Whisper's recognized word timestamps, with
   monotonic interpolation for any unaligned tokens.
"""

from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
import json
import math
import re
import struct
import subprocess
import wave
from pathlib import Path
import numpy as np
import whisper

ROOT = Path(__file__).resolve().parent.parent
INTRO_DELAY_SEC = 1.20  # adelay=1200|1200 applied during mix_voice_with_piano


def load_stories_yaml() -> dict:
    """Loads stories.yaml using system python3 PyYAML."""
    cmd = [
        "/usr/bin/python3",
        "-c",
        "import yaml, json, sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))",
        str(ROOT / "stories.yaml"),
    ]
    out = subprocess.check_output(cmd).decode("utf-8")
    return json.loads(out)


def load_pcm_24k_mono(wav_or_mp3: Path) -> np.ndarray:
    """Loads 24kHz mono float32 samples [-1.0, 1.0] from WAV or MP3."""
    if wav_or_mp3.suffix.lower() == ".wav" and wav_or_mp3.exists():
        with wave.open(str(wav_or_mp3), "rb") as wf:
            n = wf.getnframes()
            raw = wf.readframes(n)
            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(wav_or_mp3),
        "-f", "s16le", "-ac", "1", "-ar", "24000", "-"
    ]
    raw = subprocess.check_output(cmd)
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def compute_rms_envelope(samples: np.ndarray, sample_rate: int = 24000, win_ms: int = 10) -> list[float]:
    """Computes RMS energy per 10ms frame."""
    step = int(sample_rate * win_ms / 1000)
    n_frames = len(samples) // step
    trimmed = samples[: n_frames * step].reshape(n_frames, step)
    rms = np.sqrt(np.mean(trimmed * trimmed, axis=1))
    return rms.tolist()


def split_exact_page_boundaries(
    samples: np.ndarray, rms: list[float], n_pages: int, sample_rate: int = 24000, win_sec: float = 0.01
) -> list[tuple[float, float]]:
    """
    Detects the exact N-1 inter-page 0.65s zero-sample splices in the raw voice WAV.
    Falls back to longest RMS silences if reading from a piano-mixed MP3.
    """
    n_samples = len(samples)
    abs_s = np.abs(samples)
    zero_runs = []
    i = 0
    while i < n_samples:
        if abs_s[i] <= 0.00015:
            s = i
            while i < n_samples and abs_s[i] <= 0.00015:
                i += 1
            dur = (i - s) / float(sample_rate)
            if dur >= 0.45:
                zero_runs.append((s / float(sample_rate), i / float(sample_rate), dur))
        else:
            i += 1

    thresh = 0.008
    total_frames = len(rms)

    if len(zero_runs) == n_pages - 1:
        starts = [0.0] + [zr[1] for zr in zero_runs]
        ends = [zr[0] for zr in zero_runs] + [n_samples / float(sample_rate)]
        spans = []
        for ps, pe in zip(starts, ends):
            sf = max(0, int(ps / win_sec))
            ef = min(total_frames, int(pe / win_sec))
            while sf < ef and rms[sf] < thresh:
                sf += 1
            while ef > sf and rms[ef - 1] < thresh:
                ef -= 1
            spans.append((sf * win_sec, ef * win_sec))
        return spans

    # Fallback if more/fewer zero_runs found: pick the N-1 longest silence gaps well-spaced across track
    first_voiced = 0
    while first_voiced < total_frames and rms[first_voiced] < thresh:
        first_voiced += 1
    last_voiced = total_frames - 1
    while last_voiced > first_voiced and rms[last_voiced] < thresh:
        last_voiced -= 1

    boundaries = [first_voiced * win_sec]
    for k in range(1, n_pages):
        exp_f = first_voiced + int((k / float(n_pages)) * (last_voiced - first_voiced))
        rad = int(0.16 * total_frames)
        lo = max(first_voiced + 50, exp_f - rad)
        hi = min(last_voiced - 50, exp_f + rad)
        best_mid = exp_f
        best_dur = -1
        f = lo
        while f < hi:
            if rms[f] < thresh:
                st = f
                while f < hi and rms[f] < thresh:
                    f += 1
                en = f
                if (en - st) > best_dur:
                    best_dur = en - st
                    best_mid = (st + en) // 2
            else:
                f += 1
        boundaries.append(best_mid * win_sec)
    boundaries.append(last_voiced * win_sec)

    spans = []
    for k in range(n_pages):
        sf = int(boundaries[k] / win_sec)
        ef = int(boundaries[k + 1] / win_sec)
        while sf < ef and rms[sf] < thresh:
            sf += 1
        while ef > sf and rms[ef - 1] < thresh:
            ef -= 1
        spans.append((sf * win_sec, ef * win_sec))
    return spans


def norm_word(w: str) -> str:
    """Normalizes a word token for acoustic-to-text alignment."""
    return re.sub(r"[^\wÀ-ÿ]", "", w.lower())


def word_sim(a: str, b: str) -> float:
    """Returns similarity score in [-0.6, 1.5] between two normalized words."""
    na, nb = norm_word(a), norm_word(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.5
    if na in nb or nb in na:
        return 1.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    return (ratio * 1.6) - 0.55


def transcribe_page_words(
    model, samples_24k: np.ndarray, p_start_sec: float, p_end_sec: float, lang: str
) -> list[dict]:
    """Slices a page from 24kHz audio, resamples to 16kHz, and extracts Whisper word timestamps."""
    s_idx = max(0, int(p_start_sec * 24000))
    e_idx = min(len(samples_24k), int(p_end_sec * 24000))
    slice_24k = samples_24k[s_idx:e_idx]
    if len(slice_24k) < 400:
        return []

    target_len = int(len(slice_24k) * 16000 / 24000)
    x_old = np.arange(len(slice_24k), dtype=np.float32)
    x_new = np.linspace(0, len(slice_24k) - 1, target_len, dtype=np.float32)
    slice_16k = np.interp(x_new, x_old, slice_24k).astype(np.float32)

    res = model.transcribe(
        slice_16k,
        language=lang,
        word_timestamps=True,
        fp16=False,
        condition_on_previous_text=False,
    )
    words = []
    for seg in res.get("segments", []):
        for w in seg.get("words", []):
            tok = w.get("word", "").strip()
            if tok:
                words.append({
                    "w": tok,
                    "s": float(w["start"]) + p_start_sec,
                    "e": float(w["end"]) + p_start_sec,
                })
    return words


def align_ground_truth_to_whisper(
    segments_words: list[list[str]],
    whisper_words: list[dict],
    p_start_sec: float,
    p_end_sec: float,
    offset_sec: float = INTRO_DELAY_SEC,
) -> list[list[dict]]:
    """
    Aligns ground-truth segment words (story title, page title, paragraphs) to Whisper's
    acoustic word timestamps using Needleman-Wunsch dynamic programming, then interpolates
    any unmatched tokens monotonically within their segment bounds.
    """
    flat_gt = []
    for seg_i, seg in enumerate(segments_words):
        for w_i, w_str in enumerate(seg):
            flat_gt.append({"seg": seg_i, "idx": w_i, "w": w_str})

    n = len(flat_gt)
    m = len(whisper_words)
    if n == 0:
        return [[] for _ in segments_words]

    # Needleman-Wunsch DP table
    gap_penalty = -0.32
    dp = np.zeros((n + 1, m + 1), dtype=np.float32)
    ptr = np.zeros((n + 1, m + 1), dtype=np.int8)  # 1: diag, 2: up (skip gt), 3: left (skip whisper)

    for i in range(1, n + 1):
        dp[i, 0] = i * gap_penalty
        ptr[i, 0] = 2
    for j in range(1, m + 1):
        dp[0, j] = j * gap_penalty
        ptr[0, j] = 3

    for i in range(1, n + 1):
        gt_w = flat_gt[i - 1]["w"]
        pos_ratio_gt = i / float(n)
        for j in range(1, m + 1):
            pos_ratio_wh = j / float(max(1, m))
            # Band penalty so words cannot match wildly out of position
            if abs(pos_ratio_gt - pos_ratio_wh) > 0.28:
                sim = -1.5
            else:
                sim = word_sim(gt_w, whisper_words[j - 1]["w"])
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

    # Backtrack matches
    matched_wh = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        mv = ptr[i, j]
        if mv == 1:
            if word_sim(flat_gt[i - 1]["w"], whisper_words[j - 1]["w"]) >= 0.25:
                matched_wh[i - 1] = j - 1
            i -= 1
            j -= 1
        elif mv == 2:
            i -= 1
        else:
            j -= 1

    # Assign raw (s, e) from matched Whisper words and interpolate gaps
    times = [None] * n
    for idx_gt, wh_idx in enumerate(matched_wh):
        if wh_idx is not None:
            w_obj = whisper_words[wh_idx]
            s_val = max(p_start_sec, min(p_end_sec, w_obj["s"]))
            e_val = max(s_val + 0.06, min(p_end_sec, w_obj["e"]))
            times[idx_gt] = (s_val, e_val)

    # Interpolate unaligned spans between anchored matches
    idx = 0
    while idx < n:
        if times[idx] is None:
            start_gap = idx
            while idx < n and times[idx] is None:
                idx += 1
            end_gap = idx  # exclusive

            # Find left anchor time and right anchor time
            if start_gap > 0 and times[start_gap - 1] is not None:
                t_left = times[start_gap - 1][1]
            else:
                t_left = p_start_sec

            if end_gap < n and times[end_gap] is not None:
                # If there is a large pause between segments (e.g. after title), don't stretch title into paragraph!
                t_right = times[end_gap][0]
                if start_gap > 0 and flat_gt[start_gap - 1]["seg"] == flat_gt[end_gap - 1]["seg"] and (t_right - t_left) > 1.2 * (end_gap - start_gap):
                    t_right = t_left + 0.36 * (end_gap - start_gap)
            else:
                t_right = p_end_sec

            span_dur = max(0.08 * (end_gap - start_gap), t_right - t_left)
            step = span_dur / float(end_gap - start_gap)
            for k in range(start_gap, end_gap):
                s_k = t_left + (k - start_gap) * step
                e_k = s_k + max(0.08, step * 0.92)
                times[k] = (s_k, e_k)
        else:
            idx += 1

    # Group back into segments and add INTRO_DELAY_SEC offset
    aligned_segments = [[] for _ in segments_words]
    for idx_gt, item in enumerate(flat_gt):
        s_raw, e_raw = times[idx_gt]
        s_final = round(s_raw + offset_sec, 2)
        e_final = round(max(s_final + 0.08, e_raw + offset_sec), 2)
        aligned_segments[item["seg"]].append({
            "w": item["w"],
            "s": s_final,
            "e": e_final,
        })

    return aligned_segments


def build_karaoke_for_story_lang(model, story: dict, lang: str):
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
    page_spans = split_exact_page_boundaries(samples, rms, len(pages), sample_rate=24000, win_sec=0.01)

    story_title = story.get("title_en" if lang == "en" else f"title_{lang}" if lang != "it" else "title", story["title"])

    pages_out = []
    for idx, p in enumerate(pages):
        p_start, p_end = page_spans[idx]
        paras = p.get(f"paragraphs_{lang}", [])

        # Note: page_title is displayed visually on the page but NOT read aloud in TTS
        segments_words = []
        if idx == 0:
            segments_words.append(story_title.split())
        for para in paras:
            segments_words.append(para.split())

        whisper_words = transcribe_page_words(model, samples, p_start, p_end, lang)
        aligned = align_ground_truth_to_whisper(
            segments_words, whisper_words, p_start, p_end, offset_sec=offset
        )

        if idx == 0:
            story_title_aligned = aligned[0]
            page_title_aligned = []
            paras_aligned = aligned[1:]
        else:
            story_title_aligned = []
            page_title_aligned = []
            paras_aligned = aligned

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
    print(f"✅ Saved Whisper-aligned Karaoke timings: {out_json.relative_to(ROOT)} ({len(pages_out)} pages)", flush=True)
    return out_json


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", default=None)
    parser.add_argument("--lang", default=None)
    args = parser.parse_args()

    catalog = load_stories_yaml()
    model = whisper.load_model("base")
    for story in catalog.get("stories", []):
        if args.slug and story.get("slug") != args.slug:
            continue
        for lang in ("it", "en"):
            if args.lang and lang != args.lang:
                continue
            build_karaoke_for_story_lang(model, story, lang)


if __name__ == "__main__":
    main()
