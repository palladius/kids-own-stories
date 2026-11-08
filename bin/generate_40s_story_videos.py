#!/usr/bin/env python3
"""
Generates 40-second (4 acts x 10s) Italian-narrated 3D animated movies
for all 3 stories in Kids' Own Stories using Gemini Omni Flash via the
official google-genai Interactions API.

Validated 10/10 by the Adversarial Subagent Panel:
- story-director (Regista & Sceneggiatore Omni Flash)
- ale-fidelity-critic (Critico Avversario di Fedeltà Narrativa)
- omni-technical-critic (Critico Tecnico & Safety Anti-35561575)
"""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
from google import genai
from google.genai import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent


def load_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        m = re.search(r"(AIzaSy[A-Za-z0-9_-]+)", key)
        if m:
            return m.group(1)
    env_file = Path.home() / ".hermes" / ".env"
    if env_file.exists():
        text = env_file.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"GEMINI_API_KEY=[\"\x27]?(AIzaSy[A-Za-z0-9_-]+)", text)
        if m:
            return m.group(1)
    raise RuntimeError("GEMINI_API_KEY not found in environment or ~/.hermes/.env")


STORY_SPECS = [
    {
        "slug": "storia-dello-zaino-del-drago-e-dei-puffins",
        "title": "La Storia dello Zaino Magico, del Drago e dei Puffins",
        "folder": ROOT / "stories/alessandro/storia-dello-zaino-del-drago-e-dei-puffins",
        "output_mp4": "video_drago_puffins.mp4",
        "acts": [
            {
                "act": 1,
                "first_frame": "scena1_banco_porta.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame in a warm sunlit school classroom, an expressive 8-year-old boy "
                    "with brown hair and a blue hoodie sitting at his wooden desk holds a glowing ornate golden key "
                    "he found inside his backpack. As he touches the key to the wooden desk during recess, magical "
                    "golden runes swirl and a tiny arched secret door pops open right on top of his desk, radiating "
                    "warm rainbow light. Amazed and smiling, the boy shrinks in a swirl of golden sparkles and hops "
                    "right inside the glowing miniature door on his desk. Smooth cinematic camera push-in. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Trovata una chiave d'oro nello zaino, all'altro break a scuola aprì una porta magica sul suo desk e ci entrò!\" "
                    "Accompanied by magical chimes, wooden door click, and whimsical orchestral music."
                ),
            },
            {
                "act": 2,
                "first_frame": "scena2_mondo_gemme.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame inside a breathtaking underground cavern made entirely of giant "
                    "glowing gems, purple amethyst pillars, blue sapphire waterfalls, and hills of sparkling red rubies. "
                    "The curious boy in his blue hoodie lands softly on a pile of glittering crystals. His eyes go wide "
                    "with wonder; he unzips his backpack wide open and excitedly scoops up handfuls of dazzling rubies, "
                    "emeralds, and diamonds with both hands, stuffing his backpack and pockets to the brim as gems clink "
                    "and sparkle around him. Dynamic tracking shot. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Arrivò nel Mondo dei Draghi, fatto tutto di gemme scintillanti, e iniziò a prendere tantissime gemme riempiendosi lo zaino!\" "
                    "Accompanied by sparkling crystal chimes and playful mischievous pizzicato strings."
                ),
            },
            {
                "act": 3,
                "first_frame": "scena3_drago_fuoco.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family comedy film, 16:9 HD, lighthearted slapstick cartoon humor. "
                    "Starting from the first frame, a gigantic majestic red-and-gold dragon towers over the boy clutching "
                    "his gem-stuffed backpack. The dragon gestures dramatically and speaks, and the cheeky boy hugs his "
                    "backpack and replies. In harmless whimsical slapstick cartoon comedy fashion, the dragon puffs its "
                    "cheeks and blows a playful burst of warm cartoon sparkles and orange smoke that covers the boy in "
                    "funny cartoon soot before a silly cartoon gulp, then gently scoops back all the sparkling gems and "
                    "the golden key into its paw. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian with lively theatrical voices: "
                    "\"«No, tu non puoi prenderle, sono mie!» «No, ora sono mie!» Il drago lo frisse, lo mangiò e riprese gemme e chiave!\" "
                    "Accompanied by playful cartoon whoosh, funny gulp sound, and brass fanfare."
                ),
            },
            {
                "act": 4,
                "first_frame": "scena4_drago_e_puffins.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame, the giant friendly red-and-gold dragon uses the glowing golden key "
                    "to unlock a shimmering sky portal, flying joyfully into a wondrous floating realm made of gleaming "
                    "golden towers and levitating rainbow crystals among the clouds. Waiting to celebrate with him are "
                    "his best friends: a cheerful flock of adorable sea puffins with bright orange beaks wearing cute "
                    "little brass aviator goggles! The puffins flap happily around the smiling dragon, high-fiving his "
                    "claws in a heartwarming finale. Sweeping celebratory camera crane shot. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Con la chiave volò nel mondo d'oro e cristalli dai suoi amici... Erano altri draghi? No, erano PUFFINS!\" "
                    "Accompanied by joyful puffin chirps and a triumphant heartwarming orchestral finale."
                ),
            },
        ],
    },
    {
        "slug": "storia-scheletri-zombie-te",
        "title": "La Famiglia di Scheletri e gli Zombie Assetati di Tè",
        "folder": ROOT / "stories/alessandro/storia-scheletri-zombie-te",
        "output_mp4": "video_scheletri_zombie_te.mp4",
        "acts": [
            {
                "act": 1,
                "first_frame": "scena1_giardino_libreria.jpg",
                "prompt": (
                    "<FIRST_FRAME> Cute whimsical 3D animated children's storybook movie, 16:9 HD. "
                    "Starting from the first frame, a cheerful family of smooth ivory-white cartoon toy skeletons "
                    "(papa in a top hat, mama in a flower hat, and little child skeleton) along with their happy "
                    "little bony puppy walk into a very dark, deep blue enchanted garden at night. In the heart of "
                    "the dark garden stands a warm lantern-lit wooden outdoor library filled with adorable, polite "
                    "pastel-green cartoon bookworm zombie characters wearing reading glasses, who bow politely with "
                    "shy smiles and kindly ask for a cup of warm tea. Gentle cinematic dolly in. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Una famiglia di scheletri col cane scheletro andò nel buio buio giardino intenso, dove tanti zombie in libreria chiesero gentilmente del tè!\" "
                    "Accompanied by playful xylophone notes, crickets, and gentle nocturnal music."
                ),
            },
            {
                "act": 2,
                "first_frame": "scena2_primo_te.jpg",
                "prompt": (
                    "<FIRST_FRAME> Cute whimsical 3D animated children's storybook movie, 16:9 HD. "
                    "Starting from the first frame in the lantern-lit dark garden library, the kind cartoon skeleton "
                    "family returns from their house carrying a silver tray with a steaming porcelain teapot as their "
                    "bony puppy wags its tail. Papa Skeleton pours fragrant golden herbal tea with swirling warm steam "
                    "for the cute pastel-green bookworm zombies. They sip the tea with delight, their eyes sparkle with "
                    "joy, and they eagerly hold out their empty cups asking for more and more tea until the teapot is empty. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Gli scheletri andarono a casa a prendere il tè per gli zombie, ma gli zombie ne vollero di più, e ancora di più!\" "
                    "Accompanied by tea pouring sound, happy sips, and whimsical pizzicato strings."
                ),
            },
            {
                "act": 3,
                "first_frame": "scena3_due_bicchieri_grazie.jpg",
                "prompt": (
                    "<FIRST_FRAME> Cute whimsical 3D animated children's storybook movie, 16:9 HD. "
                    "Starting from the first frame in front of the glowing garden bookshelf, the smiling cartoon "
                    "skeleton family hurries back from home a second time, proudly presenting two tall, brimming "
                    "transparent glasses of steaming amber tea with lemon slices. The thirsty cute cartoon zombies "
                    "happily drink both tall glasses down to the last drop, let out a contented sigh, place the "
                    "glasses neatly on the tray, and bow politely in unison while saying thank you as the bony puppy wags its tail. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Tornati a casa, questa volta presero due bicchieri di tè. Gli zombie li bevvero tutti e dissero: Grazie!\" "
                    "Accompanied by happy drinking sounds, warm harp glissando, and cheerful woodwinds."
                ),
            },
            {
                "act": 4,
                "first_frame": "scena3_due_bicchieri_grazie.jpg",
                "prompt": (
                    "<FIRST_FRAME> Cute whimsical 3D animated children's storybook movie, 16:9 HD. "
                    "Starting from the first frame in the cozy lantern-lit dark garden beside the wooden library, "
                    "the welcoming cartoon skeleton family leans forward with big cheerful smiles, gesturing warmly "
                    "to ask if their friends would like anything else. All the cute pastel-green bookworm zombies "
                    "jump for joy, raising their hands and cheering in unison under a shower of glowing golden fireflies "
                    "while the little bony puppy does a happy spin, celebrating a joyful midnight tea party. Slow celebratory camera pull-back. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Allora gli scheletri chiesero: Vuoi un'altra cosa? E tutti gli zombie risposero in coro: Sì! Finita!\" "
                    "Accompanied by festive cheering, xylophone flourish, and a joyful orchestral finale chord."
                ),
            },
        ],
    },
    {
        "slug": "storia-pupurabbu-hot-wheels-lido-degli-estensi",
        "title": "Seby, il Dolce Pupurabbu e la Pista Fatata delle Hot Wheels a Lido degli Estensi",
        "folder": ROOT / "stories/sebastian/storia-pupurabbu-hot-wheels-lido-degli-estensi",
        "output_mp4": "video_pupurabbu_hotwheels.mp4",
        "acts": [
            {
                "act": 1,
                "first_frame": "scena1_spiaggia_lido_estensi.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame on the sunny golden sandy beach of Lido degli Estensi with colorful "
                    "beach umbrellas and turquoise Adriatic waves in the background. Six-year-old Seby, a joyful little "
                    "boy with a bright smile, kneels on the sand beside his adorable soft purple plush bunny Pupurabbu "
                    "with long floppy lavender ears. Together they press the launcher on a giant bright-orange plastic "
                    "toy car stunt track built on the sand, launching a sleek electric-blue miniature toy race car with "
                    "golden flame decals zooming fast down the orange track. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Sulla spiaggia di Lido degli Estensi, il piccolo Seby e il suo peluche viola Pupurabbu lanciano il bolide blu sulla pista arancione!\" "
                    "Accompanied by gentle ocean waves, toy race car zoom, and upbeat sunny acoustic guitar and piano."
                ),
            },
            {
                "act": 2,
                "first_frame": "scena2_portale_fatato.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame on the sunny beach, as the sleek blue toy race car reaches the top "
                    "of the giant orange vertical loop-de-loop, a dazzling turquoise-and-gold fairy portal of stardust "
                    "and iridescent bubbles spins open right inside the loop. Touched by fairy sparkles, the soft purple "
                    "plush bunny Pupurabbu magically comes to life, blinks his sweet button eyes, and smiles warmly, "
                    "taking Seby by the hand. The blue race car magically grows big enough for both; Seby and Pupurabbu "
                    "hop aboard and zoom straight into the glowing fairy portal! "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Tre, due, uno, via! Nel giro della morte si apre un portale fatato: Pupurabbu prende vita e sfreccia con Seby nella magia!\" "
                    "Accompanied by magical fairy chimes, revving race car engine, and soaring orchestral swell."
                ),
            },
            {
                "act": 3,
                "first_frame": "scena3_mondo_magico_hotwheels.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame high in an enchanted sky kingdom, six-year-old Seby at the steering "
                    "wheel and his cute purple plush bunny Pupurabbu in the co-pilot seat wearing tiny racing goggles "
                    "speed full-throttle in their electric-blue race car along giant rainbow-and-orange tracks suspended "
                    "among fluffy pink cotton-candy clouds and floating crystal sandcastles. Pupurabbu's long lavender "
                    "ears flutter in the breeze as he claps his soft paws, while cute golden starfish and pastel crabs "
                    "wave checkered flags cheering them on, leaving a sparkling rainbow trail. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Nel mondo magico corrono a tutto gas su piste arcobaleno tra nuvole di zucchero filato, castelli di cristallo e stelline in festa!\" "
                    "Accompanied by joyful child giggles, race car whoosh, and magical upbeat orchestral adventure music."
                ),
            },
            {
                "act": 4,
                "first_frame": "scena4_abbraccio_tramonto_lido.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame on the golden beach of Lido degli Estensi at a warm pink-and-violet "
                    "sunset with the wooden pier glowing in the background. A gentle beam of fairy light fades as "
                    "six-year-old Seby sits on the warm sand and tightly hugs his cuddly purple plush bunny Pupurabbu "
                    "against his cheek with pure love and wonder. Between Pupurabbu's soft purple fabric paws glows a "
                    "real magical golden-and-turquoise seashell trophy, while the blue toy race car rests beside them "
                    "on the orange track. Heartwarming cinematic close-up. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Tornati sulla spiaggia di Lido degli Estensi al tramonto con la conchiglia luminosa, Seby abbraccia forte il suo dolce Pupurabbu!\" "
                    "Accompanied by gentle evening sea waves, soft magical chime, and tender emotional piano lullaby."
                ),
            },
        ],
    },
    {
        "slug": "storia-cavalletto-marie-mondo-cavalli",
        "title": "Sebastian, il Cavalletto Magico Marie e il Camion Camper dei Cavalli",
        "folder": ROOT / "stories/sebastian/storia-cavalletto-marie-mondo-cavalli",
        "output_mp4": "video_cavalletto_marie_camion.mp4",
        "acts": [
            {
                "act": 1,
                "first_frame": "scena1_cavalletto_marie_soffio_tunnel.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame in a magical forest glade, 6-year-old Sebastian (a cute boy with "
                    "dark blonde straight hair, bright sky-blue eyes, red cap, and green hoodie) watches in amazement "
                    "as his adorable miniature white pony Marie blows a swirling stream of sparkling blue-and-gold "
                    "stardust from her snout (`fiuuu!`), spinning open a glowing cosmic vortex tunnel portal in the woods. "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"C'era una volta Sebastian con un cavalletto magico di nome Marie: con un soffio fiuuu, Marie aprì un vortice luminoso!\" "
                    "Accompanied by a magical wind chime whoosh, gentle pony whinny, and wondrous orchestral strings."
                ),
            },
            {
                "act": 2,
                "first_frame": "scena2_vortice_dimensionale_mondo_cavalli.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame, 6-year-old Sebastian (with dark blonde straight hair, bright sky-blue "
                    "eyes, denim overalls over a green striped shirt) steps joyfully out of the glowing rainbow vortex "
                    "portal into the wondrous World of Horses, a sunlit valley with horseshoe-roof cottages and friendly "
                    "horses of every color trotting happily along rainbow fences to welcome him! "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Attraverso il tunnel magico arrivò nel Mondo dei Cavalli, dove tutto era a misura di cavallo e volevano visitare il mondo umano!\" "
                    "Accompanied by sparkling portal whoosh, cheerful horse neighs, and triumphant adventure music."
                ),
            },
            {
                "act": 3,
                "first_frame": "scena3_camion_camper_tutti_cavalli.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family comedy adventure film, 16:9 HD. "
                    "Starting from the first frame at golden sunset, 6-year-old Sebastian (with dark blonde straight hair, "
                    "bright sky-blue eyes, and a blue hoodie) sits proudly at the steering wheel of his awesome custom "
                    "Scania multi-function horse-transporter camper truck ('SEBASTIAN'S ADVENTURE - THE ADVENTURE STAR'), "
                    "complete with cozy bunk beds upstairs and horse stalls below. Happy horses climb up the side ramp "
                    "and poke their smiling heads out the windows as the camper truck drives toward the glowing vortex portal! "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Trovò un fantastico camion camper dove vivere e portare tutti i cavalli, e partì a tutto gas attraverso il tunnel!\" "
                    "Accompanied by a friendly truck horn, rumbling camper engine, happy hooves, and upbeat brass fanfare."
                ),
            },
            {
                "act": 4,
                "first_frame": "scena4_marie_chiude_tunnel_mondo_umani.jpg",
                "prompt": (
                    "<FIRST_FRAME> High-end 3D animated family feature film, 16:9 HD. "
                    "Starting from the first frame inside the cozy cab of the camper truck driving down a sunny street "
                    "in the human world, 6-year-old Sebastian (with dark blonde straight hair, bright sky-blue eyes, and "
                    "blue striped hoodie) smiles at the wheel while petting his miniature white pony Marie sitting on the "
                    "passenger seat beside him. Through the rear window, the swirling vortex portal sparkles and closes "
                    "forever in a shower of golden stardust as they live happily ever after! "
                    "Audio design: A warm, expressive Italian storyteller voice narrates in clear Italian: "
                    "\"Caricata a bordo anche la piccola Marie, il tunnel magico si chiuse alle loro spalle e vissero felici per sempre!\" "
                    "Accompanied by a magical sparkling chime, celebratory horse neighs, and a warm orchestral finale chord."
                ),
            },
        ],
    },
]


