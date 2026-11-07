# Changelog

All notable changes to **kids-own-stories** will be documented in this file.

## [0.6.2] - 2026-11-07

### Fixed & Changed
- 🛠️ **Fix Definitivo Overlap / Aliasing tra Testo e Bottoni di Navigazione Pagina (`index.html`)**:
  - Aggiunto `grid-template-rows: minmax(0, 1fr)` su `.open-book`, sostituito il wrapper flessibile con `.book-text-main` (`min-height: 0; overflow: hidden`) e reso `.book-prose` un contenitore scrollabile isolato (`min-height: 0; overflow-y: auto; justify-content: safe center`) sopra un `.book-nav-footer` opaco (`background: var(--paper-bg); flex-shrink: 0; z-index: 10`), rendendo fisicamente impossibile qualsiasi sovrapposizione tra i paragrafi e i tasti `‹ Indietro` / `Avanti ›`.
  - Eliminato il vuoto scuro sopra il libro (`max-height: 100%` con layout `body` flex column `100dvh`) e reso responsiva la topbar sotto `1380px` così i tab delle 3 storie non vengono mai tagliati o schiacciati.
- 🔘 **Dock con Bottoni ENORMI Sotto al Libro (`index.html`)**:
  - Trasformato `footer.micro-footer` in una barra ad alta visibilità appena sotto il libro con 3 grandi pulsanti pillola: **`🔄 La storia non mi piace, rigenerala!`**, **`🎙️ + Racconta una Nuova Storia`** e **`📝 Audio Originale & Sbobinatura di Sebastian/Alessandro`**.
- ⏩ **Velocità Voce di Default aumentata del `+10%` (`1.1x`) su Tutte le Voci (`index.html`, `stories/*/*/index.html`)**:
  - Impostato `currentPlaybackSpeed = 1.1` (`1.1x (+10%)` selezionato di default in `#playbackSpeedSelect`, con opzioni `0.5x`, `0.75x`, `0.9x`, `1.0x`, `1.1x (+10%)`, `1.2x`, `1.25x`, `1.5x`, `1.75x`, `2.0x`) con `preservesPitch = true` su `#narratorAudio`, `#hoverTitleAudio`, sintesi vocale live e pagine singole delle storie.

## [0.6.1] - 2026-11-07

### Fixed
- 🎯 **Allineamento Acustico Whisper (`word_timestamps=True`) + Stacchi Pagina a Campioni Zero (`bin/build_karaoke_timings.py`)**:
  - Risolto il desync del Karaoke inglese (es. Pagina 3 di `storia-scheletri-zombie-te`, dove lo stacco di pagina cadeva erroneamente dopo il titolo a `141.93s` invece che allo stacco esatto di `0.65s` a campioni zero a `137.52s`, facendo partire *"Seeing that their new friends..."* cliccando sul titolo).
  - Riscritto `bin/build_karaoke_timings.py` combinando il rilevamento deterministico degli stacchi inter-pagina a campioni zero (`0.65s`) con il **forced alignment acustico parola-per-parola tramite OpenAI Whisper (`word_timestamps=True`) + programmazione dinamica Needleman-Wunsch** su tutte e 3 le storie (`IT` e `EN`).
  - Allineato al 100% il testo e il titolo di Pagina 3 di `storia-scheletri-zombie-te` (`"Two Glasses of Tea and the Grand Tea Party!"` / `"Due Bicchieri di Tè e la Grande Festa!"`) con il parlato effettivo di `Aoede`.
- ⚡ **Supporto `HTTP/1.1 206 Partial Content` (`Accept-Ranges: bytes`) sul Server Locale (`bin/serve_local.py`) e Seek Audio Robusto (`index.html`)**:
  - Sostituito `python3 -m http.server` con `bin/serve_local.py` dotato di supporto `Range: bytes=...` (`206 Partial Content`) per rendere istantaneo il Tap-to-Seek su Chrome in locale (`http://localhost:8088/`).

## [0.6.0] - 2026-11-07

### Added
- 🐰🏎️🌈 **Prima Storia di Sebastian ("Seby", 6 anni) da GitHub Issue #1 (`storia-pupurabbu-hot-wheels-lido-degli-estensi`)**:
  - **"Seby, il Dolce Pupurabbu e la Pista Fatata delle Hot Wheels a Lido degli Estensi"** (*"Seby, Sweet Pupurabbu, and the Enchanted Hot Wheels Track at Lido degli Estensi"*), completa in **5 lingue (`🇮🇹 IT`, `🇬🇧 EN`, `🇫🇷 FR`, `🇩🇪 DE`, `🇧🇷 PT-BR`)** e con **Karaoke Parola-per-Parola (`karaoke_it.json`, `karaoke_en.json`)**.
  - Scaricato e convertito l'audio originale `.webm` registrato dal modulo `+ Nuova Storia` e allegato alla GitHub Issue #1 (`audio/sebastian/2026-11-07-storia-pupurabbu-hot-wheels-lido-degli-estensi.{webm,mp3,ogg}` e `audio_originale.{mp3,ogg}`).
  - Sbobinatura fedele parola-per-parola e adattamento narrativo in 4 pagine illustrate *super cutie* per un bimbo di 6 anni.
  - 4 illustrazioni 3D Pixar coerenti (`scena1_spiaggia_lido_estensi.jpg`, `scena2_portale_fatato.jpg`, `scena3_mondo_magico_hotwheels.jpg`, `scena4_abbraccio_tramonto_lido.jpg`) con Seby, il morbido coniglietto di peluche viola **Pupurabbu** e la pista delle **Hot Wheels** tra Lido degli Estensi e il Mondo Magico.
  - Audiolibri bilingui `narrated_it.mp3` e `narrated_en.mp3` con voce femminile calma (`Aoede` via Gemini 2.5 Flash TTS) e sottofondo di pianoforte, più `title_it.mp3`, `title_en.mp3`, `video_pupurabbu_hotwheels.mp4` e `hover_preview.mp4`.
