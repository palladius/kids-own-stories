# Kids' Own Stories — Watercolor Learning Books Constitution

> **Normative Charter** for all interactive multi-page illustrated watercolor learning books in *Kids' Own Stories* (`window.KIDS_BOOKS_CATALOG`, `kids_books_catalog.js`, and the Studio Kids Book reader in `index.html`).

---

## 1. Purpose & Scope

This constitution defines the architectural, linguistic, pedagogical, and visual invariants for every multi-page interactive watercolor learning book published in `/home/riccardo/git/kids-own-stories`.

- It governs **Layer 2** interactive watercolor books (*Cala Gonone / Sardegna*, *Le Petit Prince*, and all future multi-page books).
- It complements [`GEMINI.md`](../GEMINI.md), which governs **Layer 1** mic-recorded family stories (`stories.yaml` + `stories/`).
- Every agent, build script, and test suite adding or validating a watercolor learning book MUST adhere to the rules in this document.

---

## 2. Two-Layer Repository Architecture

The repository maintains a strict separation between authentic mic-recorded stories and multi-page watercolor language-learning books:

| Dimension | Layer 1 — Mic-Recorded Stories | Layer 2 — Watercolor Learning Books |
|---|---|---|
| **Registry & Data** | `stories.yaml` -> `stories_catalog.js` | `books/<alias>/kids_book_data.json` (or `stories/.../kids_book_data.json`) -> `kids_books_catalog.js` |
| **Asset Root** | `stories/<author>/<slug>/` & `audio/<author>/` | `books/<alias>/` (e.g., `books/petit-prince/`) or story subfolder (`sardegna`) |
| **Origin** | Live microphone recordings of Ale & Seby | Family adventures & adapted literary classics (e.g., *Le Petit Prince*) |
| **Languages** | 5 prose languages (`it`, `en`, `fr`, `de`, `pt`) + `narrated_{it,en}.mp3` | **3 learning languages (`fr`, `it`, `de`)** + `en-GB` translation/explanation target |
| **Visual Format** | 16:9 scene plates + 40s animated AI video | `2N` watercolor plates (`896×1200` each) in `1792:1200` double spreads |
| **Validation Gate** | `just test` (`bin/test_stories.py`) | `just test` + `just test-fit` (`bin/test_kids_text_fit.py`) |

**Invariant:** Literary adaptations and book-only entries (such as *Le Petit Prince*, `le-petit-prince`) live exclusively in `books/<alias>/` and `kids_books_catalog.js`, and **MUST NOT** be added to `stories.yaml` (which enforces mic-recorded 40s video and 16:9 story rules via `bin/test_stories.py`).

---

## 3. Language Constitution (3 Learning Languages + `en-GB` Translation/Explanation Target)

### 3.1 The 3 Learning Languages: `FR`, `IT`, `DE`
Every Layer 2 watercolor book supports **exactly three learning languages**:
- **French (`fr`)**
- **Italian (`it`)**
- **German (`de`)**

Normative rules for learning languages:
1. `supported_langs` in every book manifest MUST be a non-empty subset or permutation of `["fr", "it", "de"]` (canonically all three).
2. `default_lang` MUST be one of `"fr"`, `"it"`, or `"de"` (e.g., `"fr"` for *Le Petit Prince*, `"it"` for *Cala Gonone*).
3. **Studio `Aoede` TTS Audio (`gemini-2.5-flash-preview-tts`, `MP3` + `OGG`)** MUST be generated for `fr`, `it`, and `de` across:
   - All 3 CEFR tiers (`seby`, `ale`, `emma`) × all plates (`pages[]`)
   - All plate speech bubbles (`speech_bubble.{fr,it,de}`)
   - Single-word vocabulary clips (`assets/words_audio/{fr,it,de}/`)
4. **Antolin comprehension quizzes (`questions.{fr,it,de}`)** MUST be authored in `fr`, `it`, and `de`.

### 3.2 English (`en-GB` Mandatory British English) — Strictly a Translation & Explanation Target
English (`en`, mandatory **British English `en-GB`**) is **strictly a native-speaker target language** for:
- Parallel translation (`Traduzione Pari Pari` / Cheating Mode right-hand page via `translations.en.{seby,ale,emma}`)
- Word glossary translations and definitions (`en_gloss` / `tok.gloss`)
- UI explanatory labels and translated page/book titles (`title.en`, `speech_bubble.en`)

