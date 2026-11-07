# Implementation Plan — `wow_hover_and_intake_20261107`

## Phase 1: Media Generation (5s Veo Videos & Calm Title Audio IT/EN)
- [x] Task: Generate calm female voiceover (`Aoede` via Gemini 2.5 Flash TTS) reciting the titles of Story #1 and Story #2 in IT and EN (`title_it.mp3`, `title_en.mp3`).
  - [x] Create `bin/generate_hover_wow_assets.py` and run it for all stories in `stories.yaml`.
- [x] Task: Generate video for Story #2 (`stories/alessandro/storia-scheletri-zombie-te/video_scheletri_zombie_te.mp4`) and 5-second `hover_preview.mp4` clips for both Story #1 and Story #2.
  - [x] Trim/encode fast-start 5-second `hover_preview.mp4` for instant zero-latency hover playback.

## Phase 2: Hover "WOW" Effect & Intake Modals in `index.html` & `stories.yaml`
- [x] Task: Update `stories.yaml` with `hover_video`, `video`, and `title_audio` (`it`, `en`) paths for both stories; set Story #2 `status: complete`.
- [x] Task: Implement Hover "WOW" video + soothing title audio playback on story cards and story tabs in `index.html`.
- [x] Task: Implement the two Intake `<dialog closedby="any">` modals (`🔄 Rigenera Storia` and `🎙️ Nuova Storia al Microfono` with `MediaRecorder` + live waveform + local/cloud/GitHub dispatch) in `index.html`.
- [x] Task: Update `creative-draft.html` and artifact `creative-draft.md` with the new Story #2 video, hover previews, and title voiceovers.

## Phase 3: Verification, Vetrina Sync & GitHub Pages Deploy
- [x] Task: Phase Verification & Checkpoint — Verify on `http://localhost:8088/`, commit `v0.4.0`, push to `origin/main` (GitHub Pages), and complete `/home/riccardo/git/vetrina` showcase integration.
