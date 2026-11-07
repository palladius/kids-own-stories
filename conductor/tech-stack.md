# Tech Stack — Kids' Own Stories

- **Frontend**: Static HTML5, Modern CSS3 (`100dvh`, 3D CSS transforms, `<dialog closedby="any">`, View Transitions), Vanilla ES2022 JavaScript (`index.html`, `creative-draft.html`), hosted on **GitHub Pages** (`https://palladius.github.io/kids-own-stories/`).
- **Single Source of Truth**: `stories.yaml` (schema `2.0`).
- **AI Media Pipeline**:
  - **Narrative Enrichment**: `cantastorie` subagent (IT & EN cohesive paragraphs).
  - **Illustrations**: Gemini 3 Pro Image / Nano Banana Pro (`scenaN_*.jpg`).
  - **Audiobooks**: `bin/generate_story_audiobooks.py` using `gemini-2.5-flash-preview-tts` (`voiceName: "Aoede"`) + `ffmpeg` piano mixing.
  - **Video**: Gemini Omni Flash / Veo (`video_*.mp4`).
- **Cloud Intake Backend (Track `intake_forms_20261107`)**: Browser `MediaRecorder` API + GCP (Cloud Run / Cloud Storage / Firestore) or GitHub Issue / Webhook dispatch.
