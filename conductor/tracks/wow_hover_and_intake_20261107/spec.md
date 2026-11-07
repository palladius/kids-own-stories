# Specification — Hover "WOW" Preview (5s Veo Video + Calm Title Voiceover) & Story Intake Forms

## 1. Overview
Enhance **Kids' Own Stories** (`index.html`, `creative-draft.html`, and `stories.yaml`) with two flagship interactive experiences:
1. **Hover "WOW" Effect on Story Cards & Story Tabs**:
   - When the user hovers over a story card in the `📚 Tutte le Storie` gallery (or hovers over a story tab / preview badge), a **5-second Veo summary video** (`hover_video.mp4` / `video_*.mp4`) smoothly crossfades in and plays, accompanied by a **soothing, calm female voice (`Aoede` via Gemini 2.5 TTS)** gently reciting the story's title (`title_it.mp3` / `title_en.mp3` matching the active language `🇮🇹 IT` or `🇬🇧 EN`).
2. **Two Interactive Story Intake Forms (`<dialog closedby="any">`)**:
   - **🔄 "La storia non mi piace, rigenerala"**: A discreet button in the book footer allowing Riccardo/Ale/Seby to submit a custom creative prompt (e.g., *"la parte degli zombi non mi piace, mettici invece una manticora..."*) to queue/trigger story regeneration (via GitHub Issue / Cloud endpoint / local JSON export).
   - **🎙️ "Nuova Storia al Microfono"**: A compact `+ 🎙️ Nuova Storia` button in the top bar that opens a `<dialog>` using the browser's `MediaRecorder` API + live Web Speech API preview to record a new story from the microphone, download the `.webm` + `.json` bundle locally or upload to GCP / GitHub Issue.

## 2. Functional Requirements
- **FR1 — 5-Second Veo Summary Videos for Every Story**:
  - Story #1 (`storia-dello-zaino-del-drago-e-dei-puffins`): 5-second cut/summary video (`hover_preview.mp4` derived from `video_drago_puffins.mp4`).
  - Story #2 (`storia-scheletri-zombie-te`): Generate a new Veo animated video (`video_scheletri_zombie_te.mp4` + 5-second `hover_preview.mp4`) showing the friendly white-bone skeleton family serving steaming cups of tea to polite green cartoon zombies outside the glowing wooden library in the dark garden.
- **FR2 — Calm Female Voice Title Audio (`title_it.mp3` & `title_en.mp3`)**:
  - Generated via `gemini-2.5-flash-preview-tts` (`voiceName: "Aoede"`) with a soft chime/piano pad, calmly reciting each story's title in Italian and English.
- **FR3 — Hover Interaction in `index.html`**:
  - On `mouseenter` / `focusin` over any story card (and optional hover preview on story tabs), immediately crossfade the static cover image to the `<video muted loop playsinline>` 5-second Veo clip AND play the corresponding `title_it.mp3` or `title_en.mp3` audio (with graceful fallback if browser autoplay policy requires a prior click anywhere on the page, plus a subtle speaker/play indicator).
  - On `mouseleave` / `focusout`, smoothly pause/reset the video and fade out the title voiceover.
- **FR4 — Story Regeneration & New Microphone Story Modals**:
  - Discreet `🔄 Non mi piace, rigenerala...` button in the book footer and `+ 🎙️ Nuova Storia` button in the navbar.
