#!/usr/bin/env python3
"""
Generate subtle, calm Veo 3.1 watercolor animations for selected illustrated
book plates (with gentle ambient audio) so they come alive 3 seconds after a
page opens ("effetto wow inaspettato").

Uses Vertex AI Veo 3.1 (`veo-3.1-fast-generate-001`) via `gcloud auth print-access-token`.
"""

import base64
import concurrent.futures
import io
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = REPO_ROOT / "books" / "petit-prince"

LOCATION_ID = "us-central1"
API_ENDPOINT = "us-central1-aiplatform.googleapis.com"
VEO_MODEL_ID = "veo-3.1-fast-generate-001"
VEO_PROJECT_ID = os.environ.get("VEO_PROJECT_ID", "palladius-genai")

# Exact 16:9 crops (in fractional coordinates of 896x1200) matching the CSS overlay box.
PLATES = [
    {
        "id": "p02",
        "src": BOOK_DIR / "wc_p02.jpg",
        "out": BOOK_DIR / "anim_p02.mp4",
        "box": {"left": 0.06, "top": 0.445, "width": 0.88, "height": 443 / 1200},
        "prompt": (
            "Very gentle, subtle hand-drawn watercolor storybook animation on warm cream "
            "parchment paper. Locked static camera, zero camera movement, zero zoom, "
            "keep the pale cream paper background completely still and uniform. "
            "The golden-ochre watercolor boa constrictor gently breathes and sways its coiled "
            "body ever so slightly, blinking once softly, while its tail tip curls gently; "
            "the little grey beast blinks calmly. Preserve the exact hand-painted ink and "
            "watercolor illustration style of Antoine de Saint-Exupery. "
            "Audio: ultra-soft, calm, barely audible ambient jungle breeze and a gentle "
            "whisper of leaves, no music, no voices, very quiet and peaceful."
        ),
    },
    {
        "id": "p04",
        "src": BOOK_DIR / "wc_p04.jpg",
        "out": BOOK_DIR / "anim_p04.mp4",
        "box": {"left": 0.05, "top": 0.45, "width": 0.90, "height": 453 / 1200},
        "prompt": (
            "Very gentle, subtle hand-drawn watercolor storybook animation on warm cream "
            "parchment paper. Locked static camera, zero camera movement, zero zoom, "
            "keep the pale cream paper background completely still and uniform. "
            "The Little Prince in his blue coat gently blinks and the hem of his blue and "
            "magenta coat sways very softly in a calm desert breeze; the tiny white watercolor "
            "sheep gently blinks, wiggles its ears, and floats softly above the wooden box. "
            "Preserve the exact hand-painted ink and watercolor style of Antoine de Saint-Exupery. "
            "Audio: ultra-soft, calm, peaceful desert breeze and one tiny gentle rustle, "
            "no music, no voices, very quiet and soothing."
        ),
    },
]


def get_access_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True
    ).strip()


def crop_16_9(src: Path, box: dict) -> bytes:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    x0 = int(round(box["left"] * w))
    y0 = int(round(box["top"] * h))
    x1 = int(round((box["left"] + box["width"]) * w))
    y1 = int(round((box["top"] + box["height"]) * h))
    cropped = img.crop((x0, y0, x1, y1)).resize((1280, 720), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return buf.getvalue()


def generate_one(spec: dict) -> Path:
    pid = spec["id"]
    print(f"[{pid}] Cropping {spec['src'].name} -> 1280x720 PNG...", flush=True)
    png_bytes = crop_16_9(spec["src"], spec["box"])

    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    request_data = {
        "instances": [
            {
                "prompt": spec["prompt"],
                "image": {
                    "bytesBase64Encoded": base64.b64encode(png_bytes).decode("utf-8"),
                    "mimeType": "image/png",
                },
            }
        ],
        "parameters": {
            "aspectRatio": "16:9",
            "sampleCount": 1,
            "durationSeconds": 4,
            "fps": 24,
            "generateAudio": True,
        },
    }

    url = f"https://{API_ENDPOINT}/v1/projects/{VEO_PROJECT_ID}/locations/{LOCATION_ID}/publishers/google/models/{VEO_MODEL_ID}:predictLongRunning"
    print(f"[{pid}] Submitting Vertex AI Veo 3.1 ({VEO_MODEL_ID}) job...", flush=True)
    resp = requests.post(url, headers=headers, json=request_data, timeout=60)
    if not resp.ok:
        raise RuntimeError(f"[{pid}] Submit failed {resp.status_code}: {resp.text[:500]}")
    op_name = resp.json().get("name")
    if not op_name:
        raise RuntimeError(f"[{pid}] Missing operation name: {resp.text[:400]}")
    print(f"[{pid}] Operation started: {op_name}", flush=True)

    fetch_url = f"https://{API_ENDPOINT}/v1/projects/{VEO_PROJECT_ID}/locations/{LOCATION_ID}/publishers/google/models/{VEO_MODEL_ID}:fetchPredictOperation"
    t0 = time.time()
    result_json = None
    for attempt in range(1, 61):
        time.sleep(8)
        token = get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.post(fetch_url, headers=headers, json={"operationName": op_name}, timeout=60)
        r.raise_for_status()
        data = r.json()
        if data.get("done"):
            result_json = data
            break
        print(f"[{pid}] Polling {attempt}/60 ({int(time.time() - t0)}s)...", flush=True)

    if not result_json:
        raise RuntimeError(f"[{pid}] Timed out waiting for Veo.")
    if "error" in result_json:
        raise RuntimeError(f"[{pid}] Veo error: {result_json['error']}")

    videos = result_json.get("response", {}).get("videos", [])
    if not videos or "bytesBase64Encoded" not in videos[0]:
        raise RuntimeError(f"[{pid}] No video bytes in response: {str(result_json)[:400]}")

    raw_mp4 = spec["out"].with_suffix(".raw.mp4")
    raw_mp4.write_bytes(base64.b64decode(videos[0]["bytesBase64Encoded"]))
    print(f"[{pid}] Downloaded raw Veo MP4 ({raw_mp4.stat().st_size // 1024} KB)", flush=True)

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(raw_mp4),
        ],
        capture_output=True, text=True, check=False,
    )
    has_audio = "audio" in (probe.stdout or "")

    cmd = [
        "ffmpeg", "-y", "-i", str(raw_mp4),
        "-vf", "scale=768:432:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
    ]
    if has_audio:
        cmd += [
            "-af", "volume=0.32,afade=t=in:st=0:d=0.6,afade=t=out:st=3.0:d=1.0",
            "-c:a", "aac", "-b:a", "96k",
        ]
    else:
        cmd += ["-an"]
    cmd += ["-movflags", "+faststart", str(spec["out"])]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw_mp4.unlink(missing_ok=True)
    size_kb = spec["out"].stat().st_size // 1024
    print(f"[{pid}] ✅ Ready: {spec['out'].name} ({size_kb} KB, audio={has_audio})", flush=True)
    return spec["out"]


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futs = [pool.submit(generate_one, spec) for spec in PLATES]
        for f in concurrent.futures.as_completed(futs):
            f.result()


if __name__ == "__main__":
    main()