**HARD PROHIBITIONS for English (`EN`):**
1. **NEVER a 4th learning book language:** `"en"` MUST NEVER appear in `supported_langs`, `default_lang`, or the Book Language selector (`📖 Lingua del Libro`).
2. **ZERO Studio TTS Audio for English:** NEVER generate `Aoede` studio TTS MP3/OGG files, single-word audio (`assets/words_audio/en/`), or studio bubble audio for English in Layer 2 books (Carlessian Compute Proportionality / anti-compute-waste).
3. **Browser `en-GB` Fallback Only:** If a reader clicks Listen on an English parallel-translation page, English speech bubble, or English token, the reader uses browser `window.speechSynthesis` fallback strictly with `lang = 'en-GB'` (UK Received Pronunciation — **NEVER `en-US`**).
4. **Pronunciation of `"Sebastian"`:** Whenever spoken or prompted in English, `"Sebastian"` must follow UK RP `/sɪˈbæstɪən/` (*Se-bas-ti-an* with crisp *t-i-an*, never *"Shebashtian"* / *"Suh-bas-chun"*).

---

## 4. Three CEFR Reading Tiers & Family Persona Mapping

Every plate provides three calibrated reading levels so the whole family can read the same illustrated book together:

| Tier Key | Reader Persona | Age | CEFR | Visual Ring | Word Budget / Plate | Narrative Style |
|---|---|---|---|---|---|---|
| `seby` | **Seby** | 6y | **A2** | Green (`tier-easy`) | `14–25` words | 1–2 short, concrete sentences wrapping >= 2 lines. |
| `ale` | **Ale** | 8y | **B1** | Yellow (`tier-medium`) | `26–42` words | 2–3 flowing sentences preserving iconic dialogues. |
| `emma` | **Emma & Papino** | 10–11y+ | **B2 / C1** | Red (`tier-hard`) | `40–64` words (`40–55` on tighter even `patch-top` pages) | Faithful / literary prose or distilled original extracts, B2/C1 glossary (`en_gloss`), and German separable verbs. |

### PuffinLogin Auto-Mapping
When a family member signs in via `<puffin-login>`, `index.html` maps the profile automatically:
- `seby` -> mode `seby`, translation language `it`
- `ale` -> mode `ale`, translation language `it`
- `emma` -> mode `emma`, translation language `it`
- `riccardo` / `papino` / `palladius` -> mode `emma`, translation language `it`
- `kate` / `mamma` -> mode `emma`, translation language `en`
- `lucilla` / `guest` / `saga` -> all 3 tiers (`seby`, `ale`, `emma`) remain selectable

### Adversarial CEFR Pedagogical Critic Gate
Before any new book's catalog and audio assets are finalized, all generated tier texts (`FR`/`IT`/`DE` × `seby`/`ale`/`emma`), `en-GB` parallel translations, `en_gloss` definitions, German separable-verb annotations, and Antolin quizzes MUST pass an **Adversarial CEFR Pedagogical Critic** audit verifying CEFR calibration, literary fidelity, British English (`en-GB`) spelling/idiom accuracy, and word-count compliance.

---

## 5. Pedagogical Mechanics (Montessori Grammar & German Separable Verbs)

### 5.1 Montessori Grammar Color Coding
Grammar highlighting is toggled via the floating bar Grammar button (off by default) and colors tokens by part of speech:
- **Nouns (`noun`)**: Black `#0f172a` (`🌸`)
- **Adjectives (`adj`)**: Green `#047857` (`🎨`)
- **Verbs (`verb`)**: Red `#dc2626` (`🏃`)
- **Adverbs (`adv`)**: Purple `#7e22ce` (`⚡`)

### 5.2 Gender & Number Endings (`IT` & `FR` ONLY — Disabled for `DE`)
- For **Italian (`it`)** and **French (`fr`)**, nouns and adjectives highlight their grammatical ending letter in Blue `#2563eb` (`kw-end-m`) or Pink `#db2777` (`kw-end-f`), with tooltip badges `m.s. 🔵👤`, `m.p. 🔵👥`, `f.s. 🌸👤`, `f.p. 🌸👥`.
- For **German (`de`)**, blue/pink final-letter gender coloring is **STRICTLY DISABLED** (to avoid confusing German grammatical gender with Italian/French inflectional endings); tooltips display number only (`Sg. 👤` / `Pl. 👥`).

### 5.3 German Separable Verbs (*Trennbare Verben*)
Split German verb stems and prefixes carry structured token metadata:
- `sep_group`: shared identifier linking the stem and detached prefix in the sentence
- `sep_role`: `"stem"` or `"prefix"`
- `sep_inf`: canonical infinitive with interpunct `·` (e.g., `"auf·brechen"`, `"an·kommen"`)
- `sep_pair`: display pair (e.g., `"bricht … auf"`)

Both tokens render in crimson `#991b1b` (`.kw-sep-verb`) and are connected dynamically by SVG dashed arcs (`drawKidsSeparableVerbArcs`) supporting both same-row arcs and wrapped multi-line arcs.

---

## 6. Visual Layout, Auto-Fit & Interactive Mechanics

