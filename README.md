# 📚🎙️ Kids' Own Stories — Le Storie di Alessandro & Sebastian

> **Raccolta delle storie inventate, raccontate al microfono, sbobinate e illustrate da Alessandro (Ale, 2018) e Sebastian (Seby, 2020).** 👦🧒✨

Questo repository raccoglie i racconti originali creati dai bimbi — registrati a voce al microfono, trascritti (sbobinati) con Gemini e trasformati in storie illustrate nella **Vetrina Web Interattiva su GitHub Pages**:

👉 **🌐 [Sfoglia tutte le storie su GitHub Pages (`https://palladius.github.io/kids-own-stories/`)](https://palladius.github.io/kids-own-stories/)**

---

## 🗂️ Struttura del Repository

```text
kids-own-stories/
├── index.html             # 🌐 Vetrina & Lettore Multi-Libro Acquerello (GitHub Pages)
├── books/                 # 📚 Libreria Acquerello 3D brossura (/books/, ?book=...)
├── docs/CONSTITUTION.md   # 📜 Costituzione linguistica e pedagogica (FR/IT/DE + en-GB)
├── GEMINI.md              # 🤖 Istruzioni operative per AI (workflow + schema YAML)
├── stories.yaml           # 📋 Catalogo deterministico delle storie mic-recorded (Layer 1)
├── kids_books_catalog.js  # 📖 Catalogo compilato dei libri illustrati ad acquerello (Layer 2)
├── stories/
│   ├── alessandro/        # 👦 Le storie di Alessandro (Primary 3)
│   └── sebastian/         # 🧒 Le storie di Sebastian / Seby (Primary 1)
├── audio/                 # 🎙️ Registrazioni vocali microfonate da sbobinare
├── CHANGELOG.md           # Registro delle modifiche e nuove storie aggiunte
├── VERSION                # Versione semantica del progetto
└── README.md              # Questo file
```

---

## 📚 Libri Illustrati ad Acquerello (`/books/` & Lettore Multi-Libro)

Accanto alle storie registrate al microfono (Layer 1), la piattaforma include una **Libreria Acquerello interattiva** ([`books/index.html`](books/index.html) → `/books/`) con copertine **3D brossura** e lettore a doppia pagina (`1792×1200`, con modalità monopagina su smartphone):

* 🏖️ **Vacanze in Sardegna** (`?book=sardegna`) — *scritto da Riccardo Carlesso* (Cala Gonone & Arbatax, **16 tavole / 8 aperture**).
* 👑 **Le Petit Prince** (`?book=petit-prince`) — *di Antoine de Saint-Exupéry* (**26 tavole / 13 aperture** con frontespizio Pag. 0 + 1 illustrazione per pagina e X-ray interattivo cappello→elefante a Pag. 2, **13 quiz Antolin** sulle pagine del libro, segnalibro automatico `ESC → /books/`, acquerelli originali del 1943 rimasterizzati su carta calda).

### 🌍 Costituzione Linguistica (`docs/CONSTITUTION.md`)
Ogni libro ad acquerello segue rigorosamente [`docs/CONSTITUTION.md`](docs/CONSTITUTION.md):
- **3 lingue di apprendimento attive (`FR`, `IT`, `DE`)**: testi completi su **3 livelli CEFR** (**Seby** 6a · A2, **Ale** 8a · B1, **Emma & Papino** 10–11a+ · B2/C1), audio studio `Aoede` (`.mp3` + `.ogg`), grammatica Montessori, verbi separabili tedeschi e quiz Antolin.
- **Inglese (`en-GB` British English) solo per traduzione e spiegazioni**: usato esclusivamente nella **Traduzione Pari Pari** (*Cheating Mode*), nei glossari (`en_gloss`) e nei titoli tradotti — **zero audio studio generato in inglese** (fallback solo browser `en-GB` RP).

### ⚖️ Trasparenza Copyright & Pubblico Dominio (*Le Petit Prince*)
L'adattamento educativo di **Le Petit Prince** utilizza le illustrazioni ad acquerello originali del 1943 e riscritture/estratti calibrati per età nel rispetto delle norme sul diritto d'autore:
- **Switzerland (`CH`) & European Union (`EU`)**: Antoine de Saint-Exupéry morì il **31 luglio 1944**; il testo originale e gli acquerelli sono entrati nel **pubblico dominio in Svizzera (`CH`) e nell'Unione Europea (`EU`) dal 1° gennaio 2015** (vita dell'autore + 70 anni).
- **France**: in **France**, in virtù della menzione *Mort pour la France* (Art. L123-10 CPI, proroga di +30 anni), l'opera resta protetta fino al **~2032–2035** (e negli Stati Uniti fino al **1° gennaio 2039**).
- Questo progetto è realizzato **esclusivamente come web app educativa privata/familiare in Svizzera (Switzerland)**, senza alcun fine commerciale.