def upload_image_asset(client: genai.Client, img_path: Path) -> tuple[str, str]:
    """Uploads a local image via the Gemini Files API and returns (normalized_uri, mime_type)."""
    print(f"📤 Uploading first-frame image: {img_path.relative_to(ROOT)} ...")
    uploaded = client.files.upload(file=str(img_path))
    while uploaded.state.name == "PROCESSING":
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"File upload failed for {img_path}: state={uploaded.state.name}")
    uri = uploaded.uri
    m = re.search(r"files/([a-zA-Z0-9]+)", uri)
    if m:
        uri = f"https://generativelanguage.googleapis.com/files/{m.group(1)}"
    return uri, uploaded.mime_type or "image/jpeg"


def generate_single_10s_act(api_key: str, story_slug: str, story_folder: Path, act_spec: dict, out_act_mp4: Path) -> Path:
    """Generates a single 10-second HD animated video act using Gemini Omni Flash."""
    if out_act_mp4.exists() and out_act_mp4.stat().st_size > 100_000:
        # Check duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(out_act_mp4)],
            capture_output=True, text=True
        )
        try:
            dur = float(probe.stdout.strip())
            if dur >= 9.0:
                print(f"⏭️  [{story_slug} Act {act_spec['act']}] Already exists ({dur:.1f}s), reusing {out_act_mp4.name}")
                return out_act_mp4
        except Exception:
            pass

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=600_000))
    img_path = story_folder / act_spec["first_frame"]
    img_uri, img_mime = upload_image_asset(client, img_path)

    input_parts = [
        {"type": "image", "uri": img_uri, "mime_type": img_mime},
        {"type": "text", "text": act_spec["prompt"]},
    ]
    video_config = {
        "type": "video",
        "aspect_ratio": "16:9",
        "duration": "10s",
        "delivery": "uri",
    }

    models_to_try = ["gemini-omni-flash-preview", "gemini-omni-1.2-flash", "gemini-omni-1.1-flash"]
    last_err = None

    for attempt in range(1, 4):
        for model_name in models_to_try:
            try:
                print(f"🎬 [{story_slug} Act {act_spec['act']}] Generating 10s clip with '{model_name}' (attempt {attempt})...")
                interaction = client.interactions.create(
                    model=model_name,
                    input=input_parts,
                    response_format=video_config,
                )
                output_video = getattr(interaction, "output_video", None)
                if not output_video:
                    raise RuntimeError(f"Empty output_video from {model_name} (interaction id={getattr(interaction, 'id', None)})")

                out_act_mp4.parent.mkdir(parents=True, exist_ok=True)
                if getattr(output_video, "data", None):
                    data = output_video.data
                    raw = base64.b64decode(data) if isinstance(data, str) else data
                    out_act_mp4.write_bytes(raw)
                elif getattr(output_video, "uri", None):
                    video_uri = output_video.uri
                    try:
                        video_bytes = client.files.download(file=output_video)
                        out_act_mp4.write_bytes(video_bytes)
                    except Exception:
                        sep = "&" if "?" in video_uri else "?"
                        dl_url = f"{video_uri}{sep}alt=media"
                        req = urllib.request.Request(dl_url, headers={"x-goog-api-key": api_key})
                        with urllib.request.urlopen(req, timeout=300) as resp:
                            out_act_mp4.write_bytes(resp.read())
                else:
                    raise RuntimeError(f"Neither data nor uri in output_video for {story_slug} Act {act_spec['act']}")

                print(f"✅ [{story_slug} Act {act_spec['act']}] Saved 10s clip -> {out_act_mp4} ({out_act_mp4.stat().st_size // 1024} KB)")
                return out_act_mp4

            except Exception as e:
                err_s = str(e)
                last_err = e
                if "404" in err_s or "not_found" in err_s.lower() or "not found" in err_s.lower():
                    continue
                print(f"⚠️  [{story_slug} Act {act_spec['act']}] Error with {model_name}: {err_s[:220]}")
                time.sleep(3 * attempt)

    raise RuntimeError(f"Failed to generate {story_slug} Act {act_spec['act']} after retries: {last_err}")