### 6.1 Double-Spread Geometry & Alternating Patches
- **Spread Aspect Ratio**: `.open-book.kids-notebook-spread` is locked to `aspect-ratio: 1792 / 1200` within `100dvh` (reserving `84px` net bottom space for `.kids-notebook-floating-bar`), displaying two `896×1200` RGB JPEG watercolor plates (`wc_pNN.jpg`) on `#fdfaf2` warm cold-press paper.
- **Alternating Reading Patches**:
  - **Odd pages (`1, 3, 5, ...`)**: `patch-bottom` (`27.6%` height + `14px` bottom margin).
  - **Even pages (`2, 4, 6, ...`)**: `patch-top` (`25.6%` height; word glossary popovers open downward so they never clip at the top edge).

### 6.2 Dynamic Text Auto-Fit (`fitKidsTextToPatch`)
Text inside `.kids-white-patch-text-zone` / `.kids-sentence-box` is sized dynamically via binary search (`fitKidsTextToPatch()`). Every book MUST satisfy the Playwright `just test-fit` invariant across all spreads, all 3 tiers (`seby`, `ale`, `emma`), all 3 learning languages (`fr`, `it`, `de`), and Traduzione Pari Pari pairs (including `-> en`):
- `overflowY <= 2px`
- `overflowX <= 2px`
- `fillRatio >= 0.42`

### 6.3 Reader Controls, Quizzes & Bookmark
- **Floating Control Bar (`.kids-notebook-floating-bar`)**: Dark-brown `webapp-that-riccardo-likes` bar (`flex-wrap: nowrap` on desktop, responsive wrap below `860px`) containing the Book Selector (`#kidsBookSelector`), tier avatars (`Seby`, `Ale`, `Emma`), Grammar toggle, `a/A` uppercase toggle, Traduzione Pari Pari (`Cheating Mode`, `?parallel=1`), 5 reading speeds (`0.75×`, `0.88×`, `1.0×`, `1.15×`, `1.3×`), Settings popover (`#kidsSettingsPopover` separating `📖 Lingua del Libro` `[fr/it/de]` from `🌍 Lingua di Traduzione / Spiegazioni` `[en/it/fr/de]`), and Bookmark (`🔖`).
- **Speech Bubbles (`bubble_anchor` & `speech_bubble`)**: Positioned per plate via `bubble_anchor` (accepting `{ top, left, maxW, tail, tailLeft }` or normalized `{ x, y, tail }`); gracefully omitted when `speech_bubble` is `null` or empty.
- **Translation Protection**: All interactive book UI, leaves, bubbles, captions, book selector, and bookmark pills enforce `translate="no"` and `class="notranslate"` to prevent browser auto-translation from mutating foreign-language tokens.
- **Antolin Comprehension Quizzes**: At least 1 comprehension quiz every 2 plates (spread-level quizzes stored on even/right pages in new books, or per-page in legacy books), with 3 questions per learning language (`fr`, `it`, `de`: 2 standard `🟢` + 1 bonus `⭐`).
- **Bookmark (`Segnalibro`)**: Persisted in `localStorage` under key `kos_kids_bookmarks_v1` as `{ [bookId]: { page, mode, lang, trLang, parallel, savedAt } }`, allowing readers to save and resume their reading position per book across sessions.

---

## 7. Verification & Copyright Transparency

### 7.1 Required Verification Commands
Before committing changes to any book or reader code, run:
- **`just test`** (`bin/test_stories.py`) — Validates `stories.yaml` integrity, Layer 1 story assets, classic JS syntax (`node --check`) on inline `<script>` blocks in `index.html` and `kids_books_catalog.js`.
- **`just test-fit`** (`bin/test_kids_text_fit.py`) — Runs headless Playwright verification of text bounding-box fit (`overflow <= 2px`, `fillRatio >= 0.42`), Pari Pari parallel badge alignment, and `en-GB` pairs across all registered books.
- **`just serve`** — Serves the repository locally on port `8088` for interactive inspection (`?book=sardegna`, `?book=petit-prince`, `?story=sardegna`).

### 7.2 Public-Domain & Copyright Transparency
When adapting literary classics or historical illustrations in Layer 2 books, provenance and copyright status MUST be documented transparently in [`README.md`](../README.md). Specifically for *Le Petit Prince* (Antoine de Saint-Exupéry, 1943):
- Original text and watercolor illustrations entered the **public domain in Switzerland and the European Union in 2015** (`70 years` after Saint-Exupéry's death in 1944).
- In **France**, wartime copyright extensions ("Mort pour la France") extend domestic copyright protection until **2032**.
- All adaptations here are non-commercial, private/family educational materials using verified 1943 public-domain scans and original pedagogical rewrites/extracts.
