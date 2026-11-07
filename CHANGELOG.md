# Changelog

All notable changes to **kids-own-stories** will be documented in this file.

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