def stitch_4_acts_to_40s_mp4(act_files: list[Path], final_mp4: Path, hover_mp4: Path):
    """Concatenates 4 x 10s clips into a seamless 40.0-second 1280x720 24fps H.264/AAC MP4."""
    print(f"🎞️  Stitching 4 x 10s acts into 40s movie: {final_mp4.relative_to(ROOT)} ...")
    inputs = []
    filter_parts = []
    concat_inputs = []

    for idx, f in enumerate(act_files):
        inputs.extend(["-i", str(f)])
        filter_parts.append(
            f"[{idx}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p,setsar=1[v{idx}];"
        )
        filter_parts.append(
            f"[{idx}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{idx}];"
        )
        concat_inputs.append(f"[v{idx}][a{idx}]")

    filter_complex = "".join(filter_parts) + "".join(concat_inputs) + f"concat=n={len(act_files)}:v=1:a=1[vout][aout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(final_mp4),
    ]
    subprocess.run(cmd, check=True)

    # Also update 5-second hover_preview.mp4
    hover_cmd = [
        "ffmpeg", "-y",
        "-i", str(final_mp4),
        "-t", "5",
        "-vf", "scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2",
        "-an",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "23",
        "-movflags", "+faststart",
        str(hover_mp4),
    ]
    subprocess.run(hover_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "default=noprint_wrappers=1", str(final_mp4)],
        capture_output=True, text=True, check=True
    )
    print(f"🎉 Completed 40s movie {final_mp4.relative_to(ROOT)}:\n{probe.stdout.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Generate 40s (4x10s) Italian-narrated videos for all 3 stories")
    parser.add_argument("--slug", help="Optional single story slug to build", default=None)
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel Omni Flash generations (default: 4)")
    args = parser.parse_args()

    api_key = load_api_key()
    specs = STORY_SPECS
    if args.slug:
        specs = [s for s in specs if s["slug"] == args.slug]

    # Build job list for all acts
    jobs = []
    for st in specs:
        acts_dir = Path("/tmp/kids_stories_40s_acts") / st["slug"]
        acts_dir.mkdir(parents=True, exist_ok=True)
        for act in st["acts"]:
            out_act = acts_dir / f"act{act['act']}_10s.mp4"
            jobs.append((st["slug"], st["folder"], act, out_act))

    print(f"🚀 Launching {len(jobs)} x 10s Gemini Omni Flash generations with concurrency={args.concurrency}...")
    results = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        future_map = {
            pool.submit(generate_single_10s_act, api_key, slug, folder, act, out_act): (slug, act["act"], out_act)
            for slug, folder, act, out_act in jobs
        }
        for fut in as_completed(future_map):
            slug, act_num, out_act = future_map[fut]
            path = fut.result()
            results[(slug, act_num)] = path

    # Stitch each story's 4 acts into the final 40s MP4
    for st in specs:
        slug = st["slug"]
        act_paths = [results[(slug, i)] for i in range(1, 5)]
        final_mp4 = st["folder"] / st["output_mp4"]
        hover_mp4 = st["folder"] / "hover_preview.mp4"
        stitch_4_acts_to_40s_mp4(act_paths, final_mp4, hover_mp4)


if __name__ == "__main__":
    main()
