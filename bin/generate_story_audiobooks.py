#!/usr/bin/env python3
"""
Generates bilingual (IT & EN) narrated audiobooks in parallel for Kids' Own Stories using:
1. Gemini 2.5 TTS (`gemini-2.5-flash-preview-tts`, voice `Aoede` - calm, reassuring female voice).
2. A gentle, soothing solo felt-piano background lullaby mixed softly underneath via `ffmpeg`.

Reads directly from `stories.yaml` (Single Source of Truth) and supports filtering by `--slug <slug>`.
"""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import os
import struct
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIANO_WAV = Path("/tmp/gentle_piano_loop.wav")


def generate_gentle_piano_wav(output_path: Path, duration_sec: float = 280.0, sample_rate: int = 24000):
    """Synthesizes a warm, soothing solo felt-piano lullaby progression (C maj7 - Am7 - F maj7 - G6)."""
    if output_path.exists() and output_path.stat().st_size > 10000:
        return output_path

    chords = [
        [261.63, 329.63, 392.00, 493.88, 523.25, 392.00, 329.63, 293.66],  # Cmaj9
        [220.00, 261.63, 329.63, 392.00, 440.00, 392.00, 329.63, 261.63],  # Am7
        [174.61, 220.00, 261.63, 349.23, 440.00, 349.23, 261.63, 220.00],  # Fmaj7
        [196.00, 246.94, 293.66, 392.00, 440.00, 392.00, 293.66, 246.94],  # G6
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


def synthesize_gemini_tts_chunk(api_key: str, text: str, lang: str, voice_name: str = "Aoede") -> bytes:
    """Calls Gemini 2.5 TTS REST API for a paragraph/chunk and returns raw 24kHz 16-bit PCM bytes."""
    if lang == "it":
        instruction = (
            "Leggi questa parte di fiaba per bambini con voce femminile dolce, calma e rassicurante:\n\n" + text
        )
    else:
        instruction = (
            "Read this part of a children's bedtime fairy tale in a calm, warm, reassuring female voice:\n\n" + text
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": instruction}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            },
        },
    }

    for attempt in range(4):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            for part in resp_data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
        except Exception as e:
            print(f"  [retry {attempt+1}/4] TTS chunk error ({lang}): {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))

    raise RuntimeError(f"No audio bytes returned by Gemini TTS for {lang}")


def mix_voice_with_piano(voice_wav: Path, piano_wav: Path, output_mp3: Path):
    """Mixes the narrator voice with a soft background piano (1.2s intro, soft background, 2s outro)."""
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
    print(f"✅ Mixed audiobook saved: {output_mp3.relative_to(REPO_ROOT)} ({total_dur:.1f}s)", flush=True)


def build_single_audiobook(api_key: str, story: dict, lang: str, piano_wav: Path):
    """Synthesizes each page of a story in parallel with Gemini TTS (`Aoede`), joins with a soft pause, and mixes with piano."""
    slug = story["slug"]
    story_dir = REPO_ROOT / story["folder"]
    story_dir.mkdir(parents=True, exist_ok=True)
    out_mp3 = story_dir / f"narrated_{lang}.mp3"

    pages = story.get("assets", {}).get("pages", [])
    title = story.get("title_en") if lang == "en" else story.get("title")
    chunks = []
    for idx, p in enumerate(pages):
        page_title = p.get("title_en") if lang == "en" else p.get("title")
        paras = " ".join(p.get(f"paragraphs_{lang}", []))
        prefix = f"{title}. " if idx == 0 else ""
        chunks.append(f"{prefix}{page_title}. {paras}")

    print(f"🎙️  [{slug} - {lang.upper()}] Synthesizing {len(chunks)} pages in parallel with Gemini TTS (Aoede)...", flush=True)
    pcm_parts = [None] * len(chunks)
    with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
        fut_map = {
            pool.submit(synthesize_gemini_tts_chunk, api_key, chunk_text, lang, "Aoede"): i
            for i, chunk_text in enumerate(chunks)
        }
        for fut in as_completed(fut_map):
            i = fut_map[fut]
            pcm_parts[i] = fut.result()

    # Add 0.65s silence between pages (24000 Hz * 2 bytes * 0.65s)
    silence = b"\x00\x00" * int(24000 * 0.65)
    combined_pcm = silence.join(pcm_parts)

    raw_voice_wav = Path(f"/tmp/{slug}_voice_{lang}.wav")
    with wave.open(str(raw_voice_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(combined_pcm)

    mix_voice_with_piano(raw_voice_wav, piano_wav, out_mp3)
    return str(out_mp3)


def main():
    parser = argparse.ArgumentParser(description="Generate bilingual narrated audiobooks from stories.yaml")
    parser.add_argument("--slug", help="Only generate for this specific story slug", default=None)
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Missing GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    catalog = yaml.safe_load((REPO_ROOT / "stories.yaml").read_text(encoding="utf-8"))
    stories = catalog.get("stories", [])
    if args.slug:
        stories = [s for s in stories if s.get("slug") == args.slug]

    piano_wav = generate_gentle_piano_wav(PIANO_WAV, duration_sec=320.0)

    tasks = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        for story in stories:
            for lang in ("it", "en"):
                tasks.append(executor.submit(build_single_audiobook, api_key, story, lang, piano_wav))
        for fut in as_completed(tasks):
            fut.result()

    print("🎉 Bilingual story audiobooks generated and mixed with soft piano!", flush=True)


if __name__ == "__main__":
    main()
