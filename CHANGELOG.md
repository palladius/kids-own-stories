# Changelog

All notable changes to **kids-own-stories** will be documented in this file.

## [0.11.0] - 2026-11-14

### Added & Changed
- 🏝️🚤🏹 **7ª Storia Completa di Famiglia (6 Pagine con Foto Reali da Immich): *La Grande Avventura in Sardegna: Cala Gonone, il Gommone con Nonna Lucilla e Arbatax* (`stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/`)**:
  - Racconta la vacanza di famiglia dal 25 settembre al 2 ottobre 2026 in 6 pagine illustrate con le vere foto da Immich (`Sinologo`) in formato `16:9` widescreen:
    1. *Benvenuti a Cala Gonone: Acqua di Cristallo e Maschere da Sub!* (`scena1_cala_gonone_mare.jpg`)
    2. *Tramonto a Cala Gonone: Cena sul Mare con Nonna Lucilla e la Luna Piena* (`scena2_cena_nonna_lucilla.jpg`)
    3. *Capitan Nonna Lucilla e Mamma Kate: In Gommone nel Golfo di Orosei!* (`scena3_gommone_golfo_orosei.jpg`)
    4. *Fratelli sul tetto della Sardegna: L'Abbraccio tra i Monti del Supramonte* (`scena4_supramonte_fratelli.jpg`)
    5. *Arbatax Park Resort: Le Frecce di Mamma Kate, Maradona #10 e l'Asinello di Seby!* (`scena5_arbatax_arco_asinelli.jpg`)
    6. *Gli Esploratori degli Scogli di Ogliastra: Arrivederci Sardegna!* (`scena6_scogli_arbatax_snorkeling.jpg`)
  - Include i bollini cartoon anche per **Mamma Kate (`assets/avatars/kate.png`)** e **Nonna Lucilla (`assets/avatars/lucilla.png`)**, audiolibri studio bilingui (`narrated_it.mp3`, `narrated_en.mp3`), Karaoke Whisper a 6 pagine (`karaoke_it.json`, `karaoke_en.json`), audio hover del titolo (`title_it.mp3`, `title_en.mp3`) e film da 40s (`video_sardegna_famiglia.mp4`).
- 🍿 **Pulsanti Netflix Espliciti & Catalogo Offline ([`index.html`](index.html), [`netflix.html`](netflix.html), [`stories_catalog.js`](stories_catalog.js))**:
  - Rinominato il tab nella topbar in **`🍿 Netflix (StorieFlix)`** e aggiunti i pulsanti rapidi **`🎬 Film 40s`** e **`🍿 Netflix (StorieFlix)`** direttamente nella barra del Karaoke sopra il libro.

## [0.10.0] - 2026-11-14

### Added & Changed
- 👦🏻🧔🏻 **Bollini Cartoon in Sovrimpressione & Modello `N:N` Autore ↔ Destinatario ([`index.html`](index.html), [`netflix.html`](netflix.html), [`stories.yaml`](stories.yaml), `assets/avatars/`)**:
  - Aggiunti i cerchietti con le faccine cartoon in sovrimpressione sulle card per **Alessandro (Ale, anello rosso `#ef4444`)**, **Sebastian (Seby, anello azzurro `#3b82f6`)** e **Papà Riccardo (Papino, anello oro `#f59e0b`)**.
  - Supporto completo per la relazione `N:N` **`authors` ("Scritta da") ↔ `recipients` ("Storia per")**: ogni card mostra sia chi ha inventato la storia sia a chi è dedicata (es. *Papino Riccardo ✍️ → per Alessandro ❤️*), e i filtri per persona mostrano sia le storie scritte da quel bimbo sia quelle dedicate a lui.
- 🍿 **Vista "StorieFlix" in Stile Netflix Senza Duplicazioni ([`netflix.html`](netflix.html) e tab `#netflix` in [`index.html`](index.html))**:
  - Pagina e vista dedicata **solo ai video** con tema scuro `#141414`, Hero Billboard in evidenza e **griglia unica con card giganti (`minmax(460px, 1fr)`)** senza righe duplicate: ogni film compare una sola volta in grande con i bollini cartoon in sovrimpressione.
  - Passando col mouse (`:hover`) il film parte subito in anteprima nella card (con audio attivo); cliccando sulla card si apre il **Cinema Modal a Tutto Schermo** con barra interattiva dei 4 Atti (`0:00–0:40`).
