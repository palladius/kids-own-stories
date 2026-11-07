#!/usr/bin/env python3
"""
Generates Hover "WOW" Assets for Kids' Own Stories:
1. Calm, soothing female voiceover (Aoede via Gemini 2.5 Flash TTS) reciting each story's title
   in Italian (title_it.mp3) and English (title_en.mp3), mixed with a gentle warm piano chord.
2. Veo video for Story #2 (video_scheletri_zombie_te.mp4) via Gemini API Veo model (or Vertex Veo),
   plus 5-second fast-start hover_preview.mp4 clips for every story.
"""

import base64
import json
import math
import os
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_KEY = os.environ.get("GEMINI_API_KEY", "")

STORIES = [
    {
        "slug": "storia-dello-zaino-del-drago-e-dei-puffins",
        "folder": ROOT / "stories/alessandro/storia-dello-zaino-del-drago-e-dei-puffins",
        "title_prompt_it": (
            "Leggi questo titolo di fiaba con voce femminile dolcissima, suadente, calda, calma e rassicurante: "
            "«La Storia dello Zaino Magico, del Drago e dei Puffins. Una fiaba di Alessandro.»"
        ),
        "title_prompt_en": (
            "Read this fairy tale title in a soothing, warm, calm, gentle female storytelling voice: "
            "'The Story of the Magic Backpack, the Dragon, and the Puffins. A story by Alessandro.'"
        ),
        "existing_video": "video_drago_puffins.mp4",
    },
    {
        "slug": "storia-scheletri-zombie-te",
        "folder": ROOT / "stories/alessandro/storia-scheletri-zombie-te",
        "title_prompt_it": (
            "Leggi questo titolo di fiaba con voce femminile dolcissima, suadente, calda, calma e rassicurante: "
            "«La Famiglia di Scheletri e gli Zombie Assetati di Tè. Una fiaba di Alessandro.»"
        ),
        "title_prompt_en": (
            "Read this fairy tale title in a soothing, warm, calm, gentle female storytelling voice: "
            "'The Skeleton Family and the Tea-Thirsty Zombies. A story by Alessandro.'"
        ),
        "existing_video": "video_scheletri_zombie_te.mp4",
        "veo_prompt": (
            "3D Pixar Coco style animated movie scene, joyful ivory-white bone skeleton family "
            "(dad skeleton in top hat, mom skeleton in flower hat, little child skeleton, cute skeleton dog wagging tail) "
            "in a magical dark blue night garden with glowing golden fireflies and a warm wooden library, "
            "happily serving two steaming glasses of herbal tea with lemon to polite cute green cartoon zombies "
            "who smile and bow in gratitude, warm lantern light, cinematic 3D animation, vibrant colors, kid-friendly."
        ),
        "veo_image": "scena3_due_bicchieri_grazie.jpg",
    },
]


def generate_warm_chime_wav(out_wav: Path, duration_sec: float = 10.0, sample_rate: int = 24000):
    """Synthesizes a soft, dreamy C-major-9th warm pad/chime for title voiceover background."""
    notes = [261.63, 329.63, 392.00, 493.88, 587.33]  # C4, E4, G4, B4, D5
    n_samples = int(duration_sec * sample_rate)
    samples = [0.0] * n_samples
    for idx, freq in enumerate(notes):
        start_t = idx * 0.12
        start_s = int(start_t * sample_rate)
        for i in range(start_s, n_samples):
            t = (i - start_s) / sample_rate
            env = min(1.0, t / 0.15) * math.exp(-t * 0.55)
            val = (
                0.65 * math.sin(2.0 * math.pi * freq * t)
                + 0.25 * math.sin(2.0 * math.pi * (freq * 2.0) * t) * math.exp(-t * 1.2)
            )
            samples[i] += val * env * 0.15

    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray()
        for s in samples:
            clipped = max(-0.95, min(0.95, s))
            raw.extend(struct.pack("<h", int(clipped * 32767)))
        wf.writeframes(bytes(raw))


