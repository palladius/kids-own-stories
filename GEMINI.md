# 📚🎙️ GEMINI.md — Manuale Operativo per *Kids' Own Stories*

Questo documento definisce **per filo e per segno** l'architettura, le convenzioni e il workflow operativo del repository `kids-own-stories`. Qualsiasi agente AI (Antigravity, Gemini CLI, Hermes/Ermete) o collaboratore umano deve seguire queste istruzioni quando aggiunge, aggiorna o verifica le storie.

---

## 🎯 Visione del Progetto

L'obiettivo di questo repository è **raccogliere e immortalare le idee e le storie inventate dai figli di Riccardo**:
* 👦 **Alessandro ("Ale")** — nato nel 2018 (`author: alessandro`). Fattezze fisiche per illustrazioni/video: bimbo di 8 anni, **capelli castani lisci con frangetta** e **occhi castani/nocciola espressivi**.
* 🧒 **Sebastian ("Seby" / "Sebi")** — nato nel 2020 (`author: sebastian`). Fattezze fisiche per illustrazioni/video: bimbo di 6 anni, **capelli biondo scuro / dorati con frangetta morbida** (*dark blonde hair*, MAI capelli neri o castano scuro!) e **grandi occhi azzurri limpidi** (*bright sky-blue eyes*, MAI occhi marroni!).
* 🇬🇧 **Regola Linguistica Inglese (`en-GB` British English OBBLIGATORIO)**: Tutti i testi e gli audio inglesi (`title_en.mp3`, `narrated_en.mp3`, Web Speech API) DEVONO usare **British English (`en-GB`, UK Received Pronunciation)** e MAI l'accento americano (`en-US`). Il nome *"Sebastian"* deve essere sempre pronunciato all'europea/britannica (`/sɪˈbæstɪən/`, *"Se-bas-ti-an"* con *t-i-an* nitido, MAI *"Shebashtian"* / *"Suh-bas-chun"*).

Il flusso parte sempre dal **dato grezzo autentico** (idealmente la **registrazione vocale al microfono** in cui il bimbo racconta la storia, spesso dialogando con papà Riccardo) e usa l'AI generativa per costruire attorno a quel seme un intero pacchetto multimediale:
1. 🎙️ **Audio Originale Raw** (`.ogg`, `.mp3`, `.m4a`, `.wav`) — la viva voce del bambino, intatta.
2. 📝 **Sbobinatura Fedele (Transcript)** — trascrizione parola-per-parola che preserva le invenzioni linguistiche, i prestiti dall'inglese/tedesco (es. *"prossimo giornata all'altro break sul suo desk"*) e il botta-e-risposta con il papà.
3. 📖 **Adattamento Narrativo in Capitoli/Pagine** — suddivisione della storia in 3–6 scene/pagine di un libro illustrato, fedele al 100% alla trama del bimbo.
4. 🎨 **Illustrazioni AI per ogni Pagina** — immagini generate con modelli di image generation (es. Gemini 3 Pro Image / Nano Banana Pro / Imagen 3) con stile coerente tra le scene (es. Pixar 3D / libro illustrato).
5. 🎬 **Video Animato AI** — clip animata (es. con Veo / Gemini Omni Flash) della scena clou o dell'intera storia.
6. 🌐 **Vetrina & Libro Multi-Pagina Interattivo** — sia una pagina `index.html` dedicata per singola storia, sia una **Web App / Libro sfogliabile multi-pagina** alimentata in modo deterministico dal file [`stories.yaml`](stories.yaml).

---

## 🗂️ Struttura Deterministica del Repository

```text
kids-own-stories/
├── GEMINI.md                                  # 👈 Questo manuale operativo per AI e umani
├── stories.yaml                               # 📋 Registro deterministico (Single Source of Truth)
├── README.md                                  # Vetrina principale del repo e indice umano
├── CHANGELOG.md                               # Storico delle modifiche e nuove storie
├── VERSION                                    # Versione semantica (es. 0.1.0)
├── audio/                                     # 🎙️ Archivio storico degli audio grezzi
│   ├── alessandro/
│   │   └── YYYY-MM-DD-<slug-breve>.{mp3,ogg}
│   └── sebastian/
│       └── YYYY-MM-DD-<slug-breve>.{mp3,ogg}
└── stories/                                   # 📖 Cartelle delle singole storie illustrate
    ├── alessandro/
    │   └── <slug-storia>/
    │       ├── README.md                      # Sbobinatura + racconto in Markdown + metadati
    │       ├── index.html                     # Libro/pagina web interattiva della storia
    │       ├── audio_originale.mp3            # Audio convertito MP3 per compatibilità browser
    │       ├── audio_originale.ogg            # Audio convertito OGG/Opus
    │       ├── scena1_<descrizione>.jpg       # Illustrazione Pagina/Capitolo 1
    │       ├── scena2_<descrizione>.jpg       # Illustrazione Pagina/Capitolo 2
    │       ├── scena3_<descrizione>.jpg       # Illustrazione Pagina/Capitolo 3
    │       ├── scena4_<descrizione>.jpg       # Illustrazione Pagina/Capitolo 4
    │       └── video_<descrizione>.mp4        # Video animato AI
    └── sebastian/
        └── <slug-storia>/
            └── ...
```