- 🍓⌨️🖥️ **6ª Storia Completa: *La Nascita di Sguisatazzo, il Computer Magico di Alessandro* (`stories/alessandro/storia-nascita-sguisatazzo-computer-alessandro/`)**:
  - Storia inventata da **Papino Riccardo** per il suo **Alessandro (Ale)**: racconta di come una tastiera **Raspberry Pi 400** bianca e rosa-lampone prese coscienza, si staccò da un computer cattivo (`TITAN`) per diventare un computer libero (*Sguisatazzo*), scappò fino a **Zurigo**, suonò al campanello di **Casa Carlesso** (`DRIIIIN!`) e fu adottata dal tenero Alessandro, vivendo da allora sul desk nella sua camera da letto tra giochi e programmi educativi.
  - Include 4 illustrazioni Pixar 3D `16:9`, testo in 5 lingue (`it`, `en`, `fr`, `de`, `pt`), audiolibri studio con pianoforte (`narrated_it.mp3`, `narrated_en.mp3`), Karaoke Whisper parola-per-parola (`karaoke_it.json`, `karaoke_en.json`), audio hover dei titoli (`title_it.mp3`, `title_en.mp3`) e film animato da 40 secondi (`video_sguisatazzo.mp4` + `hover_preview.mp4`).

## [0.9.3] - 2026-11-08

### Changed
- 🏛️ **Carlessian WebApp Decluttering & 100% `audit_webapp.mjs` Compliance ([`index.html`](index.html))**:
  - **R1–R3 (Zero "Fuffa" & Progressive Disclosure)**:
    - Eliminato il pulsante duplicato *"+ Racconta una Nuova Storia"* che compariva due volte (in alto a destra e in fondo alla pagina).
    - Rimossi i testi tutorial ridondanti tra parentesi dall'header delle pagine del libro (*"🎤 Tocca una parola per ascoltare da lì"*, *"📖 Pagina Sinistra (76%)"*, *"PAGINA ACCANTO (DESTRA • 24%) ›"*) e il banner prolisso sopra la vista Indice, sostituiti da chip compatti (`Pag. 1 / 4`).
    - Aggiunta la **Tabella Sinottica L1 (`#synopticTableWrap`)** nella vista Indice (`?tab=indice`) con `font-variant-numeric: tabular-nums`, date ISO `YYYY-MM-DD` perfettamente incolonnate al pixel, badge autore stilizzati (`Ale` `#ef4444` / `Seby` `#3b82f6`), icone SVG monocromatiche `currentColor` e zebra striping sottile.
  - **R4–R5 (Permalinks `?tab=...&page=...&kid=...&lang=...&q=...` & Sopravvivenza al Reload `F5`)**:
    - Ogni cambio di storia, pagina del libro, filtro autore (`all` / `alessandro` / `sebastian`), lingua (`it` / `en` / `fr` / `de` / `pt`) e ricerca live aggiorna in tempo reale la query string dell'URL (`window.history.replaceState`) e `localStorage`, preservando lo stato esatto al `F5` reload.
  - **R6–R8 (Header & Footer Canonici Carlessiani)**:
    - Header con link Home (`data-home-link`), **Segmented Control `role="radiogroup"`** per filtrare le storie per autore (`Tutte` | `Ale` | `Seby` senza doppie emoji), **Live Search (`/` shortcut)** e selettore lingua con `data-lang="it|en|..."`.
    - Footer canonico (`<footer>`) con versione cliccabile (`v0.9.3`), badge ambiente (`ENV: development` / `ENV: production`), azioni compatte con icone SVG monocromatiche (`Film 40s`, `Voce di Ale/Seby`, `Rigenera`) e i 4 link canonici (`GH Repo`, `GHP Live`, `GHI Issues`, `🐛 Add a Bug`).
    - Superati al **100%** sia l'audit deterministico CDP `audit_webapp.mjs` (`9/9` sulla vista Libro e `20/20` sulla vista Indice) sia `just test` (`python3 bin/test_stories.py`).

## [0.9.2] - 2026-11-08