---

## 🎙️ Workflow: Dal Microfono alla Vetrina

1. **Registrazione (`audio/`)**: I bimbi raccontano la loro storia al microfono (`.m4a`, `.mp3`, `.wav`, `.ogg`).
2. **Sbobinatura & Trascrizione (`stories/<bimbo>/`)**: Trascrizione fedele della voce con l'aiuto di Gemini STT, mantenendo lo stile, le invenzioni linguistiche e la fantasia originale dei bimbi.
3. **Illustrazione & Vetrina**: Generazione delle illustrazioni per i personaggi e pubblicazione nella vetrina sfogliabile con audio sincronizzato.

---

## 📖 Indice delle Storie

### 👦 Alessandro (Ale)
* 🏆🐴🌈 **[Sebi, il Campione del Pony Club alla Velocità della Luce e il Disco Party con Pupurabbu](stories/alessandro/storia-sebi-campione-pony-club-pupurabbu/)** *(8 Novembre 2026)* — Una storia dolcissima inventata e narrata da Ale per il fratellino Sebi: in sella al suo pony bianco, Sebi sfida i grandissimi cavalli al Pony Club, vola sugli ostacoli alla velocità della luce col tifo di Ale al microfono, vince la Coppa d'Oro e festeggia con una Disco Party sotto un arcobaleno (*Rainbow / Regenbogen*) abbracciato da un **Pupurabbu grandissimo**! ([🌐 Pagina GHP](https://palladius.github.io/kids-own-stories/stories/alessandro/storia-sebi-campione-pony-club-pupurabbu/))
* 🎒🐉🐧 **[La Storia dello Zaino Magico, del Drago e dei Puffins](stories/alessandro/storia-dello-zaino-del-drago-e-dei-puffins/)** *(6 Novembre 2026)* — Storia completa con registrazione audio originale, sbobinatura integrale, 4 illustrazioni 3D e video animato con Gemini Omni Flash! ([🌐 Pagina GHP](https://palladius.github.io/kids-own-stories/stories/alessandro/storia-dello-zaino-del-drago-e-dei-puffins/))
* 💀🧟☕ **[La Famiglia di Scheletri e gli Zombie Assetati di Tè](stories/alessandro/storia-scheletri-zombie-te/)** *(4 Novembre 2026)* — Alessandro ci racconta di zombies gentili che amano il tè servito da una famiglia di scheletri! ([🌐 Pagina GHP](https://palladius.github.io/kids-own-stories/stories/alessandro/storia-scheletri-zombie-te/))

### 🧒 Sebastian (Seby)
* 🐴🚛🌀 **[Sebastian, il Cavalletto Magico Marie e il Camion Camper dei Cavalli](stories/sebastian/storia-cavalletto-marie-mondo-cavalli/)** *(8 Novembre 2026)* — Un cavalletto magico di nome Marie apre un tunnel dimensionale per il Mondo dei Cavalli. Sebi trova un gigante camion camper, carica a bordo tutta la mandria per portarla nel mondo delle persone e non dimentica Marie prima di chiudere il portale! ([🌐 Pagina GHP](https://palladius.github.io/kids-own-stories/stories/sebastian/storia-cavalletto-marie-mondo-cavalli/))
* 🐰🏎️🌈 **[Seby, il Dolce Pupurabbu e la Pista Fatata delle Hot Wheels a Lido degli Estensi](stories/sebastian/storia-pupurabbu-hot-wheels-lido-degli-estensi/)** *(7 Novembre 2026)* — La prima storia di Seby (6 anni): sulla spiaggia di Lido degli Estensi, Seby e il suo inseparabile coniglietto viola di peluche **Pupurabbu** sfrecciano con le **Hot Wheels** dentro un portale fatato pieno di magia! ([🌐 Pagina GHP](https://palladius.github.io/kids-own-stories/stories/sebastian/storia-pupurabbu-hot-wheels-lido-degli-estensi/))

---

## 📄 Licenza
Creato con ❤️ da Papino (**Riccardo Carlesso**, `@palladius`), **Alessandro** e **Sebastian**.