- 🐛 **Fix Autore Dinamico nella Vetrina (`index.html`)**:
  - Le card della vista `📚 Tutte` ora mostrano dinamicamente l'autore e l'emoji corretta da `stories.yaml` (`🧒 Sebastian (6 anni)` vs `👦 Alessandro (8 anni)`).

## [0.5.1] - 2026-11-07

### Added
- 🌍 **Traduzione Narrativa Completa in 5 Lingue (`🇮🇹 IT`, `🇬🇧 EN`, `🇫🇷 FR`, `🇩🇪 DE`, `🇧🇷 PT-BR`) & Sblocco Immediato sopra `8.0/10` (`stories.yaml`, `index.html`)**:
  - Aggiunti titoli, titoli brevi, citazioni e tutti i paragrafi pagina per pagina in **Francese (`fr`)**, **Tedesco (`de`)** e **Portoghese Brasiliano (`pt`)** per entrambe le storie di Alessandro.
  - Quando l'utente vota **`8`, `9` o `10`** nel modale `⭐ Vota la Storia`, i pulsanti `🇫🇷 FR`, `🇩🇪 DE` e `🇧🇷 PT` si sbloccano istantaneamente nella topbar e permettono di sfogliare il libro nelle 5 lingue, con **Karaoke Live (`Web Speech API` `onboundary` + moltiplicatore velocità `0.5x–2x` + Auto-Scroll + Auto-Page-Turn)** a costo zero di token AI, oltre al bottone per richiedere la sintesi studio `Aoede + Pianino` via GitHub Issue.

## [0.5.0] - 2026-11-07

### Added
- 🎤 **Motore Karaoke Parola-per-Parola + Auto-Scroll + Auto-Page-Turn (`index.html`, `bin/build_karaoke_timings.py`)**:
  - Allineamento al centesimo di secondo (`karaoke_it.json` e `karaoke_en.json`) calcolato sui campioni vocali puri a `24.000 Hz` di `Aoede` con rilevamento pause naturali (`RMS VAD`) e pesatura sillabica.
  - Ogni parola (`.k-word`) si illumina di giallo oro mentre viene pronunciata, con **Tap-to-Seek** (toccando qualsiasi parola l'audio salta a quel punto).
  - **Auto-Scroll fluido** su Mobile e Desktop che mantiene sempre al centro dello schermo la riga letta.
  - **Auto-Page-Turn**: quando la voce finisce una pagina e inizia la successiva, il libro gira pagina da solo (con foglio 3D che ruota e sfruscio della carta).
- ⚡ **Moltiplicatore di Velocità Voce stile YouTube (`0.5x` .. `2x`)**:
  - Selettore velocità (`0.5x`, `0.75x`, `1x`, `1.25x`, `1.5x`, `1.75x`, `2x` con `preservesPitch = true`) integrato nella barra `🎤 Karaoke + Pianino`, perfettamente sincronizzato col Karaoke.
- ⭐ **Sistema di Voting Storia (`1..10`) con Gate Anti-Spreco Token (`>= 8/10`) per `🇫🇷 FR`, `🇩🇪 DE`, `🇧🇷 PT-BR`**:
  - Italiano (`🇮🇹 IT`) e Inglese (`🇬🇧 EN`) attivi subito col Karaoke; Francese, Tedesco e Portoghese Brasiliano si sbloccano quando il voto della storia supera **`8.0/10`**.

## [0.4.1] - 2026-11-07

### Fixed & Improved (Mobile UX, Swipe & 3D Page Leaf + Sound)
- 📱 **Mobile Layout Zero-Scroll (`100dvh`) & Audio Narrato Sempre Visibile**:
  - La barra **`🎧 Voce + Pianino (IT/EN)`** ora si dispone su una riga dedicata a larghezza piena su mobile (`<= 900px`) così l'audiolibro narrato è sempre visibile e cliccabile in alto.
  - Il libro su mobile ora entra interamente nello schermo (`calc(100dvh - 118px)`) con illustrazione panoramica compatta in alto (`21dvh`), testo dei 3 paragrafi subito leggibile al centro e bottoni `‹ Indietro | Avanti ›` fissati in basso senza dover fare scrolling della pagina.
- 👆 **Touch Swipe Left / Right su Mobile**:
  - Aggiunto il supporto nativo allo swipe orizzontale col dito (`touchstart` / `touchend`) sul libro per sfogliare avanti e indietro come su un vero libro.
- 📄🔊 **Foglio 3D che Gira (`#pageTurnLeaf`) + Sfruscio Realistico della Carta (`Web Audio API`)**:
  - Ad ogni cambio pagina (click, frecce o swipe), una pagina fisica 3D ruota con ombra dinamica accompagnata dal suono sintetizzato dello **sfruscio di carta** (`playPageFlipRustle`).

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
