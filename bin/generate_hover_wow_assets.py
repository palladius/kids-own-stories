#!/usr/bin/env python3
"""
Generates Hover "WOW" Assets for Kids' Own Stories:
1. Calm, soothing female voiceover (Aoede via Gemini 2.5 Flash TTS) reciting each story's title
   in Italian (title_it.mp3) and English (title_en.mp3), mixed with a gentle warm piano chord.
2. Veo video for the story (via Gemini API Veo model or dynamic multi-scene 1280x720 fallback),
   plus 5-second fast-start hover_preview.mp4 clips for every story.
"""

import argparse
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
            "Speak with a warm, soothing, posh British English (UK Received Pronunciation / BBC CBeebies bedtime story) female voice: "
            "\"The Story of the Magic Backpack, the Dragon, and the Puffins. A story by Alessandro.\""
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
            "Speak with a warm, soothing, posh British English (UK Received Pronunciation / BBC CBeebies bedtime story) female voice: "
            "\"The Skeleton Family and the Tea-Thirsty Zombies. A story by Alessandro.\""
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
        "scenes": [
            "scena1_giardino_libreria.jpg",
            "scena2_primo_te.jpg",
            "scena3_due_bicchieri_grazie.jpg",
        ],
    },
    {
        "slug": "storia-pupurabbu-hot-wheels-lido-degli-estensi",
        "folder": ROOT / "stories/sebastian/storia-pupurabbu-hot-wheels-lido-degli-estensi",
        "title_prompt_it": (
            "Leggi questo titolo di fiaba con voce femminile dolcissima, suadente, calda, calma e rassicurante: "
            "«Seby, il Dolce Pupurabbu e la Pista Fatata delle Hot Wheels a Lido degli Estensi. Una fiaba di Sebastian.»"
        ),
        "title_prompt_en": (
            "Speak with a warm, soothing, posh British English (UK Received Pronunciation / BBC CBeebies bedtime story) female voice. "
            "Pronounce the name Sebastian in the clear European/British way as \"Se-bas-ti-an\" (with a clear T-I-A-N, never American \"Suh-bas-chun\"): "
            "\"Seby, Sweet Pupurabbu, and the Enchanted Hot Wheels Track at Lido degli Estensi. A story by Se-bas-ti-an.\""
        ),
        "existing_video": "video_pupurabbu_hotwheels.mp4",
        "veo_prompt": (
            "3D Pixar animated movie scene, a joyful 6-year-old boy (Seby) in a yellow-and-teal striped shirt "
            "and his adorable soft purple plush bunny rabbit friend (Pupurabbu, with long floppy lavender ears and racing goggles) "
            "driving a sleek electric-blue Hot Wheels race car with golden flames along a glowing rainbow-and-orange loop track "
            "high among pink cotton-candy clouds, floating crystal sandcastles, and cute cheering golden starfish waving checkered flags, "
            "magical sparkles, vibrant colors, heartwarming kid-friendly 3D animation."
        ),
        "veo_image": "scena3_mondo_magico_hotwheels.jpg",
        "scenes": [
            "scena1_spiaggia_lido_estensi.jpg",
            "scena2_portale_fatato.jpg",
            "scena3_mondo_magico_hotwheels.jpg",
            "scena4_abbraccio_tramonto_lido.jpg",
        ],
    },
    {
        "slug": "storia-cavalletto-marie-mondo-cavalli",
        "folder": ROOT / "stories/sebastian/storia-cavalletto-marie-mondo-cavalli",
        "title_prompt_it": (
            "Leggi questo titolo di fiaba con voce femminile dolcissima, suadente, calda, calma e rassicurante: "
            "«Sebastian, il Cavalletto Magico Marie e il Camion Camper dei Cavalli. Una fiaba di Sebastian.»"
        ),
        "title_prompt_en": (
            "Speak with a warm, soothing, posh British English (UK Received Pronunciation / BBC CBeebies bedtime story) female voice. "
            "Pronounce the name Sebastian in the clear European/British way as \"Se-bas-ti-an\" (with a clear T-I-A-N, never American \"Suh-bas-chun\"): "
            "\"Sebastian, Marie the Magic Pony, and the Horses' Camper Truck. A story by Se-bas-ti-an.\""
        ),
        "existing_video": "video_cavalletto_marie_camion.mp4",
        "scenes": [
            "scena1_cavalletto_marie_soffio_tunnel.jpg",
            "scena2_vortice_dimensionale_mondo_cavalli.jpg",
            "scena3_camion_camper_tutti_cavalli.jpg",
            "scena4_marie_chiude_tunnel_mondo_umani.jpg",
        ],
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


def synthesize_tts_pcm(prompt_text: str, lang_code: str = "en-GB") -> bytes:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "languageCode": lang_code,
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


def build_title_mp3(prompt_text: str, chime_wav: Path, out_mp3: Path, lang_code: str = "en-GB"):
    print(f"🎙️ Generating calm title voiceover ({lang_code}): {out_mp3.relative_to(ROOT)} ...")
    pcm = synthesize_tts_pcm(prompt_text, lang_code=lang_code)
    voice_dur = len(pcm) / (24000.0 * 2.0)
    fade_start = max(1.0, voice_dur + 0.15)
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
        f"[0:a]volume=1.5,apad=pad_dur=0.8[v];"
        f"[1:a]volume=0.22[bg];"
        f"[v][bg]amix=inputs=2:duration=first:dropout_transition=1,afade=t=out:st={fade_start:.2f}:d=0.65[out]",
        "-map", "[out]",
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(out_mp3),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ Saved {out_mp3.relative_to(ROOT)} ({voice_dur + 0.8:.1f}s)")


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


def build_cinematic_multiscene_video_fallback(folder: Path, scene_names: list[str], out_mp4: Path):
    """Creates a lush 1280x720 30fps dynamic pan-and-zoom summary video across all scenes of the story."""
    print(f"🎞️ Building dynamic {len(scene_names)}-scene summary video for {folder.name}...")
    scene_paths = [folder / s for s in scene_names]
    if len(scene_paths) == 4:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", "2.1", "-i", str(scene_paths[0]),
            "-loop", "1", "-t", "2.1", "-i", str(scene_paths[1]),
            "-loop", "1", "-t", "2.1", "-i", str(scene_paths[2]),
            "-loop", "1", "-t", "2.2", "-i", str(scene_paths[3]),
            "-filter_complex",
            "[0:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
            "zoompan=z='min(zoom+0.0022,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=63:s=1280x720:fps=30,format=yuv420p[v0];"
            "[1:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
            "zoompan=z='1.15-0.002*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=63:s=1280x720:fps=30,format=yuv420p[v1];"
            "[2:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
            "zoompan=z='min(zoom+0.0025,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=63:s=1280x720:fps=30,format=yuv420p[v2];"
            "[3:v]scale=1440:810:force_original_aspect_ratio=increase,crop=1440:810,"
            "zoompan=z='1.16-0.002*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=66:s=1280x720:fps=30,format=yuv420p[v3];"
            "[v0][v1]xfade=transition=fade:duration=0.4:offset=1.7[v01];"
            "[v01][v2]xfade=transition=circleopen:duration=0.4:offset=3.4[v012];"
            "[v012][v3]xfade=transition=fade:duration=0.4:offset=5.1[vout]",
            "-map", "[vout]",
            "-t", "7.0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "21",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", "2.4", "-i", str(scene_paths[0]),
            "-loop", "1", "-t", "2.4", "-i", str(scene_paths[1]),
            "-loop", "1", "-t", "2.6", "-i", str(scene_paths[2]),
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
    parser = argparse.ArgumentParser(description="Generate Hover WOW assets (title TTS + Veo video + 5s clip)")
    parser.add_argument("--slug", help="Only generate for this specific story slug", default=None)
    parser.add_argument("--titles-only", action="store_true", help="Only generate title_it.mp3 and title_en.mp3")
    args = parser.parse_args()

    if not API_KEY:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    chime_wav = Path("/tmp/warm_title_chime.wav")
    generate_warm_chime_wav(chime_wav, duration_sec=16.0)

    stories = STORIES
    if args.slug:
        stories = [s for s in stories if s["slug"] == args.slug]

    for st in stories:
        folder = st["folder"]
        build_title_mp3(st["title_prompt_it"], chime_wav, folder / "title_it.mp3", lang_code="it-IT")
        build_title_mp3(st["title_prompt_en"], chime_wav, folder / "title_en.mp3", lang_code="en-GB")

        if args.titles_only:
            continue

        full_video = folder / st["existing_video"]
        if not full_video.exists() and "veo_prompt" in st:
            ok = try_generate_veo_video_gemini_api(
                st["veo_prompt"],
                folder / st["veo_image"],
                full_video,
            )
            if not ok or not full_video.exists():
                build_cinematic_multiscene_video_fallback(folder, st.get("scenes", []), full_video)

        hover_mp4 = folder / "hover_preview.mp4"
        create_5s_hover_clip(full_video, hover_mp4)


if __name__ == "__main__":
    main()
