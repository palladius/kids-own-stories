# Changelog

All notable changes to **kids-own-stories** will be documented in this file.

## [0.4.0] - 2026-11-07

### Added
- ✨ **Hover "WOW" Preview (5s Veo Video + Voce Suadente Titolo IT/EN)**:
  - Passando il mouse (`hover` / `focus`) sulle card della vetrina `📚 Tutte` o sui tab storia nella barra in alto, parte istantaneamente il **video riassuntivo di 5 secondi** (`hover_preview.mp4`) accompagnato da una **voce femminile calma e suadente (`Aoede` via Gemini 2.5 Flash TTS + accordo caldo di pianoforte)** che recita dolcemente il titolo della storia in Italiano (`title_it.mp3`) o Inglese (`title_en.mp3`).
  - Generato `video_scheletri_zombie_te.mp4` e `hover_preview.mp4` anche per la Storia #2 (*"La Famiglia di Scheletri e gli Zombie Assetati di Tè"*), portando entrambe le storie a `status: complete` in `stories.yaml`.
- 🎙️🔄 **Due Modali di Intake Storie (`<dialog closedby="any">`)**:
  - **🔄 "La storia non mi piace, rigenerala…"**: bottone discreto nel footer del libro per inviare commenti creativi al subagente `cantastorie` (es. sostituire personaggi o cambiare il finale) tramite GitHub Issue `agy-actionable` o esportazione JSON.
  - **🎙️ "+ Nuova Storia"**: studio di registrazione vocale nel browser (`MediaRecorder` API + visualizzatore di forma d'onda `AudioContext` in tempo reale + trascrizione live `Web Speech API`) per registrare nuove storie di Alessandro e Sebastian direttamente dal microfono.

## [0.3.0] - 2026-11-07

### Added
- 📖 **3D Open-Book Zero-Scroll Carousel (`index.html`, `100dvh`)**:
  - Header ultra-compatto su singola riga (`58px`) con 1 Tab per storia, selettore lingua `🇮🇹 IT` / `🇬🇧 EN` e **Player Audiolibro Narrato (`🎧 Voce + Pianino`)** in alto a destra.
  - Libro aperto 3D a doppia pagina (`calc(100dvh - 58px)`, zero scrolling verticale) con illustrazione a sinistra, 3 paragrafi narrativi ben legati a destra e animazione 3D `rotateY` al cambio pagina (`‹ Indietro` / `Avanti ›` e frecce tastiera).
  - Link discreto in piccolo a fondo pagina (`📝 Vedi cosa Alessandro intendeva davvero...`) che apre un `<dialog closedby="any">` con l'audio grezzo originale e la sbobinatura parola-per-parola.
- 🗣️ **Subagente `cantastorie` & Testi Bilingui (`IT` / `EN`)**:
  - Arricchimento narrativo di tutte le pagine (3 paragrafi coesi per pagina in italiano e in inglese) salvato in `stories.yaml` (schema `2.0`).
- 🎧 **Audiolibri Bilingui con Voce Femminile (`Aoede`) e Sottofondo di Pianoforte (`bin/generate_story_audiobooks.py`)**:
  - Generati `narrated_it.mp3` e `narrated_en.mp3` per entrambe le storie con Gemini 2.5 Flash TTS (`voiceName: "Aoede"`) + loop di pianoforte dolce mixato in `ffmpeg`.
- 🎨 **Remake Illustrazioni Storia #2 (`storia-scheletri-zombie-te`)**:
  - Rimossa la vecchia immagine viola con bias di Pux (`scena1_scheletri_te.png`) e generate 3 nuove illustrazioni Pixar 3D / *Coco*-style coerenti (`scena1_giardino_libreria.jpg`, `scena2_primo_te.jpg`, `scena3_due_bicchieri_grazie.jpg`).
- 🧪 **Creative Draft (`creative-draft.html` + artifact `creative-draft.md`)**:
  - Dashboard di revisione multimediale per monitorare e commentare immagini, video e tracce audio.

## [0.2.0] - 2026-11-06

### Added
- 🌐 **Vetrina & Libro Multi-Pagina Interattivo con 1 Tab per Storia (`index.html`)**:
  - Barra di navigazione sticky in alto (`role="tablist"`) generata deterministicamente da `stories.yaml` con **un Tab dedicato per ogni storia** (`🎒🐉🐧 1. Zaino, Drago & Puffins`, `💀🧟☕ 2. Scheletri, Zombie & Tè`) + il tab generale `📚 Tutte le Storie` e deep-linking tramite hash URL (`#<slug>`).
  - Dentro ogni Tab storia: player dell'audio originale (`.mp3`/`.ogg`), sfogliatore interattivo pagina-per-pagina o vista continua di tutti i capitoli, citazione iconica, video animato AI e sbobinatura fedele parola-per-parola.
  - Pagina web dedicata `stories/alessandro/storia-scheletri-zombie-te/index.html` per la seconda storia di Alessandro.
  - Workflow GitHub Actions (`.github/workflows/pages.yml`) e `.nojekyll` per il deploy automatico su GitHub Pages (`https://palladius.github.io/kids-own-stories/`).

## [0.1.0] - 2026-11-06

### Added
- 🎒🐉🐧 Aggiunta la prima storia ufficiale di Alessandro: **"La Storia dello Zaino Magico, del Drago e dei Puffins"** sotto `stories/alessandro/storia-dello-zaino-del-drago-e-dei-puffins/`.
  - Registrazione audio microfonata originale di Alessandro (`.mp3` e `.ogg`).
  - Sbobinatura integrale fedele (trascrizione audio-to-text).
  - 4 scene illustrate in stile Pixar 3D (Nano Banana Pro / Gemini 3 Pro Image).
  - Video animato del gran finale generato con Gemini Omni Flash (`gemini-omni-flash-preview`).
  - Pagina web interattiva `index.html` con audio player e video incorporati.

## [0.0.1] - 2026-11-06

### Added
- 🔵 Initial repository scaffold (`stories/alessandro/`, `stories/sebastian/`, `audio/`) ready for transcribing recorded stories and building the web showcase (*vetrina*).