---

## 🛠️ Come Aggiungere una Nuova Storia (Per Filo e Per Segno)

Quando l'utente fornisce un nuovo file audio (o un'idea raccontata da Ale o Seby), segui **rigorosamente** questi 7 passaggi nell'ordine indicato:

### Passo 1 — Identificazione Autore, Data e Slug
1. Determina l'**autore**:
   * `alessandro` (Ale, 2018)
   * `sebastian` (Seby / Sebi, 2020)
2. Determina la **data di creazione** (`YYYY-MM-DD`, es. `2026-11-06`).
3. Scegli uno **slug descrittivo in kebab-case** in italiano (es. `storia-dello-zaino-del-drago-e-dei-puffins`):
   * La cartella ufficiale della storia sarà: `stories/<autore>/<slug-storia>/`
   * **Nota importante:** Non lasciare cartelle temporanee o duplicate con nomi diversi (es. `20261106-...`) dentro `stories/<autore>/`. Una storia = una sola cartella canonica.

### Passo 2 — Archiviazione e Conversione Audio (`ffmpeg`)
1. Salva l'audio originale nell'archivio globale:
   * `audio/<autore>/YYYY-MM-DD-<slug-breve>.<ext>`
2. Copia/converti l'audio dentro la cartella della storia `stories/<autore>/<slug-storia>/` in **entrambi** i formati standard per garantire il funzionamento su tutti i browser (Safari iOS/macOS, Chrome, Firefox):
   * `audio_originale.mp3` (`ffmpeg -i <input> -codec:a libmp3lame -qscale:a 2 audio_originale.mp3`)
   * `audio_originale.ogg` (`ffmpeg -i <input> -codec:a libvorbis -qscale:a 5 audio_originale.ogg` o copia se già `.ogg`)

### Passo 3 — Sbobinatura Fedele (Speech-to-Text)
1. Ascolta/trascrivi l'audio originale con Gemini.
2. **REGOLA D'ORO DELLA SBOBINATURA:**
   * **Non correggere la grammatica infantile** nella sezione `"Sbobinatura Fedele"`. Le frasi spontanee dei bambini (es. *"un zaino"*, *"prossimo giornata all'altro break"*, *"ci ha entrato"*) sono il tesoro più prezioso del repository!
   * Distingui chiaramente i turni di parola tra chi racconta (es. `**Alessandro:**` o `**Sebastian:**`) e chi fa domande (`**Papà Riccardo:**`).
   * Usa il grassetto o il maiuscolo per dare enfasi alle esclamazioni del bimbo (es. `**PUFFINS**!`).

### Passo 4 — Strutturazione in Pagine/Capitoli e Generazione Illustrazioni
1. Suddividi il racconto in **3–6 Capitoli (Pagine)** logici:
   * Ogni capitolo rappresenta una "pagina" del libro illustrato multi-pagina.
   * Nella versione narrativa (`Il Racconto Illustrato`), arricchisci il testo in bell'italiano da libro di fiabe, pur mantenendo **ogni singolo dettaglio e colpo di scena** inventato dal bambino (anche quelli assurdi o comici!).
2. Genera un'illustrazione per ciascun capitolo/pagina:
   * Salvale come `scena1_<tema>.jpg`, `scena2_<tema>.jpg`, `scena3_<tema>.jpg`, ecc. dentro `stories/<autore>/<slug-storia>/`.
   * Mantieni la **coerenza visiva** dei personaggi da una scena all'altra (stesso aspetto del protagonista, stesso colore del drago, stesso stile Pixar 3D / illustrazione digitale calda e vibrante).

### Passo 5 — Generazione Video AI (Opzionale ma Consigliato)
1. Genera un video animato (`.mp4`, preferibilmente 16:9 `1280x720`) a partire dalla scena clou o dal gran finale della storia.
2. Salvalo nella cartella della storia come `video_<tema>.mp4`.

### Passo 6 — Creazione di `README.md` e `index.html` della Storia
Dentro `stories/<autore>/<slug-storia>/` crea:
1. **`README.md`** contenente:
   * Titolo con emoji + blockquote con autore, età, data e luogo.
   * Link ai file audio (`audio_originale.mp3`, `audio_originale.ogg` e copia in `audio/`).
   * Sezione `## 📝 Sbobinatura Fedele (Audio Transcript)` con la trascrizione integrale.
   * Sezione `## 📖 Il Racconto Illustrato` con i capitoli e le immagini `![Capitolo N](scenaN_....jpg)`.
   * Sezione `## 🎬 Il Video Ufficiale` (se presente) e link a `index.html`.