### Changed & Fixed
- 📖 **Impaginazione a Doppia Pagina Asimmetrica (`76% / 24%` in base alla Parità) con Illustrazione 16:9 in Alto e Testo in Basso su Entrambe le Pagine ([`index.html`](index.html))**:
  - Ogni pagina del libro aperto (Sinistra = pagine dispari `1, 3, 5`; Destra = pagine pari `2, 4`) è ora un'unità narrativa completa con **Illustrazione 16:9 in alto** e **Testo della storia in basso** (con pulsante **`⇅ Testo in Alto / Foto in Alto`** per invertire istantaneamente l'ordine verticale e **`↔️ 84% / 16%`** per regolare la proporzione).
  - La pagina attiva in **primo piano** occupa il **76% (`70–80%`)** della larghezza del libro (`.open-book.focus-left` sulle pagine dispari `1, 3, 5`; `.open-book.focus-right` sulle pagine pari `2, 4`), mentre la pagina adiacente resta visibile sull'altro lato al **24% (`20–30%`)** in *minore importanza* con miniatura 16:9, titolo, anteprima del testo e clic diretto per voltare pagina.
- 🔇 **Rimozione dei Sottotitoli di Pagina dalla Pronuncia Vocale e dal Karaoke ([`index.html`](index.html), [`bin/generate_story_audiobooks.py`](bin/generate_story_audiobooks.py), [`bin/build_karaoke_timings.py`](bin/build_karaoke_timings.py), `stories/*/*/narrated_{it,en}.mp3`, `stories/*/*/karaoke_{it,en}.json`)**:
  - I sottotitoli di capitolo (`h2.book-chapter-title`) restano visibili graficamente in testa a ogni pagina, ma **non vengono più pronunciati** dalla voce narrante né nel Karaoke Live, evitando di interrompere il flusso della fiaba ogni 2–3 paragrafi.
  - Rimossi chirurgicamente i segmenti vocali dei sottotitoli di pagina da tutti i 10 audiolibri (`5 storie × IT/EN`) e ricalibrati al millisecondo tutti i 10 file `karaoke_{it,en}.json` (`title_words: []`).

## [0.9.1] - 2026-11-08

