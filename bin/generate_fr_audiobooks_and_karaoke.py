#!/usr/bin/env python3
"""
Generates high-precision French (FR) narrated audiobooks (`narrated_fr.mp3`) and
word-level Karaoke timing files (`karaoke_fr.json`) for all stories in `stories.yaml`.

Uses:
1. `edge-tts` (`fr-FR-DeniseNeural` or `fr-FR-EloiseNeural`) with `boundary="WordBoundary"`
   for exact acoustic word timestamps.
2. Needleman-Wunsch / SequenceMatcher alignment to ground-truth `paragraphs_fr` tokens.
3. Gentle felt-piano background mixed underneath (`1.20s` intro delay, matching IT/EN).
"""

import asyncio
from difflib import SequenceMatcher
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import wave
import edge_tts
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIANO_WAV = Path("/tmp/gentle_piano_loop.wav")
INTRO_DELAY_SEC = 1.20
INTER_PAGE_GAP_SEC = 0.65
FR_VOICE = "fr-FR-DeniseNeural"


def generate_gentle_piano_wav(output_path: Path, duration_sec: float = 320.0, sample_rate: int = 24000) -> Path:
    if output_path.exists() and output_path.stat().st_size > 10000:
        return output_path

    chords = [
        [261.63, 329.63, 392.00, 493.88, 523.25, 392.00, 329.63, 293.66],
        [220.00, 261.63, 329.63, 392.00, 440.00, 392.00, 329.63, 261.63],
        [174.61, 220.00, 261.63, 349.23, 440.00, 349.23, 261.63, 220.00],
        [196.00, 246.94, 293.66, 392.00, 440.00, 392.00, 293.66, 246.94],
    ]
    note_dur = 0.85
    total_samples = int(duration_sec * sample_rate)
    buf = [0.0] * total_samples

    idx_note = 0
    t_cursor = 0.0
    while t_cursor < duration_sec:
        chord = chords[(idx_note // 8) % len(chords)]
        freq = chord[idx_note % len(chord)]
        bass_freq = chord[0] * 0.5 if (idx_note % 8 == 0) else None

        start_sample = int(t_cursor * sample_rate)
        ring_samples = int(min(2.6, duration_sec - t_cursor) * sample_rate)

        for i in range(ring_samples):
            t = i / sample_rate
            attack = min(1.0, t / 0.04)
            decay = math.exp(-t * 1.45)
            env = attack * decay

            val = (
                0.65 * math.sin(2.0 * math.pi * freq * t)
                + 0.20 * math.sin(2.0 * math.pi * freq * 2.0 * t) * math.exp(-t * 2.2)
                + 0.06 * math.sin(2.0 * math.pi * freq * 3.0 * t) * math.exp(-t * 3.5)
            )
            if bass_freq:
                val += 0.35 * math.sin(2.0 * math.pi * bass_freq * t) * math.exp(-t * 0.9)

            buf[start_sample + i] += val * env * 0.25

        t_cursor += note_dur
        idx_note += 1

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        pcm_data = bytearray()
        for s in buf:
            clamped = max(-0.95, min(0.95, s))
            pcm_data.extend(struct.pack("<h", int(clamped * 32767)))
        wf.writeframes(pcm_data)

    return output_path


def norm_tok(w: str) -> str:
    return re.sub(r"[^\wÀ-ÿ]+", "", w.lower())


def align_tokens_to_boundaries(gt_tokens: list[str], wb_events: list[dict], page_offset_sec: float, page_dur_sec: float) -> list[dict]:
    if not gt_tokens:
        return []
    if not wb_events:
        step = max(0.15, page_dur_sec / len(gt_tokens))
        return [
            {
                "w": w,
                "s": round(page_offset_sec + i * step, 2),
                "e": round(page_offset_sec + (i + 1) * step, 2),
            }
            for i, w in enumerate(gt_tokens)
        ]

    gt_norm = [norm_tok(w) for w in gt_tokens]
    wb_norm = [norm_tok(ev["text"]) for ev in wb_events]

    sm = SequenceMatcher(None, gt_norm, wb_norm, autojunk=False)
    mapped: list[tuple[float, float] | None] = [None] * len(gt_tokens)

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                ev = wb_events[j1 + k]
                mapped[i1 + k] = (page_offset_sec + ev["s"], page_offset_sec + ev["e"])
        elif tag == "replace" and (i2 - i1) > 0 and (j2 - j1) > 0:
            span_s = page_offset_sec + wb_events[j1]["s"]
            span_e = page_offset_sec + wb_events[j2 - 1]["e"]
            cnt = i2 - i1
            step = max(0.06, (span_e - span_s) / cnt)
            for k in range(cnt):
                mapped[i1 + k] = (span_s + k * step, span_s + (k + 1) * step)

    # Interpolate any remaining None entries monotonically
    n = len(gt_tokens)
    for i in range(n):
        if mapped[i] is not None:
            continue
        prev_idx = i - 1
        while prev_idx >= 0 and mapped[prev_idx] is None:
            prev_idx -= 1
        next_idx = i + 1
        while next_idx < n and mapped[next_idx] is None:
            next_idx += 1

        start_t = mapped[prev_idx][1] if prev_idx >= 0 else (page_offset_sec + (wb_events[0]["s"] if wb_events else 0.0))
        end_t = mapped[next_idx][0] if next_idx < n else (page_offset_sec + page_dur_sec)
        if end_t <= start_t:
            end_t = start_t + 0.18 * (next_idx - prev_idx)
        gap_count = next_idx - prev_idx - 1
        step = (end_t - start_t) / max(1, gap_count)
        pos_in_gap = i - prev_idx - 1
        mapped[i] = (start_t + pos_in_gap * step, start_t + (pos_in_gap + 1) * step)

    return [
        {
            "w": gt_tokens[i],
            "s": round(mapped[i][0], 2),
            "e": round(max(mapped[i][0] + 0.05, mapped[i][1]), 2),
        }
        for i in range(n)
    ]


async def synth_page_fr(text: str) -> tuple[bytes, list[dict]]:
    comm = edge_tts.Communicate(text, FR_VOICE, boundary="WordBoundary")
    mp3_bytes = bytearray()
    wb_events = []
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            mp3_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            s = chunk["offset"] / 1e7
            e = (chunk["offset"] + chunk["duration"]) / 1e7
            wb_events.append({"text": chunk["text"], "s": s, "e": e})
    return bytes(mp3_bytes), wb_events


def mp3_bytes_to_pcm_24k(mp3_bytes: bytes) -> bytes:
    cmd = ["ffmpeg", "-v", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "24000", "pipe:1"]
    res = subprocess.run(cmd, input=mp3_bytes, capture_output=True, check=True)
    return res.stdout


def mix_voice_with_piano(voice_wav: Path, piano_wav: Path, output_mp3: Path):
    with wave.open(str(voice_wav), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        voice_dur = frames / float(rate)

    total_dur = voice_dur + 3.2
    fade_out_start = max(0.0, total_dur - 2.2)

    filter_complex = (
        f"[0:a]adelay=1200|1200,volume=1.18[v];"
        f"[1:a]atrim=0:{total_dur:.2f},afade=t=in:st=0:d=1.0,afade=t=out:st={fade_out_start:.2f}:d=2.0,volume=0.14[p];"
        f"[v][p]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(voice_wav),
        "-i", str(piano_wav),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(output_mp3),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def process_story_fr(story: dict, piano_wav: Path):
    slug = story["slug"]
    story_dir = REPO_ROOT / story["folder"]
    out_mp3 = story_dir / "narrated_fr.mp3"
    out_karaoke = story_dir / "karaoke_fr.json"
    title_fr_mp3 = story_dir / "title_fr.mp3"

    if out_mp3.exists() and out_mp3.stat().st_size > 10000 and out_karaoke.exists() and title_fr_mp3.exists():
        print(f"⏩ [{slug}] French assets already present, skipping.", flush=True)
        return

    pages = story.get("assets", {}).get("pages", [])
    title_fr = story.get("title_fr") or story.get("title")

    pcm_parts = []
    karaoke_pages = []
    running_voice_sec = 0.0

    for idx, p in enumerate(pages):
        paras_fr = p.get("paragraphs_fr") or []
        title_tokens = title_fr.split() if idx == 0 else []
        para_token_lists = [para.split() for para in paras_fr]
        all_gt_tokens = title_tokens + [tok for plist in para_token_lists for tok in plist]

        spoken_text = (f"{title_fr}. " if idx == 0 else "") + " ".join(paras_fr)
        mp3_bytes, wb_events = await synth_page_fr(spoken_text)
        pcm = mp3_bytes_to_pcm_24k(mp3_bytes)
        page_dur = len(pcm) / (24000.0 * 2.0)

        page_start_mixed = INTRO_DELAY_SEC + running_voice_sec
        aligned = align_tokens_to_boundaries(all_gt_tokens, wb_events, page_start_mixed, page_dur)

        cursor = 0
        story_title_words = aligned[cursor : cursor + len(title_tokens)]
        cursor += len(title_tokens)

        paragraphs_aligned = []
        for plist in para_token_lists:
            paragraphs_aligned.append(aligned[cursor : cursor + len(plist)])
            cursor += len(plist)

        karaoke_pages.append({
            "page": idx + 1,
            "start": round(page_start_mixed, 2),
            "end": round(page_start_mixed + page_dur, 2),
            "story_title_words": story_title_words,
            "title_words": [],
            "paragraphs": paragraphs_aligned,
        })

        pcm_parts.append(pcm)
        running_voice_sec += page_dur + INTER_PAGE_GAP_SEC

    silence = b"\x00\x00" * int(24000 * INTER_PAGE_GAP_SEC)
    combined_pcm = silence.join(pcm_parts)
    raw_wav = Path(f"/tmp/{slug}_voice_fr.wav")
    with wave.open(str(raw_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(combined_pcm)

    mix_voice_with_piano(raw_wav, piano_wav, out_mp3)

    karaoke_payload = {
        "story_slug": slug,
        "lang": "fr",
        "intro_delay_sec": INTRO_DELAY_SEC,
        "pages": karaoke_pages,
    }
    out_karaoke.write_text(json.dumps(karaoke_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also generate title_fr.mp3 for hover if missing
    title_fr_mp3 = story_dir / "title_fr.mp3"
    if not title_fr_mp3.exists() or title_fr_mp3.stat().st_size < 1000:
        t_mp3, _ = await synth_page_fr(f"{title_fr}. Une histoire racontée par {story.get('author', 'Alessandro').capitalize()}.")
        t_pcm = mp3_bytes_to_pcm_24k(t_mp3)
        # Ensure at least 5.2s with gentle piano
        t_wav = Path(f"/tmp/{slug}_title_fr.wav")
        with wave.open(str(t_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(t_pcm)
        mix_voice_with_piano(t_wav, piano_wav, title_fr_mp3)

    print(f"✅ [{slug}] Generated narrated_fr.mp3, karaoke_fr.json & title_fr.mp3", flush=True)


async def main():
    catalog = yaml.safe_load((REPO_ROOT / "stories.yaml").read_text(encoding="utf-8"))
    stories = catalog.get("stories", [])
    piano_wav = generate_gentle_piano_wav(PIANO_WAV, duration_sec=320.0)

    await asyncio.gather(*(process_story_fr(st, piano_wav) for st in stories))


if __name__ == "__main__":
    asyncio.run(main())