2. **`index.html`** contenente:
   * Pagina web autonoma, curata e responsiva (font `Fredoka` e `Nunito`), con:
     * Box `<audio controls>` in alto con `<source src="audio_originale.mp3">` e `<source src="audio_originale.ogg">`.
     * Card illustrate per ciascun capitolo/pagina con dialoghi evidenziati (`.dialogue-box`).
     * Quote box con la battuta più iconica del bimbo.
     * Player `<video>` per l'animazione finale (se presente).

### Passo 7 — Aggiornamento del Registro Deterministico (`stories.yaml`) e File Globali
Ogni volta che aggiungi o modifichi una storia, **DEVI** aggiornare:
1. **[`stories.yaml`](stories.yaml)** — Aggiungi o aggiorna la voce della storia con tutti i campi e verifica la `checklist` (vedi sezione seguente).
2. **[`README.md`](README.md)** — Aggiungi la storia sotto la sezione del bimbo corrispondente (`### 👦 Alessandro` o `### 🧒 Sebastian`).
3. **[`CHANGELOG.md`](CHANGELOG.md)** e **[`VERSION`](VERSION)** — Incrementa la versione e documenta la nuova storia o gli asset aggiunti.

---

## 📋 Il Registro Deterministico: `stories.yaml`

Il file [`stories.yaml`](stories.yaml) nella root del repository permette di rispondere istantaneamente e in modo deterministico a domande come:
* *"Quante storie ci sono di Ale e quante di Seby?"*
* *"Quali storie sono complete e a quali manca ancora il video o la sbobinatura?"*
* *"Quali sono le pagine, i testi e le immagini da mostrare nella Web App del libro sfogliabile?"*

### Schema di una Storia in `stories.yaml`

```yaml
  - id: YYYY-MM-DD-<slug-storia>
    slug: <slug-storia>
    title: "Titolo della Storia"
    emoji: "🎒🐉🐧"
    author: alessandro # oppure: sebastian
    author_age_at_recording: 8
    co_authors: ["papà Riccardo"]
    created_at: "YYYY-MM-DD"
    location: "Zurigo"
    language: "it"
    folder: stories/<author>/<slug-storia>

    # Stato del ciclo di vita:
    # idea_only | raw_audio | transcribed | illustrated | complete
    status: complete

    # Checklist deterministica ("C'è tutto? Manca qualcosa?")
    checklist:
      raw_audio: true          # C'è la registrazione vocale originale?
      audio_converted: true    # Ci sono sia .mp3 che .ogg nella cartella storia?
      transcription: true      # C'è la sbobinatura fedele parola-per-parola?
      chapters_text: true      # C'è il testo diviso in capitoli/pagine?
      illustrations: true      # Ogni pagina ha la sua immagine .jpg/.png?
      video: true              # C'è il video .mp4 generato con AI?
      web_page: true           # C'è il file index.html della storia?
    missing_assets: []         # Elenco esplicito di cosa manca (es. ["video", "illustrations"])

    assets:
      archive_audio:
        mp3: audio/<author>/YYYY-MM-DD-<slug-breve>.mp3
        ogg: audio/<author>/YYYY-MM-DD-<slug-breve>.ogg
      story_audio:
        mp3: stories/<author>/<slug-storia>/audio_originale.mp3
        ogg: stories/<author>/<slug-storia>/audio_originale.ogg
      readme: stories/<author>/<slug-storia>/README.md
      web_page: stories/<author>/<slug-storia>/index.html
      video:
        file: stories/<author>/<slug-storia>/video_<tema>.mp4
        model: gemini-omni-flash-preview
        resolution: "1280x720"
      pages:
        - page: 1
          title: "Titolo Capitolo 1"
          image: stories/<author>/<slug-storia>/scena1_<tema>.jpg
          summary: "Breve riassunto della pagina per il libro multi-pagina."
```

### Come verificare lo stato ("C'è tutto? Manca qualcosa?" — `just test`)
Prima di ogni commit (o quando l'utente chiede una verifica di integrità), esegui **`just test`** (`python3 bin/test_stories.py`), che fallisce con exit code `1` se a qualsiasi storia manca anche solo uno tra:
- `archive_audio.{mp3,ogg}` e `story_audio.{mp3,ogg}`
- **Hover WOW assets**: `hover_preview.mp4` (`5s`), `title_it.mp3` e `title_en.mp3` (`bin/generate_hover_wow_assets.py`)
- **Audiolibri Studio + Karaoke Whisper**: `narrated_{it,en}.mp3` (`bin/generate_story_audiobooks.py`) e `karaoke_{it,en}.json` (`bin/build_karaoke_timings.py`)
- **Film 40s (`4 × 10s`)**: `video_*.mp4` (`>= 35s`, `bin/generate_40s_story_videos.py`)
- **Illustrazioni 16:9 Orizzontali** (`width > height`) e testo in **5 lingue** (`it`, `en`, `fr`, `de`, `pt`).