### Changed
- ⚡🐴 **Nuova Illustrazione Epica `16:9` per la Scena 2 + Rigenerazione Atto 2 del Film 40s (`stories/alessandro/storia-sebi-campione-pony-club-pupurabbu/scena2_salto_impossibile_velocita_luce.jpg`)**:
  - Sostituita la precedente Scena 2 con un'inquadratura Pixar d'azione dal basso ad altissima energia: Sebi e il suo pony bianco sfrecciano sopra un colossale ostacolo da Grand Prix (stanghe bianco-rosse, ali blu/oro e stella d'oro in cima) attraversando un cono d'onda d'urto supersonico con fulmini al plasma dorati/blu e vortice di sabbia, mentre i grandissimi cavalli sotto sgranano gli occhi e il fratello maggiore Ale salta con i capelli spettinati dal boom sonico esultando al microfono d'oro!
  - Rigenerato l'Atto 2 (`10s`) e riassemblato `video_sebi_campione_pony_club.mp4` (`40s`).

## [0.9.0] - 2026-11-08

### Added & Changed
- 🏆🐴🌈 **5ª Storia Completa: *Sebi, il Campione del Pony Club alla Velocità della Luce e il Disco Party con Pupurabbu* (`stories/alessandro/storia-sebi-campione-pony-club-pupurabbu/`, Issue `#2`)**:
  - Promossa da `inbox/2026-11-08-alessandro-sebi-campione-pony-club/` la nuova storia inventata e raccontata a voce da **Alessandro ("Ale", 8 anni)** per il fratellino **Sebastian ("Sebi", 6 anni)** insieme a papà Riccardo.
  - **Sbobinatura Fedele Riascoltata all'Audio Originale**: corretta l'attribuzione delle battute di papà Riccardo e preservata la perla multilingue di Ale (*"poi c'è un rainbow, Regenbogen!"*).
  - **4 Illustrazioni 16:9 Widescreen Pixar 3D (`1376x768`) con Entrambi i Fratelli**:
    - **Sebi** (6 anni, capelli biondo scuro con frangetta morbida, grandi occhi azzurri limpidi, giacca da equitazione blu) in sella al suo pony bianco;
    - **Ale** (8 anni, capelli castani lisci con frangetta, occhi nocciola espressivi, felpa blu/rossa e microfono dorato da narratore/cronista ufficiale) che fa il tifo a bordo campo, esulta al salto alla velocità della luce, batte il cinque sul podio della Coppa d'Oro e balla alla **Disco Party** sotto il **Regenbogen** insieme a **Pupurabbu gigante**!
  - **Pacchetto Multimediale Completo (`just test` 100% PASS)**:
    - Testo del Cantastorie in **5 lingue** (`it`, `en-GB`, `fr`, `de`, `pt`) in [`stories.yaml`](stories.yaml).
    - Audiolibri Studio con pianoforte (`narrated_it.mp3`, `narrated_en.mp3` in British English `en-GB`) + Karaoke Whisper parola-per-parola (`karaoke_it.json`, `karaoke_en.json`).
    - Film animato completo da **40 secondi (`4 × 10s`)** (`video_sebi_campione_pony_club.mp4`) + anteprima Hover 5s (`hover_preview.mp4`) + annunci vocali del titolo (`title_it.mp3`, `title_en.mp3` in `en-GB`).

## [0.8.4] - 2026-11-08

### Fixed & Changed
- 🇬🇧 **British English (`en-GB`) Obbligatorio su Tutti gli Audio Inglesi e Pronuncia Europea di `"Sebastian"` (`bin/generate_hover_wow_assets.py`, `bin/generate_story_audiobooks.py`, `index.html`, `GEMINI.md`)**:
  - **Addio pronuncia americana *"Shebashtian"* (`en-US`)**: impostato `languageCode: "en-GB"` in `speechConfig` di Gemini 2.5 TTS, `en: 'en-GB'` in Web Speech API (`index.html`) e istruzioni di regia vocale British RP (*UK Received Pronunciation / BBC CBeebies bedtime story*), forzando la pronuncia europea/britannica cristallina **`"Se-bas-ti-an"`** (`/sɪˈbæstɪən/`, con *t-i-an* nitido e MAI *"Suh-bas-chun"*).
  - **Fix Fade-Out Precoce su `title_it.mp3` e `title_en.mp3` (`bin/generate_hover_wow_assets.py`)**: rimosso il fade-out hardcoded a `st=4.5s` che tagliava la fine dei titoli più lunghi (*"A story by Sebastian"* / *"Una fiaba di Sebastian"*), calcolando dinamicamente `fade_start = voice_dur + 0.15s` sulla durata reale del parlato.
  - Rigenerati tutti i file `title_it.mp3`, `title_en.mp3`, `narrated_en.mp3` e `karaoke_en.json` in British English (`en-GB`).

## [0.8.3] - 2026-11-08

### Fixed & Changed
- 🖼️ **Impaginazione Intelligente "Widescreen Album 16:9" per Tutte le Illustrazioni del Libro (`index.html`)**:
  - **Zero Cropping Orizzontale sulle Foto 16:9**: eliminato `height: 100%; object-fit: cover` su `.book-page-left img` che tagliava i lati destro e sinistro delle illustrazioni 16:9 (es. il muso dello Scania e il vortice a Pagina 3 di *Cavalletto Marie*, o metà di Pupurabbu a Pagina 1 di *Seby & Pupurabbu*).
  - **Griglia Libro Asimmetrica (`1.32fr : 0.94fr`) + Cornice 16:9 + Storyboard Filmstrip**:
    - La pagina sinistra dedica ora il 58% della larghezza del libro alla tavola illustrata orizzontale (`aspect-ratio: 16 / 9; object-fit: contain`) incorniciata su sfondo ambient sfocato, con pulsante **`[ ⛶ Tutto Schermo ]`** (`openPhotoLightbox()`) nell'angolo in alto a destra per ingrandire qualsiasi illustrazione a pieno schermo.
    - Nella fascia inferiore della pagina sinistra è stata aggiunta la **Storyboard Filmstrip 16:9** (`Pag. 1`, `Pag. 2`, `Pag. 3`, `Pag. 4`, `🎬 Film 40s`) con miniature orizzontali cliccabili e pulsante `↔️ Allarga Pagina`, riempiendo armoniosamente l'altezza della pagina senza mai tagliare un solo pixel delle foto.
- 🧪 **Test Deterministico di Integrità `just test` (`justfile`, `bin/test_stories.py`, `GEMINI.md`)**:
  - Aggiunto `just test` (`python3 bin/test_stories.py`) che verifica con `ffprobe` e JSON schema tutte le storie in `stories.yaml` e **fallisce (`exit 1`)** se a una storia manca l'hover video (`hover_preview.mp4`), l'annuncio vocale del titolo (`title_it.mp3`, `title_en.mp3`), l'audiolibro (`narrated_it.mp3`, `narrated_en.mp3`), il Karaoke Whisper (`karaoke_it.json`, `karaoke_en.json`), il film da 40s (`video_*.mp4 >= 35s`), le illustrazioni 16:9 orizzontali (`width > height`) o le 5 lingue (`it`, `en`, `fr`, `de`, `pt`).

## [0.8.2] - 2026-11-08

### Fixed & Changed
- 🎬 **Fix Video Orizzontale 16:9 a Pagina 5 + Controlli "Tutto Schermo" in Stile Netflix (`index.html`)**:
  - **Risolto il bug del video tagliato in verticale**: rimosso `height: 100%; object-fit: cover` sul `<video>` di `.book-page-left` che costringeva il film 16:9 dentro il formato verticale della pagina sinistra tagliando i lati. Ora la pagina del film (`.book-page-left.is-video-page`) monta un **Netflix-style 16:9 Widescreen Player Frame** (`aspect-ratio: 16 / 9; object-fit: contain`) su sfondo ambient sfocato, mostrando il 100% dell'inquadratura orizzontale.
  - **Bottone col Quadratino `[ ⛶ Tutto Schermo ]` in Stile Netflix + Modalità `↔️ Allarga Player`**:
    - Aggiunto il pulsante con l'icona del quadratino **`[ ⛶ Tutto Schermo ]`** sia in sovraimpressione nell'angolo in alto a destra del video, sia nella barra di controllo Netflix sotto al player, sia sulla pagina destra (oltre al doppio clic sul video), che massimizza il film nella Sala Cinema mantenendo il secondo esatto di riproduzione (`currentTime`) e con pulsante per il Fullscreen nativo del browser (`requestFullscreen()`).
    - Aggiunto il pulsante **`↔️ Allarga Player`** (`.open-book.book-wide-theater`) per allargare la pagina sinistra del cinema dentro il libro.
  - **Fix Griglia dei 4 Atti sulla Pagina Destra**: usato `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)` e `.book-prose.movie-program-prose` eliminando lo spazio vuoto in alto, il capolettera gigante sulla descrizione e la scrollbar orizzontale.

## [0.8.1] - 2026-11-08

### Added & Fixed
- 🧒🏼💙 **Fix Fedele delle Fattezze di Seby (Capelli Biondo Scuro + Occhi Azzurri) preservando il Camion Camper Scania Originale (`storia-cavalletto-marie-mondo-cavalli`)**:
  - Editate chirurgicamente tutte e 4 le illustrazioni originali (`scena1_cavalletto_marie_soffio_tunnel.jpg`, `scena2_vortice_dimensionale_mondo_cavalli.jpg`, `scena3_camion_camper_tutti_cavalli.jpg`, `scena4_marie_chiude_tunnel_mondo_umani.jpg`) mantenendo al 100% le scene originali e il bellissimo camion camper multifunzione portacavalli **Scania `"SEBASTIAN'S ADVENTURE — THE ADVENTURE STAR"`** (con letti a castello, stalle e cavalli a bordo), correggendo solo Seby con i suoi veri **capelli biondo scuro lisci con frangetta** e **grandi occhi azzurri**.
  - Codificata in `GEMINI.md` e `stories.yaml` (`authors:`) la **Regola Canonica sull'Aspetto Fisico di Ale (capelli castani, occhi castani) e Seby (capelli biondo scuro, occhi azzurri)** affinché nessun agente AI sbagli mai più i loro tratti.
- 🎬 **Film Animato Completo da 40 Secondi (`4 Atti × 10s`) + Anteprima Hover (`video_cavalletto_marie_camion.mp4`, `hover_preview.mp4`)**:
  - Generato con `gemini-omni-flash-preview` (`bin/generate_40s_story_videos.py`) il film animato completo da **40 secondi** (`1280x720` HD, narrato in italiano) partendo dalle 4 scene editate col camion camper Scania di Seby, più la clip rapida `hover_preview.mp4` (`5s`).
- 🎧 **Audiolibri Studio Bilingui (`narrated_it.mp3`, `narrated_en.mp3`), Voci Hover (`title_it.mp3`, `title_en.mp3`), Karaoke Whisper (`karaoke_it.json`, `karaoke_en.json`) e 5 Lingue (`IT`, `EN`, `FR`, `DE`, `PT-BR`)**:
  - Espanso il racconto di `storia-cavalletto-marie-mondo-cavalli` a 3 ricchi paragrafi per pagina in tutte e 5 le lingue (`IT`, `EN`, `FR`, `DE`, `PT-BR`).
  - Generati gli audiolibri narrati da `Aoede` con sottofondo di pianoforte (`narrated_it.mp3` e `narrated_en.mp3`), gli audio del titolo per l'hover (`title_it.mp3` e `title_en.mp3`) e l'allineamento Karaoke parola-per-parola con OpenAI Whisper (`karaoke_it.json` e `karaoke_en.json`).
  - Aggiornata la pagina dedicata `stories/sebastian/storia-cavalletto-marie-mondo-cavalli/index.html` (incluso fix del link `← Torna al Libro`, player audiolibro IT/EN, player del film da 40s e velocità `1.1x` di default).

## [0.8.0] - 2026-11-08

### Added
- 🐴🚛🌀 **Nuova Storia di Sebastian (6 anni): *Sebastian, il Cavalletto Magico Marie e il Camion Camper dei Cavalli***:
  - **Audio Originale Archiviato e Convertito**: salvato in `audio/sebastian/2026-11-08-storia-cavalletto-marie-mondo-cavalli.{mp3,ogg}` e dentro la cartella dedicata `stories/sebastian/storia-cavalletto-marie-mondo-cavalli/audio_originale.{mp3,ogg}`.
  - **Sbobinatura Integrale Fedele**: dialogo spontaneo parola-per-parola tra Sebi e papà Riccardo con Marie, il piccolo cavalletto magico, il tunnel vortice, il mondo dei cavalli e il camion camper gigante.
  - **4 Illustrazioni di Scena 3D Pixar Generate con Gemini Flash Image (16:9 1K)**:
    1. `scena1_cavalletto_marie_soffio_tunnel.jpg`: Sebi incontra Marie che soffia il tunnel vorticoso.
    2. `scena2_vortice_dimensionale_mondo_cavalli.jpg`: Sebi attraversa il vortice ed entra nel Mondo dei Cavalli con case a ferro di cavallo.
    3. `scena3_camion_camper_tutti_cavalli.jpg`: Sebi guida il grande camion camper con tutta la mandria a bordo verso il portale.
    4. `scena4_marie_chiude_tunnel_mondo_umani.jpg`: Sebi carica Marie in cabina, il tunnel si sigilla e tutti vivono felici nel mondo umano.
  - **Vetrina Web Dedicata (`index.html`) e Documentazione (`README.md`)**: con card illustrate, box dialoghi, player audio e trascrizione.
  - **Registro Deterministico Aggiornato (`stories.yaml`)**: nuova scheda storia completa per il libro interattivo.

## [0.7.1] - 2026-11-07

### Added & Changed
- 🍿 **Integrazione "Sala Cinema 40s" e Storyboard Interattivo a 4 Atti nel Libro 3D (`index.html`)**:
  - **Pulsante Gigante `🎬 Guarda il Film (40s)` nel Dock sotto al Libro**: permette di saltare da qualsiasi pagina direttamente alla pagina del film animato da 40 secondi con **audio italiano attivo** (o di aprire la **Sala Cinema a Schermo Intero** se si è già sulla pagina del film).
  - **Pillola `🎬 Film 40s` nei Indicatori Pagina del Libro (`.book-dots`)**: l'ultima pagina di ogni storia è ora segnalata da un badge dedicato `🎬 Film 40s` cliccabile con un tocco.
  - **Pagina Destra del Film con Storyboard Interattivo dei 4 Atti (`0:00`, `0:10`, `0:20`, `0:30`)**: quando si sfoglia fino alla pagina del video nel libro 3D, la pagina destra mostra il programma interattivo dei **4 atti da 10 secondi** con miniatura, orario e titolo; cliccando su un atto il video salta istantaneamente a `0s`, `10s`, `20s` o `30s` con audio attivo, evidenziando in tempo reale l'atto in riproduzione (`timeupdate`).
  - **Modal `🍿 Sala Cinema (Schermo Intero)` (`#cinemaDialog`)**: teatro 16:9 HD dedicato con selettore rapido dei 4 atti e pausa automatica della voce narrante Karaoke (`#narratorAudio`) per evitare sovrapposizioni audio.
  - **Pulsante diretto `🎬 Film Completo (40s)` anche nelle Card della Vetrina (`📚 Tutte`)** e cache-busting aggiornato a `?v=0.7.1`.

## [0.7.0] - 2026-11-07

### Added & Changed
- 🎬 **3 Film Animati Completi da 40 Secondi (`4 Atti × 10s`) Narrati in Italiano con Gemini Omni Flash (`bin/generate_40s_story_videos.py`)**:
  - Sostituiti i brevi clip da 5–7 secondi con **3 veri mini-film animati da `40.1` secondi ciascuno (`1280x720` 24fps H.264 + AAC 48kHz stereo)** che raccontano **l'intera trama dall'inizio alla fine** in 4 atti da 10 secondi partendo dalle illustrazioni `<FIRST_FRAME>` di ogni pagina:
    1. 🎒🐉🐧 **`stories/alessandro/storia-dello-zaino-del-drago-e-dei-puffins/video_drago_puffins.mp4`** (`40.1s`, `17.2 MB`): Atto 1 Chiave nello zaino e porta magica sul banco a scuola (*all'altro break sul suo desk*) → Atto 2 Mondo dei Draghi fatto di gemme → Atto 3 Battibecco col Drago (*«No, tu non puoi prenderle, sono mie!» / «No, ora sono mie!»*), fiammata cartoon e recupero di gemme e chiave → Atto 4 Volo nel mondo d'oro e cristalli con i **Puffins**!
    2. 💀🧟☕ **`stories/alessandro/storia-scheletri-zombie-te/video_scheletri_zombie_te.mp4`** (`40.1s`, `16.4 MB`): Atto 1 Passeggiata della famiglia di scheletri col cane scheletro nel *buio buio giardino intenso* e scoperta della libreria di zombie → Atto 2 Primo viaggio a casa, prima teiera fumante e zombie che ne vogliono *di più e ancora di più* → Atto 3 Secondo viaggio a casa con i **due bicchieri di tè** e il *«Grazie!»* degli zombie → Atto 4 *«Vuoi un'altra cosa? — Sì! Finita!»* festa di mezzanotte nel giardino.
    3. 🐰🏎️🌈 **`stories/sebastian/storia-pupurabbu-hot-wheels-lido-degli-estensi/video_pupurabbu_hotwheels.mp4`** (`40.1s`, `16.1 MB`): Atto 1 Seby (6 anni) e il suo morbido coniglietto di peluche viola **Pupurabbu** sulla spiaggia di **Lido degli Estensi** lanciano il bolide blu sulla pista arancione → Atto 2 Giro della morte, apertura del **portale fatato** e Pupurabbu che prende vita → Atto 3 Corsa a tutto gas sulle piste arcobaleno tra nuvole di zucchero filato, castelli di cristallo e stelline marine in festa → Atto 4 Ritorno al tramonto a Lido degli Estensi con la Conchiglia-Trofeo luminosa e l'abbraccio tenerissimo a Pupurabbu.
  - Rigenerati anche i 3 clip rapidi `hover_preview.mp4` (`5.0s` fast-start) e aggiornati `stories.yaml`, i `README.md` e gli `index.html` delle 3 storie.
- ⚖️ **Validazione Avversaria Multi-Agente (`10/10 APPROVATO`)**:
  - Tutti i 12 prompt da 10 secondi sono stati progettati e sottoposti a revisione avversaria incrociata tra `story-director`, `ale-fidelity-critic` (verifica al 100% di ogni dettaglio delle sbobinature originali di Ale e Seby) e `omni-technical-critic` (calibrazione prosodica a 16–23 parole italiane per atto da 10s anti-cutoff e sanitizzazione anti-blocco `35561575`).

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