def synthesize_tts_pcm(prompt_text: str) -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Aoede"
                    }
                }
            },
        },
    }
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            b64 = body["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            return base64.b64decode(b64)
        except Exception as e:
            print(f"  [retry {attempt+1}/4] TTS error: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Failed to synthesize title TTS")


def build_title_mp3(prompt_text: str, chime_wav: Path, out_mp3: Path):
    print(f"🎙️ Generating calm title voiceover: {out_mp3.relative_to(ROOT)} ...")
    pcm = synthesize_tts_pcm(prompt_text)
    voice_wav = Path(f"/tmp/title_voice_{out_mp3.stem}_{out_mp3.parent.name}.wav")
    with wave.open(str(voice_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(voice_wav),
        "-i", str(chime_wav),
        "-filter_complex",
        "[0:a]volume=1.5,apad=pad_dur=0.6[v];"
        "[1:a]volume=0.22[bg];"
        "[v][bg]amix=inputs=2:duration=first:dropout_transition=1,afade=t=out:st=4.5:d=0.8[out]",
        "-map", "[out]",
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(out_mp3),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Saved {out_mp3.relative_to(ROOT)}")


def try_generate_veo_video_gemini_api(prompt: str, image_path: Path, out_mp4: Path) -> bool:
    """Tries generating a 5-8s video via Gemini API Veo models."""
    models = ["veo-2.0-generate-001", "veo-3.0-generate-preview"]
    img_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")

    for model in models:
        try:
            print(f"🎬 Attempting Veo generation via Gemini API ({model})...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning?key={API_KEY}"
            payload = {
                "instances": [
                    {
                        "prompt": prompt,
                        "image": {
                            "bytesBase64Encoded": img_b64,
                            "mimeType": "image/jpeg",
                        },
                    }
                ],
                "parameters": {
                    "aspectRatio": "16:9",
                    "sampleCount": 1,
                    "durationSeconds": 5,
                },
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                op_data = json.loads(resp.read().decode("utf-8"))
            op_name = op_data.get("name")
            if not op_name:
                continue
            print(f"⏳ Veo operation started: {op_name}")
            poll_url = f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={API_KEY}"
            for i in range(36):
                time.sleep(8)
                with urllib.request.urlopen(poll_url, timeout=30) as presp:
                    pbody = json.loads(presp.read().decode("utf-8"))
                if pbody.get("done"):
                    if "error" in pbody:
                        print(f"  Veo operation error: {pbody['error']}", file=sys.stderr)
                        break
                    resp_obj = pbody.get("response", {})
                    # Check generateVideoResponse or videos
                    samples = (
                        resp_obj.get("generateVideoResponse", {}).get("generatedSamples", [])
                        or resp_obj.get("videos", [])
                    )
                    if samples:
                        sample = samples[0]
                        video_info = sample.get("video", sample)
                        if "uri" in video_info:
                            dl_url = video_info["uri"]
                            if "?" in dl_url:
                                dl_url += f"&key={API_KEY}"
                            else:
                                dl_url += f"?key={API_KEY}"
                            urllib.request.urlretrieve(dl_url, str(out_mp4))
                            print(f"✅ Downloaded Veo video to {out_mp4.relative_to(ROOT)}")
                            return True
                        elif "bytesBase64Encoded" in video_info:
                            out_mp4.write_bytes(base64.b64decode(video_info["bytesBase64Encoded"]))
                            print(f"✅ Saved Veo video to {out_mp4.relative_to(ROOT)}")
                            return True
                    break
        except Exception as e:
            print(f"  Veo model {model} note: {e}", file=sys.stderr)
    return False


def build_cinematic_3scene_video_fallback(folder: Path, out_mp4: Path):
    """Creates a lush 6-second 1280x720 30fps dynamic pan-and-zoom summary video across all 3 scenes."""
    print(f"🎞️ Building 6s dynamic 3-scene summary video for {folder.name}...")
    s1 = folder / "scena1_giardino_libreria.jpg"
    s2 = folder / "scena2_primo_te.jpg"
    s3 = folder / "scena3_due_bicchieri_grazie.jpg"
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", "2.4", "-i", str(s1),
        "-loop", "1", "-t", "2.4", "-i", str(s2),
        "-loop", "1", "-t", "2.6", "-i", str(s3),
        "-filter_complex",
        "[0:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
        "zoompan=z='min(zoom+0.0022,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=72:s=1280x720:fps=30,format=yuv420p[v0];"
        "[1:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
        "zoompan=z='1.15-0.002*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=72:s=1280x720:fps=30,format=yuv420p[v1];"
        "[2:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
        "zoompan=z='min(zoom+0.0025,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=78:s=1280x720:fps=30,format=yuv420p[v2];"
        "[v0][v1]xfade=transition=fade:duration=0.45:offset=1.95[v01];"
        "[v01][v2]xfade=transition=circleopen:duration=0.45:offset=3.90[vout]",
        "-map", "[vout]",
        "-t", "6.2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "21",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created {out_mp4.relative_to(ROOT)}")


def create_5s_hover_clip(src_mp4: Path, out_hover_mp4: Path):
    """Creates an ultra-responsive 5-second muted fast-start MP4 clip for instant hover playback."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src_mp4),
        "-t", "5",
        "-vf", "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2",
        "-an",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "23",
        "-movflags", "+faststart",
        str(out_hover_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Created 5s hover preview: {out_hover_mp4.relative_to(ROOT)}")


def main():
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    chime_wav = Path("/tmp/warm_title_chime.wav")
    generate_warm_chime_wav(chime_wav)

    for st in STORIES:
        folder = st["folder"]
        build_title_mp3(st["title_prompt_it"], chime_wav, folder / "title_it.mp3")
        build_title_mp3(st["title_prompt_en"], chime_wav, folder / "title_en.mp3")

        full_video = folder / st["existing_video"]
        if not full_video.exists() and "veo_prompt" in st:
            ok = try_generate_veo_video_gemini_api(
                st["veo_prompt"],
                folder / st["veo_image"],
                full_video,
            )
            if not ok or not full_video.exists():
                build_cinematic_3scene_video_fallback(folder, full_video)

        hover_mp4 = folder / "hover_preview.mp4"
        create_5s_hover_clip(full_video, hover_mp4)


if __name__ == "__main__":
    main()
