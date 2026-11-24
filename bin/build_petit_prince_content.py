#!/usr/bin/env python3
"""
Authoritative content specification, Montessori/separable-verb compiler, and
deterministic validator for *Le Petit Prince* (26 plates / 13 double spreads).

Generates:
  books/petit-prince/content_spec.json

Design rules (docs/CONSTITUTION.md & PROJECT.md):
  - Exactly 3 learning languages: fr, it, de (default_lang = fr).
  - English (en-GB British English ONLY) is strictly for parallel translation
    (Traduzione Pari Pari / Cheating Mode) and glossary explanations.
  - ZERO English studio TTS audio (no audio_mp3/audio_ogg on any `en` object).
  - 3 CEFR tiers: seby (A2), ale (B1), emma (B2/C1).
  - Curated FR/IT noun & adjective lexicons with explicit gender (m/f) and
    number (s/p); zero gender emitted for German tokens.
  - Clause-bounded German separable verb pairing (V2/V1 right-bracket only).
  - 13 Antolin comprehension quizzes on even pages (2, 4, ..., 26).
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "books" / "petit-prince"
CONTENT_SPEC_PATH = BOOK_DIR / "content_spec.json"

SUPPORTED_LANGS = ["fr", "it", "de"]
ALL_TEXT_LANGS = ["fr", "it", "de", "en"]
TIERS = ["seby", "ale", "emma"]

WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿŒœŸÿ0-9'’-]+")
STRIP_OUTER_RE = re.compile(r"^[^\wÀ-ÿŒœŸÿÄÖÜäöüß]+|[^\wÀ-ÿŒœŸÿÄÖÜäöüß]+$")
SLUG_RE = re.compile(r"[^\wÀ-ÿŒœŸÿÄÖÜäöüß]+")

BOOK_META = {
    "story_id": "le-petit-prince",
    "book_alias": "petit-prince",
    "title": {
        "fr": "Le Petit Prince",
        "it": "Il Piccolo Principe",
        "de": "Der kleine Prinz",
        "en": "The Little Prince",
    },
    "author_label": "Antoine de Saint-Exupéry (1943)",
    "supported_langs": ["fr", "it", "de"],
    "default_lang": "fr",
    "total_pages": 26,
    "buttons": {
        "seby": {
            "image": "assets/avatars/seby_tier.jpg",
            "label": {
                "fr": "🧒 Seby lis ici ! (6-7 ans · A2)",
                "it": "🧒 Seby leggi qui! (6-7 anni · A2)",
                "de": "🧒 Seby lies hier! (6-7 J. · A2)",
                "en": "🧒 Seby read here! (6-7 yo · A2)",
            },
        },
        "ale": {
            "image": "assets/avatars/ale_tier.jpg",
            "label": {
                "fr": "👦 Ale lis ici ! (8-9 ans · B1)",
                "it": "👦 Ale leggi qui! (8-9 anni · B1)",
                "de": "👦 Ale lies hier! (8-9 J. · B1)",
                "en": "👦 Ale read here! (8-9 yo · B1)",
            },
        },
        "emma": {
            "image": "assets/avatars/emma.png",
            "label": {
                "fr": "👧 Emma lis ici ! (10-11+ ans · B2/C1)",
                "it": "👧 Emma leggi qui! (10-11+ anni · B2/C1)",
                "de": "👧 Emma lies hier! (10-11+ J. · B2/C1)",
                "en": "👧 Emma read here! (10-11+ yo · B2/C1)",
            },
        },
    },
}

TAIL_LEFT_MAP = {
    "left": "22%",
    "center": "50%",
    "right": "74%",
}


def make_bubble_anchor(x: int, y: int, tail_spec: str, max_w: int) -> dict:
    v_dir, h_align = tail_spec.split("-")
    return {
        "x": x,
        "y": y,
        "tail": v_dir,
        "maxW": f"{max_w}%",
        "top": f"{y}%",
        "left": f"{x}%",
        "tailLeft": TAIL_LEFT_MAP[h_align],
    }


PAGES_DATA = [
    # =========================================================================
    # SPREAD 1: P01 (Frontispiece Page 0) + P02 (Ch. I Boa Swallowing Beast)
    # =========================================================================
    {
        "page": 1,
        "is_frontispiece": True,
        "art_refs": {
            "chapters": "Frontispiece",
            "primary_0300771h": [],
            "ia_1943_leaves": [],
            "scene_summary": "Clean blank warm parchment frontispiece (Page 0 verso).",
        },
        "bubble_anchor": None,
        "title": {
            "fr": "",
            "it": "",
            "de": "",
            "en": "",
        },
        "speech_bubble": None,
        "seby": {
            "fr": "",
            "it": "",
            "de": "",
            "en": "",
        },
        "ale": {
            "fr": "",
            "it": "",
            "de": "",
            "en": "",
        },
        "emma": {
            "fr": "",
            "it": "",
            "de": "",
            "en": "",
        },
        "questions": None,
    },
    {
        "page": 2,
        "art_refs": {
            "chapters": "Ch. I",
            "primary_0300771h": ["0300771h-05.jpg"],
            "ia_1943_leaves": ["n1"],
            "scene_summary": "Histoires Vecues: boa constrictor swallowing a wild beast whole.",
        },
        "bubble_anchor": make_bubble_anchor(10, 32, "bottom-left", 56),
        "title": {
            "fr": "1. Histoires Vécues : Le Serpent Boa",
            "it": "1. Storie Vissute: Il Serpente Boa",
            "de": "1. Erlebte Geschichten: Die Boa",
            "en": "1. True Stories: The Boa Constrictor",
        },
        "speech_bubble": {
            "speaker": "Le Narrateur (L'Aviateur)",
            "fr": "Les serpents boas avalent leur proie tout entière!",
            "it": "I serpenti boa ingoiano la preda tutta intera!",
            "de": "Riesenschlangen verschlingen ihre Beute ganz im Stück!",
            "en": "Boa constrictors swallow their prey completely whole!",
        },
        "seby": {
            "fr": "Un garçon voit une belle image dans un livre: un serpent boa avale un gros animal.",
            "it": "Un bambino guarda una bella figura in un libro: un serpente boa ingoia un grande animale.",
            "de": "Ein Junge sieht ein tolles Bild in einem Buch: Eine riesige Schlange frisst ein wildes Tier.",
            "en": "A young boy sees a lovely picture in a book: a boa swallows a wild animal.",
        },
        "ale": {
            "fr": "Dans un livre sur la forêt vierge appelé «Histoires Vécues», un garçon admire un boa qui avale un fauve. Il apprend que ces serpents dorment six mois après le repas.",
            "it": "In un libro sulla foresta vergine chiamato «Storie Vissute», il bambino ammira un boa che ingoia una belva. Scopre così che i serpenti dormono sei mesi dopo il pasto.",
            "de": "In einem Buch über den Urwald, das «Erlebte Geschichten» heißt, schaut ein Junge eine Schlange beim Fressen an. Er erfährt, dass Boas danach sechs Monate lang schlafen.",
            "en": "In a book about the primeval forest called \"True Stories\", a boy admires a boa swallowing a wild beast. He learns that boas sleep for six whole months afterwards.",
        },
        "emma": {
            "fr": "Lorsque j'avais six ans, je vis une magnifique image dans un livre sur la forêt vierge intitulé «Histoires Vécues». Elle représentait un serpent boa qui avalait un fauve. On y lisait: «Les boas avalent leur proie tout entière, sans la mâcher, puis dorment six mois pour digérer.»",
            "it": "Quando avevo sei anni vidi una magnifica illustrazione in un libro sulla foresta vergine intitolato «Storie Vissute». Essa rappresentava un serpente boa che inghiottiva una belva. Nel libro si leggeva: «I serpenti boa ingoiano la preda intera, senza masticarla, poi dormono sei mesi per digerire.»",
            "de": "Als ich sechs Jahre alt war, sah ich in einem Buch über den Urwald namens «Erlebte Geschichten» ein wunderbares Bild. Es stellte eine Riesenschlange beim Verschlingen eines wilden Tieres dar. Darin stand: «Riesenschlangen schlucken ihre Beute ganz, ohne zu kauen, und schlafen sechs Monate, um zu verdauen.»",
            "en": "When I was six years old, I saw a magnificent picture in a book about the primeval forest called \"True Stories\". It showed a boa constrictor swallowing a wild beast. The book said: \"Boas swallow their prey whole, without chewing it, and then sleep six months to digest.\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p02_q1", "difficulty": "easy", "q": "Comment s'appelle le livre sur la forêt vierge ?", "options": ["Histoires Vécues", "Les Contes de la Lune", "Le Grand Désert Blanc"], "correct": 0},
                {"id": "pp_p02_q2", "difficulty": "easy", "q": "Que fait le serpent boa sur l'image du livre ?", "options": ["Il dort sous un arbre", "Il avale un fauve", "Il nage dans la mer"], "correct": 1},
                {"id": "pp_p02_q3", "difficulty": "hard", "q": "Pourquoi les boas dorment-ils six mois après avoir mangé ?", "options": ["Pour se cacher des oiseaux", "Pour jouer dans le sable", "Pour digérer leur proie"], "correct": 2},
            ],
            "it": [
                {"id": "pp_p02_q1", "difficulty": "easy", "q": "Come si chiama il libro sulla foresta vergine?", "options": ["Racconti di Luna", "Storie Vissute", "Il Grande Deserto"], "correct": 1},
                {"id": "pp_p02_q2", "difficulty": "easy", "q": "Che cosa fa il serpente boa nell'illustrazione del libro?", "options": ["Dorme sotto un albero", "Nuota nel mare blu", "Ingoia una belva"], "correct": 2},
                {"id": "pp_p02_q3", "difficulty": "hard", "q": "Perché i serpenti boa dormono per sei mesi dopo il pasto?", "options": ["Per digerire la preda", "Per nascondersi dal sole", "Per aspettare la pioggia"], "correct": 0},
            ],
            "de": [
                {"id": "pp_p02_q1", "difficulty": "easy", "q": "Wie heißt das Buch über den Urwald?", "options": ["Geschichten vom Mond", "Die große Wüstenreise", "Erlebte Geschichten"], "correct": 2},
                {"id": "pp_p02_q2", "difficulty": "easy", "q": "Was macht die Riesenschlange auf dem Bild im Buch?", "options": ["Sie frisst ein wildes Tier", "Sie schläft unter einem Baum", "Sie schwimmt im blauen Meer"], "correct": 0},
                {"id": "pp_p02_q3", "difficulty": "hard", "q": "Warum schlafen Riesenschlangen nach dem Fressen sechs Monate lang?", "options": ["Um vor wilden Vögeln zu fliehen", "Um ihre Beute zu verdauen", "Um auf den Winter zu warten"], "correct": 1},
            ],
        },
    },
    # =========================================================================
    # SPREAD 1: P01 (Ch. I) + P02 (Ch. II)
    # =========================================================================
    {
        "page": 3,
        "hover_reveal_image": "books/petit-prince/wc_p03_xray.jpg",
        "art_refs": {
            "chapters": "Ch. I",
            "primary_0300771h": ["0300771h-05.jpg", "0300771h-06.jpg", "0300771h-07.jpg"],
            "ia_1943_leaves": ["n1", "n2"],
            "scene_summary": "Boa constrictor digesting an elephant and the 'hat' drawing.",
        },
        "bubble_anchor": make_bubble_anchor(10, 12, "bottom-right", 54),
        "title": {
            "fr": "2. Le Serpent Boa et le Chapeau",
            "it": "2. Il Serpente Boa e il Cappello",
            "de": "2. Die Boa und der Hut",
            "en": "2. The Boa Constrictor and the Hat",
        },
        "speech_bubble": {
            "speaker": "Le Narrateur (L'Aviateur)",
            "fr": "Mon dessin montrait un serpent boa, pas du tout un chapeau!",
            "it": "Il mio disegno mostrava un serpente boa, non era un cappello!",
            "de": "Meine Zeichnung stellte eine Riesenschlange dar, keinen Hut!",
            "en": "My drawing showed a boa constrictor, not a hat at all!",
        },
        "seby": {
            "fr": "Un enfant dessine un grand serpent boa qui mange un éléphant. Les adultes voient seulement un chapeau.",
            "it": "Un bambino disegna un grande serpente boa che mangia un elefante. I grandi vedono solo un cappello.",
            "de": "Ein Junge zeichnet eine riesige Schlange, die einen Elefanten frisst. Die Erwachsenen sehen nur einen Hut.",
            "en": "A little boy draws a giant boa swallowing an elephant. Grown-ups only see a hat.",
        },
        "ale": {
            "fr": "À six ans, le narrateur dessine un serpent boa en train de digérer un énorme éléphant. Mais les grandes personnes ne comprennent pas et répondent toujours qu'un chapeau ne fait pas peur.",
            "it": "A sei anni, il narratore disegna un serpente boa che digerisce un enorme elefante. Ma i grandi non capiscono e rispondono sempre che un cappello non fa affatto paura.",
            "de": "Mit sechs Jahren zeichnet der Erzähler eine Riesenschlange, die einen riesigen Elefanten verdaut. Doch die Erwachsenen verstehen das nicht und sagen immer, dass ein Hut gar keine Angst macht.",
            "en": "At six years old, the narrator draws a boa constrictor digesting a huge elephant. Yet grown-ups do not understand and always reply that a hat is not frightening at all.",
        },
        "emma": {
            "fr": "Lorsque j'avais six ans j'ai vu, une fois, une magnifique image: un serpent boa qui avalait un fauve. Mon dessin ne représentait pas un chapeau. Il représentait un serpent boa qui digérait un éléphant. Les grandes personnes ne comprennent jamais rien toutes seules, et c'est fatigant, pour les enfants, de toujours leur donner des explications.",
            "it": "Quando avevo sei anni vidi, una volta, una magnifica illustrazione: un serpente boa che inghiottiva una belva. Il mio disegno non rappresentava un cappello. Rappresentava un serpente boa che digeriva un elefante. I grandi non capiscono mai nulla da soli, ed è faticoso, per i bambini, dare sempre loro delle spiegazioni.",
            "de": "Als ich sechs Jahre alt war, sah ich einmal ein wunderbares Bild: eine Riesenschlange verschlang ein wildes Tier. Meine Zeichnung stellte keinen Hut dar, sondern eine Boa, die einen Elefanten verdaute. Erwachsene verstehen von selbst gar nichts, und für Kinder ist es sehr anstrengend, ihnen immer alles zu erklären.",
            "en": "When I was six years old I once saw a magnificent picture: a boa constrictor swallowing a wild beast. My drawing did not represent a hat. It showed a boa constrictor digesting an elephant. Grown-ups never understand anything by themselves, and it is tiresome for children to give them constant explanations.",
        },
        "questions": None,
    },
    {
        "page": 4,
        "art_refs": {
            "chapters": "Ch. II",
            "primary_0300771h": ["0300771h-08.jpg", "0300771h-09.jpg", "0300771h-01.gif", "0300771h-10.jpg", "0300771h-11.jpg"],
            "ia_1943_leaves": ["n3", "n5"],
            "scene_summary": "Sahara crash, Little Prince portrait, and the sheep inside the box.",
        },
        "bubble_anchor": make_bubble_anchor(8, 36, "bottom-right", 54),
        "title": {
            "fr": "3. Le Mouton dans la Caisse",
            "it": "3. La Pecora nella Cassa",
            "de": "3. Das Schaf in der Kiste",
            "en": "3. The Sheep in the Box",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "S'il vous plaît... dessine-moi un mouton!",
            "it": "Per favore... disegnami una pecora!",
            "de": "Bitte... zeichne mir ein Schaf!",
            "en": "If you please... draw me a sheep!",
        },
        "seby": {
            "fr": "Un avion atterrit dans le désert. Un petit prince demande un mouton dans une caisse.",
            "it": "Un aereo atterra nel deserto. Un piccolo principe chiede una pecora dentro una cassa.",
            "de": "Ein Flugzeug landet in der Wüste. Ein kleiner Prinz wünscht sich ein Schaf in einer Kiste.",
            "en": "An aeroplane lands in the desert. A little prince asks for a sheep inside a box.",
        },
        "ale": {
            "fr": "Après une panne d'avion dans le Sahara, une petite voix réveille le pilote à l'aube. Le garçon refuse trois dessins et sourit devant une simple caisse qui cache son mouton.",
            "it": "Dopo un guasto all'aereo nel deserto del Sahara, una vocina sveglia il pilota all'alba. Il bambino scarta tre disegni e sorride davanti a una semplice cassa che nasconde la pecora.",
            "de": "Nach einer Flugzeugpanne in der Sahara wacht der Pilot früh auf. Der kleine Prinz lehnt drei Zeichnungen ab, doch die Kiste mit dem Schaf darin schaut er glücklich an.",
            "en": "After an engine breakdown in the Sahara desert, a little voice wakes the pilot at dawn. The boy refuses three drawings, yet smiles at a simple box holding his sheep.",
        },
        "emma": {
            "fr": "Dans le désert, une drôle de petite voix m'a réveillé: «S'il vous plaît... dessine-moi un mouton!» Alors je lançai: «Ça c'est la caisse. Le mouton que tu veux est dedans.» Mais je fus bien surpris: «C'est tout à fait comme ça que je le voulais!» «Tiens! Il s'est endormi...»",
            "it": "Nel deserto una buffa vocina mi svegliò all'alba: «Per favore... disegnami una pecora!» Allora dissi deciso: «Questa è la cassa. La pecora che vuoi è lì dentro.» Ma fui molto sorpreso di sentirlo dire: «È proprio così che la volevo!» «Guarda! Si è addormentata...»",
            "de": "In der Wüste weckte mich eine seltsame kleine Stimme: «Bitte... zeichne mir ein Schaf!» Da rief ich: «Das hier ist die Kiste. Das Schaf, das du willst, ist darin.» Doch ich staunte sehr, als er sagte: «Genau so wollte ich es!» «Sieh, es schläft ein...»",
            "en": "In the desert, a funny little voice woke me at dawn: \"If you please... draw me a sheep!\" So I replied: \"This is the box. The sheep you want is inside.\" I was quite amazed to hear him say: \"That is exactly how I wanted it!\" \"Look! He has fallen asleep...\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p04_q1", "difficulty": "easy", "q": "Que croient voir les grandes personnes sur le premier dessin de l'enfant ?", "options": ["Un simple chapeau posé sur la table", "Un éléphant caché dans un boa", "Une caisse fermée pour un mouton"], "correct": 0},
                {"id": "pp_p04_q2", "difficulty": "easy", "q": "Où le pilote rencontre-t-il le petit prince à son réveil ?", "options": ["Sur une montagne", "Dans le désert", "Dans un jardin"], "correct": 1},
                {"id": "pp_p04_q3", "difficulty": "hard", "q": "Pourquoi le petit prince est-il si content du dessin de la caisse ?", "options": ["Parce qu'il aime collectionner de jolies boîtes en carton", "Parce que le pilote veut seulement dessiner un beau chapeau", "Parce que le mouton qu'il veut se trouve juste dedans"], "correct": 2},
            ],
            "it": [
                {"id": "pp_p04_q1", "difficulty": "easy", "q": "Che cosa credono di vedere i grandi nel primo disegno del bambino?", "options": ["Un semplice cappello", "Un elefante nel boa", "Una cassa di legno"], "correct": 0},
                {"id": "pp_p04_q2", "difficulty": "easy", "q": "Dove incontra il pilota il piccolo principe al risveglio?", "options": ["Su una montagna", "Nel deserto", "In un giardino"], "correct": 1},
                {"id": "pp_p04_q3", "difficulty": "hard", "q": "Perché il piccolo principe è così contento del disegno della cassa?", "options": ["Perché colleziona tantissime scatole di cartone colorate e vuote", "Perché il pilota vuole disegnare soltanto un cappello", "Perché la pecora che desidera si trova proprio lì dentro"], "correct": 2},
            ],
            "de": [
                {"id": "pp_p04_q1", "difficulty": "easy", "q": "Was sehen die Erwachsenen auf der ersten Zeichnung des Jungen?", "options": ["Nur einen Hut", "Einen großen Elefanten", "Eine hölzerne Kiste"], "correct": 0},
                {"id": "pp_p04_q2", "difficulty": "easy", "q": "Wo begegnet der Pilot dem kleinen Prinzen am frühen Morgen?", "options": ["Auf einem Berg", "In der Wüste", "In einem Garten"], "correct": 1},
                {"id": "pp_p04_q3", "difficulty": "hard", "q": "Warum freut sich der kleine Prinz so sehr über das Bild der Kiste?", "options": ["Weil er am liebsten bunte Schachteln ohne Inhalt sammelt", "Weil der Pilot ihm gar keinen Hut mehr malen wollte", "Weil das gewünschte Schaf genau in dieser Kiste steckt"], "correct": 2},
            ],
        },
    },
    # =========================================================================
    # SPREAD 2: P03 (Ch. III-IV) + P04 (Ch. V)
    # =========================================================================
    {
        "page": 5,
        "art_refs": {
            "chapters": "Ch. III-IV",
            "primary_0300771h": ["0300771h-12.jpg", "0300771h-13.jpg", "0300771h-14.jpg", "0300771h-15.jpg", "0300771h-16.jpg"],
            "ia_1943_leaves": ["n6", "n8"],
            "scene_summary": "Prince among stars, Asteroid B 612, and the Turkish astronomer.",
        },
        "bubble_anchor": make_bubble_anchor(10, 11, "bottom-right", 54),
        "title": {
            "fr": "4. L'Astéroïde B 612",
            "it": "4. L'Asteroide B 612",
            "de": "4. Der Asteroid B 612",
            "en": "4. Asteroid B 612",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Droit devant soi on ne peut pas aller bien loin...",
            "it": "Sempre dritto davanti a sé non si può andare molto lontano...",
            "de": "Immer geradeaus kann man nicht sehr weit gehen...",
            "en": "Straight ahead, nobody can go very far...",
        },
        "seby": {
            "fr": "Le petit prince vient d'une minuscule planète appelée B 612. Elle est grande comme une maison!",
            "it": "Il piccolo principe viene da un pianeta piccolissimo chiamato B 612. È grande come una casa!",
            "de": "Wo kommt der kleine Prinz her? Er wohnt auf einem winzigen Planeten namens B 612.",
            "en": "The little prince comes from a tiny planet called B 612. It is barely larger than a house!",
        },
        "ale": {
            "fr": "Le garçon habite l'astéroïde B 612, découvert une seule fois en 1909 par un astronome turc. Le savant doit changer de costume pour que les adultes croient enfin à ses chiffres.",
            "it": "Il bambino viene dall'asteroide B 612, visto una sola volta al telescopio nel 1909 da un astronomo turco. I grandi credono alle sue cifre soltanto quando cambia abito.",
            "de": "Der kleine Prinz stammt vom Asteroiden B 612, den ein türkischer Astronom 1909 entdeckte. Weil Erwachsene Zahlen lieben, glauben sie ihm erst, als er seine Kleidung wechselt.",
            "en": "The boy comes from asteroid B 612, spotted only once in 1909 by a Turkish astronomer. Because grown-ups love numbers, they only believe him when he changes his clothes.",
        },
        "emma": {
            "fr": "J'ai de sérieuses raisons de croire que la planète d'où venait le petit prince est l'astéroïde B 612. Cet astéroïde n'a été aperçu qu'une fois au télescope, en 1909, par un astronome turc. Les grandes personnes aiment les chiffres. Elles ne demandent jamais: «Quel est le son de sa voix?» «Est-ce qu'il collectionne les papillons?»",
            "it": "Ho serie ragioni di credere che il pianeta da cui veniva il piccolo principe sia l'asteroide B 612. Questo asteroide è stato visto una sola volta al telescopio, nel 1909, da un astronomo turco. I grandi amano le cifre. Non chiedono mai: «Qual è il suono della sua voce?» «Fa collezione di farfalle?»",
            "de": "Ich habe gute Gründe zu glauben, dass der kleine Prinz vom Asteroiden B 612 kam. Dieser Stern wurde nur ein einziges Mal im Jahr 1909 von einem türkischen Astronomen im Fernrohr gesehen. Erwachsene lieben Zahlen. Sie fragen niemals: «Wie klingt seine Stimme?» «Sammelt er wohl auch bunte Schmetterlinge?»",
            "en": "I have serious reason to believe that the planet from which the little prince came is asteroid B 612. This asteroid has only once been seen through a telescope, in 1909, by a Turkish astronomer. Grown-ups love figures. They never ask you: \"What does his voice sound like?\" \"Does he collect butterflies?\"",
        },
        "questions": None,
    },
    {
        "page": 6,
        "art_refs": {
            "chapters": "Ch. V",
            "primary_0300771h": ["0300771h-46.jpg", "0300771h-18.jpg", "0300771h-17.jpg", "0300771h-00.jpg"],
            "ia_1943_leaves": ["n13"],
            "scene_summary": "Giant baobabs bursting a lazy planet and good vs bad seeds.",
        },
        "bubble_anchor": make_bubble_anchor(8, 35, "bottom-left", 52),
        "title": {
            "fr": "5. Le Danger des Baobabs",
            "it": "5. Il Pericolo dei Baobab",
            "de": "5. Die Gefahr der Affenbrotbäume",
            "en": "5. The Danger of Baobabs",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Enfants! Faites très attention aux grands baobabs!",
            "it": "Bambini! Fate molta attenzione ai terribili baobab!",
            "de": "Kinder! Passt gut auf die großen Affenbrotbäume auf!",
            "en": "Children! Watch out for the giant baobabs!",
        },
        "seby": {
            "fr": "Chaque matin, le petit prince arrache les jeunes baobabs. Sinon leurs racines cassent sa planète.",
            "it": "Ogni mattina il piccolo principe strappa i piccoli baobab. Altrimenti le radici rompono il pianeta.",
            "de": "Jeden Morgen reißt der kleine Prinz die jungen Baobabsämlinge aus. Sonst sprengen sie den Stern.",
            "en": "Every morning, the little prince pulls up tiny baobab shoots before they break his small planet.",
        },
        "ale": {
            "fr": "Sur B 612 poussent de bonnes graines de roses et de terribles graines de baobabs. Si on les arrache trop tard, leurs racines énormes font éclater toute la planète.",
            "it": "Sul piccolo pianeta crescono semi buoni e semi terribili di baobab. Bisogna estirpare i germogli ogni mattina appena riconosciuti, prima che le radici giganti spezzino la terra.",
            "de": "Auf seinem Stern wachsen gute Rosensamen und gefährliche Baobabsamen. Jeden Morgen räumt der Junge gründlich auf und reißt jede böse Pflanze aus, sonst sprengt sie den ganzen Planeten.",
            "en": "Good rose seeds and terrible baobab seeds grow on B 612. Every morning, the prince must pull up each young baobab shoot before its roots shatter his tiny world.",
        },
        "emma": {
            "fr": "Il y avait des graines terribles sur sa planète: des graines de baobabs. «C'est une question de discipline», me disait plus tard le petit prince. «Quand on a terminé sa toilette du matin, il faut faire soigneusement la toilette de la planète.» Si la planète est trop petite, les baobabs la font éclater.",
            "it": "C'erano semi terribili sul pianeta del piccolo principe... i semi di baobab. «È una questione di disciplina», mi diceva più tardi il piccolo principe. «Finita la pulizia del mattino, bisogna fare con cura la pulizia del pianeta.» Se i baobab diventano troppo grandi, lo fanno esplodere.",
            "de": "Es gab schreckliche Samen auf dem Planeten: die Samen der Affenbrotbäume. «Das ist eine Frage der Disziplin», sagte mir später der kleine Prinz. «Nach der Morgentoilette muss man sorgsam den Planeten reinigen.» Wenn der Planet zu klein ist, sprengen die Affenbrotbäume den ganzen Stern.",
            "en": "There were terrible seeds on the little prince's planet: the seeds of the baobab. \"It is a question of discipline,\" the little prince told me later. \"After your morning toilet, you must carefully clean the planet.\" If the planet is too small, the baobabs burst it apart.",
        },
        "questions": {
            "fr": [
                {"id": "pp_p06_q1", "difficulty": "easy", "q": "Quel est le numéro de l'astéroïde d'où vient le petit prince ?", "options": ["L'astéroïde A 100", "L'astéroïde B 612", "L'astéroïde C 44"], "correct": 1},
                {"id": "pp_p06_q2", "difficulty": "easy", "q": "Que fait le petit prince chaque matin pour protéger sa planète ?", "options": ["Il compte toutes les étoiles du ciel", "Il arrose les grands éléphants gris", "Il arrache les jeunes baobabs"], "correct": 2},
                {"id": "pp_p06_q3", "difficulty": "hard", "q": "Que risque-t-il d'arriver si l'on n'arrache pas les jeunes baobabs à temps ?", "options": ["Ils grandissent et font éclater la petite planète", "Ils se transforment vite en belles fleurs rouges parfumées", "Ils attirent des troupeaux d'oiseaux sauvages"], "correct": 0},
            ],
            "it": [
                {"id": "pp_p06_q1", "difficulty": "easy", "q": "Come si chiama l'asteroide da cui proviene il piccolo principe?", "options": ["Asteroide A 100", "Asteroide B 612", "Asteroide C 44"], "correct": 1},
                {"id": "pp_p06_q2", "difficulty": "easy", "q": "Che cosa fa il piccolo principe ogni mattina per proteggere il suo pianeta?", "options": ["Conta tutte le stelle del cielo", "Bagna i grandi elefanti grigi", "Strappa i giovani baobab"], "correct": 2},
                {"id": "pp_p06_q3", "difficulty": "hard", "q": "Che cosa può succedere se non si strappano in tempo i giovani baobab?", "options": ["Crescono troppo e spezzano il piccolo pianeta", "Si trasformano subito in belle rose rosse profumate", "Chiamano uno stormo di uccelli selvatici"], "correct": 0},
            ],
            "de": [
                {"id": "pp_p06_q1", "difficulty": "easy", "q": "Wie heißt der winzige Asteroid des kleinen Prinzen?", "options": ["Asteroid A 100", "Asteroid B 612", "Asteroid C 44"], "correct": 1},
                {"id": "pp_p06_q2", "difficulty": "easy", "q": "Was tut der kleine Prinz jeden Morgen zum Schutz seines Planeten?", "options": ["Er zählt alle weißen Vögel", "Er malt drei graue Elefanten", "Er reißt junge Baobabs aus"], "correct": 2},
                {"id": "pp_p06_q3", "difficulty": "hard", "q": "Was passiert, wenn die jungen Baobabs auf dem Stern nicht rechtzeitig ausgerissen werden?", "options": ["Sie wachsen riesig und sprengen den kleinen Planeten", "Sie verwandeln sich über Nacht in duftende rote Rosenblüten", "Sie locken eine große Schar wilder Vögel heran"], "correct": 0},
            ],
        },
    },
    # =========================================================================
    # SPREAD 3: P05 (Ch. VI) + P06 (Ch. VII-VIII)
    # =========================================================================
    {
        "page": 7,
        "art_refs": {
            "chapters": "Ch. VI",
            "primary_0300771h": ["0300771h-00.jpg", "0300771h-17.jpg"],
            "ia_1943_leaves": ["n14"],
            "scene_summary": "Tiny Asteroid B 612 and watching 44 sunsets by moving the chair.",
        },
        "bubble_anchor": make_bubble_anchor(28, 12, "bottom-left", 56),
        "title": {
            "fr": "6. Quarante-Quatre Couchers de Soleil",
            "it": "6. Quarantaquattro Tramonti",
            "de": "6. Vierundvierzig Sonnenuntergänge",
            "en": "6. Forty-Four Sunsets",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Un jour, j'ai vu le soleil se coucher quarante-quatre fois!",
            "it": "Un giorno ho visto il sole tramontare quarantaquattro volte!",
            "de": "Eines Tages sah ich die Sonne vierundvierzigmal untergehen!",
            "en": "One day, I saw the sun set forty-four times!",
        },
        "seby": {
            "fr": "Quand il est triste, le prince déplace sa chaise et voit quarante-quatre couchers de soleil.",
            "it": "Quando si sente triste, il piccolo principe sposta la sedia e guarda quarantaquattro tramonti.",
            "de": "Wenn er traurig ist, rückt der Prinz den Stuhl weiter und zählt vierundvierzig Sonnenuntergänge.",
            "en": "When he feels sad, the little prince moves his chair to watch forty-four sunsets.",
        },
        "ale": {
            "fr": "La planète est si minuscule qu'il suffit de tirer sa chaise de quelques pas pour revoir le crépuscule. Un jour très triste, le petit prince admira quarante-quatre couchers de soleil.",
            "it": "Il pianeta è così minuscolo che basta spostare la sedia di pochi passi per rivedere il tramonto. In un giorno di grande malinconia, il bambino guardò il sole calare quarantaquattro volte.",
            "de": "Sein Planet ist so winzig, dass ein paar Schritte mit dem Stuhl genügen. An einem traurigen Tag geht die Sonne vor seinen Augen vierundvierzigmal in goldenem Licht unter.",
            "en": "His planet is so tiny that moving his chair a few paces brings another sunset. On a day of deep sadness, the little prince watched the sun go down forty-four times.",
        },
        "emma": {
            "fr": "Sur ta si petite planète, il te suffisait de tirer ta chaise de quelques pas. Et tu regardais le crépuscule chaque fois que tu le désirais... «Un jour, j'ai vu le soleil se coucher quarante-quatre fois!» «Tu sais... quand on est tellement triste on aime les couchers de soleil...»",
            "it": "Sul tuo così piccolo pianeta ti bastava tirare la sedia di qualche piccolo passo. E guardavi il crepuscolo ogni volta che lo desideravi... «Un giorno ho visto il sole tramontare quarantaquattro volte!» «Sai... quando si è tanto tristi si amano i tramonti...»",
            "de": "Auf deinem so winzigen Stern genügte es, deinen Stuhl ein paar Schritte weiterzurücken. Und du schautest dir die Abenddämmerung an, wann immer du wolltest... «Eines Tages ging die Sonne vierundvierzigmal unter!» «Weißt du... wenn man so traurig ist, liebt man Sonnenuntergänge.»",
            "en": "On your tiny little planet, you merely had to pull your chair a few steps further. And you watched the twilight whenever you truly wished... \"One day, I saw the sun set forty-four times!\" \"You know... one loves the sunset, when one is really so sad...\"",
        },
        "questions": None,
    },
    {
        "page": 8,
        "art_refs": {
            "chapters": "Ch. VII-VIII",
            "primary_0300771h": ["0300771h-19.jpg", "0300771h-20.jpg", "0300771h-21.jpg", "0300771h-02.gif", "0300771h-23.jpg"],
            "ia_1943_leaves": ["n18", "n19", "n20"],
            "scene_summary": "The proud Rose, watering can, screen, and glass dome.",
        },
        "bubble_anchor": make_bubble_anchor(8, 36, "bottom-center", 56),
        "title": {
            "fr": "7. La Rose sous Globe",
            "it": "7. La Rosa sotto la Campana",
            "de": "7. Die Rose unter der Glasglocke",
            "en": "7. The Rose Under Glass",
        },
        "speech_bubble": {
            "speaker": "La Rose",
            "fr": "Le soir vous me mettrez sous globe. Il fait froid ici.",
            "it": "La sera mi metterete sotto la campana. Qui fa freddo.",
            "de": "Abends stellt ihr mich unter die Glasglocke. Hier ist es kalt.",
            "en": "At night you must put me under a glass globe. It is cold.",
        },
        "seby": {
            "fr": "Une belle rose pousse sur la planète. Le prince l'arrose et la protège sous un globe en verre.",
            "it": "Una bella rosa sboccia sul pianeta. Il principe la bagna e la copre con una campana.",
            "de": "Eine schöne Rose blüht auf dem Stern. Der Prinz gießt sie und schützt sie unter einer Glasglocke.",
            "en": "A lovely rose blooms on the planet. The little prince waters her and covers her under glass.",
        },
        "ale": {
            "fr": "Une fleur vaniteuse mais fragile s'épanouit au soleil du matin. Le petit prince la protège du vent avec un paravent et un globe en verre, mais il est trop jeune pour la comprendre.",
            "it": "Un fiore vanitoso ma fragile si apre al sole del mattino. Il piccolo principe lo protegge dal vento con un paravento e una campana di vetro, ma è troppo giovane per capirlo.",
            "de": "Eine stolze, zarte Rose öffnet ihre Blütenblätter im Morgenlicht. Der Prinz schützt sie vor dem Wind mit einem Wandschirm und einer Glasglocke, doch er ist zu jung, um sie zu verstehen.",
            "en": "A vain yet fragile rose opens her petals in the morning sun. The little prince shelters her from the wind with a folding screen and a glass dome, though he is too young to understand her.",
        },
        "emma": {
            "fr": "Elle choisissait avec soin ses couleurs. Elle s'habillait lentement, elle ajustait un à un ses pétales. «Le soir vous me mettrez sous globe.» J'aurais dû la juger sur les actes et non sur les mots. Elle m'embaumait et m'éclairait. Mais j'étais trop jeune pour savoir l'aimer.",
            "it": "Sceglieva con cura i suoi colori. Si vestiva lentamente, sistemava ad uno ad uno i suoi petali. «La sera mi metterete sotto la campana.» Avrei dovuto giudicarla dai gesti e non dalle parole. Mi profumava e m'illuminava. Ma ero troppo giovane per saperla amare.",
            "de": "Sorgfältig wählte sie ihre Farben aus. Langsam kleidete sie sich an und ordnete Blatt für Blatt. «Abends stellt ihr mich unter eine Glasglocke.» Ich hätte nach ihren Taten urteilen sollen, nicht nach ihren Worten. Sie schenkte mir Duft und Licht, doch ich war zu jung.",
            "en": "She chose her colours with the greatest care. She dressed slowly, adjusting her petals one by one. \"At night you will put me under a glass globe.\" I ought to have judged her by deeds and not by words. She cast her fragrance over me, yet I was too young to love her.",
        },
        "questions": {
            "fr": [
                {"id": "pp_p08_q1", "difficulty": "easy", "q": "Combien de fois le petit prince a-t-il vu le soleil se coucher un jour ?", "options": ["Douze fois seulement", "Cent cinquante fois", "Quarante-quatre fois"], "correct": 2},
                {"id": "pp_p08_q2", "difficulty": "easy", "q": "Que demande la rose pour se protéger du froid la nuit ?", "options": ["Un globe en verre", "Un manteau rouge", "Une maison grise"], "correct": 0},
                {"id": "pp_p08_q3", "difficulty": "hard", "q": "À quel moment aime-t-on tellement regarder les couchers de soleil, selon le petit prince ?", "options": ["Quand on veut compter les étoiles brillantes", "Quand on se sent profondément triste", "Quand on arrose sa fleur le matin"], "correct": 1},
            ],
            "it": [
                {"id": "pp_p08_q1", "difficulty": "easy", "q": "Quante volte il piccolo principe vide tramontare il sole in un solo giorno?", "options": ["Dodici volte soltanto", "Centocinquanta volte", "Quarantaquattro volte"], "correct": 2},
                {"id": "pp_p08_q2", "difficulty": "easy", "q": "Che cosa chiede la rosa per proteggersi dal freddo della notte?", "options": ["Una campana di vetro", "Un mantello rosso", "Una casa di pietra"], "correct": 0},
                {"id": "pp_p08_q3", "difficulty": "hard", "q": "In quale momento si amano tanto i tramonti, secondo il piccolo principe?", "options": ["Quando si vogliono contare le stelle", "Quando ci si sente tanto tristi", "Quando si bagna il fiore la mattina"], "correct": 1},
            ],
            "de": [
                {"id": "pp_p08_q1", "difficulty": "easy", "q": "Wie oft sah der kleine Prinz an einem traurigen Tag die Sonne untergehen?", "options": ["Nur zwölfmal", "Einhundertmal", "Vierundvierzigmal"], "correct": 2},
                {"id": "pp_p08_q2", "difficulty": "easy", "q": "Womit schützt der kleine Prinz die Rose vor der Nachtkälte?", "options": ["Mit einer Glasglocke", "Mit einem roten Mantel", "Mit einem Holzhaus"], "correct": 0},
                {"id": "pp_p08_q3", "difficulty": "hard", "q": "Wann schaut man besonders gern den Sonnenuntergang an, sagt der kleine Prinz?", "options": ["Wenn man früh am Morgen die Blumen gießt", "Wenn man im Herzen sehr traurig ist", "Wenn man viele weiße Vögel zählt"], "correct": 1},
            ],
        },
    },
    # =========================================================================
    # SPREAD 4: P07 (Ch. IX) + P08 (Ch. X)
    # =========================================================================
    {
        "page": 9,
        "art_refs": {
            "chapters": "Ch. IX",
            "primary_0300771h": ["0300771h-24.jpg", "0300771h-25.jpg"],
            "ia_1943_leaves": ["n21"],
            "scene_summary": "Sweeping the volcanoes and flying away with a flock of wild birds.",
        },
        "bubble_anchor": make_bubble_anchor(10, 11, "bottom-right", 52),
        "title": {
            "fr": "8. Le Départ avec les Oiseaux",
            "it": "8. Il Viaggio con gli Uccelli",
            "de": "8. Der Flug mit den Wildvögeln",
            "en": "8. Departure With Wild Birds",
        },
        "speech_bubble": {
            "speaker": "La Rose",
            "fr": "Supporte deux ou trois chenilles pour voir les papillons!",
            "it": "Sopporta due o tre bruchi per conoscere le farfalle!",
            "de": "Ertrage zwei Raupen, um die Schmetterlinge zu sehen!",
            "en": "Endure two or three caterpillars to see the butterflies!",
        },
        "seby": {
            "fr": "Le prince nettoie ses volcans et dit au revoir. Puis il s'envole avec des oiseaux sauvages.",
            "it": "Il principe pulisce i vulcani e saluta il fiore. Poi vola via con gli uccelli selvatici.",
            "de": "Der Prinz putzt seine Vulkane sauber. Dann fliegt er mit einer Schar wilder Vögel weg.",
            "en": "The little prince sweeps his volcanoes clean. Then he flies away with a flock of wild birds.",
        },
        "ale": {
            "fr": "Avant de partir, le petit prince ramone ses trois volcans avec soin. La rose lui avoue enfin son amour et refuse le globe en verre pour voir les beaux papillons.",
            "it": "Prima della partenza, il piccolo principe spazza con cura i suoi tre vulcani. La rosa gli confessa finalmente il suo affetto e rifiuta la campana per poter incontrare le farfalle.",
            "de": "Vor der Abreise fegt der kleine Prinz seine drei Vulkane sorgfältig aus. Als er Abschied nimmt, gesteht ihm die Rose ihre Liebe und lehnt die Glasglocke ab, um Schmetterlinge zu sehen.",
            "en": "Before leaving, the little prince carefully sweeps out his three volcanoes. As he says goodbye, the rose confesses her love at last and declines the glass globe to welcome butterflies.",
        },
        "emma": {
            "fr": "Il profita, pour son évasion, d'une migration d'oiseaux sauvages. Au matin du départ il ramona soigneusement ses deux volcans en activité et son volcan éteint. «Adieu», dit-il à la fleur. «Mais oui, je t'aime», lui dit la fleur. «Tâche d'être heureux... Laisse ce globe tranquille. Je n'en veux plus.»",
            "it": "Approfittò, per la sua fuga, di una migrazione di uccelli selvatici. La mattina della partenza spazzò con cura i due vulcani attivi e il vulcano spento. «Addio», disse al fiore. «Sì, ti voglio bene», gli rispose il fiore. «Cerca di essere felice... Lascia stare questa campana. Non la voglio più.»",
            "de": "Für seine Flucht nutzte er einen Zug wilder Vögel. Am Morgen des Aufbruchs fegte er sorgsam seine zwei tätigen Vulkane und den erloschenen Vulkan aus. «Leb wohl», sagte er zur Blume. «Ja, ich liebe dich», flüsterte sie. «Versuche glücklich zu sein... Lass die Glasglocke ruhig liegen.»",
            "en": "For his escape he took advantage of a migration of wild birds. On the morning of his departure he carefully swept out his two active volcanoes and his extinct volcano. \"Goodbye,\" he said to the flower. \"Of course I love you,\" she replied. \"Try to be happy... Leave that globe alone.\"",
        },
        "questions": None,
    },
    {
        "page": 10,
        "art_refs": {
            "chapters": "Ch. X",
            "primary_0300771h": ["0300771h-26.jpg"],
            "ia_1943_leaves": ["n24"],
            "scene_summary": "The King sitting on his throne on Asteroid 325 in purple and ermine.",
        },
        "bubble_anchor": make_bubble_anchor(32, 36, "bottom-left", 54),
        "title": {
            "fr": "9. La Planète du Roi",
            "it": "9. Il Pianeta del Re",
            "de": "9. Der Planet des Königs",
            "en": "9. The Planet of the King",
        },
        "speech_bubble": {
            "speaker": "Le Roi",
            "fr": "Il faut exiger de chacun ce que chacun peut donner.",
            "it": "Bisogna esigere da ciascuno ciò che ciascuno può dare.",
            "de": "Man muss von jedem verlangen, was er leisten kann.",
            "en": "One must require from each what each one can give.",
        },
        "seby": {
            "fr": "Sur la première planète vit un vieux roi tout seul. Il croit commander aux étoiles avec raison.",
            "it": "Sul primo pianeta vive un vecchio re tutto solo. Crede di comandare alle stelle con ragione.",
            "de": "Auf dem ersten Planeten lebt ein einsamer König. Er glaubt, er herrsche mit Vernunft über alle Sterne.",
            "en": "On the first planet lives a lonely king. He believes he rules every star with reason.",
        },
        "ale": {
            "fr": "Le roi vêtu de pourpre croit régner sur tout l'univers, mais son manteau couvre toute la planète. Il explique calmement qu'un bon souverain donne seulement des ordres raisonnables.",
            "it": "Il re vestito di porpora crede di regnare sull'intero universo, anche se il mantello copre tutto il pianeta. Spiega con calma che un vero sovrano dà soltanto ordini ragionevoli.",
            "de": "Der König im Purpurmantel glaubt, über das ganze All zu herrschen, obwohl sein Mantel den winzigen Planeten bedeckt. Doch er erklärt ruhig, dass echte Macht auf Vernunft beruht.",
            "en": "The king dressed in purple believes he rules the entire universe, though his robe fills the tiny planet. Yet he kindly explains that wise authority always rests upon reason.",
        },
        "emma": {
            "fr": "La première était habitée par un roi. Le roi siégeait, habillé de pourpre et d'hermine, sur un trône très simple et cependant majestueux. «Ah! Voilà un sujet», s'écria le roi. «Il faut exiger de chacun ce que chacun peut donner», reprit le roi. «L'autorité repose d'abord sur la raison.»",
            "it": "Il primo pianeta era abitato da un re. Il re sedeva, vestito di porpora e d'ermellino, su un trono molto semplice eppure maestoso. «Ah! Ecco un suddito», esclamò il re. «Bisogna esigere da ciascuno ciò che ciascuno può dare. L'autorità poggia anzitutto sulla ragione.»",
            "de": "Der erste Planet war von einem König bewohnt. Der König saß, in Purpur und Hermelin gekleidet, auf einem sehr einfachen und doch majestätischen Thron. «Sieh da, ein Untertan!», rief der König. «Man muss von jedem fordern, was jeder leisten kann. Autorität beruht zuerst auf Vernunft.»",
            "en": "The first planet was inhabited by a king. Clad in royal purple and ermine, he sat upon a throne that was simple yet majestic. \"Ah! Here is a subject!\" cried the king. \"One must require from each what each can perform. Authority rests first on reason.\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p10_q1", "difficulty": "easy", "q": "Comment le petit prince voyage-t-il pour quitter sa planète ?", "options": ["Grâce à une migration d'oiseaux sauvages", "Dans un grand bateau à voile blanche", "À bord d'une fusée rapide et rouge"], "correct": 0},
                {"id": "pp_p10_q2", "difficulty": "easy", "q": "Que nettoie le petit prince le matin de son départ ?", "options": ["Les cheminées de sa petite maison", "Ses volcans sur la planète", "Les nuages gris du matin"], "correct": 1},
                {"id": "pp_p10_q3", "difficulty": "hard", "q": "Selon le roi, sur quoi doit reposer toute véritable autorité ?", "options": ["Sur la colère brutale et sur une grande peur", "Sur les grands chiffres d'or du commerce", "D'abord sur la raison et des ordres justes"], "correct": 2},
            ],
            "it": [
                {"id": "pp_p10_q1", "difficulty": "easy", "q": "In che modo il piccolo principe lascia il suo pianeta?", "options": ["Con una migrazione di uccelli selvatici", "Con una grande barca a vela bianca", "Con un razzo veloce e luminoso"], "correct": 0},
                {"id": "pp_p10_q2", "difficulty": "easy", "q": "Che cosa pulisce il piccolo principe prima di partire?", "options": ["I camini di una piccola casa", "I vulcani sul suo pianeta", "Le nuvole grigie del cielo"], "correct": 1},
                {"id": "pp_p10_q3", "difficulty": "hard", "q": "Secondo il re, su che cosa deve poggiare la vera autorità?", "options": ["Sulla paura costante e sulla forza brutale", "Sui grandi numeri d'oro del commercio", "Prima sulla ragione e su ordini giusti"], "correct": 2},
            ],
            "de": [
                {"id": "pp_p10_q1", "difficulty": "easy", "q": "Wie verlässt der kleine Prinz seinen winzigen Planeten?", "options": ["Mit einem Zug wilder Vögel", "Mit einem großen Segelboot", "Mit einer schnellen Rakete"], "correct": 0},
                {"id": "pp_p10_q2", "difficulty": "easy", "q": "Was macht der kleine Prinz am Morgen seines Aufbruchs sauber?", "options": ["Die Schornsteine des Dorfes", "Seine Vulkane auf dem Stern", "Die weißen Wolken am Himmel"], "correct": 1},
                {"id": "pp_p10_q3", "difficulty": "hard", "q": "Worauf muss jede echte Autorität nach den Worten des Königs beruhen?", "options": ["Auf sehr großer Angst und strenger harter Strafe", "Auf vielen Goldmünzen und großem Reichtum", "Zuerst auf Vernunft und gerechten Befehlen"], "correct": 2},
            ],
        },
    },
    # =========================================================================
    # SPREAD 5: P09 (Ch. XI-XII) + P10 (Ch. XIII)
    # =========================================================================
    {
        "page": 11,
        "art_refs": {
            "chapters": "Ch. XI-XII",
            "primary_0300771h": ["0300771h-27.jpg", "0300771h-03.gif"],
            "ia_1943_leaves": ["n28", "n30"],
            "scene_summary": "The Vain Man tipping his hat and the Drunkard before bottles.",
        },
        "bubble_anchor": make_bubble_anchor(12, 12, "bottom-center", 56),
        "title": {
            "fr": "10. Le Vaniteux et le Buveur",
            "it": "10. Il Vanitoso e l'Ubriacone",
            "de": "10. Der Eitle und der Säufer",
            "en": "10. The Vain Man and the Drunkard",
        },
        "speech_bubble": {
            "speaker": "Le Buveur",
            "fr": "Je bois pour oublier que j'ai honte... honte de boire!",
            "it": "Bevo per dimenticare che ho vergogna... vergogna di bere!",
            "de": "Ich trinke, um meine Scham über das Trinken zu vergessen!",
            "en": "I drink to forget that I am ashamed of drinking!",
        },
        "seby": {
            "fr": "Le vaniteux salue quand on l'applaudit. Le buveur reste triste devant ses bouteilles vides.",
            "it": "Il vanitoso saluta quando tutti battono le mani. Il bevitore resta triste davanti alle bottiglie.",
            "de": "Der Eitle hebt den Hut beim Klatschen. Der Säufer sitzt stumm vor vielen leeren Flaschen.",
            "en": "The vain man lifts his hat for applause. The drunkard sits sadly beside empty bottles.",
        },
        "ale": {
            "fr": "Sur la deuxième planète, le vaniteux n'entend que les compliments et lève son grand chapeau. Sur la troisième, un buveur solitaire boit en silence pour oublier sa propre honte.",
            "it": "Sul secondo pianeta, il vanitoso ascolta soltanto gli applausi e solleva il suo grande cappello. Sul terzo pianeta, un uomo beve in silenzio per cercare di dimenticare la sua vergogna.",
            "de": "Auf dem zweiten Stern will der Eitle nur bewundert werden und hebt stolz seinen Hut. Auf dem dritten Planeten trinkt ein trauriger Mann stumm weiter, um seine eigene Scham zu vergessen.",
            "en": "On the second planet, the vain man hears nothing but praise and tips his hat. On the third planet, a silent drunkard drinks endlessly just to forget how ashamed he feels.",
        },
        "emma": {
            "fr": "Les vaniteux n'entendent jamais que les louanges. La planète suivante était habitée par un buveur installé en silence devant des bouteilles vides et des bouteilles pleines. «Pourquoi bois-tu?» «Pour oublier que j'ai honte», avoua le buveur. «Honte de quoi?» «Honte de boire!» Les grandes personnes sont décidément très très bizarres.",
            "it": "I vanitosi non odono mai altro che le lodi. Il pianeta successivo era abitato da un ubriacone seduto in silenzio davanti a bottiglie vuote e bottiglie piene. «Perché bevi?» «Per dimenticare che ho vergogna», confessò l'ubriacone. «Vergogna di che?» «Vergogna di bere!» I grandi sono davvero molto molto bizzarri.",
            "de": "Die Eitlen hören immer nur Lobreden. Der nächste Planet war von einem Trinker bewohnt, der schweigend vor leeren und vollen Flaschen saß. «Warum trinkst du?» «Um zu vergessen, dass ich mich schäme», gestand der Trinker. «Worüber?» «Weil ich trinke!» Die großen Leute sind entschieden höchst wunderlich.",
            "en": "Conceited people never hear anything but praise. The next planet was inhabited by a tippler, settled in silence before empty bottles and full bottles. \"Why are you drinking?\" \"To forget that I am ashamed,\" the tippler confessed. \"Ashamed of what?\" \"Ashamed of drinking!\" Grown-ups are certainly very, very odd.",
        },
        "questions": None,
    },
    {
        "page": 12,
        "art_refs": {
            "chapters": "Ch. XIII",
            "primary_0300771h": ["0300771h-04.gif", "0300771h-44.jpg"],
            "ia_1943_leaves": ["n31", "n32"],
            "scene_summary": "The Businessman counting millions of stars at his desk.",
        },
        "bubble_anchor": make_bubble_anchor(8, 38, "bottom-right", 56),
        "title": {
            "fr": "11. Le Businessman et les Étoiles",
            "it": "11. L'Uomo d'Affari e le Stelle",
            "de": "11. Der Geschäftsmann",
            "en": "11. The Businessman and the Stars",
        },
        "speech_bubble": {
            "speaker": "Le Businessman",
            "fr": "Je possède les étoiles! Je suis un homme très sérieux!",
            "it": "Io possiedo tutte le stelle! Sono un uomo serio!",
            "de": "Mir gehören die Sterne! Ich bin ein ernster Mann!",
            "en": "I own the stars! I am a very serious man!",
        },
        "seby": {
            "fr": "Un monsieur compte des millions d'étoiles sur du papier. Mais il ne fait rien pour elles.",
            "it": "Un signore conta milioni di stelle su un foglio. Però non è affatto utile alle stelle.",
            "de": "Ein Mann zählt Millionen Sterne auf Papier. Aber er schaut nie hinauf und tut nichts für sie.",
            "en": "A busy man counts millions of bright stars on paper. Yet he does nothing for them.",
        },
        "ale": {
            "fr": "Le businessman est trop occupé pour lever la tête. Il écrit des nombres énormes et prétend posséder les étoiles, mais le petit prince remarque qu'il ne leur sert à rien.",
            "it": "L'uomo d'affari è così occupato che non alza neppure la testa. Scrive numeri enormi per possedere le stelle, ma il bambino gli fa notare che lui non è utile a nessuna stella.",
            "de": "Der Geschäftsmann blickt kaum von seinen Zahlen auf. Er schreibt den Reichtum auf ein Blatt Papier, doch der kleine Prinz merkt schnell: Dem Himmel und den Sternen nützt das gar nichts.",
            "en": "The businessman is far too busy to look up. He writes giant numbers on a slip of paper and claims to own the stars, yet the prince shows he is of no use to them.",
        },
        "emma": {
            "fr": "La quatrième planète était celle du businessman. «Ça fait donc cinq cent un millions six cent vingt-deux mille sept cent trente et un.» «Je possède les étoiles, puisque jamais personne avant moi n'a songé à les posséder.» «Mais tu n'es pas utile aux étoiles...»",
            "it": "Il quarto pianeta era quello dell'uomo d'affari, così occupato che non alzò neppure la testa. «Fa dunque cinquecentouno milioni seicentoventiduemila settecentotrentuno.» «Io possiedo tutte le stelle, poiché nessuno prima di me ci ha pensato.» «Ma non sei utile alle stelle...»",
            "de": "Der vierte Planet gehörte dem Geschäftsmann, der beim Besuch nicht einmal den Kopf hob. «Das macht also 501 Millionen 622 Tausend 731.» «Ich besitze alle Sterne, weil vor mir niemand daran gedacht hat, sie zu besitzen.» «Aber du bist den Sternen nicht nützlich...»",
            "en": "The fourth planet belonged to the businessman. \"That makes five hundred and one million, six hundred and twenty-two thousand, seven hundred and thirty-one.\" \"I own the stars, because nobody before me ever thought of owning them.\" \"But you are of no use to the stars...\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p12_q1", "difficulty": "easy", "q": "Que veut absolument recevoir le vaniteux sur la deuxième planète ?", "options": ["Des bouteilles d'eau", "Des applaudissements", "Des graines de baobab"], "correct": 1},
                {"id": "pp_p12_q2", "difficulty": "easy", "q": "Que compte sans arrêt le businessman à son bureau ?", "options": ["Des moutons endormis", "Des pièces jaunes d'or", "Des millions d'étoiles"], "correct": 2},
                {"id": "pp_p12_q3", "difficulty": "hard", "q": "Pourquoi le petit prince trouve-t-il que le businessman ne possède pas vraiment les étoiles ?", "options": ["Il ne fait rien et n'est utile à aucune étoile", "Il ignore la couleur bleue de toutes les fleurs", "Les étoiles brillantes appartiennent déjà au roi"], "correct": 0},
            ],
            "it": [
                {"id": "pp_p12_q1", "difficulty": "easy", "q": "Che cosa desidera soltanto ricevere il vanitoso sul secondo pianeta?", "options": ["Bottiglie d'acqua", "Lodi e applausi", "Semi di baobab"], "correct": 1},
                {"id": "pp_p12_q2", "difficulty": "easy", "q": "Che cosa conta senza sosta l'uomo d'affari alla sua scrivania?", "options": ["Pecore addormentate", "Monete gialle d'oro", "Milioni di stelle"], "correct": 2},
                {"id": "pp_p12_q3", "difficulty": "hard", "q": "Perché secondo il piccolo principe l'uomo d'affari non possiede davvero le stelle?", "options": ["Non fa nulla e non è utile a nessuna stella", "Non conosce affatto il colore di tutti i fiori", "Le stelle luminose appartengono già al re"], "correct": 0},
            ],
            "de": [
                {"id": "pp_p12_q1", "difficulty": "easy", "q": "Was möchte der Eitle auf dem zweiten Planeten immerzu hören?", "options": ["Lieder über das Meer", "Lob und Beifall", "Witze über Schafe"], "correct": 1},
                {"id": "pp_p12_q2", "difficulty": "easy", "q": "Was zählt der Geschäftsmann ununterbrochen an seinem Schreibtisch?", "options": ["Schlafende Schafe", "Glänzende Goldstücke", "Millionen von Sternen"], "correct": 2},
                {"id": "pp_p12_q3", "difficulty": "hard", "q": "Warum überzeugt der Geschäftsmann den kleinen Prinzen nicht?", "options": ["Er tut nichts und nützt keinem einzigen Stern", "Er kennt leider die Farben aller wilden Rosen nicht", "Alle schönen Sterne gehören längst dem König"], "correct": 0},
            ],
        },
    },
    # =========================================================================
    # SPREAD 6: P11 (Ch. XIV) + P12 (Ch. XV)
    # =========================================================================
    {
        "page": 13,
        "art_refs": {
            "chapters": "Ch. XIV",
            "primary_0300771h": ["0300771h-28.jpg"],
            "ia_1943_leaves": ["n34", "n35"],
            "scene_summary": "The Lamplighter beside his streetlamp on the smallest planet.",
        },
        "bubble_anchor": make_bubble_anchor(10, 11, "bottom-right", 56),
        "title": {
            "fr": "12. L'Allumeur de Réverbères",
            "it": "12. Il Lampionaio",
            "de": "12. Der Laternenanzünder",
            "en": "12. The Lamplighter",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "C'est véritablement utile puisque c'est joli!",
            "it": "È davvero utile perché è bello!",
            "de": "Das ist wirklich nützlich, weil es schön ist!",
            "en": "It is truly useful because it is pretty!",
        },
        "seby": {
            "fr": "Sur une planète qui tourne très vite, un homme allume et éteint son réverbère chaque minute.",
            "it": "Su un pianeta che gira velocissimo, un uomo accende e spegne un lampione ogni minuto.",
            "de": "Auf einem Planeten, der sich sehr schnell dreht, zündet ein Mann jede Minute seine Lampe an.",
            "en": "On a planet that spins very fast, a man lights and puts out his lamp every minute.",
        },
        "ale": {
            "fr": "La planète tourne si vite que l'allumeur n'a pas une seconde de repos. Pourtant le petit prince l'admire, car il s'occupe d'autre chose que de lui-même avec fidélité.",
            "it": "Il pianeta gira così velocemente che il lampionaio non ha un attimo di riposo. Eppure il piccolo principe lo ammira, perché si prende cura di qualcosa di diverso da sé.",
            "de": "Der Planet dreht sich so rasend schnell, dass jede Minute ein neuer Tag beginnt. Trotzdem mag der Junge diesen Mann: Treu zündet er das Licht für andere an und denkt nicht an sich.",
            "en": "The planet spins so fast that the lamplighter has not a moment's rest. Yet the little prince admires him, because he faithfully cares for something outside himself.",
        },
        "emma": {
            "fr": "La cinquième planète était la plus petite de toutes, avec un réverbère et un allumeur. Elle tourne toujours plus vite, et il n'a pas de repos. «Au moins son travail a-t-il un sens.» «C'est une occupation très jolie. C'est véritablement utile puisque c'est joli.»",
            "it": "Il quinto pianeta era il più piccolo di tutti, con un solo lampione e un lampionaio. Il pianeta gira sempre più veloce e l'uomo non ha mai riposo. «Almeno il suo lavoro ha un senso.» «È un'occupazione molto graziosa. È davvero utile proprio perché è molto bella.»",
            "de": "Der fünfte Planet war der kleinste von allen, mit einer Straßenlaterne und einem Laternenanzünder. Er dreht sich immer schneller ohne Ruhe. «Immerhin hat seine Arbeit einen Sinn.» «Es ist eine sehr hübsche Beschäftigung. Sie ist wahrhaft nützlich, weil sie schön ist.»",
            "en": "The fifth planet was the smallest of all, holding a street lamp and a lamplighter. It spins faster and faster, giving him not a moment's rest. \"At least his work has real meaning.\" \"It is a charming occupation. Since it is pretty, it is truly useful.\"",
        },
        "questions": None,
    },
    {
        "page": 14,
        "art_refs": {
            "chapters": "Ch. XV",
            "primary_0300771h": ["0300771h-29.jpg"],
            "ia_1943_leaves": ["n37", "n38"],
            "scene_summary": "The Geographer sitting behind his huge desk and books.",
        },
        "bubble_anchor": make_bubble_anchor(8, 36, "bottom-right", 56),
        "title": {
            "fr": "13. Le Géographe et l'Éphémère",
            "it": "13. Il Geografo e l'Effimero",
            "de": "13. Der Geograph",
            "en": "13. The Geographer",
        },
        "speech_bubble": {
            "speaker": "Le Géographe",
            "fr": "Nous ne notons pas les fleurs: elles sont éphémères.",
            "it": "Non segniamo i fiori: sono effimeri e passeggeri.",
            "de": "Blumen schreiben wir nicht auf: Sie sind vergänglich.",
            "en": "We do not record flowers: they are ephemeral.",
        },
        "seby": {
            "fr": "Le vieux géographe écrit de gros livres sur les montagnes. Il conseille de visiter la Terre.",
            "it": "Il vecchio geografo scrive grandi libri sulle montagne. Poi consiglia di visitare la Terra.",
            "de": "Der alte Geograph schreibt dicke Bücher über Berge. Er rät dem Prinzen zu einer Reise zur Erde.",
            "en": "An old geographer writes thick books about tall mountains. He advises visiting planet Earth.",
        },
        "ale": {
            "fr": "Le géographe ne sort jamais de son bureau. Quand il explique que les fleurs sont éphémères, le prince s'inquiète pour sa rose, puis suit son conseil de visiter la Terre.",
            "it": "Il geografo non lascia mai il suo scrittoio. Quando spiega che i fiori sono effimeri, il bambino teme per la sua rosa, ma segue il consiglio di visitare la Terra.",
            "de": "Der Geograph verlässt nie seinen Schreibtisch. Als er erklärt, dass Blumen bald vergehen, sorgt sich der Prinz um seine Rose und reist auf seinen Rat zur Erde.",
            "en": "The geographer never leaves his desk. When he explains that flowers are ephemeral, the prince worries for his rose, then follows his advice to visit planet Earth.",
        },
        "emma": {
            "fr": "La sixième planète était habitée par un vieux Monsieur qui écrivait d'énormes livres. «Les géographies», dit le géographe, «sont les livres les plus sérieux de tous les livres.» «Nous ne notons pas les fleurs», dit-il. «Parce que les fleurs sont éphémères.» Il lui conseilla de visiter la Terre, et il songea à sa fleur.",
            "it": "Il sesto pianeta era abitato da un vecchio signore che scriveva enormi libri. «I libri di geografia», disse il geografo, «sono i più seri fra tutti i libri.» «Non annotiamo i fiori.» «Perché i fiori sono effimeri.» Gli consigliò infine di visitare la Terra, e ripensò al suo fiore.",
            "de": "Der sechste Planet war von einem alten Herrn bewohnt, der dicke Bücher schrieb. «Geographien», sagte der Geograph, «sind die ernsthaftesten aller Bücher.» «Blumen halten wir nicht fest.» «Weil Blumen vergänglich sind.» Schließlich riet er ihm, die Erde zu besuchen, und der Prinz dachte an seine Blume.",
            "en": "The sixth planet was inhabited by an old gentleman who wrote enormous books. \"Geographies,\" said the geographer, \"are the books most concerned with serious matters.\" \"We do not record flowers.\" \"Because flowers are ephemeral.\" Finally he advised him to visit Earth, and the prince thought of his rose.",
        },
        "questions": {
            "fr": [
                {"id": "pp_p14_q1", "difficulty": "easy", "q": "Pourquoi l'allumeur de réverbères ne peut-il jamais se reposer ?", "options": ["Il a perdu sa montre dorée", "Il doit compter les nuages", "Sa planète tourne très vite"], "correct": 2},
                {"id": "pp_p14_q2", "difficulty": "easy", "q": "Pourquoi le géographe refuse-t-il de noter les fleurs dans ses livres ?", "options": ["Elles sont éphémères", "Elles n'ont pas d'odeur", "Elles sont trop petites"], "correct": 0},
                {"id": "pp_p14_q3", "difficulty": "hard", "q": "Quelle planète le géographe conseille-t-il au petit prince de visiter ensuite ?", "options": ["La planète du vieux roi fier", "La planète appelée la Terre", "L'astéroïde caché B 612"], "correct": 1},
            ],
            "it": [
                {"id": "pp_p14_q1", "difficulty": "easy", "q": "Perché il lampionaio non riesce mai a riposarsi?", "options": ["Ha perso il suo orologio d'oro", "Deve contare tutte le stelle", "Il suo pianeta gira velocissimo"], "correct": 2},
                {"id": "pp_p14_q2", "difficulty": "easy", "q": "Perché il geografo non scrive i fiori nei suoi enormi libri?", "options": ["Perché sono effimeri", "Perché hanno le spine", "Perché sono troppo piccoli"], "correct": 0},
                {"id": "pp_p14_q3", "difficulty": "hard", "q": "Quale pianeta consiglia di visitare il geografo al piccolo principe?", "options": ["Il pianeta del vecchio re solitario", "Il pianeta chiamato la Terra", "L'asteroide lontano B 612"], "correct": 1},
            ],
            "de": [
                {"id": "pp_p14_q1", "difficulty": "easy", "q": "Warum findet der Laternenanzünder keinen Augenblick Ruhe?", "options": ["Er hat seine goldene Uhr verloren", "Er muss weiße Wolken zählen", "Sein Planet dreht sich zu schnell"], "correct": 2},
                {"id": "pp_p14_q2", "difficulty": "easy", "q": "Warum trägt der Geograph keine Blumen in seine großen Bücher ein?", "options": ["Weil sie vergänglich sind", "Weil sie keine Farben haben", "Weil sie viel zu klein sind"], "correct": 0},
                {"id": "pp_p14_q3", "difficulty": "hard", "q": "Welchen Planeten rät der Geograph dem kleinen Prinzen zu besuchen?", "options": ["Den Stern des alten Königs", "Den Planeten namens Erde", "Den kleinen Asteroiden B 612"], "correct": 1},
            ],
        },
    },
]

PAGES_DATA.extend([
    # =========================================================================
    # SPREAD 7: P13 (Ch. XVI-XVII) + P14 (Ch. XVIII-XIX)
    # =========================================================================
    {
        "page": 15,
        "art_refs": {
            "chapters": "Ch. XVI-XVII",
            "primary_0300771h": ["0300771h-30.jpg", "0300771h-31.jpg"],
            "ia_1943_leaves": ["n41", "n42"],
            "scene_summary": "Arrival on Earth in the African desert and meeting the golden snake.",
        },
        "bubble_anchor": make_bubble_anchor(10, 12, "bottom-right", 56),
        "title": {
            "fr": "14. La Terre et le Serpent d'Or",
            "it": "14. La Terra e il Serpente d'Oro",
            "de": "14. Die Erde und die Schlange",
            "en": "14. Earth and the Golden Snake",
        },
        "speech_bubble": {
            "speaker": "Le Serpent",
            "fr": "On est un peu seul dans le désert... et chez les hommes.",
            "it": "Si è soli nel deserto... ma si è soli anche tra gli uomini.",
            "de": "Man ist einsam in der Wüste... auch bei den Menschen.",
            "en": "It is lonely in the desert... and among people too.",
        },
        "seby": {
            "fr": "Sur Terre, le prince arrive dans le désert. Un petit serpent doré lui parle doucement.",
            "it": "Sulla Terra il principe arriva nel deserto. Un serpentello color oro gli parla piano piano.",
            "de": "Der kleine Prinz landet im Wüstensand. Eine goldene Schlange taucht auf und spricht leise.",
            "en": "On Earth, the prince lands in the desert. A tiny golden snake greets him softly.",
        },
        "ale": {
            "fr": "Arrivé sur la septième planète, le petit prince ne voit personne autour de lui. Un mince serpent couleur de lune glisse dans le sable et lui parle en énigmes mystérieuses.",
            "it": "Arrivato sulla Terra, il piccolo principe non incontra nessuno intorno a sé. Un sottile serpente color di luna scivola sulla sabbia calda e gli parla con parole misteriose.",
            "de": "Auf dem siebten Planeten sieht der kleine Prinz weit und breit keinen einzigen Menschen. Da taucht eine schlanke goldene Schlange im Sand auf und spricht rätselhafte Worte.",
            "en": "Arriving on the seventh planet, the little prince sees nobody around him. A slender moon-coloured snake glides across the warm sand and speaks to him in mysterious riddles.",
        },
        "emma": {
            "fr": "La septième planète fut donc la Terre. Le petit prince, une fois sur Terre, fut bien surpris de ne voir personne, quand un anneau couleur de lune remua dans le sable. «On est un peu seul dans le désert...» «On est seul aussi chez les hommes», dit le serpent.",
            "it": "Il settimo pianeta fu dunque la Terra. Il piccolo principe, giunto sulla Terra, fu molto sorpreso di non vedere nessuno, quando un anello color di luna si mosse nella sabbia. «Si è un po' soli nel deserto...» «Si è soli anche tra gli uomini», disse il serpente.",
            "de": "Der siebte Planet war also die Erde. Als der kleine Prinz dort ankam, war er erstaunt, niemanden zu sehen, bis sich ein mondfarbener Ring im Sand bewegte. «Man ist ein wenig einsam in der Wüste...» «Man ist auch bei den Menschen einsam», erwiderte die Schlange.",
            "en": "So the seventh planet was the Earth. Once on Earth, the little prince was quite surprised to see nobody at all, until a moon-coloured coil stirred softly in the sand. \"It is a little lonely in the desert...\" \"It is lonely among people too,\" said the snake.",
        },
        "questions": None,
    },
    {
        "page": 16,
        "art_refs": {
            "chapters": "Ch. XVIII-XIX",
            "primary_0300771h": ["0300771h-32.jpg", "0300771h-33.jpg"],
            "ia_1943_leaves": ["n42", "n43"],
            "scene_summary": "Tiny three-petal desert flower and the Prince calling from the mountain peak.",
        },
        "bubble_anchor": make_bubble_anchor(8, 36, "bottom-right", 56),
        "title": {
            "fr": "15. La Montagne et l'Écho",
            "it": "15. La Montagna e l'Eco",
            "de": "15. Der Berg und das Echo",
            "en": "15. The Mountain and the Echo",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Soyez mes amis, je suis seul! — Je suis seul...",
            "it": "Siate miei amici, sono solo! — Sono solo...",
            "de": "Seid meine Freunde, ich bin allein! — Allein...",
            "en": "Be my friends, I am all alone! — All alone...",
        },
        "seby": {
            "fr": "Le prince monte sur une haute montagne. L'écho répète exactement tout ce qu'il crie.",
            "it": "Il principe sale su una montagna alta. L'eco ripete subito tutte le parole che lui dice.",
            "de": "Der Prinz klettert hoch auf einen Berg. Das Echo ruft seine eigenen Worte laut zurück.",
            "en": "The little prince climbs a tall rocky mountain. Only the echo answers his lonely call.",
        },
        "ale": {
            "fr": "Après avoir croisé une minuscule fleur à trois pétales, il escalade une haute montagne. En entendant seulement l'écho, il pense que les hommes répètent sans inventer.",
            "it": "Dopo aver incontrato un fiorellino con tre petali nel deserto, scala un'alta montagna rocciosa. Sentendo soltanto la propria eco, crede che gli uomini sappiano solo ripetere le parole.",
            "de": "Nachdem er einer winzigen Blume im Sand begegnet ist, steigt er auf einen hohen Gipfel. Weil nur das Echo antwortet, denkt er, den Menschen fehlt jede Phantasie.",
            "en": "After meeting a tiny three-petalled flower in the sand, he climbs a jagged mountain. Hearing only his own echo bounce back, he believes people lack imagination.",
        },
        "emma": {
            "fr": "Le petit prince traversa le désert et ne rencontra qu'une fleur à trois pétales, puis fit l'ascension d'une haute montagne. «Soyez mes amis, je suis seul», dit-il. «Je suis seul...» répondit l'écho. «Et les hommes manquent d'imagination. Ils répètent ce qu'on leur dit...»",
            "it": "Il piccolo principe attraversò il deserto e incontrò soltanto un fiore a tre petali, poi salì su una montagna molto alta. «Siate miei amici, sono solo», disse. «Sono solo...» rispose l'eco. «E gli uomini mancano di immaginazione. Ripetono sempre ciò che si dice loro...»",
            "de": "Der kleine Prinz wanderte durch die Wüste und traf nur eine kleine Blume mit drei Blütenblättern, dann bestieg er einen hohen Berg. «Seid meine Freunde, ich bin allein», rief er. «Allein...» antwortete das Echo. «Die Menschen haben keine Phantasie. Sie sprechen nur alles nach...»",
            "en": "The little prince crossed the desert and met only a flower with three petals, then climbed a high mountain. \"Be my friends, I am all alone,\" he said. \"All alone...\" answered the echo. \"And people lack imagination. They merely repeat whatever one says...\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p16_q1", "difficulty": "easy", "q": "Quel animal couleur de lune rencontre d'abord le petit prince dans le désert ?", "options": ["Un serpent doré", "Un renard roux", "Un grand éléphant"], "correct": 0},
                {"id": "pp_p16_q2", "difficulty": "easy", "q": "Qui répond au petit prince quand il appelle du haut de la montagne ?", "options": ["L'astronome turc", "L'écho des rochers", "Le vieux roi seul"], "correct": 1},
                {"id": "pp_p16_q3", "difficulty": "hard", "q": "Pourquoi le petit prince pense-t-il que les hommes répètent ce qu'on leur dit ?", "options": ["Parce qu'ils ne dessinent jamais de jolis moutons blancs", "Parce qu'ils dorment profondément toute la journée", "Parce que l'écho ne fait que répéter ses propres mots"], "correct": 2},
            ],
            "it": [
                {"id": "pp_p16_q1", "difficulty": "easy", "q": "Quale animale color di luna incontra per primo il piccolo principe nel deserto?", "options": ["Un serpente dorato", "Una volpe rossa", "Un grande elefante"], "correct": 0},
                {"id": "pp_p16_q2", "difficulty": "easy", "q": "Chi risponde al piccolo principe quando chiama dalla cima della montagna?", "options": ["L'astronomo turco", "L'eco delle rocce", "Il re del pianeta"], "correct": 1},
                {"id": "pp_p16_q3", "difficulty": "hard", "q": "Perché il piccolo principe crede che gli uomini ripetano sempre le parole?", "options": ["Perché non disegnano mai delle belle pecore bianche", "Perché dormono profondamente tutto il giorno", "Perché l'eco ripete soltanto le sue stesse parole"], "correct": 2},
            ],
            "de": [
                {"id": "pp_p16_q1", "difficulty": "easy", "q": "Welchem mondfarbenen Tier begegnet der kleine Prinz zuerst in der Wüste?", "options": ["Einer goldenen Schlange", "Einem roten Fuchs", "Einem großen Elefanten"], "correct": 0},
                {"id": "pp_p16_q2", "difficulty": "easy", "q": "Wer antwortet dem kleinen Prinzen vom Gipfel des hohen Berges?", "options": ["Der türkische Astronom", "Das Echo der Felsen", "Der einsame König"], "correct": 1},
                {"id": "pp_p16_q3", "difficulty": "hard", "q": "Warum denkt der kleine Prinz auf dem Berg, dass die Menschen alles nachsprechen?", "options": ["Weil niemand ein hübsches weißes Schaf zeichnen kann", "Weil alle Menschen den ganzen Tag lang schlafen", "Weil das Echo nur seine eigenen Worte zurückruft"], "correct": 2},
            ],
        },
    },
    # =========================================================================
    # SPREAD 8: P15 (Ch. XX) + P16 (Ch. XXI Part 1)
    # =========================================================================
    {
        "page": 17,
        "art_refs": {
            "chapters": "Ch. XX",
            "primary_0300771h": ["0300771h-34.jpg"],
            "ia_1943_leaves": ["n44"],
            "scene_summary": "Little Prince lying in the grass crying before the garden of 5,000 roses.",
        },
        "bubble_anchor": make_bubble_anchor(26, 12, "bottom-left", 56),
        "title": {
            "fr": "16. Le Jardin des Cinq Mille Roses",
            "it": "16. Il Giardino delle Cinquemila Rose",
            "de": "16. Der Garten der Fünftausend Rosen",
            "en": "16. The Garden of Five Thousand Roses",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Je croyais avoir une fleur unique, et voilà cinq mille roses!",
            "it": "Credevo di avere un fiore unico, e invece ci sono cinquemila rose!",
            "de": "Ich dachte, meine Blume wäre einzigartig, doch hier stehen Tausende!",
            "en": "I thought I had a unique flower, yet here are five thousand!",
        },
        "seby": {
            "fr": "Le prince trouve un grand jardin avec cinq mille roses. Il pleure dans l'herbe verte.",
            "it": "Il principe trova un grande giardino pieno di cinquemila rose. Piange triste sull'erba verde.",
            "de": "Der Prinz sieht einen Garten mit fünftausend gleichen Rosen. Traurig weint er im grünen Gras.",
            "en": "The prince finds a garden with five thousand roses. Sadly, he weeps on the grass.",
        },
        "ale": {
            "fr": "En suivant une route, le petit prince découvre cinq mille roses toutes pareilles. Sa fleur lui avait dit être unique au monde, alors il s'allonge dans l'herbe et pleure.",
            "it": "Seguendo un sentiero, il piccolo principe scopre cinquemila rose tutte uguali in un solo giardino. Il suo fiore si credeva unico nell'universo, così il bambino piange sull'erba.",
            "de": "Auf einer Straße entdeckt der kleine Prinz einen Garten mit fünftausend gleichen Rosen. Seine Blume hatte ihm erzählt, sie sei einzig auf der Welt. Traurig weint er im grünen Gras.",
            "en": "Following a country road, the little prince discovers five thousand identical roses in one garden. His flower had claimed to be unique in the universe, so he lies in the grass weeping.",
        },
        "emma": {
            "fr": "Il découvrit enfin une route. C'était un jardin fleuri de roses. Et voici qu'il en était cinq mille, toutes semblables, dans un seul jardin! «Je me croyais riche d'une fleur unique, et je ne possède qu'une rose ordinaire.» Et, couché dans l'herbe, il pleura.",
            "it": "Scoprì finalmente una strada. Era un giardino fiorito di rose. Ed ecco che ce n'erano cinquemila, tutte simili, in un solo giardino! «Mi credevo ricco di un fiore unico, e non possiedo che una rosa qualunque.» E, sdraiato nell'erba, scoppiò a piangere.",
            "de": "Endlich fand er eine Straße. Es war ein blühender Rosengarten. Und siehe da: Fünftausend gleiche Rosen standen in einem einzigen Garten! «Ich hielt mich für reich durch eine einzigartige Blume, und besitze doch nur eine gewöhnliche Rose.» Und er legte sich ins Gras und weinte.",
            "en": "At last he discovered a road. It led to a garden blooming with roses. And behold, there were five thousand of them, all alike, in a single garden! \"I thought I was rich with a unique flower, and I own only an ordinary rose.\" Lying in the grass, he wept.",
        },
        "questions": None,
    },
    {
        "page": 18,
        "art_refs": {
            "chapters": "Ch. XXI (Part 1)",
            "primary_0300771h": ["0300771h-35.jpg", "0300771h-36.jpg"],
            "ia_1943_leaves": ["n45"],
            "scene_summary": "The Fox appears under the apple tree and asks to be tamed.",
        },
        "bubble_anchor": make_bubble_anchor(8, 36, "bottom-center", 56),
        "title": {
            "fr": "17. Le Renard : «Apprivoise-moi!»",
            "it": "17. La Volpe: «Addomesticami!»",
            "de": "17. Der Fuchs: «Zähme mich!»",
            "en": "17. The Fox: \"Tame Me!\"",
        },
        "speech_bubble": {
            "speaker": "Le Renard",
            "fr": "S'il te plaît... apprivoise-moi! Créons des liens!",
            "it": "Per favore... addomesticami! Creiamo un legame vero!",
            "de": "Bitte... zähme mich! Lass uns Bande knüpfen!",
            "en": "Please... tame me! Let us create real ties!",
        },
        "seby": {
            "fr": "Un joli renard apparaît sous un pommier. Il demande au petit prince de l'apprivoiser.",
            "it": "Una bella volpe arriva sotto un melo. Chiede al piccolo principe di diventare suo amico.",
            "de": "Ein kleiner Fuchs schaut unter dem Apfelbaum hervor. Er lädt den Prinzen zum Zähmen ein.",
            "en": "A friendly fox appears under an apple tree. He asks the little prince to tame him.",
        },
        "ale": {
            "fr": "Un renard sort de l'ombre du pommier et explique ce que veut dire apprivoiser: créer des liens précieux. Ainsi chacun deviendra unique au monde pour son ami.",
            "it": "Sotto l'albero di melo appare una volpe gentile e spiega che addomesticare significa creare legami profondi. Se diventeranno amici veri, avranno bisogno l'uno dell'altro per sempre.",
            "de": "Unter dem Apfelbaum erscheint ein kluger Fuchs. Er erklärt dem kleinen Prinzen das vergessene Wort «zähmen»: Es bedeutet, Bande zu knüpfen und einander einzigartig zu werden.",
            "en": "A clever fox appears under an apple tree and explains what taming means: creating precious ties. If they become friends, they will truly need each other and be unique.",
        },
        "emma": {
            "fr": "C'est alors qu'apparut le renard sous le pommier. «Je ne suis pas apprivoisé», dit le renard. «Ça signifie créer des liens...» «Tu seras pour moi unique au monde. Je serai pour toi unique au monde...» Et le renard dit: «S'il te plaît... apprivoise-moi!»",
            "it": "Fu allora che apparve la volpe sotto l'albero di melo. «Non sono ancora addomesticata», disse la volpe. «Significa creare dei legami...» «Tu sarai per me unico al mondo. Io sarò per te unica al mondo...» E la volpe disse: «Per favore... addomesticami!»",
            "de": "Da erschien der kluge Fuchs unter dem Apfelbaum. «Ich bin nicht gezähmt», sagte der Fuchs. «Es bedeutet, Bande zu knüpfen...» «Du wirst für mich einzig auf der Welt sein. Ich werde für dich einzig auf der Welt sein...» Und der Fuchs sagte: «Bitte... zähme mich!»",
            "en": "It was then that the fox appeared beneath the apple tree. \"I am not tamed,\" said the fox. \"It means to establish ties...\" \"To me, you will be unique in all the world. To you, I shall be unique in all the world...\" And the fox said: \"Please... tame me!\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p18_q1", "difficulty": "easy", "q": "Combien de roses semblables le petit prince voit-il dans le jardin ?", "options": ["Quarante-quatre roses", "Cinq mille roses", "Trois petites roses"], "correct": 1},
                {"id": "pp_p18_q2", "difficulty": "easy", "q": "Où apparaît le renard devant le petit prince ?", "options": ["Sur une haute montagne", "Dans une caisse en bois", "Sous un grand pommier"], "correct": 2},
                {"id": "pp_p18_q3", "difficulty": "hard", "q": "Que signifie le mot «apprivoiser» selon le renard ?", "options": ["Créer des liens forts qui rendent deux êtres uniques", "Acheter de beaux cadeaux dans une boutique de la ville", "Répéter toujours les mêmes phrases sur une haute montagne"], "correct": 0},
            ],
            "it": [
                {"id": "pp_p18_q1", "difficulty": "easy", "q": "Quante rose simili vede il piccolo principe nel giardino?", "options": ["Quarantaquattro rose", "Cinquemila rose", "Tre piccole rose"], "correct": 1},
                {"id": "pp_p18_q2", "difficulty": "easy", "q": "Dove appare la volpe davanti al piccolo principe?", "options": ["Su un'alta montagna", "Dentro una cassa di legno", "Sotto un albero di melo"], "correct": 2},
                {"id": "pp_p18_q3", "difficulty": "hard", "q": "Che cosa significa la parola «addomesticare» secondo la volpe?", "options": ["Creare legami forti che rendono due esseri unici", "Comprare molti regali nuovi in una grande città", "Ripetere sempre le stesse parole su una montagna"], "correct": 0},
            ],
            "de": [
                {"id": "pp_p18_q1", "difficulty": "easy", "q": "Wie viele gleiche Rosen entdeckt der kleine Prinz in dem Garten?", "options": ["Vierundvierzig Rosen", "Fünftausend Rosen", "Drei kleine Rosen"], "correct": 1},
                {"id": "pp_p18_q2", "difficulty": "easy", "q": "Wo begegnet der kleine Prinz dem Fuchs?", "options": ["Auf einem hohen Berg", "In einer Holzkiste", "Unter einem Apfelbaum"], "correct": 2},
                {"id": "pp_p18_q3", "difficulty": "hard", "q": "Was bedeutet das Wort «zähmen» nach den Worten des Fuchses?", "options": ["Starke Bande knüpfen, bis man einander einzigartig wird", "Viele teure Dinge in einem großen Geschäft kaufen gehen", "Immer die gleichen fremden Worte auf einem hohen Berg rufen"], "correct": 0},
            ],
        },
    },
    # =========================================================================
    # SPREAD 9: P17 (Ch. XXI Part 2) + P18 (Ch. XXI Part 3)
    # =========================================================================
    {
        "page": 19,
        "art_refs": {
            "chapters": "Ch. XXI (Part 2)",
            "primary_0300771h": ["0300771h-37.jpg"],
            "ia_1943_leaves": ["n47"],
            "scene_summary": "Taming ritual day by day and the golden wheat recalling hair.",
        },
        "bubble_anchor": make_bubble_anchor(10, 12, "bottom-center", 56),
        "title": {
            "fr": "18. Les Rites et le Blé Doré",
            "it": "18. I Riti e il Grano Dorato",
            "de": "18. Die Bräuche und das Goldkorn",
            "en": "18. Rites and Golden Wheat",
        },
        "speech_bubble": {
            "speaker": "Le Renard",
            "fr": "Le blé doré me fera toujours souvenir de tes cheveux!",
            "it": "Il grano dorato mi ricorderà sempre i tuoi capelli!",
            "de": "Das goldene Korn wird mich immer an dein Haar erinnern!",
            "en": "The golden wheat will always remind me of your hair!",
        },
        "seby": {
            "fr": "Chaque jour, le petit prince s'assoit plus près du renard. Ils deviennent de grands amis.",
            "it": "Ogni giorno il piccolo principe si siede più vicino alla volpe. Diventano subito grandi amici.",
            "de": "Jeden Tag setzt sich der kleine Prinz näher zum Fuchs. Bald werden sie richtig gute Freunde.",
            "en": "Every day, the little prince sits closer to the fox. Soon they become dear friends.",
        },
        "ale": {
            "fr": "Le renard enseigne la patience et les rites au petit prince. Quand l'enfant vient à quatre heures, le renard commence à être heureux dès trois heures et aime le blé doré.",
            "it": "La volpe insegna la pazienza e la bellezza dei riti al bambino. Se verrà alle quattro del pomeriggio, già alle tre il cuore della volpe inizierà a battere di gioia.",
            "de": "Geduldig bringt der Fuchs dem kleinen Prinzen feste Bräuche bei. Wenn er pünktlich um vier Uhr kommt, fängt der Fuchs schon um drei Uhr mit dem Glücklichsein an.",
            "en": "The fox teaches the little prince patience and the magic of rites. If the boy arrives at four o'clock, the fox will already start feeling happy at three o'clock.",
        },
        "emma": {
            "fr": "«Mais tu as des cheveux couleur d'or.» «Le blé, qui est doré, me fera souvenir de toi. Et j'aimerai le bruit du vent dans le blé...» «Il faut être très patient.» «Il faut des rites.» Chaque jour, le petit prince s'assit plus près. Ainsi il apprivoisa le renard.",
            "it": "«Ma tu hai i capelli color dell'oro.» «Il grano, che è dorato, mi farà ricordare di te. E amerò il rumore del vento tra le spighe...» «Bisogna essere molto pazienti.» «Ci vogliono i riti.» Ogni giorno, il piccolo principe si sedette più vicino. Così addomesticò la volpe.",
            "de": "«Aber du hast goldfarbenes Haar.» «Das Korn, das golden ist, wird mich an dich erinnern. Und ich werde das Rauschen des Windes im Weizen lieben...» «Man muss sehr geduldig sein.» «Man braucht feste Bräuche.» Jeden Tag rückte der kleine Prinz näher heran. So zähmte er den Fuchs.",
            "en": "«But you have hair the colour of gold.» «The wheat, which is golden, will remind me of you. And I shall love the sound of the wind in the wheat...» «One must be very patient.» «One needs rites.» Each day, the little prince sat closer. Thus he tamed the fox.".replace("«", "\"").replace("»", "\""),
        },
        "questions": None,
    },
    {
        "page": 20,
        "art_refs": {
            "chapters": "Ch. XXI (Part 3)",
            "primary_0300771h": ["0300771h-43.jpg"],
            "ia_1943_leaves": ["n48"],
            "scene_summary": "The Fox's secret farewell: 'One sees clearly only with the heart.'",
        },
        "bubble_anchor": make_bubble_anchor(8, 38, "bottom-center", 56),
        "title": {
            "fr": "19. Le Secret du Renard",
            "it": "19. Il Segreto della Volpe",
            "de": "19. Das Geheimnis des Fuchses",
            "en": "19. The Secret of the Fox",
        },
        "speech_bubble": {
            "speaker": "Le Renard",
            "fr": "On ne voit bien qu'avec le cœur. L'essentiel est invisible.",
            "it": "Non si vede bene che col cuore. L'essenziale è invisibile!",
            "de": "Man sieht nur mit dem Herzen gut. Das Wesentliche ist unsichtbar.",
            "en": "One sees clearly only with the heart. What is essential is invisible.",
        },
        "seby": {
            "fr": "Il a soigné sa rose avec amour. Le renard révèle son secret: on voit bien avec le cœur.",
            "it": "Ha curato la sua rosa con amore. La volpe svela il segreto: si vede bene col cuore.",
            "de": "Er hat seine Rose liebevoll gepflegt. Der Fuchs verrät: Man sieht nur mit dem Herzen gut.",
            "en": "He cared lovingly for his rose. The fox reveals his secret: one sees well with the heart.",
        },
        "ale": {
            "fr": "En revoyant les cinq mille roses, le petit prince comprend que sa fleur est unique parce qu'il l'a arrosée et aimée. Le renard lui confie alors son secret éternel.",
            "it": "Rivedendo le cinquemila rose, il piccolo principe capisce che il suo fiore è unico per tutto il tempo che gli ha dedicato. Prima dell'addio, la volpe gli affida un segreto prezioso.",
            "de": "Beim Anblick der vielen Rosen versteht der Prinz, warum seine Rose wegen der verlorenen Zeit für sie so wichtig ist. Beim Abschied hört er dem Fuchs genau zu.",
            "en": "Looking back at the rose garden, the little prince realises why his own rose is unique: because of the time he spent caring for her. The fox whispers his timeless secret.",
        },
        "emma": {
            "fr": "Et il revint vers le renard: «Adieu», dit le renard. «Voici mon secret. Il est très simple: on ne voit bien qu'avec le cœur. L'essentiel est invisible pour les yeux.» «C'est le temps que tu as perdu pour ta rose qui fait ta rose si importante.» «Tu es responsable de ta rose.»",
            "it": "E tornò dalla volpe: «Addio», disse la volpe. «Ecco il mio segreto. È molto semplice: non si vede bene che col cuore. L'essenziale è invisibile agli occhi.» «È il tempo che hai perduto per la tua rosa che ha reso la tua rosa così importante.» «Tu sei responsabile della tua rosa.»",
            "de": "Und er ging zum Fuchs zurück: «Leb wohl», sagte der Fuchs. «Hier ist mein Geheimnis. Es ist ganz einfach: Man sieht nur mit dem Herzen gut. Das Wesentliche ist für die Augen unsichtbar.» «Die Zeit, die du für deine Rose verloren hast, macht sie so wichtig.» «Du bist für sie verantwortlich.»",
            "en": "And he went back to the fox. \"Goodbye,\" said the fox. \"Here is my secret. It is very simple: one sees clearly only with the heart. What is essential is invisible to the eyes. The time you wasted for your rose makes her important. You are responsible for your rose.\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p20_q1", "difficulty": "easy", "q": "Qu'est-ce qui rappellera les cheveux du petit prince au renard ?", "options": ["Les pierres du vieux mur", "La neige de la montagne", "La couleur dorée du blé"], "correct": 2},
                {"id": "pp_p20_q2", "difficulty": "easy", "q": "Avec quoi voit-on vraiment l'essentiel selon le secret du renard ?", "options": ["Avec le cœur", "Avec un télescope", "Avec ses yeux"], "correct": 0},
                {"id": "pp_p20_q3", "difficulty": "hard", "q": "Pourquoi la rose du petit prince est-elle si importante malgré les cinq mille autres roses ?", "options": ["Parce qu'elle possède des épines plus longues que les autres", "À cause du temps et du soin donnés pour elle avec amour", "Parce qu'elle pousse seule au milieu d'un champ de blé"], "correct": 1},
            ],
            "it": [
                {"id": "pp_p20_q1", "difficulty": "easy", "q": "Che cosa ricorderà alla volpe i capelli del piccolo principe?", "options": ["Le pietre del vecchio muro", "La neve sulla montagna", "Il colore dorato del grano"], "correct": 2},
                {"id": "pp_p20_q2", "difficulty": "easy", "q": "Con che cosa si vede bene l'essenziale secondo il segreto della volpe?", "options": ["Con il cuore", "Con il telescopio", "Solo con gli occhi"], "correct": 0},
                {"id": "pp_p20_q3", "difficulty": "hard", "q": "Perché la rosa del piccolo principe è così importante rispetto alle cinquemila altre rose?", "options": ["Perché possiede tante spine molto lunghe e forti", "Per il tempo e la cura dedicati a lei con amore", "Perché cresce sola in un grande campo di grano dorato"], "correct": 1},
            ],
            "de": [
                {"id": "pp_p20_q1", "difficulty": "easy", "q": "Woran wird der Fuchs sich beim Anblick des goldenen Weizens immer erinnern?", "options": ["An die Steine der alten Mauer", "An den Schnee auf dem Gipfel", "An die Haare des kleinen Prinzen"], "correct": 2},
                {"id": "pp_p20_q2", "difficulty": "easy", "q": "Womit sieht man das Wesentliche nach dem Geheimnis des Fuchses?", "options": ["Mit dem Herzen", "Mit dem Fernrohr", "Mit beiden Augen"], "correct": 0},
                {"id": "pp_p20_q3", "difficulty": "hard", "q": "Warum ist gerade seine eigene Rose so wichtig und einzigartig?", "options": ["Weil sie viel spitzere und längere Dornen besitzt", "Wegen der liebevollen Zeit, die er ihr geschenkt hat", "Weil sie ganz allein mitten im goldenen Kornfeld wächst"], "correct": 1},
            ],
        },
    },
    # =========================================================================
    # SPREAD 10: P19 (Ch. XXII-XXIV) + P20 (Ch. XXV)
    # =========================================================================
    {
        "page": 21,
        "art_refs": {
            "chapters": "Ch. XXII-XXIV",
            "primary_0300771h": ["0300771h-12.jpg", "0300771h-45.jpg"],
            "ia_1943_leaves": ["n50", "n51", "n52", "n53"],
            "scene_summary": "Fast trains, thirst-quenching pills, and searching the starry desert for a well.",
        },
        "bubble_anchor": make_bubble_anchor(10, 12, "bottom-right", 56),
        "title": {
            "fr": "20. Le Désert et les Étoiles",
            "it": "20. Il Deserto e le Stelle",
            "de": "20. Die Wüste und die Sterne",
            "en": "20. Desert Under the Stars",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Ce qui embellit le désert, c'est qu'il cache un puits...",
            "it": "Ciò che rende bello il deserto è che nasconde un pozzo!",
            "de": "Die Wüste ist so schön, weil sie irgendwo einen Brunnen birgt!",
            "en": "What makes the desert beautiful is that it hides a well!",
        },
        "seby": {
            "fr": "Il fait très soif dans le grand désert. Sous les étoiles, les amis cherchent un puits.",
            "it": "Fa molta sete nel grande deserto. Sotto le stelle luminose, i due amici cercano un pozzo.",
            "de": "In der großen Wüste haben beide großen Durst. Unter den hellen Sternen suchen die Freunde einen Brunnen.",
            "en": "Both friends feel very thirsty in the desert. Beneath the stars, they seek a hidden well.",
        },
        "ale": {
            "fr": "Les hommes courent dans des trains rapides sans savoir ce qu'ils cherchent. Dans la nuit du désert, l'aviateur assoiffé marche avec le petit prince vers l'eau cachée.",
            "it": "Gli uomini viaggiano su treni veloci senza sapere che cosa cercano davvero. Nella notte silenziosa del deserto, il pilota assetato cammina accanto al piccolo principe in cerca di un pozzo.",
            "de": "Die Erwachsenen rasen in schnellen Zügen vorbei und jagen unnötigen Dingen nach. In der klaren Wüstennacht brechen der durstige Pilot und der kleine Prinz gemeinsam zur Brunnensuche auf.",
            "en": "Grown-ups rush aboard express trains without knowing what they seek. Through the quiet starry desert night, the thirsty pilot and the little prince walk together towards a hidden well.",
        },
        "emma": {
            "fr": "«Les enfants seuls savent ce qu'ils cherchent», fit le petit prince. La nuit tomba, et les étoiles commencèrent de s'éclairer dans l'immensité du désert. «Ce qui embellit le désert», dit le petit prince, «c'est qu'il cache un puits quelque part...» «Ce qui fait leur beauté est invisible!»",
            "it": "«Solo i bambini sanno che cosa cercano», disse il piccolo principe. Scese la notte e le stelle cominciarono a illuminarsi nell'immensità del deserto. «Ciò che abbellisce il deserto», disse il piccolo principe, «è che nasconde un pozzo da qualche parte...» «Ciò che li rende belli è invisibile!»",
            "de": "«Nur die Kinder wissen, wonach sie suchen», sagte der kleine Prinz. Die Nacht brach herein, und die Sterne begannen in der weiten Wüste zu leuchten. «Was die Wüste so schön macht, ist, dass sie irgendwo einen Brunnen verbirgt...» «Was ihnen Schönheit gibt, bleibt unsichtbar!»",
            "en": "\"Only children know what they are looking for,\" said the little prince. Night fell, and the stars began to shine across the vast desert. \"What makes the desert beautiful,\" said the prince, \"is that it hides a well... What gives them beauty is invisible!\"",
        },
        "questions": None,
    },
    {
        "page": 22,
        "art_refs": {
            "chapters": "Ch. XXV",
            "primary_0300771h": ["0300771h-38.jpg"],
            "ia_1943_leaves": ["n54"],
            "scene_summary": "The desert well with singing pulley, rope, and cool water at dawn.",
        },
        "bubble_anchor": make_bubble_anchor(8, 36, "bottom-right", 54),
        "title": {
            "fr": "21. Le Puits qui Chante",
            "it": "21. Il Pozzo che Canta",
            "de": "21. Der singende Brunnen",
            "en": "21. The Singing Well",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Les yeux sont aveugles. Il faut chercher avec le cœur.",
            "it": "Gli occhi sono ciechi. Bisogna cercare col cuore.",
            "de": "Die Augen sind blind. Man muss mit dem Herzen suchen.",
            "en": "The eyes are blind. One must look with the heart.",
        },
        "seby": {
            "fr": "À l'aube, ils trouvent un puits qui chante. L'eau fraîche est douce comme un cadeau.",
            "it": "All'alba trovano un vecchio pozzo che canta. L'acqua fresca sembra un bel regalo per il cuore.",
            "de": "Am Morgen finden sie einen singenden Brunnen. Das kühle Wasser schmeckt süß wie ein schönes Geschenk.",
            "en": "At dawn they discover a singing well. Its cool water tastes sweet like a lovely gift.",
        },
        "ale": {
            "fr": "Au lever du jour apparaît un vrai puits de village. Quand le pilote hisse le seau lourd, la poulie chante doucement, et cette eau fraîche réchauffe le cœur comme une fête.",
            "it": "Allo spuntare dell'alba trovano un vero pozzo nel deserto. Mentre il pilota tira su il secchio pesante, la carrucola canta dolcemente e l'acqua fresca ristora il cuore come una festa.",
            "de": "Bei Tagesanbruch stoßen sie endlich auf einen echten Dorfbrunnen. Als der Pilot den schweren Eimer aus der Tiefe hochzieht, singt die rostige Rolle leise, und das kühle Wasser erquickt beide.",
            "en": "At daybreak they discover a real village well in the sand. As the pilot hauls up the heavy bucket, the old pulley sings softly, and the cool water feels like a festive gift.",
        },
        "emma": {
            "fr": "«Tu entends», dit le petit prince, «nous réveillons ce puits et il chante...» Cette eau était née de la marche sous les étoiles, du chant de la poulie, de l'effort de mes bras. Elle était bonne pour le cœur. «Les yeux sont aveugles. Il faut chercher avec le cœur.»",
            "it": "«Senti», disse il piccolo principe, «noi svegliamo questo pozzo e lui canta...» Quest'acqua era nata dal cammino sotto le stelle, dal canto della carrucola, dallo sforzo delle mie braccia. Faceva bene al cuore. «Gli occhi sono ciechi. Bisogna cercare con il cuore.»",
            "de": "«Hörst du», sagte der kleine Prinz, «wir wecken diesen Brunnen auf und er singt...» Dieses Wasser war entstanden aus dem Marsch unter Sternen, dem Lied der Rolle und der Mühe meiner Arme. Es tat dem Herzen wohl. «Die Augen sind blind. Man muss mit dem Herzen suchen.»",
            "en": "\"Do you hear,\" said the little prince, \"we have wakened this well, and it is singing...\" This water was born of the walk beneath the stars, the song of the pulley, and the effort of my arms. It was good for the heart. \"Eyes are blind; look with the heart.\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p22_q1", "difficulty": "easy", "q": "Que cache le désert pour le rendre si beau selon le petit prince ?", "options": ["Un puits caché quelque part", "Un jardin de grands baobabs", "Une gare de trains rapides"], "correct": 0},
                {"id": "pp_p22_q2", "difficulty": "easy", "q": "Quel bruit fait la vieille poulie quand le pilote tire l'eau du puits ?", "options": ["Elle sonne comme une trompette", "Elle chante doucement", "Elle reste tout à fait muette"], "correct": 1},
                {"id": "pp_p22_q3", "difficulty": "hard", "q": "Pourquoi l'eau du puits est-elle si bonne pour le cœur selon le narrateur ?", "options": ["Parce qu'elle coûte très cher à tous les voyageurs pressés", "Parce qu'elle sort d'une pilule magique contre la grande soif", "Parce qu'elle vient de la marche et de l'effort sous les étoiles"], "correct": 2},
            ],
            "it": [
                {"id": "pp_p22_q1", "difficulty": "easy", "q": "Che cosa nasconde il deserto per essere così bello secondo il piccolo principe?", "options": ["Un pozzo nascosto da qualche parte", "Un giardino con grandi baobab", "Una stazione di treni veloci"], "correct": 0},
                {"id": "pp_p22_q2", "difficulty": "easy", "q": "Che suono fa la carrucola quando il pilota tira su l'acqua dal pozzo?", "options": ["Suona come una grande tromba", "Canta dolcemente", "Resta del tutto muta"], "correct": 1},
                {"id": "pp_p22_q3", "difficulty": "hard", "q": "Perché quell'acqua sembra un dono prezioso per il cuore?", "options": ["Perché costa molto denaro ai viaggiatori stanchi del viaggio", "Perché esce da una scatola magica contro la grande sete", "Perché nasce dal cammino e dalla fatica sotto le stelle"], "correct": 2},
            ],
            "de": [
                {"id": "pp_p22_q1", "difficulty": "easy", "q": "Was verbirgt die Wüste, damit sie laut dem kleinen Prinzen so schön ist?", "options": ["Irgendwo einen tiefen Brunnen", "Einen Wald voller Affenbrotbäume", "Einen großen Schnellzugbahnhof"], "correct": 0},
                {"id": "pp_p22_q2", "difficulty": "easy", "q": "Welches Geräusch macht die alte Brunnenrolle beim Hochziehen des Eimers?", "options": ["Sie klingelt wie ein heller Wecker", "Sie singt ganz leise", "Sie bleibt völlig stumm"], "correct": 1},
                {"id": "pp_p22_q3", "difficulty": "hard", "q": "Warum tut dieses Wasser dem Herzen wie ein Geschenk wohl?", "options": ["Weil es auf einem großen Markt sehr viel Geld kostet", "Weil es aus einer winzigen Durstpille gemacht wurde", "Weil es aus dem gemeinsamen Weg unter Sternen entstand"], "correct": 2},
            ],
        },
    },
    # =========================================================================
    # SPREAD 11: P21 (Ch. XXVI Part 1) + P22 (Ch. XXVI Part 2)
    # =========================================================================
    {
        "page": 23,
        "art_refs": {
            "chapters": "Ch. XXVI (Part 1)",
            "primary_0300771h": ["0300771h-39.jpg", "0300771h-40.jpg"],
            "ia_1943_leaves": ["n57", "n61"],
            "scene_summary": "Ruined stone wall by the well and the yellow snake one year after arrival.",
        },
        "bubble_anchor": make_bubble_anchor(10, 12, "bottom-center", 56),
        "title": {
            "fr": "22. Le Vieux Mur de Pierre",
            "it": "22. Il Vecchio Muro di Pietra",
            "de": "22. Die alte Steinmauer",
            "en": "22. The Old Stone Wall",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Cette nuit, ça fera un an que je suis arrivé sur Terre.",
            "it": "Stanotte farà un anno esatto che sono arrivato sulla Terra.",
            "de": "Heute Nacht jährt sich meine Ankunft auf der Erde genau.",
            "en": "Tonight, it will be one whole year since I landed.",
        },
        "seby": {
            "fr": "Près d'un vieux mur en pierre, le prince se souvient de son étoile dans le ciel.",
            "it": "Vicino a un vecchio muro di pietra, il principe guarda la sua stella alta nel cielo.",
            "de": "An einer alten Mauer sitzt der Prinz allein. Sein eigener Stern leuchtet hoch am Himmel.",
            "en": "Beside a ruined stone wall, the prince gazes at his bright star in the sky.",
        },
        "ale": {
            "fr": "Près du puits se trouve une ruine de mur en pierre. Le petit prince annonce doucement au pilote réparant son avion que son étoile brillera juste au-dessus cette nuit.",
            "it": "Accanto al pozzo sorge un vecchio muro di pietra. Quando il pilota ripara il motore dell'aereo, il piccolo principe annuncia commosso che proprio stanotte la sua stella sarà sopra di loro.",
            "de": "Neben dem Brunnen steht eine alte verfallene Steinmauer. Als der Pilot seinen Motor repariert, flüstert der kleine Prinz ihm leise zu: Genau heute Nacht steht sein Stern wieder hoch über ihm.",
            "en": "Beside the well stands the ruin of an old stone wall. While the pilot finishes repairing his aeroplane engine, the prince whispers gently that his star will shine right above tonight.",
        },
        "emma": {
            "fr": "Il y avait, à côté du puits, une ruine de vieux mur de pierre. Il était là, dressé vers le petit prince, un de ces serpents jaunes qui vous exécutent en trente secondes. «Cette nuit, ça fera un an. Mon étoile se trouvera juste au-dessus de l'endroit où je suis tombé...»",
            "it": "C'era, accanto al pozzo, il rudere di un vecchio muro di pietra. Proprio lì stava dritto verso il piccolo principe uno di quei serpenti gialli che ti uccidono in trenta secondi. «Stanotte sarà passato un anno. La mia stella si troverà proprio sopra il punto dove sono caduto...»",
            "de": "Neben dem Brunnen stand die Ruine einer alten Steinmauer. Dort richtete sich vor dem kleinen Prinzen eine jener gelben Schlangen auf, die in dreißig Sekunden töten. «Heute Nacht wird es ein Jahr her sein. Mein Stern steht genau über der Stelle, wo ich ankam...»",
            "en": "Beside the well stood the ruin of an old stone wall. Coiled upright there, facing the little prince, was one of those yellow snakes that take your life in thirty seconds. \"Tonight it will be a whole year. My star will stand right above the spot where I fell...\"",
        },
        "questions": None,
    },
    {
        "page": 24,
        "art_refs": {
            "chapters": "Ch. XXVI (Part 2)",
            "primary_0300771h": ["0300771h-41.jpg"],
            "ia_1943_leaves": ["n61", "n62"],
            "scene_summary": "The gift of laughing stars like five hundred million little bells.",
        },
        "bubble_anchor": make_bubble_anchor(8, 38, "bottom-center", 56),
        "title": {
            "fr": "23. Les Étoiles qui Rient",
            "it": "23. Le Stelle che Ridono",
            "de": "23. Die lachenden Sterne",
            "en": "23. The Laughing Stars",
        },
        "speech_bubble": {
            "speaker": "Le Petit Prince",
            "fr": "Tu auras, toi, des étoiles qui savent rire!",
            "it": "Tu avrai, solo tu, delle stelle che sanno ridere!",
            "de": "Du wirst Sterne haben, die wunderbar lachen können!",
            "en": "You alone will have stars that know how to laugh!",
        },
        "seby": {
            "fr": "Le prince rira depuis son étoile: la nuit, toutes les étoiles riront comme des grelots.",
            "it": "Il principe riderà dalla sua stella: di notte tutte le stelle rideranno come piccoli sonagli.",
            "de": "Der Prinz lacht bald auf seinem Stern: Nachts klingen alle Sterne wie kleine goldene Glöckchen.",
            "en": "The prince will laugh from his star: at night, every star will laugh like bells.",
        },
        "ale": {
            "fr": "Pour consoler son ami avant de partir, le prince lui fait un cadeau merveilleux: parce qu'il rira sur l'une d'elles, toutes les étoiles riront pour lui la nuit.",
            "it": "Per consolare l'amico prima di tornare, il principe gli fa un dono meraviglioso: poiché riderà su una di esse, tutte le stelle rideranno come piccoli campanelli.",
            "de": "Zum Abschied macht der kleine Prinz seinem Freund ein wunderbares Geschenk: Weil er auf einem der Sterne wohnt und lacht, werden nachts alle Sterne wie Glöckchen lachen.",
            "en": "To comfort his friend before returning home, the prince gives a marvellous gift: since he will laugh on one of the stars, every star will laugh like bells.",
        },
        "emma": {
            "fr": "«Quand tu regarderas le ciel, la nuit, puisque j'habiterai dans l'une d'elles, puisque je rirai dans l'une d'elles, alors ce sera pour toi comme si riaient toutes les étoiles.» «Ce sera comme si je t'avais donné... des tas de petits grelots qui savent rire...»",
            "it": "«Quando guarderai il cielo nella notte, poiché io abiterò in una di quelle stelle e riderò proprio in una di esse, allora sarà per te come se ridessero insieme tutte le stelle.» «Sarà come se ti avessi donato tanti piccoli sonagli d'oro che sanno ridere...»",
            "de": "«Wenn du nachts in den Himmel schaust, wird es für dich sein, als lachten alle Sterne, weil ich auf einem von ihnen wohne und auf einem von ihnen lache.» «Es wird sein, als hätte ich dir viele kleine Glöckchen geschenkt, die so fröhlich lachen können...»",
            "en": "\"When you look at the night sky, since I shall be living on one of those stars, since I shall be laughing on one of them, it will be as if all the stars laughed for you.\" \"It will be as if I had given you swarms of little golden bells that truly laugh...\"",
        },
        "questions": {
            "fr": [
                {"id": "pp_p24_q1", "difficulty": "easy", "q": "Quel anniversaire spécial a lieu cette nuit-là dans le désert ?", "options": ["Cela fait dix ans que le puits est à sec", "Cela fait un an que le prince est sur Terre", "C'est le premier matin chaud du printemps"], "correct": 1},
                {"id": "pp_p24_q2", "difficulty": "easy", "q": "À quoi ressembleront les étoiles pour le pilote après le départ du prince ?", "options": ["À de petits grains de sable chaud", "À de grands avions en papier blanc", "À des grelots qui savent rire"], "correct": 2},
                {"id": "pp_p24_q3", "difficulty": "hard", "q": "Pourquoi toutes les étoiles sembleront-elles rire quand l'aviateur regardera le ciel ?", "options": ["Parce que le prince vit et rit sur l'une d'elles", "Parce que le renard roux chante fort dans le désert", "Parce que la rose éclaire la lune toute la nuit"], "correct": 0},
            ],
            "it": [
                {"id": "pp_p24_q1", "difficulty": "easy", "q": "Quale anniversario speciale cade proprio quella notte nel deserto?", "options": ["Sono passati dieci anni da quel giorno", "È passato un anno dall'arrivo sulla Terra", "È il primo giorno caldo di primavera"], "correct": 1},
                {"id": "pp_p24_q2", "difficulty": "easy", "q": "A che cosa assomiglieranno le stelle per il pilota dopo la partenza?", "options": ["A piccoli granelli di sabbia chiara", "A grandi aeroplani bianchi di carta", "A tanti sonagli che sanno ridere"], "correct": 2},
                {"id": "pp_p24_q3", "difficulty": "hard", "q": "Perché tutte le stelle sembreranno ridere al pilota quando guarderà il cielo?", "options": ["Perché il piccolo principe vive e ride su una di esse", "Perché la volpe rossa canta felice nel grande deserto", "Perché la sua rosa illumina tutta la luna di notte"], "correct": 0},
            ],
            "de": [
                {"id": "pp_p24_q1", "difficulty": "easy", "q": "Welcher besondere Jahrestag ist in jener Nacht in der Wüste?", "options": ["Vor zehn Jahren trocknete der Brunnen aus", "Vor genau einem Jahr kam er auf die Erde", "Es ist der erste helle Tag im Frühling"], "correct": 1},
                {"id": "pp_p24_q2", "difficulty": "easy", "q": "Woran werden die Sterne den Piloten nach dem Abschied erinnern?", "options": ["An graue Sandkörner in der Wüste", "An große weiße Papierflugzeuge", "An kleine Glöckchen, die lachen"], "correct": 2},
                {"id": "pp_p24_q3", "difficulty": "hard", "q": "Warum lachen scheinbar alle Sterne am Himmel für den Piloten?", "options": ["Weil der kleine Prinz auf einem von ihnen wohnt und lacht", "Weil der kluge Fuchs nachts in der weiten Wüste singt", "Weil seine stolze Rose die ganze Nacht über hell leuchtet"], "correct": 0},
            ],
        },
    },
    # =========================================================================
    # SPREAD 12: P23 (Ch. XXVI-XXVII) + P24 (Ch. XXVII Epilogue)
    # =========================================================================
    {
        "page": 25,
        "art_refs": {
            "chapters": "Ch. XXVI-XXVII",
            "primary_0300771h": ["0300771h-45.jpg"],
            "ia_1943_leaves": ["n63"],
            "scene_summary": "Gentle return to B 612 at dawn and remembering the muzzle leather strap.",
        },
        "bubble_anchor": make_bubble_anchor(26, 12, "bottom-left", 56),
        "title": {
            "fr": "24. Le Doux Retour et la Muselière",
            "it": "24. Il Ritorno e la Museruola",
            "de": "24. Die Rückkehr und der Maulkorb",
            "en": "24. Gentle Return and Muzzle",
        },
        "speech_bubble": {
            "speaker": "Le Narrateur (L'Aviateur)",
            "fr": "J'ai oublié d'ajouter la courroie de cuir à la muselière!",
            "it": "Ho dimenticato la cinghia di cuoio per la museruola!",
            "de": "Ich vergaß den Lederriemen am Maulkorb für das Schaf!",
            "en": "I forgot to draw the leather strap on the muzzle!",
        },
        "seby": {
            "fr": "Le matin, le petit prince est parti chez sa fleur. Le pilote s'inquiète pour la muselière du mouton.",
            "it": "Al mattino il piccolo principe è tornato dal suo fiore. Il pilota si preoccupa per la museruola della pecora.",
            "de": "Morgens kehrt der kleine Prinz zu seiner Blume zurück. Der Pilot sorgt sich um den Maulkorb des Schafes.",
            "en": "By morning the little prince has gone back to his flower. The pilot worries about the sheep's muzzle.",
        },
        "ale": {
            "fr": "Le petit prince est retourné doucement sur sa planète, car au lever du jour le pilote ne retrouve plus son corps. Mais il a oublié la courroie pour la muselière du mouton!",
            "it": "Il piccolo principe è tornato leggero sul suo asteroide, perché all'alba l'aviatore non trova più il suo corpo. Però si accorge di aver dimenticato la cinghia di cuoio della museruola!",
            "de": "Am frühen Morgen kehrt der kleine Prinz leise zu seinem Stern und seiner Rose zurück. Doch plötzlich erschrickt der Pilot: Am gezeichneten Maulkorb fehlt der Lederriemen für das kleine Schaf!",
            "en": "The little prince returned gently to his tiny star, for at daybreak his body was gone. Yet suddenly the pilot realises he forgot to draw the leather strap on the sheep's muzzle!",
        },
        "emma": {
            "fr": "Il tomba doucement comme tombe un arbre. Ça ne fit même pas de bruit, à cause du sable. Au lever du jour, je n'ai pas retrouvé son corps. Mais la muselière que j'ai dessinée, j'ai oublié d'y ajouter la courroie de cuir! Alors les grelots se changent en larmes!...",
            "it": "Cadde dolcemente come cade un albero. Non fece neppure rumore, per via della sabbia. Allo spuntare del giorno non ritrovai il suo corpo. Ma alla museruola che ho disegnato ho dimenticato di aggiungere la cinghia di cuoio! Allora tutti i sonagli si trasformano in lacrime!...",
            "de": "Er fiel ganz sanft, wie ein Baum fällt. Wegen des Sandes gab es nicht einmal ein Geräusch. Bei Tagesanbruch fand ich seinen Körper nicht mehr. Doch an dem Maulkorb, den ich zeichnete, vergaß ich den Lederriemen! Da verwandeln sich alle Glöckchen in stille Tränen!...",
            "en": "He fell as gently as a tree falls. There was not even any sound, because of the sand. At daybreak I could not find his body anywhere. But on the muzzle I drew for the sheep, I forgot to add the leather strap! So all the little bells turn into tears!...",
        },
        "questions": None,
    },
    {
        "page": 26,
        "art_refs": {
            "chapters": "Ch. XXVII (Epilogue)",
            "primary_0300771h": ["0300771h-42.jpg"],
            "ia_1943_leaves": ["n63", "n64"],
            "scene_summary": "Epilogue: Two desert lines and one bright star above.",
        },
        "bubble_anchor": make_bubble_anchor(14, 40, "bottom-center", 58),
        "title": {
            "fr": "25. Sous l'Étoile du Désert",
            "it": "25. Sotto la Stella del Deserto",
            "de": "25. Unter dem Stern der Wüste",
            "en": "25. Beneath the Desert Star",
        },
        "speech_bubble": {
            "speaker": "Le Narrateur (L'Aviateur)",
            "fr": "Ne me laissez pas tellement triste: écrivez-moi vite qu'il est revenu...",
            "it": "Non lasciatemi così triste: scrivetemi presto che è tornato...",
            "de": "Lasst mich nicht so traurig: schreibt mir schnell, dass er zurück ist...",
            "en": "Do not leave me so sad: write quickly that he has come back...",
        },
        "seby": {
            "fr": "Regardez ce paysage triste et beau: le prince y a disparu. S'il revient, écrivez-moi vite!",
            "it": "Guardate questo paesaggio bello e triste: qui il principe è scomparso. Se torna, scrivetemi subito!",
            "de": "Schaut dieses schöne und traurige Bild an: Hier verschwand er. Wenn er wiederkommt, schreibt mir!",
            "en": "Look at this lovely, sad landscape where he vanished. If he comes back, write to me straight away!",
        },
        "ale": {
            "fr": "Voici le plus beau et le plus triste paysage du monde, où le petit prince a apparu puis disparu. Si vous passez dans le désert, attendez sous l'étoile et écrivez-moi vite!",
            "it": "Ecco il più bello e il più triste paesaggio del mondo, dove il piccolo principe è apparso e scomparso. Se passate nel deserto, aspettate sotto la stella e scrivetemi subito!",
            "de": "Hier ist die schönste und traurigste Landschaft der Welt, wo der kleine Prinz erschien und verschwand. Wenn ihr durch die Wüste reist, wartet unter dem Stern und schreibt mir schnell!",
            "en": "Here is the loveliest and saddest landscape in the world, where the little prince appeared and vanished. If you cross the desert, wait beneath the star and write quickly!",
        },
        "emma": {
            "fr": "C'est ici que le petit prince a apparu sur terre, puis disparu. Regardez attentivement ce paysage afin de le reconnaître si vous voyagez dans le désert, et attendez juste sous l'étoile! Alors soyez gentils! Ne me laissez pas triste: écrivez-moi vite qu'il est revenu...",
            "it": "È qui che il piccolo principe è apparso sulla terra, e poi scomparso. Guardate attentamente questo paesaggio per riconoscerlo se viaggiate nel deserto, e aspettate proprio sotto la stella! Allora siate gentili! Non lasciatemi così triste: scrivetemi presto che è tornato...",
            "de": "Hier ist der kleine Prinz auf der Erde erschienen und dann wieder verschwunden. Schaut euch diese Landschaft aufmerksam an, wenn ihr durch die Wüste reist, und wartet unter dem Stern! Seid so gut und lasst mich nicht traurig: Schreibt mir schnell, dass er zurückgekehrt ist...",
            "en": "It is here that the little prince appeared on Earth, and then vanished. Look at this landscape carefully so that you will recognise it if you travel in the desert, and wait beneath the star! Then please be kind! Do not leave me so sad: write quickly that he has come back...",
        },
        "questions": {
            "fr": [
                {"id": "pp_p26_q1", "difficulty": "easy", "q": "Qu'est-ce que le pilote a oublié de dessiner sur la muselière du mouton ?", "options": ["Trois trous pour respirer", "Deux grandes cornes grises", "La courroie de cuir"], "correct": 2},
                {"id": "pp_p26_q2", "difficulty": "easy", "q": "Que demande le narrateur aux lecteurs qui voyageront un jour dans le désert ?", "options": ["De lui écrire vite si le prince revient", "De cueillir cinq mille roses rouges", "De compter tous les grands baobabs"], "correct": 0},
                {"id": "pp_p26_q3", "difficulty": "hard", "q": "Pourquoi le dernier dessin du livre est-il à la fois le plus beau et le plus triste ?", "options": ["Parce que l'avion du pilote est tombé au fond de la mer", "Parce que le petit prince y est apparu puis a disparu", "Parce qu'il n'y a aucune étoile brillante dans le ciel"], "correct": 1},
            ],
            "it": [
                {"id": "pp_p26_q1", "difficulty": "easy", "q": "Che cosa ha dimenticato di disegnare il pilota sulla museruola della pecora?", "options": ["Tre fori per respirare", "Due lunghe corna grigie", "La cinghia di cuoio"], "correct": 2},
                {"id": "pp_p26_q2", "difficulty": "easy", "q": "Che cosa chiede il narratore ai lettori che viaggeranno un giorno nel deserto?", "options": ["Di scrivergli subito se il principe torna", "Di raccogliere cinquemila rose rosse", "Di contare tutti i grandi baobab"], "correct": 0},
                {"id": "pp_p26_q3", "difficulty": "hard", "q": "Perché l'ultimo disegno del libro è insieme il più bello e il più triste del mondo?", "options": ["Perché l'aereo del pilota è caduto in mezzo al mare", "Perché lì il piccolo principe è apparso e scomparso", "Perché non c'è nessuna stella luminosa nel cielo"], "correct": 1},
            ],
            "de": [
                {"id": "pp_p26_q1", "difficulty": "easy", "q": "Was hat der Pilot auf der Zeichnung des Maulkorbs vergessen?", "options": ["Drei kleine Luftlöcher", "Zwei große graue Hörner", "Den Lederriemen"], "correct": 2},
                {"id": "pp_p26_q2", "difficulty": "easy", "q": "Worum bittet der Erzähler am Ende alle Leserinnen und Leser?", "options": ["Ihm schnell zu schreiben, falls der Prinz wiederkommt", "Fünftausend schöne rote Rosen im Garten zu pflücken", "Alle großen Affenbrotbäume in der Wüste zu zählen"], "correct": 0},
                {"id": "pp_p26_q3", "difficulty": "hard", "q": "Warum ist das letzte Bild für den Erzähler zugleich die schönste und traurigste Landschaft?", "options": ["Weil das alte Flugzeug des Piloten tief ins Meer fiel", "Weil dort der kleine Prinz erschien und verschwand", "Weil über dem Wüstensand kein einziger Stern scheint"], "correct": 1},
            ],
        },
    },
])


# =============================================================================
# CURATED MONTESSORI LEXICONS (ZERO NAIVE SUFFIX GUESSING)
# =============================================================================
# Format:
#   FR_LEXICON / IT_LEXICON: lemma -> (pos, gender_or_None, number_or_None)
#   DE_LEXICON: lemma -> (pos, number_or_None)   [NEVER gender on DE tokens]

FR_NOUNS_META = {
    "actes": ("m", "p"), "activité": ("f", "s"), "adieu": ("m", "s"), "adultes": ("m", "p"),
    "allumeur": ("m", "s"), "ami": ("m", "s"), "amis": ("m", "p"), "amour": ("m", "s"), "animal": ("m", "s"),
    "an": ("m", "s"), "anneau": ("m", "s"), "ans": ("m", "p"), "arbre": ("m", "s"),
    "ascension": ("f", "s"), "astronome": ("m", "s"), "astéroïde": ("m", "s"), "aube": ("f", "s"),
    "autorité": ("f", "s"), "aviateur": ("m", "s"), "avion": ("m", "s"),
    "baobabs": ("m", "p"), "beauté": ("f", "s"), "blé": ("m", "s"), "boa": ("m", "s"), "boas": ("m", "p"),
    "bouteilles": ("f", "p"), "bras": ("m", "p"), "bruit": ("m", "s"), "bureau": ("m", "s"),
    "businessman": ("m", "s"), "buveur": ("m", "s"), "cadeau": ("m", "s"), "caisse": ("f", "s"),
    "cause": ("f", "s"), "chaise": ("f", "s"), "champ": ("m", "s"), "chant": ("m", "s"), "chapeau": ("m", "s"), "cheveux": ("m", "p"),
    "chiffres": ("m", "p"), "chose": ("f", "s"), "choses": ("f", "p"), "ciel": ("m", "s"),
    "collines": ("f", "p"), "compliments": ("m", "p"), "conseil": ("m", "s"), "corps": ("m", "s"), "costume": ("m", "s"),
    "couchers": ("m", "p"), "couleur": ("f", "s"), "couleurs": ("f", "p"), "courroie": ("f", "s"),
    "crépuscule": ("m", "s"), "cuir": ("m", "s"), "côté": ("m", "s"), "cœur": ("m", "s"),
    "dessin": ("m", "s"), "dessins": ("m", "p"), "discipline": ("f", "s"), "départ": ("m", "s"),
    "désert": ("m", "s"), "eau": ("f", "s"), "effort": ("m", "s"), "endroit": ("m", "s"),
    "enfant": ("m", "s"), "enfants": ("m", "p"), "explications": ("f", "p"), "fauve": ("m", "s"),
    "fidélité": ("f", "s"), "fleur": ("f", "s"), "fleurs": ("f", "p"), "fleuves": ("m", "p"),
    "fois": ("f", "s"), "forêt": ("f", "s"), "fête": ("f", "s"), "garçon": ("m", "s"), "globe": ("m", "s"),
    "graines": ("f", "p"), "grelots": ("m", "p"), "géographe": ("m", "s"), "géographies": ("f", "p"),
    "herbe": ("f", "s"), "hermine": ("f", "s"), "histoires": ("f", "p"), "heures": ("f", "p"), "homme": ("m", "s"),
    "hommes": ("m", "p"), "honte": ("f", "s"), "image": ("f", "s"), "imagination": ("f", "s"),
    "immensité": ("f", "s"), "jardin": ("m", "s"), "jour": ("m", "s"), "larmes": ("f", "p"),
    "liens": ("m", "p"), "livre": ("m", "s"), "livres": ("m", "p"), "louanges": ("f", "p"),
    "lune": ("f", "s"), "maison": ("f", "s"), "manteau": ("m", "s"),
    "matin": ("m", "s"), "mers": ("f", "p"), "migration": ("f", "s"), "millions": ("m", "p"),
    "minute": ("f", "s"), "mois": ("m", "p"), "monde": ("m", "s"), "monsieur": ("m", "s"), "montagne": ("f", "s"),
    "montagnes": ("f", "p"), "mots": ("m", "p"), "mouton": ("m", "s"), "mur": ("m", "s"),
    "muselière": ("f", "s"), "narrateur": ("m", "s"), "nombres": ("m", "p"), "nuit": ("f", "s"),
    "occupation": ("f", "s"), "oiseaux": ("m", "p"), "ombre": ("f", "s"), "or": ("m", "s"),
    "ordres": ("m", "p"), "panne": ("f", "s"), "papier": ("m", "s"), "papillons": ("m", "p"),
    "paravent": ("m", "s"), "part": ("f", "s"), "patience": ("f", "s"), "paysage": ("m", "s"),
    "personnes": ("f", "p"), "peur": ("f", "s"), "pierre": ("f", "s"),
    "pilote": ("m", "s"), "place": ("f", "s"), "planète": ("f", "s"), "pommier": ("m", "s"),
    "poulie": ("f", "s"), "pourpre": ("f", "s"), "proie": ("f", "s"), "prince": ("m", "s"), "puits": ("m", "s"),
    "pétales": ("m", "p"), "question": ("f", "s"), "racines": ("f", "p"), "raison": ("f", "s"),
    "raisons": ("f", "p"), "renard": ("m", "s"), "repas": ("m", "s"), "repos": ("m", "s"), "rites": ("m", "p"),
    "roi": ("m", "s"), "rose": ("f", "s"), "roses": ("f", "p"), "route": ("f", "s"),
    "ruine": ("f", "s"), "réverbère": ("m", "s"), "réverbères": ("m", "p"), "sable": ("m", "s"),
    "sahara": ("m", "s"), "savant": ("m", "s"), "seau": ("m", "s"), "seconde": ("f", "s"),
    "secondes": ("f", "p"), "secret": ("m", "s"), "sens": ("m", "s"), "serpent": ("m", "s"),
    "serpents": ("m", "p"), "silence": ("m", "s"), "soif": ("f", "s"), "soin": ("m", "s"),
    "soir": ("m", "s"), "soleil": ("m", "s"), "souverain": ("m", "s"), "sujet": ("m", "s"), "tas": ("m", "p"),
    "temps": ("m", "s"), "terre": ("f", "s"), "toilette": ("f", "s"), "train": ("m", "s"), "trains": ("m", "p"),
    "travail": ("m", "s"), "trous": ("m", "p"), "trône": ("m", "s"), "télescope": ("m", "s"), "tête": ("f", "s"),
    "univers": ("m", "s"), "vaniteux": ("m", "s"), "vent": ("m", "s"), "verre": ("m", "s"),
    "village": ("m", "s"), "voix": ("f", "s"), "volcan": ("m", "s"), "volcans": ("m", "p"),
    "yeux": ("m", "p"), "écho": ("m", "s"), "éléphant": ("m", "s"), "énigmes": ("f", "p"),
    "étoile": ("f", "s"), "étoiles": ("f", "p"), "évasion": ("f", "s"),
}

FR_ADJS_META = {
    "appelé": ("m", "s"), "apprivoisé": ("m", "s"), "assoiffé": ("m", "s"),
    "autre": ("f", "s"), "aveugles": ("m", "p"), "beau": ("m", "s"), "beaux": ("m", "p"),
    "belle": ("f", "s"), "bizarres": ("f", "p"), "bon": ("m", "s"), "bonne": ("f", "s"),
    "bonnes": ("f", "p"), "cachée": ("f", "s"), "cinquième": ("f", "s"), "couché": ("m", "s"),
    "curieuse": ("f", "s"), "deuxième": ("f", "s"), "doré": ("m", "s"), "douce": ("f", "s"),
    "dressé": ("m", "s"), "drôle": ("f", "s"), "entière": ("f", "s"), "essentiel": ("m", "s"), "fatigant": ("m", "s"),
    "fleuri": ("m", "s"), "fragile": ("f", "s"), "fraîche": ("f", "s"), "gentils": ("m", "p"),
    "grand": ("m", "s"), "grande": ("f", "s"), "grandes": ("f", "p"), "grands": ("m", "p"),
    "gros": ("m", "p"), "habillé": ("m", "s"), "habitée": ("f", "s"), "haute": ("f", "s"),
    "heureux": ("m", "s"), "importante": ("f", "s"), "installé": ("m", "s"), "intitulé": ("m", "s"), "invisible": ("m", "s"),
    "jaunes": ("m", "p"), "jeune": ("m", "s"), "jeunes": ("m", "p"), "joli": ("m", "s"),
    "jolie": ("f", "s"), "lourd": ("m", "s"), "magnifique": ("f", "s"), "majestueux": ("m", "s"),
    "merveilleux": ("m", "s"), "mince": ("m", "s"), "minuscule": ("f", "s"), "mystérieuses": ("f", "p"),
    "occupé": ("m", "s"), "ordinaire": ("f", "s"), "pareilles": ("f", "p"), "patient": ("m", "s"),
    "petit": ("m", "s"), "petite": ("f", "s"), "petits": ("m", "p"), "plein": ("m", "s"),
    "pleines": ("f", "p"), "première": ("f", "s"), "propre": ("f", "s"), "précieux": ("m", "p"),
    "quatrième": ("f", "s"), "raisonnables": ("m", "p"), "rapides": ("m", "p"), "responsable": ("m", "s"),
    "riche": ("m", "s"), "sauvages": ("m", "p"), "semblables": ("f", "p"), "septième": ("f", "s"),
    "seul": ("m", "s"), "seule": ("f", "s"), "seules": ("f", "p"), "seuls": ("m", "p"), "simple": ("m", "s"),
    "sixième": ("f", "s"), "solitaire": ("m", "s"), "suivante": ("f", "s"), "surpris": ("m", "s"),
    "sérieuses": ("f", "p"), "sérieux": ("m", "p"), "terribles": ("f", "p"), "tranquille": ("m", "s"),
    "triste": ("m", "s"), "troisième": ("f", "s"), "trouée": ("f", "s"), "turc": ("m", "s"),
    "unique": ("m", "s"), "utile": ("m", "s"), "vaniteuse": ("f", "s"), "verte": ("f", "s"), "vierge": ("f", "s"),
    "vides": ("f", "p"), "vieux": ("m", "s"), "vrai": ("m", "s"), "vécues": ("f", "p"), "vêtu": ("m", "s"),
    "éteint": ("m", "s"), "éternel": ("m", "s"), "éternelles": ("f", "p"), "étoilée": ("f", "s"),
    "énorme": ("m", "s"), "énormes": ("m", "p"), "éphémères": ("f", "p"),
}

FR_VERBS = {
    "a", "a-t-il", "admira", "admire", "ai", "aime", "aiment", "aimer", "aimerai", "aimée",
    "ajouter", "ajustait", "allonge", "allume", "annonce", "aperçu", "apparaît", "apparu",
    "apparut", "appelée", "applaudit", "apprivoisa", "apprivoise-moi", "apprend", "apprivoiser",
    "arrache", "arracher", "arrive", "arrivé", "arrose", "arrosée", "as", "assit", "assoit",
    "attendez", "atterrit", "aurais", "avais", "avait", "avale", "avalent", "avalait", "avoir", "avoua", "avoue", "boire",
    "bois-tu", "boit", "brillera", "cache", "cassent", "changent", "changer", "chante",
    "cherchent", "chercher", "choisissait", "collectionne", "collectionne-t-il", "commander", "commande", "commence",
    "commencèrent", "comprend", "comprendre", "comprennent", "comprise", "compte", "confie", "connaît",
    "conseilla", "conseille", "consoler", "couche", "coucher", "courent", "couvre", "crie", "croient",
    "croire", "croisé", "croit", "croyais", "créer", "demande", "demandent", "dessine", "dessine-moi",
    "dessinée", "deviendra", "deviennent", "digérait", "digérer", "dire", "disait",
    "disent", "disparu", "dit", "dit-il", "doit", "donne", "donner", "donné", "dorment", "dort", "dut",
    "découvert", "découvre", "découvrit", "déplace", "désirais", "dû", "embaumait", "embellit", "endormi", "enseigne", "entend",
    "entendant", "entendent", "entendre", "entends", "envole", "es", "escalade", "est",
    "exiger", "explique", "exécutent", "faire", "fait", "faut", "fera", "fit", "font",
    "fus", "fut", "glisse", "habillait", "habite", "habiterai", "hisse", "inquiète",
    "inventer", "jouer", "juger", "laisse", "laissez", "lançai", "lever", "lisait", "loger", "lève", "mange", "mâcher",
    "manquent", "marche", "mettrez", "monte", "nettoie", "notons", "née", "occupe", "offre",
    "oublier", "oublié", "parle", "parti", "partir", "passez", "pense", "perdu",
    "peut", "plaît", "pleura", "pleure", "possède", "posséder", "pousse", "poussent",
    "profita", "protège", "prétend", "ramona", "ramone", "reconnaître", "refuse",
    "regardais", "regardera", "regarderas", "regardez", "regrettera", "remarque", "remua",
    "rencontra", "repose", "reprit", "représentait", "reste", "retourné", "retrouve", "retrouvé",
    "revenu", "revient", "revint", "revoir", "revoyant", "riaient", "rira", "rirai", "rire", "riront",
    "réchauffe", "régner", "réparant", "répondent", "répondit", "répète", "répètent",
    "réveille", "réveillons", "réveillé", "révèle", "sais", "salue", "savent", "savoir", "sera",
    "serai", "seras", "sert", "signifie", "siégeait", "soigné", "songea", "songé", "sont", "sort",
    "sourit", "souvenir", "souvient", "soyez", "suffisait", "suffit", "suis", "suit", "suivant", "termine",
    "terminé", "tiens", "tirer", "tomba", "tombe", "tombé", "tourne", "traversa", "trouve",
    "trouvent", "trouvera", "tâche", "venait", "veut", "veux", "vient", "vis", "visiter", "vit",
    "voient", "voir", "voit", "voulais", "voyagez", "voyez", "vu", "éclairait", "éclairer",
    "éclater", "écria", "écrit", "écrivait", "écrivez", "écrivez-moi", "écrivons",
    "épanouit", "étaient", "étais", "était", "été", "être",
}

FR_ADVS = {
    "abord", "afin", "ainsi", "alors", "après", "assez", "attentivement", "aussi", "autour",
    "avant", "bien", "calmement", "cependant", "dedans", "depuis", "donc", "doucement", "dès",
    "décidément", "enfin", "exactement", "ici", "jamais", "juste", "lentement", "loin",
    "là", "maintenant", "moins", "même", "ne", "non", "oui", "où", "pas", "peu", "plus",
    "pourquoi", "pourtant", "près", "puis", "quand", "rien", "seulement", "si", "sinon",
    "soigneusement", "surtout", "tard", "tellement", "toujours", "tout", "trop", "très",
    "vite", "vraiment", "véritablement",
}

FR_OTHER = {
    "1909", "612", "ah", "au", "au-dessus", "aux", "avec", "b", "car", "ce", "celle", "cent",
    "ces", "cet", "cette", "chacun", "chaque", "chez", "cinq", "comme", "dans", "de",
    "des", "deux", "devant", "du", "elle", "elles", "en", "est-ce", "et", "il", "ils", "je", "la",
    "le", "les", "leur", "leurs", "lorsque", "lui", "lui-même", "mais", "me", "mes", "mille", "moi",
    "mon", "nous", "on", "par", "parce", "personne", "pour", "puisque", "quarante-quatre", "quatre",
    "que", "quel", "quelque", "quelques", "qui", "quoi", "sa", "sans", "se", "sept", "ses", "six",
    "son", "sous", "sur", "ta", "te", "toi", "tous", "toute", "toutes", "trente", "trois",
    "tu", "un", "une", "vers", "vingt-deux", "voici", "voilà", "vous", "y", "à", "ça",
}


IT_NOUNS_META = {
    "abito": ("m", "s"), "addio": ("m", "s"), "aereo": ("m", "s"), "affari": ("m", "p"),
    "affetto": ("m", "s"), "agnello": ("m", "s"), "alba": ("f", "s"), "albero": ("m", "s"),
    "amici": ("m", "p"), "amico": ("m", "s"), "amore": ("m", "s"), "anello": ("m", "s"), "animale": ("m", "s"), "anni": ("m", "p"),
    "anno": ("m", "s"), "applausi": ("m", "p"), "asteroide": ("m", "s"), "astronomo": ("m", "s"),
    "attimo": ("m", "s"), "autorità": ("f", "s"), "aviatore": ("m", "s"),
    "bambini": ("m", "p"), "bambino": ("m", "s"), "baobab": ("m", "p"), "bellezza": ("f", "s"),
    "belva": ("f", "s"), "bevitore": ("m", "s"), "bisogno": ("m", "s"), "boa": ("m", "s"),
    "bottiglie": ("f", "p"), "braccia": ("f", "p"), "buchi": ("m", "p"), "calma": ("f", "s"), "cammino": ("m", "s"),
    "campana": ("f", "s"), "campanelli": ("m", "p"), "canto": ("m", "s"), "capelli": ("m", "p"),
    "cappello": ("m", "s"), "carrucola": ("f", "s"), "casa": ("f", "s"), "cassa": ("f", "s"),
    "cielo": ("m", "s"), "cifre": ("f", "p"), "cima": ("f", "s"), "cinghia": ("f", "s"), "collezione": ("f", "s"),
    "color": ("m", "s"), "colori": ("m", "p"), "consiglio": ("m", "s"), "corpo": ("m", "s"), "cosa": ("f", "s"),
    "cose": ("f", "p"), "crepuscolo": ("m", "s"), "cuoio": ("m", "s"), "cuore": ("m", "s"),
    "cura": ("f", "s"), "deserto": ("m", "s"), "disciplina": ("f", "s"), "disegni": ("m", "p"),
    "disegno": ("m", "s"), "dono": ("m", "s"), "dune": ("f", "p"), "eco": ("f", "s"),
    "elefante": ("m", "s"), "erba": ("f", "s"), "ermellino": ("m", "s"), "farfalle": ("f", "p"),
    "fatica": ("f", "s"), "favore": ("m", "s"), "festa": ("f", "s"), "figura": ("f", "s"), "fiore": ("m", "s"), "fiorellino": ("m", "s"),
    "fiori": ("m", "p"), "foglio": ("m", "s"), "foresta": ("f", "s"), "fuga": ("f", "s"), "geografia": ("f", "s"),
    "geografo": ("m", "s"), "germogli": ("m", "p"), "gesti": ("m", "p"), "giardino": ("m", "s"),
    "gioia": ("f", "s"), "giorno": ("m", "s"), "grano": ("m", "s"),
    "guasto": ("m", "s"), "illustrazione": ("f", "s"), "immaginazione": ("f", "s"),
    "immensità": ("f", "s"), "laccio": ("m", "s"), "lacrime": ("f", "p"), "lampionaio": ("m", "s"),
    "lampione": ("m", "s"), "lavoro": ("m", "s"), "legami": ("m", "p"), "libri": ("m", "p"), "libro": ("m", "s"),
    "lodi": ("f", "p"), "luna": ("f", "s"), "malinconia": ("f", "s"), "mani": ("f", "p"),
    "mantello": ("m", "s"), "mari": ("m", "p"), "mattina": ("f", "s"), "mesi": ("m", "p"), "mattino": ("m", "s"),
    "melo": ("m", "s"), "migrazione": ("f", "s"), "milioni": ("m", "p"), "minuto": ("m", "s"),
    "mondo": ("m", "s"), "montagna": ("f", "s"), "montagne": ("f", "p"), "motore": ("m", "s"),
    "muro": ("m", "s"), "museruola": ("f", "s"), "narratore": ("m", "s"), "notte": ("f", "s"), "numeri": ("m", "p"),
    "occhi": ("m", "p"), "occupazione": ("f", "s"), "ordini": ("m", "p"), "oro": ("m", "s"),
    "paesaggio": ("m", "s"), "paravento": ("m", "s"), "parole": ("f", "p"), "parte": ("f", "s"), "pasto": ("m", "s"),
    "partenza": ("f", "s"), "passi": ("m", "p"), "paura": ("f", "s"), "pazienza": ("f", "s"), "pecora": ("f", "s"),
    "pena": ("f", "s"), "petali": ("m", "p"), "pianeta": ("m", "s"), "pietra": ("f", "s"),
    "pilota": ("m", "s"), "pomeriggio": ("m", "s"), "porpora": ("f", "s"), "pozzo": ("m", "s"), "preda": ("f", "s"),
    "principe": ("m", "s"), "pulizia": ("f", "s"), "punto": ("m", "s"), "questione": ("f", "s"),
    "radici": ("f", "p"), "ragione": ("f", "s"), "ragioni": ("f", "p"), "re": ("m", "s"),
    "regalo": ("m", "s"), "riposo": ("m", "s"), "riti": ("m", "p"), "ritorno": ("m", "s"),
    "rosa": ("f", "s"), "rose": ("f", "p"), "rudere": ("m", "s"), "rumore": ("m", "s"),
    "sabbia": ("f", "s"), "sahara": ("m", "s"), "scrittoio": ("m", "s"), "secchio": ("m", "s"),
    "secondi": ("m", "p"), "sedia": ("f", "s"), "segreto": ("m", "s"), "semi": ("m", "p"),
    "senso": ("m", "s"), "sentiero": ("m", "s"), "sera": ("f", "s"), "serpente": ("m", "s"), "serpentello": ("m", "s"),
    "serpenti": ("m", "p"), "sete": ("f", "s"), "sforzo": ("m", "s"), "signore": ("m", "s"),
    "silenzio": ("m", "s"), "sole": ("m", "s"), "sonagli": ("m", "p"), "sovrano": ("m", "s"),
    "spazio": ("m", "s"), "spiegazioni": ("f", "p"), "spighe": ("f", "p"), "stella": ("f", "s"),
    "stelle": ("f", "p"), "storie": ("f", "p"), "strada": ("f", "s"), "suddito": ("m", "s"), "suono": ("m", "s"),
    "telescopio": ("m", "s"), "tempo": ("m", "s"), "terra": ("f", "s"), "testa": ("f", "s"),
    "tramonti": ("m", "p"), "tramonto": ("m", "s"), "treni": ("m", "p"), "trono": ("m", "s"), "ubriacone": ("m", "s"),
    "uccelli": ("m", "p"), "universo": ("m", "s"), "uomo": ("m", "s"), "uomini": ("m", "p"),
    "vanitoso": ("m", "s"), "vento": ("m", "s"), "vergogna": ("f", "s"), "vetro": ("m", "s"), "voce": ("f", "s"),
    "vocina": ("f", "s"), "volpe": ("f", "s"), "volta": ("f", "s"), "volte": ("f", "p"),
    "vulcani": ("m", "p"), "vulcano": ("m", "s"), "acqua": ("f", "s"),
}

IT_ADJS_META = {
    "abitato": ("m", "s"), "addomesticata": ("f", "s"), "alta": ("f", "s"),
    "altro": ("m", "s"), "assetato": ("m", "s"), "attivi": ("m", "p"), "bel": ("m", "s"),
    "bella": ("f", "s"), "belli": ("m", "p"), "bello": ("m", "s"), "bizzarri": ("m", "p"),
    "bravo": ("m", "s"), "buffa": ("f", "s"), "buoni": ("m", "p"),
    "calda": ("f", "s"), "chiamato": ("m", "s"), "ciechi": ("m", "p"), "commosso": ("m", "s"),
    "curioso": ("m", "s"), "deciso": ("m", "s"), "destinati": ("m", "p"),
    "diverso": ("m", "s"), "dorato": ("m", "s"), "dritto": ("m", "s"),
    "effimeri": ("m", "p"), "elegante": ("m", "s"), "enorme": ("m", "s"), "enormi": ("m", "p"),
    "essenziale": ("m", "s"), "eterne": ("f", "p"), "faticoso": ("m", "s"), "felice": ("m", "s"),
    "fiorito": ("m", "s"), "fragile": ("m", "s"), "fresca": ("f", "s"),
    "gentile": ("f", "s"), "gentili": ("m", "p"), "gialli": ("m", "p"), "giganti": ("f", "p"),
    "giovane": ("m", "s"), "giunto": ("m", "s"), "giusto": ("m", "s"), "grande": ("m", "s"), "grandi": ("m", "p"),
    "graziosa": ("f", "s"), "importante": ("f", "s"), "intera": ("f", "s"), "intero": ("m", "s"), "intitolato": ("m", "s"), "invisibile": ("m", "s"),
    "leggero": ("m", "s"), "luminose": ("f", "p"), "maestoso": ("m", "s"), "magnifica": ("f", "s"),
    "meraviglioso": ("m", "s"), "minuscolo": ("m", "s"), "misteriose": ("f", "p"), "molta": ("f", "s"),
    "molti": ("m", "p"), "occupato": ("m", "s"),
    "pazienti": ("m", "p"), "pesante": ("m", "s"), "piccola": ("f", "s"),
    "piccoli": ("m", "p"), "piccolissimo": ("m", "s"), "piccolo": ("m", "s"), "piene": ("f", "p"),
    "pieno": ("m", "s"), "prezioso": ("m", "s"), "primo": ("m", "s"), "profondi": ("m", "p"),
    "propria": ("f", "s"), "qualunque": ("f", "s"), "quarto": ("m", "s"),
    "quinto": ("m", "s"), "ragionevoli": ("m", "p"), "responsabile": ("m", "s"),
    "ricco": ("m", "s"), "riconosciuti": ("m", "p"), "rocciosa": ("f", "s"), "sdraiato": ("m", "s"),
    "secondo": ("m", "s"), "seduto": ("m", "s"), "selvatici": ("m", "p"), "semplice": ("m", "s"),
    "seri": ("m", "p"), "serie": ("f", "p"), "sesto": ("m", "s"), "settimo": ("m", "s"),
    "silenziosa": ("f", "s"), "simili": ("f", "p"), "sola": ("f", "s"), "soli": ("m", "p"),
    "solitaria": ("f", "s"), "solo": ("m", "s"), "sorpreso": ("m", "s"), "sottile": ("m", "s"),
    "spento": ("m", "s"), "stesso": ("m", "s"), "successivo": ("m", "s"), "tanta": ("f", "s"),
    "tanti": ("m", "p"), "terribili": ("m", "p"), "terzo": ("m", "s"),
    "triste": ("m", "s"), "tristi": ("m", "p"), "turco": ("m", "s"), "uguali": ("f", "p"),
    "unica": ("f", "s"), "unico": ("m", "s"), "utile": ("m", "s"), "vanitosi": ("m", "p"),
    "vecchio": ("m", "s"), "veloci": ("m", "p"), "velocissimo": ("m", "s"), "verde": ("f", "s"), "vergine": ("f", "s"), "veri": ("m", "p"), "vero": ("m", "s"),
    "vestito": ("m", "s"), "vissute": ("f", "p"), "vuote": ("f", "p"),
}

IT_VERBS = {
    "abbellisce", "abiterò", "accende", "accorge", "addomesticami", "addomesticare",
    "addomesticò", "addormentata", "adora", "affida", "aggiungere", "alza", "alzò", "amano", "amare", "amerò", "ammira",
    "annotiamo", "annuncia", "appare", "apparso", "apparve", "approfittò", "apre",
    "arriva", "arrivato", "ascolta", "ascoltarono", "aspettate", "atterra", "attraversò", "aver",
    "avessi", "avevo", "avranno", "avrei", "bagna", "basta", "bastava", "battere",
    "battono", "bere", "beve", "bevi", "bisogna", "cadde", "cade", "caduto", "calare", "cambia", "cammina",
    "canta", "capirà", "capirlo", "capisce", "capiscono", "cerca", "cercano", "cercare", "chiede",
    "chiedono", "comandare", "cominciarono", "confessa", "consiglia", "consigliò", "consolare",
    "conta", "copre", "creare", "crede", "credere", "credeva", "credevo", "credono", "crescono", "curato", "confessò",
    "dare", "dedicato", "desideravi", "dice", "diceva", "digerire", "digerisce", "digeriva", "dimenticare",
    "dimenticato", "dire", "disegna", "disegnami", "disegnato", "disse", "dissi", "diventano", "diventare", "diventeranno",
    "donato", "dormono", "dovuto", "dà", "era", "erano", "ero", "esclamare", "esclamò", "esigere", "esplodere", "essere",
    "estirpare", "fa", "faceva", "fanno", "fare", "farà", "fece", "fermatevi", "finita", "fu", "fui",
    "gira", "giocare", "giudicarla", "guarda", "guardando", "guardate", "guardavi", "guarderai",
    "guardò", "ha", "hai", "ho", "illuminarsi", "illuminava", "incontra", "incontrare",
    "incontrato", "incontrò", "indossò", "inghiottiva", "ingoia", "ingoiano", "inizierà", "insegna",
    "lasceranno", "lascia", "lasciatemi", "leggeva", "mancano", "masticarla", "mangia", "metterete", "mosse",
    "nasconde", "nata", "notare", "odono", "ospitare", "parla", "partire", "passate", "passato", "pensa",
    "pensano", "pensato", "perduto", "piange", "piangere", "poggia", "possedere", "possiedo",
    "posso", "poter", "prende", "preoccupa", "profumasse", "profumava", "protegge", "pulisce", "può", "rappresentava", "regnare", "rende",
    "reso", "resta", "riconoscerlo", "ricordare", "ridano", "rideranno", "riderà", "ridere", "riderò",
    "ridessero", "rifiuta", "ripara", "ripensò", "ripete", "ripetere", "ripetono",
    "rispondono", "rispose", "ristora", "ritrovai", "rivedendo", "rivedere", "rompono", "sai", "sale",
    "saluta", "salutarsi", "salì", "sanno", "sapere", "saperla", "sappiano", "sarai",
    "sarà", "sarò", "sboccia", "scala", "scarta", "sceglieva", "scese", "scivola",
    "scomparire", "scomparso", "scoppiò", "scopre", "scoprì", "scrive", "scrivetemi",
    "scriveva", "scriviamo", "sedette", "sedeva", "segue", "seguendo", "sembra", "sembrerà",
    "sentendo", "sente", "senti", "sentirlo", "sia", "siate", "siede", "significa", "sistemava", "solleva",
    "sono", "sorge", "sorride", "spazza", "spazzò", "spegne", "spezzino", "spiega", "sposta",
    "spostare", "spuntare", "stare", "stato", "stava", "strappa", "strappare", "studia",
    "sveglia", "svegliamo", "svegliò", "svela", "teme", "tira", "tirare", "torna", "tornare", "tornato", "tornò",
    "tramontare", "trasformano", "trova", "trovano", "troverà", "uccidono", "vede",
    "vedere", "vedete", "vedono", "veniva", "verrà", "vestiva", "viaggiano", "viaggiate", "vidi", "viene",
    "visitare", "visto", "vive", "voglio", "vogliono", "vola", "volevo", "vuoi", "è",
}

IT_ADVS = {
    "affatto", "allora", "almeno", "altrimenti", "anche", "ancora", "anzitutto", "appena", "attentamente",
    "bene", "così", "davvero", "dolcemente", "dopo", "dunque", "finalmente", "già",
    "infine", "insieme", "intorno", "lentamente", "lì", "mai", "molto", "neppure", "non",
    "piano", "più", "po", "poi", "presto", "prima", "proprio", "quando", "qui",
    "sempre", "soltanto", "stanotte", "subito", "sì", "tanto", "tardi", "troppo",
    "veloce", "velocemente", "via", "vicino",
}

IT_OTHER = {
    "1909", "612", "a", "accanto", "ad", "agli", "ah", "al", "alla", "alle", "allo",
    "b", "ce", "che", "chi", "ci", "ciascuno", "cinquecento", "cinquecentouno", "cinquemila", "ciò",
    "col", "come", "con", "cui", "da", "dai", "dal", "dalla", "dalle", "dallo",
    "davanti", "dei", "del", "della", "delle", "dentro", "di", "dove", "due", "e",
    "ecco", "ed", "eppure", "essa", "esse", "fra", "gli", "i", "il", "in", "io", "la",
    "le", "li", "lo", "loro", "lui", "ma", "me", "mentre", "mi", "mia", "mie", "miei",
    "mila", "mio", "nel", "nella", "nessuna", "nessuno", "noi", "nulla", "ogni", "per",
    "perché", "però", "pochi", "poiché", "qual", "qualche", "qualcosa", "quanti",
    "quanto", "quarantaquattro", "quattro", "quei", "quelle", "quello", "questa",
    "questo", "se", "seicento", "seicentoventiduemila", "senza", "settecento", "settecentotrentuno", "si", "sopra", "sotto", "su",
    "sua", "sue", "sul", "sulla", "sulle", "suo", "suoi", "sé", "tra", "tre", "trenta",
    "trentuno", "te", "ti", "tu", "tua", "tuo", "tutte", "tutti", "tutto", "un", "una",
    "ventidue", "verso", "uno",
}


DE_NOUNS_NUM = {
    "abend": "s", "abenddämmerung": "s", "abreise": "s", "abschied": "s",
    "affenbrotbäume": "p", "anblick": "s", "angst": "s", "ankunft": "s", "anzug": "s",
    "apfelbaum": "s", "arbeit": "s", "arme": "p", "asteroiden": "s", "astronom": "s",
    "astronomen": "s", "aufbruchs": "s", "augen": "p", "autorität": "s",
    "bande": "p", "baobabs": "p", "baobabsamen": "p", "baobabsämlinge": "p", "bauch": "s", "baum": "s", "befehle": "p",
    "berg": "s", "berge": "p", "beute": "s", "beschäftigung": "s", "besuch": "s", "bild": "s",
    "blatt": "s", "blume": "s", "blumen": "p", "blütenblätter": "p", "blütenblättern": "p",
    "boa": "s", "boas": "p", "brief": "s", "buch": "s", "brunnen": "s", "brunnensuche": "s", "bräuche": "p",
    "bücher": "p", "dinge": "p", "dingen": "p", "disziplin": "s", "dorfbrunnen": "s",
    "duft": "s", "durst": "s", "echo": "s", "eimer": "s", "eitle": "s", "eitlen": "p",
    "elefanten": "s", "erde": "s", "erwachsene": "p", "erwachsenen": "p", "erzähler": "s",
    "farben": "p", "fernrohr": "s", "flaschen": "p", "flucht": "s", "flugzeug": "s", "flugzeugpanne": "s",
    "frage": "s", "freude": "s", "freund": "s", "fressen": "s", "freunde": "p", "fuchs": "s",
    "garten": "s", "geheimnis": "s", "geograph": "s", "geographien": "p", "geräusch": "s", "geschichten": "p",
    "geschäftsmann": "s", "geschenk": "s", "gipfel": "s", "glasglocke": "s", "glöckchen": "p",
    "glücklichsein": "s", "gras": "s", "gründe": "p", "haar": "s", "hermelin": "s",
    "herr": "s", "herrn": "s", "herrscher": "s", "herzen": "s", "himmel": "s", "hut": "s",
    "jahr": "s", "jahre": "p", "jahren": "p", "junge": "s", "kind": "s", "kinder": "p",
    "kiste": "s", "klatschen": "s", "kleidung": "s", "kopf": "s", "korn": "s", "krawatte": "s",
    "könig": "s", "körper": "s", "lampe": "s", "landschaft": "s", "laternenanzünder": "s",
    "lederriemen": "s", "leute": "p", "licht": "s", "lied": "s",
    "lobreden": "p", "luftlöchern": "p", "mal": "s", "mann": "s", "mantel": "s", "marsch": "s",
    "mauer": "s", "maulkorb": "s", "menschen": "p", "millionen": "p", "minute": "s", "monate": "p",
    "morgen": "s", "morgenlicht": "s", "morgentoilette": "s", "motor": "s", "mut": "s",
    "mühe": "s", "nacht": "s", "ozeane": "p", "panne": "s", "papier": "s",
    "pflanze": "s", "phantasie": "s", "pilot": "s", "planet": "s", "planeten": "s",
    "platz": "s", "prinz": "s", "prinzen": "s", "purpur": "s", "purpurmantel": "s",
    "rat": "s", "rauschen": "s", "reichtum": "s", "reise": "s", "riemen": "s", "riesenschlange": "s", "riesenschlangen": "p",
    "ring": "s", "rolle": "s", "rose": "s", "rosen": "p", "rosengarten": "s",
    "rosensamen": "p", "ruhe": "s", "ruine": "s", "sahara": "s", "samen": "p", "sand": "s", "sandes": "s",
    "schaf": "s", "schafes": "s", "scham": "s", "schar": "s", "schlange": "s", "schlangen": "p",
    "schmerzen": "p", "schmetterlinge": "p", "schreibtisch": "s", "schritte": "p",
    "schönheit": "s", "sekunden": "p", "sinn": "s", "sonne": "s", "sonnenuntergänge": "p",
    "steinmauer": "s", "stelle": "s", "stern": "s", "sterne": "p", "sternen": "p",
    "stimme": "s", "straße": "s", "straßenlaterne": "s",
    "stuhl": "s", "stunde": "s", "säufer": "s", "tag": "s", "tages": "s",
    "tagesanbruch": "s", "taten": "p", "thron": "s", "tiefe": "s", "tier": "s", "tieres": "s",
    "tisch": "s", "trinker": "s", "trost": "s", "tränen": "p", "uhr": "s",
    "untertan": "s", "urwald": "s", "vernunft": "s", "verschlingen": "s", "vulkan": "s", "vulkane": "p", "vögel": "p",
    "wandschirm": "s", "wasser": "s", "weizen": "s", "welt": "s", "wesentliche": "s",
    "wind": "s", "windes": "s", "wort": "s", "worte": "p", "worten": "p", "wüste": "s",
    "wüstennacht": "s", "wüstensand": "s", "zahlen": "p", "zeichnung": "s",
    "zeichnungen": "p", "zeit": "s", "zug": "s", "zügen": "p",
}

DE_ADJS_NUM = {
    "alt": "s", "alte": "s", "alten": "s", "alter": "s", "andere": "p", "anstrengend": "s", "blind": "p", "blondes": "s", "blühender": "s", "bunte": "p", "böse": "s",
    "dicke": "p", "dritten": "s", "durstige": "s", "echte": "s", "echten": "s", "eigene": "s", "eigenen": "p", "eigener": "s",
    "einfach": "s", "einfachen": "s", "einmalig": "s", "einsam": "s", "einsamer": "s", "einzig": "s",
    "einzigartig": "s", "einzigartige": "s", "einzigen": "s", "einziges": "s",
    "erlebte": "p", "erloschenen": "s", "ernsthaftesten": "p", "erste": "s", "ersten": "s", "ewige": "p",
    "feinen": "s", "ferne": "s", "feste": "p", "frühen": "s", "fünfte": "s",
    "ganze": "s", "ganzen": "s", "geduldig": "s", "gefährliche": "p", "gelben": "p",
    "gewöhnliche": "s", "gezeichneten": "s", "gleiche": "s", "gleichen": "p",
    "glücklich": "s", "golden": "s", "goldene": "s", "goldenem": "s", "goldenen": "p",
    "goldener": "p", "goldfarbenes": "s", "groß": "s", "große": "p", "großen": "p",
    "grünen": "s", "gut": "s", "gute": "p", "hellen": "p", "hohen": "s", "hübsche": "s", "jung": "s",
    "jungen": "p", "klaren": "s", "klein": "s", "kleine": "s", "kleinen": "s", "kleiner": "s",
    "kleinste": "s", "kluge": "s", "kluger": "s", "kühle": "s", "leeren": "p",
    "majestätischen": "s", "merkwürdig": "s", "mondfarbener": "s", "neuer": "s",
    "nächste": "s", "nützlich": "s", "rechten": "s", "reich": "s", "riesige": "s", "riesigen": "s",
    "rostige": "s", "ruhig": "s", "ruhige": "s", "rätselhafte": "p", "sauber": "s",
    "schlanke": "s", "schnellen": "p", "schreckliche": "p", "schweren": "s",
    "schön": "s", "schöne": "s", "schönes": "s", "schönste": "s", "sechste": "s", "seltsame": "s", "siebte": "s", "siebten": "s",
    "singenden": "s", "stille": "p", "stolz": "s", "stolze": "s", "süß": "s", "traurig": "s", "traurigen": "s",
    "trauriger": "s", "traurige": "s", "traurigste": "s", "tolles": "s", "tätigen": "p", "türkischen": "s", "türkischer": "s",
    "unnötigen": "p", "unsichtbar": "s", "verantwortlich": "s", "verfallene": "s",
    "vergessene": "s", "vergänglich": "p", "verlorene": "s", "verlorenen": "s", "vernünftige": "p",
    "vierte": "s", "vollen": "s", "weiten": "s", "wichtig": "s",
    "wilden": "s", "wilder": "p", "wildes": "s", "winzig": "s", "winzigen": "s", "wunderbaren": "s",
    "wunderbares": "s", "wunderlich": "p", "zarte": "s", "zweiten": "s",
}

DE_VERBS = {
    "ankam", "antwortet", "antwortete", "bat", "bedeckt", "bedeutet", "befiehlt", "begannen",
    "begegnen", "begegnet", "begeistert", "beginnt", "behauptet", "bereitet", "beruht",
    "besitze", "besitzen", "bestieg", "besuchen", "bewegte", "bewohnt", "bewundert", "bin", "bindet",
    "bist", "bleibt", "blickt", "blüht", "brach", "braucht", "brechen", "bringt",
    "dachte", "denkt", "dreht", "empfiehlt", "entdeckt", "entdeckte", "entfaltet", "entstanden",
    "erinnern", "erklären", "erklärt", "erquickt", "erscheint", "erschien", "erschienen",
    "erschrickt", "erstaunt", "erwiderte", "erfährt", "erzählt", "fand", "fangen", "fegt", "fegte",
    "fehlt", "fiel", "finden", "fliegt", "flüstert", "flüsterte", "fordern", "fragen",
    "frisst", "fällt", "fängt", "gab", "gedacht", "geht", "gehörte", "gekleidet", "genügen",
    "genügte", "gepflegt", "geschenkt", "gesehen", "gestand", "gesteht", "gewünscht", "gezähmt", "gibt", "gießt", "ging",
    "glauben", "glaubt", "glaubten", "grüßt", "habe", "haben", "halten", "hast", "hat", "hatte",
    "hebt", "heißt", "hervor", "herrsche", "herrschen", "hielt", "hinaufblickt", "hob", "hochzieht", "hätte", "hören",
    "hörst", "hört", "ist", "jagen", "kam", "kann", "kauen", "kehrt", "kennt", "kleidete",
    "klettert", "klingen", "klingt", "knüpfen", "kommt", "können", "lache", "lachen", "lacht",
    "lachten", "landet", "lass", "lasst", "leb", "lebt", "legte", "lehnt", "leisten", "leuchten",
    "leuchtet", "lieben", "liebe", "liebt", "liegen", "lädt", "machen", "macht", "mag", "merkt", "muss",
    "nimmt", "nutzte", "nützt", "ordnete", "passt", "putzt", "rasen", "reinigen", "reist", "reißt",
    "repariert", "richtete", "rief", "riet", "ruft", "räumt", "rückt", "rückte", "rät", "sagen", "sagte", "sah",
    "sammelt", "saß", "schadet", "schaut", "schaust", "schautest", "schenkt", "schenkte",
    "schlafen", "schlucken", "schläft", "schmeckt", "schreibt", "schrieb", "schäme", "schützt", "sehen", "sei", "seid", "sein", "setzt",
    "sieh", "siehe", "sieht", "sind", "singt", "sitzt", "sollen", "sorgt", "spielen", "sprechen", "sprengen",
    "sprengt", "spricht", "stammt", "stand", "standen", "staunte", "stehen", "steht",
    "steigt", "stellen", "stellt", "stellte", "stoßen", "suchen", "tat", "taucht",
    "thront", "traf", "tragen", "trinke", "trinkst", "trinkt", "tut", "töten", "urteilen",
    "verabschiedet", "verbirgt", "verdauen", "verdaut", "verdaute", "vergaß", "vergehen", "vergessen", "verlässt", "verloren",
    "verrät", "verschlang", "verschwand", "verschwunden", "verstehen",
    "versteht", "versuche", "verwandeln", "verwirren", "wachsen", "wacht", "wanderte",
    "war", "wartet", "wechselt", "wecken", "weckte", "weint", "weinte", "weiterzurücken", "weiß",
    "weißt", "werde", "werden", "wiederkommt", "will", "willst", "wird", "wirst", "wissen", "wohne", "wohnt",
    "wolltest", "wollte", "wurde", "wählte", "wünscht", "zeichne", "zeichnen", "zeichnet",
    "zeichnete", "zieht", "zurückgekehrt", "zurückkehrt", "zählt", "zähme", "zähmen", "zähmte", "zündet", "öffnet",
}

DE_ADVS = {
    "abends", "anders", "aufmerksam", "bald", "besorgt", "bitte", "breit",
    "da", "danach", "dann", "daran", "darin", "doch", "dort", "endlich", "entschieden", "erst",
    "freundlich", "fröhlich", "früh", "ganz", "gar", "gemeinsam", "genau", "genug", "gerade", "gründlich", "heim",
    "her", "heran", "herein", "heute", "hier", "hinauf", "hoch", "höchst", "immer", "immerhin",
    "irgendwo", "ja", "kaum", "kurz", "künftig", "lang", "langsam", "laut", "leider", "leise", "liebevoll",
    "mehr", "morgens", "mutig", "nachts", "nicht", "nie", "niemals", "noch", "nur",
    "näher", "plötzlich", "pünktlich", "rasend", "rechtzeitig", "richtig", "sanft", "schließlich", "schnell", "schneller", "schon",
    "schweigend", "sehr", "selbst", "so", "sonst", "sorgfältig", "sorgsam", "später",
    "stumm", "treu", "trotzdem", "ungeduldig", "vertraut", "viel", "vorbei", "wahrhaft",
    "wann", "warum", "wehmütig", "weit", "weiter", "wenig", "wie", "wieder", "wirklich",
    "wo", "wohl", "wonach", "worüber", "zuerst", "zurück",
}

DE_OTHER = {
    "1909", "501", "612", "622", "731", "ab", "aber", "all", "alle", "allein", "allen",
    "aller", "alles", "als", "also", "am", "an", "auch", "auf", "aus", "b", "bei", "beide",
    "beim", "bevor", "bis", "dar", "das", "dass", "deine", "deinem", "deinen", "dem", "den", "der", "des",
    "dich", "die", "diese", "diesen", "dieser", "dieses", "dir", "drei", "dreißig",
    "du", "durch", "ein", "einander", "eine", "einem", "einen", "einer", "eines",
    "einmal", "er", "es", "euch", "fest", "fünf", "fünftausend", "für", "ich",
    "ihm", "ihn", "ihnen", "ihr", "ihre", "ihren", "im", "in", "ins", "jede", "jedem",
    "jeden", "jeder", "jener", "keine", "keinen", "man", "mein", "meine", "meiner",
    "mich", "mir", "mit", "nach", "nachdem", "namens", "neben", "nichts", "niemand",
    "niemandem", "niemanden", "ob", "obwohl", "ohne", "paar", "sechs", "seine", "seinem", "seinen", "seiner",
    "sich", "sie", "sondern", "tausend", "um", "und", "uns", "unter", "viele",
    "vielen", "vier", "vierundvierzig", "vierundvierzigmal", "vom", "von", "vor", "was", "weg", "wegen",
    "weil", "wenn", "wir", "zu", "zum", "zur", "zwei", "über",
}


# Context-specific POS/gender/number overrides for homographs within the same language
# PREV_CONTEXT_OVERRIDES: (lang, prev_lemma, target_lemma) -> (pos, g, n)
PREV_CONTEXT_OVERRIDES = {
    ("fr", "le", "son"): ("noun", "m", "s"),
    ("fr", "au", "lever"): ("noun", "m", "s"),
    ("fr", "du", "coucher"): ("noun", "m", "s"),
    ("fr", "la", "marche"): ("noun", "f", "s"),
    ("fr", "se", "coucher"): ("verb", None, None),
    ("fr", "fera", "souvenir"): ("verb", None, None),
    ("fr", "à", "fait"): ("adv", None, None),
    ("fr", "quelques", "pas"): ("noun", "m", "p"),
    ("fr", "une", "simple"): ("adj", "f", "s"),
    ("fr", "racines", "énormes"): ("adj", "f", "p"),
    ("fr", "les", "vaniteux"): ("noun", "m", "p"),
    ("fr", "fleur", "unique"): ("adj", "f", "s"),
    ("fr", "est", "unique"): ("adj", "f", "s"),
    ("fr", "être", "unique"): ("adj", "f", "s"),
    ("fr", "rose", "ordinaire"): ("adj", "f", "s"),
    ("fr", "étoile", "solitaire"): ("adj", "f", "s"),
    ("fr", "un", "gros"): ("adj", "m", "s"),
    ("it", "i", "grandi"): ("noun", "m", "p"),
    ("it", "una", "semplice"): ("adj", "f", "s"),
    ("it", "fiore", "vanitoso"): ("adj", "m", "s"),
    ("it", "i", "vanitosi"): ("noun", "m", "p"),
    ("it", "davvero", "utile"): ("adj", "f", "s"),
    ("it", "tutto", "solo"): ("adj", "m", "s"),
    ("it", "sono", "solo"): ("adj", "m", "s"),
    ("it", "da", "solo"): ("adj", "m", "s"),
    ("it", "un", "solo"): ("adj", "m", "s"),
    ("it", "stella", "solitaria"): ("adj", "f", "s"),
    ("it", "voce", "dolce"): ("adj", "f", "s"),
    ("it", "acqua", "fresca"): ("adj", "f", "s"),
    ("it", "volpe", "gentile"): ("adj", "f", "s"),
    ("it", "rosa", "importante"): ("adj", "f", "s"),
    ("it", "rosa", "unica"): ("adj", "f", "s"),
    ("it", "fiori", "uguali"): ("adj", "m", "p"),
    ("it", "rose", "simili"): ("adj", "f", "p"),
    ("it", "piccolo", "passo"): ("noun", "m", "s"),
    ("it", "quelche", "passo"): ("noun", "m", "s"),
    ("it", "alcun", "passo"): ("noun", "m", "s"),
    ("it", "a", "sei"): ("other", None, None),
    ("it", "avevo", "sei"): ("other", None, None),
    ("it", "dormono", "sei"): ("other", None, None),
    ("it", "non", "sei"): ("verb", None, None),
    ("it", "tu", "sei"): ("verb", None, None),
    ("it", "in", "cerca"): ("noun", "f", "s"),
    ("de", "fünftausend", "gleiche"): ("adj", None, "p"),
    ("de", "einzigen", "menschen"): ("noun", None, "s"),
    ("de", "viele", "kleine"): ("adj", None, "p"),
    ("de", "wie", "kleine"): ("adj", None, "p"),
    ("de", "kleine", "goldene"): ("adj", None, "p"),
    ("de", "als", "ihre"): ("other", None, None),
    ("de", "einander", "einzigartig"): ("adj", None, "p"),
    ("de", "so", "gut"): ("adj", None, "p"),
}

# NEXT_CONTEXT_OVERRIDES: (lang, target_lemma, next_lemma) -> (pos, g, n)
NEXT_CONTEXT_OVERRIDES = {
    ("fr", "faire", "peur"): ("verb", None, None),
    ("fr", "tout", "à"): ("adv", None, None),
    ("fr", "la", "plus"): ("other", None, None),
    ("it", "grande", "malinconia"): ("adj", "f", "s"),
    ("it", "solo", "un"): ("adv", None, None),
    ("it", "solo", "i"): ("adv", None, None),
    ("it", "solo", "ripetere"): ("adv", None, None),
    ("it", "solo", "col"): ("adv", None, None),
    ("it", "solo", "tu"): ("adv", None, None),
    ("de", "alle", "sterne"): ("other", None, None),
    ("de", "glücklich", "an"): ("adv", None, None),
    ("de", "großen", "wüste"): ("adj", None, "s"),
    ("de", "großen", "durst"): ("adj", None, "s"),
    ("de", "vollen", "flaschen"): ("adj", None, "p"),
}

# Canonical base/infinitive English gloss for each unique sep_inf (prevents tense/number overwrite collisions)
DE_SEP_INF_GLOSS = {
    "ab·lehnen": {
        "tr": "to refuse / turn down",
        "def": "Separable verb \"ab·lehnen\": to decline or reject something.",
    },
    "an·fangen": {
        "tr": "to begin / start",
        "def": "Separable verb \"an·fangen\" (fängt/fangen … an): to start or begin doing something.",
    },
    "an·kleiden": {
        "tr": "to dress / put on",
        "def": "Separable verb \"an·kleiden\": to get dressed slowly and with care.",
    },
    "an·schauen": {
        "tr": "to look at / watch",
        "def": "Separable verb \"an·schauen\" (schaut/schautest … an): to look closely at or watch something.",
    },
    "an·zünden": {
        "tr": "to light (a lamp)",
        "def": "Separable verb \"an·zünden\": to light or ignite a street lamp.",
    },
    "auf·blicken": {
        "tr": "to look up",
        "def": "Separable verb \"auf·blicken\": to glance upwards from work or numbers.",
    },
    "auf·brechen": {
        "tr": "to set off",
        "def": "Separable verb \"auf·brechen\": to set out on a journey.",
    },
    "auf·räumen": {
        "tr": "to tidy up / clean",
        "def": "Separable verb \"auf·räumen\": to tidy up or put a place in order.",
    },
    "auf·richten": {
        "tr": "to rear up / rise up",
        "def": "Separable verb \"auf·richten\": to rise upright on the desert sand.",
    },
    "auf·tauchen": {
        "tr": "to emerge / appear",
        "def": "Separable verb \"auf·tauchen\": to appear suddenly out of nowhere.",
    },
    "auf·wachen": {
        "tr": "to wake up",
        "def": "Separable verb \"auf·wachen\": to wake up from sleep.",
    },
    "auf·wecken": {
        "tr": "to wake up",
        "def": "Separable verb \"auf·wecken\": to awaken a sleeping well so it sings.",
    },
    "aus·fegen": {
        "tr": "to sweep out",
        "def": "Separable verb \"aus·fegen\" (fegt/fegte … aus): to sweep clean inside (volcanoes!).",
    },
    "aus·reißen": {
        "tr": "to pull up / uproot",
        "def": "Separable verb \"aus·reißen\": to pull out by the roots (like young baobab shoots!).",
    },
    "aus·wählen": {
        "tr": "to choose / select",
        "def": "Separable verb \"aus·wählen\": to select or pick out carefully.",
    },
    "bei·bringen": {
        "tr": "to teach",
        "def": "Separable verb \"bei·bringen\": to teach someone patiently step by step.",
    },
    "dar·stellen": {
        "tr": "to represent / depict",
        "def": "Separable verb \"dar·stellen\": to depict or represent something in a drawing.",
    },
    "ein·laden": {
        "tr": "to invite",
        "def": "Separable verb \"ein·laden\": to invite someone warmly.",
    },
    "ein·schlafen": {
        "tr": "to fall asleep",
        "def": "Separable verb \"ein·schlafen\": to fall asleep gently.",
    },
    "fest·halten": {
        "tr": "to hold fast / record",
        "def": "Separable verb \"fest·halten\": to capture or record enduring things.",
    },
    "her·kommen": {
        "tr": "to come from",
        "def": "Separable verb \"her·kommen\": to originate or come from a place.",
    },
    "heran·rücken": {
        "tr": "to move closer",
        "def": "Separable verb \"heran·rücken\": to edge gradually nearer.",
    },
    "herein·brechen": {
        "tr": "to fall / close in (night)",
        "def": "Separable verb \"herein·brechen\": to fall suddenly, as nightfall in the desert.",
    },
    "hervor·schauen": {
        "tr": "to peek out",
        "def": "Separable verb \"hervor·schauen\": to peek gently out from under shelter.",
    },
    "hinauf·schauen": {
        "tr": "to look up",
        "def": "Separable verb \"hinauf·schauen\": to gaze upwards at the sky.",
    },
    "nach·jagen": {
        "tr": "to chase after",
        "def": "Separable verb \"nach·jagen\": to hurry after unnecessary things.",
    },
    "nach·sprechen": {
        "tr": "to repeat after",
        "def": "Separable verb \"nach·sprechen\": to echo or repeat someone else's words.",
    },
    "unter·gehen": {
        "tr": "to set (sun)",
        "def": "Separable verb \"unter·gehen\" (geht/ging … unter): to go down below the horizon.",
    },
    "vorbei·rasen": {
        "tr": "to rush past",
        "def": "Separable verb \"vorbei·rasen\": to speed past without stopping.",
    },
    "weg·fliegen": {
        "tr": "to fly away",
        "def": "Separable verb \"weg·fliegen\": to fly off into the distance.",
    },
    "weiter·rücken": {
        "tr": "to move further",
        "def": "Separable verb \"weiter·rücken\": to shift a chair a little further along.",
    },
    "weiter·trinken": {
        "tr": "to keep on drinking",
        "def": "Separable verb \"weiter·trinken\": to continue drinking in silence.",
    },
    "zu·flüstern": {
        "tr": "to whisper to",
        "def": "Separable verb \"zu·flüstern\": to whisper gently to someone.",
    },
    "zu·hören": {
        "tr": "to listen attentively",
        "def": "Separable verb \"zu·hören\": to listen carefully to someone speaking.",
    },
    "zurück·gehen": {
        "tr": "to go back",
        "def": "Separable verb \"zurück·gehen\": to return to see a friend.",
    },
    "zurück·kehren": {
        "tr": "to return",
        "def": "Separable verb \"zurück·kehren\": to return home.",
    },
    "zurück·rufen": {
        "tr": "to call back",
        "def": "Separable verb \"zurück·rufen\": to echo or call someone's words back.",
    },
}

# Explicit DE separable verb dictionary keyed by (stem_clean, prefix_clean) -> metadata
DE_SEPARABLE_VERBS = {
    ("stellte", "dar"): {
        "sep_inf": "dar·stellen",
        "tr": "represented / depicted",
        "def": "Separable verb \"dar·stellen\" (stellte … dar): past tense of to depict or represent.",
    },
    ("lehnt", "ab"): {
        "sep_inf": "ab·lehnen",
        "tr": "to refuse / reject",
        "def": "Separable verb \"ab·lehnen\" (lehnt … ab): declines or rejects something.",
    },
    ("wacht", "auf"): {
        "sep_inf": "auf·wachen",
        "tr": "to wake up",
        "def": "Separable verb \"auf·wachen\" (wacht … auf): to wake up from sleep!",
    },
    ("schaut", "an"): {
        "sep_inf": "an·schauen",
        "tr": "to look at / gaze upon",
        "def": "Separable verb \"an·schauen\" (schaut … an): to look closely at something.",
    },
    ("schläft", "ein"): {
        "sep_inf": "ein·schlafen",
        "tr": "to fall asleep",
        "def": "Separable verb \"ein·schlafen\" (schläft … ein): to fall asleep gently.",
    },
    ("kommt", "her"): {
        "sep_inf": "her·kommen",
        "tr": "to come from",
        "def": "Separable verb \"her·kommen\" (kommt … her): to originate or come from a place.",
    },
    ("reißt", "aus"): {
        "sep_inf": "aus·reißen",
        "tr": "to pull up / uproot",
        "def": "Separable verb \"aus·reißen\" (reißt … aus): to pull out by the roots (like young baobab shoots!).",
    },
    ("räumt", "auf"): {
        "sep_inf": "auf·räumen",
        "tr": "to tidy up / to clean",
        "def": "Separable verb \"auf·räumen\" (räumt … auf): to tidy up or put a place in order.",
    },
    ("rückt", "weiter"): {
        "sep_inf": "weiter·rücken",
        "tr": "to move further",
        "def": "Separable verb \"weiter·rücken\" (rückt … weiter): shifts his chair a few steps further.",
    },
    ("geht", "unter"): {
        "sep_inf": "unter·gehen",
        "tr": "to set (sun)",
        "def": "Separable verb \"unter·gehen\" (geht … unter): to go down / set below the horizon.",
    },
    ("ging", "unter"): {
        "sep_inf": "unter·gehen",
        "tr": "set (past of to set)",
        "def": "Separable verb \"unter·gehen\" (ging … unter): past tense of to set (said of the sun!).",
    },
    ("schautest", "an"): {
        "sep_inf": "an·schauen",
        "tr": "looked at / watched",
        "def": "Separable verb \"an·schauen\" (schautest … an): past tense of to watch closely.",
    },
    ("wählte", "aus"): {
        "sep_inf": "aus·wählen",
        "tr": "chose / selected",
        "def": "Separable verb \"aus·wählen\" (wählte … aus): carefully selected or picked out.",
    },
    ("kleidete", "an"): {
        "sep_inf": "an·kleiden",
        "tr": "dressed / clothed",
        "def": "Separable verb \"an·kleiden\" (kleidete … an): got dressed slowly and with care.",
    },
    ("fliegt", "weg"): {
        "sep_inf": "weg·fliegen",
        "tr": "to fly away",
        "def": "Separable verb \"weg·fliegen\" (fliegt … weg): to fly off into the distance.",
    },
    ("fegt", "aus"): {
        "sep_inf": "aus·fegen",
        "tr": "to sweep out",
        "def": "Separable verb \"aus·fegen\" (fegt … aus): sweeps clean inside (volcanoes!).",
    },
    ("fegte", "aus"): {
        "sep_inf": "aus·fegen",
        "tr": "swept out",
        "def": "Separable verb \"aus·fegen\" (fegte … aus): swept clean inside (volcanoes!).",
    },
    ("trinkt", "weiter"): {
        "sep_inf": "weiter·trinken",
        "tr": "to keep on drinking",
        "def": "Separable verb \"weiter·trinken\" (trinkt … weiter): keeps drinking in silence.",
    },
    ("schaut", "hinauf"): {
        "sep_inf": "hinauf·schauen",
        "tr": "to look up",
        "def": "Separable verb \"hinauf·schauen\" (schaut … hinauf): looks upwards towards the sky.",
    },
    ("blickt", "auf"): {
        "sep_inf": "auf·blicken",
        "tr": "to look up",
        "def": "Separable verb \"auf·blicken\" (blickt … auf): glances upwards from his numbers.",
    },
    ("zündet", "an"): {
        "sep_inf": "an·zünden",
        "tr": "to light (a lamp)",
        "def": "Separable verb \"an·zünden\" (zündet … an): to light or ignite a street lamp.",
    },
    ("halten", "fest"): {
        "sep_inf": "fest·halten",
        "tr": "to hold fast / record",
        "def": "Separable verb \"fest·halten\" (halten … fest): record enduring things in geography books.",
    },
    ("taucht", "auf"): {
        "sep_inf": "auf·tauchen",
        "tr": "to emerge / appear",
        "def": "Separable verb \"auf·tauchen\" (taucht … auf): to appear suddenly out of nowhere.",
    },
    ("ruft", "zurück"): {
        "sep_inf": "zurück·rufen",
        "tr": "to call back",
        "def": "Separable verb \"zurück·rufen\" (ruft … zurück): echoes or calls his words back.",
    },
    ("sprechen", "nach"): {
        "sep_inf": "nach·sprechen",
        "tr": "to repeat after",
        "def": "Separable verb \"nach·sprechen\" (sprechen … nach): to echo or repeat someone else's words.",
    },
    ("schaut", "hervor"): {
        "sep_inf": "hervor·schauen",
        "tr": "to peek out",
        "def": "Separable verb \"hervor·schauen\" (schaut … hervor): to peek gently out from under shelter.",
    },
    ("lädt", "ein"): {
        "sep_inf": "ein·laden",
        "tr": "to invite",
        "def": "Separable verb \"ein·laden\" (lädt … ein): to invite someone warmly.",
    },
    ("bringt", "bei"): {
        "sep_inf": "bei·bringen",
        "tr": "to teach",
        "def": "Separable verb \"bei·bringen\" (bringt … bei): to teach someone patiently step by step.",
    },
    ("fängt", "an"): {
        "sep_inf": "an·fangen",
        "tr": "to begin / start",
        "def": "Separable verb \"an·fangen\" (fängt … an): to start or begin doing something.",
    },
    ("rückte", "heran"): {
        "sep_inf": "heran·rücken",
        "tr": "moved closer",
        "def": "Separable verb \"heran·rücken\" (rückte … heran): edged gradually nearer.",
    },
    ("ging", "zurück"): {
        "sep_inf": "zurück·gehen",
        "tr": "went back",
        "def": "Separable verb \"zurück·gehen\" (ging … zurück): returned to see a friend.",
    },
    ("hört", "zu"): {
        "sep_inf": "zu·hören",
        "tr": "to listen attentively",
        "def": "Separable verb \"zu·hören\" (hört … zu): to listen carefully to someone speaking.",
    },
    ("rasen", "vorbei"): {
        "sep_inf": "vorbei·rasen",
        "tr": "to rush past",
        "def": "Separable verb \"vorbei·rasen\" (rasen … vorbei): speed past on express trains.",
    },
    ("jagen", "nach"): {
        "sep_inf": "nach·jagen",
        "tr": "to chase after",
        "def": "Separable verb \"nach·jagen\" (jagen … nach): chase after unnecessary things.",
    },
    ("brechen", "auf"): {
        "sep_inf": "auf·brechen",
        "tr": "to set off",
        "def": "Separable verb \"auf·brechen\" (brechen … auf): to set out on a journey.",
    },
    ("brach", "herein"): {
        "sep_inf": "herein·brechen",
        "tr": "fell / closed in (night)",
        "def": "Separable verb \"herein·brechen\" (brach … herein): fell suddenly, as nightfall in the desert.",
    },
    ("wecken", "auf"): {
        "sep_inf": "auf·wecken",
        "tr": "to wake up",
        "def": "Separable verb \"auf·wecken\" (wecken … auf): to awaken a sleeping well so it sings.",
    },
    ("richtete", "auf"): {
        "sep_inf": "auf·richten",
        "tr": "reared up / rose up",
        "def": "Separable verb \"auf·richten\" (richtete … auf): rose upright on the desert sand.",
    },
    ("flüstert", "zu"): {
        "sep_inf": "zu·flüstern",
        "tr": "to whisper to",
        "def": "Separable verb \"zu·flüstern\" (flüstert … zu): whispers gently to the pilot.",
    },
    ("kehrt", "zurück"): {
        "sep_inf": "zurück·kehren",
        "tr": "to return",
        "def": "Separable verb \"zurück·kehren\" (kehrt … zurück): to return home.",
    },
}

# Book-level English (en-GB) glossary.
# Keys MUST NOT include bare German separable prefixes (auf, an, aus, ein, mit, nach, vor, zu, etc.).
# No cross-language homograph contradictions.
EN_GLOSS = {
    # French B1/B2/C1 literary vocabulary
    "forêt": {"tr": "forest", "def": "A dense primeval forest full of wild creatures.", "pos": "noun", "g": "f"},
    "vierge": {"tr": "primeval / virgin", "def": "Untouched, ancient wilderness where wild beasts roam.", "pos": "adj", "g": "f"},
    "proie": {"tr": "prey", "def": "An animal hunted and swallowed by a predator.", "pos": "noun", "g": "f"},
    "mâcher": {"tr": "to chew", "def": "To grind food with teeth — something boas never do!", "pos": "verb"},
    "intitulé": {"tr": "entitled / called", "def": "Given a book title, such as 'Histoires Vécues'.", "pos": "adj", "g": "m"},
    "fauve": {"tr": "wild beast", "def": "A fierce wild animal, such as a lion or tiger, in the jungle.", "pos": "noun", "g": "m"},
    "digérait": {"tr": "was digesting", "def": "Breaking down food slowly inside the boa's stomach.", "pos": "verb"},
    "fatigant": {"tr": "tiresome / exhausting", "def": "Making one feel tired from having to explain everything.", "pos": "adj", "g": "m"},
    "explications": {"tr": "explanations", "def": "Clear reasons given so grown-ups can understand.", "pos": "noun", "g": "f"},
    "caisse": {"tr": "wooden crate / box", "def": "A small box with air holes where the little sheep sleeps.", "pos": "noun", "g": "f"},
    "astéroïde": {"tr": "asteroid", "def": "A tiny rocky planet floating in outer space, like B 612.", "pos": "noun", "g": "m"},
    "astronome": {"tr": "astronomer", "def": "A scientist who studies stars and planets through a telescope.", "pos": "noun", "g": "m"},
    "télescope": {"tr": "telescope", "def": "An optical instrument that makes distant stars look closer.", "pos": "noun", "g": "m"},
    "baobabs": {"tr": "baobab trees", "def": "Giant trees whose roots can split a tiny asteroid apart.", "pos": "noun", "g": "m"},
    "graines": {"tr": "seeds", "def": "Tiny plant seeds hidden in the soil before they sprout.", "pos": "noun", "g": "f"},
    "crépuscule": {"tr": "twilight / dusk", "def": "The soft glowing sky just as the sun goes down.", "pos": "noun", "g": "m"},
    "quarante_quatre": {"tr": "forty-four", "def": "The remarkable number of sunsets the prince watched in one day!", "pos": "other"},
    "pétales": {"tr": "petals", "def": "The soft coloured leaves of the proud rose.", "pos": "noun", "g": "m"},
    "paravent": {"tr": "folding screen", "def": "A shield placed around the rose to protect her from draughts.", "pos": "noun", "g": "m"},
    "embaumait": {"tr": "filled with fragrance", "def": "Scented the air sweetly all over the tiny planet.", "pos": "verb"},
    "évasion": {"tr": "escape / departure", "def": "Setting off on a daring journey into the stars.", "pos": "noun", "g": "f"},
    "ramona": {"tr": "swept out", "def": "Cleaned the soot from his volcanoes like a chimney sweep.", "pos": "verb"},
    "pourpre": {"tr": "royal purple", "def": "A deep crimson-purple colour worn by kings.", "pos": "noun", "g": "f"},
    "hermine": {"tr": "ermine fur", "def": "Soft white fur lining a royal cloak.", "pos": "noun", "g": "f"},
    "majestueux": {"tr": "majestic", "def": "Grand and dignified, even on a tiny asteroid.", "pos": "adj", "g": "m"},
    "vaniteux": {"tr": "vain / conceited people", "def": "People who only ever wish to hear applause and praise.", "pos": "noun", "g": "m"},
    "louanges": {"tr": "praise / compliments", "def": "Flattering words admiring someone.", "pos": "noun", "g": "f"},
    "buveur": {"tr": "drunkard / tippler", "def": "The sad man on the third planet who drinks to forget.", "pos": "noun", "g": "m"},
    "honte": {"tr": "shame", "def": "A heavy feeling of regret or embarrassment.", "pos": "noun", "g": "f"},
    "réverbère": {"tr": "street lamp", "def": "A tall outdoor lamp lit each evening and put out at dawn.", "pos": "noun", "g": "m"},
    "allumeur": {"tr": "lamplighter", "def": "The faithful keeper who lights the street lamp every minute.", "pos": "noun", "g": "m"},
    "éphémères": {"tr": "ephemeral / short-lived", "def": "Threatened with disappearing soon, unlike eternal mountains.", "pos": "adj", "g": "f"},
    "géographe": {"tr": "geographer", "def": "A scholar who maps seas, rivers, and towns in huge books.", "pos": "noun", "g": "m"},
    "apprivoiser": {"tr": "to tame", "def": "To create patient ties of friendship so two beings need each other.", "pos": "verb"},
    "apprivoisé": {"tr": "tamed", "def": "Bound by patience, trust, and shared rituals.", "pos": "adj", "g": "m"},
    "blé": {"tr": "wheat", "def": "Golden grain swaying in the wind, reminding the fox of golden hair.", "pos": "noun", "g": "m"},
    "rites": {"tr": "rituals / customs", "def": "Special daily habits that make one hour different from all others.", "pos": "noun", "g": "m"},
    "cœur": {"tr": "heart", "def": "Where true feelings live — the only way to see what is essential.", "pos": "noun", "g": "m"},
    "essentiel": {"tr": "what is essential", "def": "The deepest truth of love and friendship, invisible to the eyes.", "pos": "adj", "g": "m"},
    "puits": {"tr": "well", "def": "A deep desert well with cool water hidden beneath the stars.", "pos": "noun", "g": "m"},
    "poulie": {"tr": "pulley", "def": "The wheel and rope that sing as you draw up the bucket of water.", "pos": "noun", "g": "f"},
    "grelots": {"tr": "little sleigh bells", "def": "Tiny golden bells whose chiming sounds like joyful laughter.", "pos": "noun", "g": "m"},
    "muselière": {"tr": "muzzle", "def": "A guard drawn for the sheep so it will not nibble the rose.", "pos": "noun", "g": "f"},
    "courroie": {"tr": "leather strap", "def": "The missing strap needed to fasten the sheep's muzzle!", "pos": "noun", "g": "f"},
    # Italian B1/B2/C1 literary vocabulary
    "foresta": {"tr": "forest", "def": "A vast primeval woodland in a storybook.", "pos": "noun", "g": "f"},
    "preda": {"tr": "prey", "def": "The wild animal swallowed whole by the boa.", "pos": "noun", "g": "f"},
    "masticarla": {"tr": "to chew it", "def": "To chew food before swallowing.", "pos": "verb"},
    "digerire": {"tr": "to digest", "def": "To break down food slowly during six months of sleep.", "pos": "verb"},
    "belva": {"tr": "wild beast", "def": "A fierce wild animal swallowed whole by the boa.", "pos": "noun", "g": "f"},
    "inghiottiva": {"tr": "was swallowing", "def": "Gulping down prey whole without chewing.", "pos": "verb"},
    "spiegazioni": {"tr": "explanations", "def": "Patient details adults always demand from children.", "pos": "noun", "g": "f"},
    "guasto": {"tr": "breakdown / engine failure", "def": "Mechanical trouble forcing the pilot to land in the Sahara.", "pos": "noun", "g": "m"},
    "cassa": {"tr": "wooden crate", "def": "A simple box with air holes holding the little prince's sheep.", "pos": "noun", "g": "f"},
    "asteroide": {"tr": "asteroid", "def": "A tiny rocky planet in space, such as B 612.", "pos": "noun", "g": "m"},
    "astronomo": {"tr": "astronomer", "def": "A scientist who observes the heavens through a telescope.", "pos": "noun", "g": "m"},
    "estirpare": {"tr": "to uproot", "def": "To pull dangerous baobab seedlings right out of the soil.", "pos": "verb"},
    "germogli": {"tr": "shoots / sprouts", "def": "Young baby plants just pushing up through the earth.", "pos": "noun", "g": "m"},
    "crepuscolo": {"tr": "twilight", "def": "The quiet golden glow at sunset.", "pos": "noun", "g": "m"},
    "malinconia": {"tr": "melancholy / gentle sadness", "def": "A quiet, wistful feeling at the end of the day.", "pos": "noun", "g": "f"},
    "petali": {"tr": "petals", "def": "Delicate crimson petals arranged carefully by the rose.", "pos": "noun", "g": "m"},
    "campana": {"tr": "glass dome / bell jar", "def": "A protective glass cover placed over the rose at night.", "pos": "noun", "g": "f"},
    "migrazione": {"tr": "migration", "def": "A seasonal flight of wild birds across the sky.", "pos": "noun", "g": "f"},
    "porpora": {"tr": "royal purple", "def": "Rich crimson-purple cloth fit for a king.", "pos": "noun", "g": "f"},
    "ermellino": {"tr": "ermine", "def": "Precious white winter fur trimming a royal robe.", "pos": "noun", "g": "m"},
    "suddito": {"tr": "subject (of a king)", "def": "A person living under a monarch's rule.", "pos": "noun", "g": "m"},
    "lodi": {"tr": "praises", "def": "Compliments and applause craved by the vain man.", "pos": "noun", "g": "f"},
    "lampione": {"tr": "street lamp", "def": "A tall lamp lit at dusk and put out at dawn.", "pos": "noun", "g": "m"},
    "lampionaio": {"tr": "lamplighter", "def": "The devoted keeper of the fifth asteroid's street lamp.", "pos": "noun", "g": "m"},
    "effimeri": {"tr": "ephemeral", "def": "Lasting only a short while; threatened with vanishing.", "pos": "adj", "g": "m"},
    "scrittoio": {"tr": "writing desk", "def": "The grand desk the geographer never leaves.", "pos": "noun", "g": "m"},
    "addomesticare": {"tr": "to tame", "def": "To build warm, patient ties of friendship.", "pos": "verb"},
    "legami": {"tr": "ties / bonds", "def": "Invisible threads of care connecting true friends.", "pos": "noun", "g": "m"},
    "spighe": {"tr": "ears of wheat", "def": "Golden wheat stalks rippling in the breeze.", "pos": "noun", "g": "f"},
    "pozzo": {"tr": "well", "def": "A deep stone well hidden beneath the Sahara sands.", "pos": "noun", "g": "m"},
    "carrucola": {"tr": "pulley", "def": "The singing wooden wheel used to haul up the water bucket.", "pos": "noun", "g": "f"},
    "sonagli": {"tr": "little bells", "def": "Tiny bells ringing joyfully like laughter in the stars.", "pos": "noun", "g": "m"},
    "museruola": {"tr": "muzzle", "def": "A protective guard drawn for the little sheep.", "pos": "noun", "g": "f"},
    "cinghia": {"tr": "leather strap", "def": "The strap the pilot forgot to draw on the muzzle.", "pos": "noun", "g": "f"},
    # German B1/B2/C1 literary vocabulary (NEVER gender on DE)
    "urwald": {"tr": "primeval forest / jungle", "def": "An ancient untouched forest from the storybook.", "pos": "noun"},
    "verschlingen": {"tr": "swallowing / devouring", "def": "To gulp down prey completely whole.", "pos": "noun"},
    "beute": {"tr": "prey", "def": "An animal caught and swallowed by the boa.", "pos": "noun"},
    "riesenschlange": {"tr": "giant boa constrictor", "def": "A huge snake that swallows its prey whole.", "pos": "noun"},
    "verdaute": {"tr": "was digesting", "def": "Slowly digesting a whole elephant inside its belly.", "pos": "verb"},
    "kiste": {"tr": "wooden crate", "def": "The box holding the sleeping little sheep.", "pos": "noun"},
    "fernrohr": {"tr": "telescope", "def": "An optical tube for spotting distant asteroids.", "pos": "noun"},
    "affenbrotbäume": {"tr": "baobab trees", "def": "Enormous trees whose roots threaten tiny planets.", "pos": "noun"},
    "abenddämmerung": {"tr": "evening twilight", "def": "The peaceful dusk light as the sun sinks.", "pos": "noun"},
    "sonnenuntergänge": {"tr": "sunsets", "def": "Forty-four golden sunsets watched on one sad day.", "pos": "noun"},
    "glasglocke": {"tr": "glass dome", "def": "A clear glass bell jar keeping the rose warm at night.", "pos": "noun"},
    "wandschirm": {"tr": "folding screen", "def": "A small screen shielding the rose from chilly winds.", "pos": "noun"},
    "purpurmantel": {"tr": "purple cloak", "def": "The king's grand robe covering his entire tiny planet.", "pos": "noun"},
    "untertan": {"tr": "subject", "def": "Someone a king expects to obey reasonable commands.", "pos": "noun"},
    "lobreden": {"tr": "speeches of praise", "def": "Flattering applause that conceited people love to hear.", "pos": "noun"},
    "geschäftsmann": {"tr": "businessman", "def": "The busy star-counter who never looks up from his desk.", "pos": "noun"},
    "laternenanzünder": {"tr": "lamplighter", "def": "The loyal worker lighting his street lamp every minute.", "pos": "noun"},
    "vergänglich": {"tr": "ephemeral / fleeting", "def": "Destined to fade away rather than last for ever.", "pos": "adj"},
    "phantasie": {"tr": "imagination", "def": "The gift of dreaming up new things instead of echoing others.", "pos": "noun"},
    "zähmen": {"tr": "to tame", "def": "To make oneself familiar and create precious bonds.", "pos": "verb"},
    "bräuche": {"tr": "rites / customs", "def": "Regular little rituals that make each visit special.", "pos": "noun"},
    "wesentliche": {"tr": "what is essential", "def": "What truly matters — visible only to the heart.", "pos": "noun"},
    "brunnensuche": {"tr": "search for a well", "def": "A night-time trek across the desert seeking water.", "pos": "noun"},
    "dorfbrunnen": {"tr": "village well", "def": "A real stone well discovered at daybreak in the Sahara.", "pos": "noun"},
    "glöckchen": {"tr": "little bells", "def": "Five hundred million tiny bells laughing in the night sky.", "pos": "noun"},
    "maulkorb": {"tr": "muzzle", "def": "A little guard to keep the sheep from eating the rose.", "pos": "noun"},
    "lederriemen": {"tr": "leather strap", "def": "The strap the aviator forgot to attach to the muzzle.", "pos": "noun"},
    # German Separable Verbs (keyed by unique sep_inf using canonical infinitive glosses)
    **{
        sep_inf: {
            "tr": DE_SEP_INF_GLOSS[sep_inf]["tr"],
            "def": DE_SEP_INF_GLOSS[sep_inf]["def"],
            "pos": "verb",
            "sep_inf": sep_inf,
        }
        for sep_inf in sorted({info["sep_inf"] for info in DE_SEPARABLE_VERBS.values()})
    },
}


# =============================================================================
# TOKENIZER, SEPARABLE-VERB LINKER, COMPILER & DETERMINISTIC VALIDATOR
# =============================================================================

US_ENGLISH_FORBIDDEN = {
    "color", "colors", "colored", "coloring",
    "favorite", "favorites",
    "realize", "realized", "realizes", "realizing",
    "marvelous",
    "traveler", "travelers", "traveling", "traveled",
    "airplane", "airplanes",
    "neighbor", "neighbors", "neighborhood",
    "cozy", "cozier", "coziest",
    "gray",
    "program", "programs",
    "judgment", "judgments",
    "honor", "honors", "honored",
    "center", "centers",
    "recognize", "recognized", "recognizes",
    "behavior", "harbor", "flavor", "rumor", "labor", "odor", "vapor",
    "theater", "meter", "meters", "kilometers", "kilometer",
    "dialog", "catalog",
    "mom", "gotten", "sidewalk", "flashlight", "truck", "sweater", "soccer", "sneakers",
}

BARE_DE_PREFIXES = {
    "ab", "an", "auf", "aus", "bei", "dar", "ein", "empor", "fest", "her", "heran",
    "herein", "hervor", "hinauf", "hinaus", "hoch", "los", "mit", "nach",
    "um", "unter", "vor", "vorbei", "weg", "weiter", "zu", "zurück",
}


def slugify_word(w: str) -> str:
    clean = STRIP_OUTER_RE.sub("", w.lower())
    clean = SLUG_RE.sub("_", clean)
    return clean or "word"


def extract_lemma(w: str) -> str:
    stripped = STRIP_OUTER_RE.sub("", w.lower())
    if "'" in stripped or "’" in stripped:
        parts = re.split(r"['’]", stripped)
        return parts[-1] if parts[-1] else parts[0]
    return stripped


def strip_outer(w: str) -> str:
    return STRIP_OUTER_RE.sub("", w)


def lookup_lexicon(
    lemma: str,
    prev_lemma: str,
    next_lemma: str,
    lang: str,
    is_cap: bool = False,
) -> tuple[str, str | None, str | None]:
    # Check context-specific overrides first
    if prev_lemma and (lang, prev_lemma, lemma) in PREV_CONTEXT_OVERRIDES:
        return PREV_CONTEXT_OVERRIDES[(lang, prev_lemma, lemma)]
    if next_lemma and (lang, lemma, next_lemma) in NEXT_CONTEXT_OVERRIDES:
        return NEXT_CONTEXT_OVERRIDES[(lang, lemma, next_lemma)]

    if lang == "fr":
        if lemma in FR_NOUNS_META:
            g, n = FR_NOUNS_META[lemma]
            return ("noun", g, n)
        if lemma in FR_ADJS_META:
            g, n = FR_ADJS_META[lemma]
            return ("adj", g, n)
        if lemma in FR_VERBS:
            return ("verb", None, None)
        if lemma in FR_ADVS:
            return ("adv", None, None)
        if lemma in FR_OTHER:
            return ("other", None, None)
    elif lang == "it":
        if lemma in IT_NOUNS_META:
            g, n = IT_NOUNS_META[lemma]
            return ("noun", g, n)
        if lemma in IT_ADJS_META:
            g, n = IT_ADJS_META[lemma]
            return ("adj", g, n)
        if lemma in IT_VERBS:
            return ("verb", None, None)
        if lemma in IT_ADVS:
            return ("adv", None, None)
        if lemma in IT_OTHER:
            return ("other", None, None)
    elif lang == "de":
        # Case-aware German disambiguation (Liebe vs liebe, All vs all, Macht vs macht, etc.)
        if is_cap and lemma == "liebe":
            return ("noun", None, "s")
        if is_cap and lemma == "all":
            return ("noun", None, "s")
        if is_cap and lemma == "macht":
            return ("noun", None, "s")
        if is_cap and lemma == "zähmen":
            return ("noun", None, "s")
        if is_cap and lemma == "tausend":
            return ("noun", None, "p")
        if is_cap and lemma in DE_NOUNS_NUM:
            return ("noun", None, DE_NOUNS_NUM[lemma])
        if lemma in DE_ADJS_NUM:
            return ("adj", None, DE_ADJS_NUM[lemma])
        if lemma in DE_VERBS:
            return ("verb", None, None)
        if lemma in DE_ADVS:
            return ("adv", None, None)
        if lemma in DE_OTHER:
            return ("other", None, None)

    raise ValueError(f"Unclassified token lemma '{lemma}' in lang '{lang}' (prev='{prev_lemma}', next='{next_lemma}', is_cap={is_cap})")


def is_clause_ending_token(raw_w: str) -> bool:
    return bool(re.search(r"[.!?,;:»\"…]+$", raw_w))


def link_de_separable_verbs(tokens_out: list[dict]) -> None:
    """
    Strictly clause-bounded V2/V1 German separable verb pairing.
    Matches only when:
      - prefix_idx > stem_idx within the same clause (stops at any clause boundary),
      - prefix sits in the right-bracket position (ends with clause punctuation OR
        precedes coordinating conjunction und/aber/oder/denn),
      - never crosses a clause boundary or matches a middle-field preposition.
    """
    coord_after = {"und", "aber", "oder", "denn"}
    clause_break_re = re.compile(r"[.!?,;:»—]+$")

    for i, tok_i in enumerate(tokens_out):
        if tok_i.get("sep_group"):
            continue
        stem_lemma = extract_lemma(tok_i["w"])
        # If stem itself already ends a clause (e.g. comma), cannot look past it
        if clause_break_re.search(tok_i["w"]):
            continue

        for j in range(i + 1, len(tokens_out)):
            tok_j = tokens_out[j]
            if tok_j.get("sep_group"):
                if clause_break_re.search(tok_j["w"]):
                    break
                continue

            pref_lemma = extract_lemma(tok_j["w"])
            pair_key = (stem_lemma, pref_lemma)
            at_right_bracket = (
                is_clause_ending_token(tok_j["w"])
                or (j + 1 < len(tokens_out) and extract_lemma(tokens_out[j + 1]["w"]) in coord_after)
                or j == len(tokens_out) - 1
            )

            if pair_key in DE_SEPARABLE_VERBS and at_right_bracket:
                info = DE_SEPARABLE_VERBS[pair_key]
                gid = f"sep_{i}_{j}"
                pair_display = f"{stem_lemma} … {pref_lemma}"
                gloss_obj = {
                    "tr": info["tr"],
                    "def": info["def"],
                    "sep_inf": info["sep_inf"],
                    "sep_pair": pair_display,
                }

                tok_i["pos"] = "verb"
                tok_i.pop("g", None)
                tok_i["sep_group"] = gid
                tok_i["sep_role"] = "stem"
                tok_i["sep_inf"] = info["sep_inf"]
                tok_i["sep_pair"] = pair_display
                tok_i["gloss"] = gloss_obj

                tok_j["pos"] = "verb"
                tok_j.pop("g", None)
                tok_j["sep_group"] = gid
                tok_j["sep_role"] = "prefix"
                tok_j["sep_inf"] = info["sep_inf"]
                tok_j["sep_pair"] = pair_display
                tok_j["gloss"] = gloss_obj
                break

            if clause_break_re.search(tok_j["w"]) or "«" in tok_j["w"]:
                break


def build_tokens(sentence: str, lang: str) -> list[dict]:
    raw_tokens = sentence.split()
    lemmas = [extract_lemma(w) for w in raw_tokens]
    weights = [max(2, len(strip_outer(w))) for w in raw_tokens]
    total_w = sum(weights) or 1
    est_total_dur = max(2.0, len(raw_tokens) * 0.40)
    usable_dur = max(1.0, est_total_dur - 0.16)

    cur_t = 0.08
    tokens_out = []
    for idx, raw_w in enumerate(raw_tokens):
        lemma = lemmas[idx]
        prev_l = lemmas[idx - 1] if idx > 0 else ""
        next_l = lemmas[idx + 1] if idx + 1 < len(lemmas) else ""
        core = strip_outer(raw_w)
        is_cap = bool(core and core[0].isupper())
        pos, gender, number = lookup_lexicon(lemma, prev_l, next_l, lang, is_cap=is_cap)
        slug = slugify_word(raw_w)
        dur = usable_dur * (weights[idx] / total_w)

        entry = {
            "w": raw_w,
            "clean": slug,
            "pos": pos,
            "s": round(cur_t, 3),
            "e": round(cur_t + dur, 3),
            "audio_mp3": f"assets/words_audio/{lang}/{slug}.mp3",
            "audio_ogg": f"assets/words_audio/{lang}/{slug}.ogg",
        }
        cur_t += dur

        if lang in ("fr", "it") and pos in ("noun", "adj") and gender and len(core) >= 3:
            entry["g"] = gender
        if number and pos in ("noun", "adj"):
            entry["n"] = number

        gloss_key = lemma if lemma in EN_GLOSS else (slug if slug in EN_GLOSS else None)
        if gloss_key:
            g_info = EN_GLOSS[gloss_key]
            entry["gloss"] = {
                "tr": g_info["tr"],
                "def": g_info["def"],
            }

        tokens_out.append(entry)

    if lang == "de":
        link_de_separable_verbs(tokens_out)

    return tokens_out


def compile_content_spec() -> dict:
    pages_out = []
    for p in PAGES_DATA:
        pnum = p["page"]
        pstr = f"{pnum:02d}"
        patch_pos = "bottom" if pnum % 2 == 1 else "top"
        is_front = bool(p.get("is_frontispiece"))

        if is_front:
            bubble_obj = None
            levels_obj = {
                tier: {
                    lang: {
                        "text": "",
                        "audio_mp3": "",
                        "audio_ogg": "",
                        "tokens": [],
                    }
                    for lang in SUPPORTED_LANGS
                }
                for tier in TIERS
            }
            translations_obj = {
                "en": {tier: {"text": ""} for tier in TIERS}
            }
        else:
            bubble_obj = {"speaker": p["speech_bubble"]["speaker"]}
            for lang in SUPPORTED_LANGS:
                bubble_obj[lang] = {
                    "text": p["speech_bubble"][lang],
                    "audio_mp3": f"books/petit-prince/kids_audio/{lang}_bubble_p{pstr}.mp3",
                    "audio_ogg": f"books/petit-prince/kids_audio/{lang}_bubble_p{pstr}.ogg",
                }
            bubble_obj["en"] = {
                "text": p["speech_bubble"]["en"],
                "is_browser_tts": True,
            }

            levels_obj = {}
            for tier in TIERS:
                levels_obj[tier] = {}
                for lang in SUPPORTED_LANGS:
                    txt = p[tier][lang]
                    levels_obj[tier][lang] = {
                        "text": txt,
                        "audio_mp3": f"books/petit-prince/kids_audio/{lang}_{tier}_p{pstr}.mp3",
                        "audio_ogg": f"books/petit-prince/kids_audio/{lang}_{tier}_p{pstr}.ogg",
                        "tokens": build_tokens(txt, lang),
                    }

            translations_obj = {
                "en": {
                    tier: {"text": p[tier]["en"]}
                    for tier in TIERS
                }
            }

        page_entry = {
            "page": pnum,
            "display_page": pnum - 1,
            "patch_pos": patch_pos,
            "title": p["title"],
            "image": f"books/petit-prince/wc_p{pstr}.jpg",
            "art_refs": p["art_refs"],
            "bubble_anchor": p["bubble_anchor"],
            "speech_bubble": bubble_obj,
            "levels": levels_obj,
            "translations": translations_obj,
            "questions": p["questions"],
        }
        if is_front:
            page_entry["is_frontispiece"] = True
        if p.get("hover_reveal_image"):
            page_entry["hover_reveal_image"] = p["hover_reveal_image"]
        pages_out.append(page_entry)

    spec = {
        **BOOK_META,
        "en_gloss": EN_GLOSS,
        "pages": pages_out,
    }
    return spec


def check_en_gb(text: str, ctx: str, errors: list[str]) -> None:
    if "«" in text or "»" in text:
        errors.append(f"French guillemets («/») forbidden in English {ctx}: {text!r}")
    for w in WORD_RE.findall(text.lower()):
        if w in US_ENGLISH_FORBIDDEN:
            errors.append(f"US English spelling '{w}' forbidden in {ctx}: {text!r}")


def validate_content_spec(spec: dict) -> list[str]:
    errors = []

    # 0. Intra-language lexicon overlap check (zero silent POS shadowing)
    for lang_name, dicts in [
        ("FR", [("noun", FR_NOUNS_META), ("adj", FR_ADJS_META), ("verb", FR_VERBS), ("adv", FR_ADVS), ("other", FR_OTHER)]),
        ("IT", [("noun", IT_NOUNS_META), ("adj", IT_ADJS_META), ("verb", IT_VERBS), ("adv", IT_ADVS), ("other", IT_OTHER)]),
        ("DE", [("noun", DE_NOUNS_NUM), ("adj", DE_ADJS_NUM), ("verb", DE_VERBS), ("adv", DE_ADVS), ("other", DE_OTHER)]),
    ]:
        seen_pos: dict[str, list[str]] = {}
        for pos_name, d in dicts:
            for k in d:
                seen_pos.setdefault(k, []).append(pos_name)
        for k, plist in seen_pos.items():
            if len(plist) > 1:
                errors.append(f"Intra-language lexicon overlap in {lang_name}: {k!r} in {plist}")

    # 1. Top-level metadata & buttons
    if spec.get("story_id") != "le-petit-prince":
        errors.append("story_id must be 'le-petit-prince'")
    if spec.get("book_alias") != "petit-prince":
        errors.append("book_alias must be 'petit-prince'")
    if spec.get("supported_langs") != ["fr", "it", "de"]:
        errors.append(f"supported_langs must be ['fr', 'it', 'de'], got {spec.get('supported_langs')}")
    if spec.get("default_lang") != "fr":
        errors.append("default_lang must be 'fr'")
    if spec.get("total_pages") != 26 or len(spec.get("pages", [])) != 26:
        errors.append("total_pages and len(pages) must be 26")

    for tier in TIERS:
        btn = spec.get("buttons", {}).get(tier, {})
        img_rel = btn.get("image", "")
        if not (ROOT / img_rel).exists():
            errors.append(f"Missing avatar image for button '{tier}': {img_rel}")
        check_en_gb(btn.get("label", {}).get("en", ""), f"buttons.{tier}.label.en", errors)

    # 2. en_gloss checks (no bare DE prefixes, no US English, no guillemets, no cross-lang homographs)
    en_gloss = spec.get("en_gloss", {})
    for gk, gval in en_gloss.items():
        if gk in BARE_DE_PREFIXES:
            errors.append(f"Bare German prefix '{gk}' must NEVER be a key in en_gloss")
        check_en_gb(gval.get("tr", ""), f"en_gloss[{gk}].tr", errors)
        check_en_gb(gval.get("def", ""), f"en_gloss[{gk}].def", errors)

    gloss_langs_seen: dict[str, set[str]] = {}
    used_gloss_keys: set[str] = set()
    sep_verb_count = 0
    correct_counts = {0: 0, 1: 0, 2: 0}
    easy_correct_counts = {0: 0, 1: 0, 2: 0}
    hard_correct_counts = {0: 0, 1: 0, 2: 0}
    slot_lang_counts: dict[tuple[int, str], dict[int, int]] = {}
    total_quizzes = 0
    total_hard = 0
    longest_correct_all = 0
    longest_correct_hard = 0
    seen_q_ids = set()

    # 3. Page-by-page checks
    for idx, page in enumerate(spec["pages"], start=1):
        pnum = page["page"]
        if pnum != idx:
            errors.append(f"Page numbering mismatch: index {idx} has page {pnum}")
        odd = (pnum % 2 == 1)
        expected_patch = "bottom" if odd else "top"
        if page.get("patch_pos") != expected_patch:
            errors.append(f"P{pnum:02d}: expected patch_pos={expected_patch}, got {page.get('patch_pos')}")
        if page.get("image") != f"books/petit-prince/wc_p{pnum:02d}.jpg":
            errors.append(f"P{pnum:02d}: unexpected image {page.get('image')}")
        if page.get("display_page") != pnum - 1:
            errors.append(f"P{pnum:02d}: expected display_page={pnum - 1}, got {page.get('display_page')}")

        if page.get("is_frontispiece"):
            if pnum != 1:
                errors.append(f"P{pnum:02d}: only page 1 may be frontispiece")
            if page.get("speech_bubble") is not None:
                errors.append("P01 frontispiece must have speech_bubble=None")
            if page.get("questions") is not None:
                errors.append("P01 frontispiece must have questions=None")
            if page.get("hover_reveal_image") is not None:
                errors.append("P01 frontispiece must not have hover_reveal_image")
            for tier in TIERS:
                if page["translations"]["en"][tier]["text"] != "":
                    errors.append(f"P01 frontispiece translations.en.{tier} must be empty")
                for lang in SUPPORTED_LANGS:
                    lvl = page["levels"][tier][lang]
                    if lvl["text"] != "" or lvl["tokens"] != [] or lvl["audio_mp3"] != "" or lvl["audio_ogg"] != "":
                        errors.append(f"P01 frontispiece levels.{tier}.{lang} must be empty")
            continue

        ba = page.get("bubble_anchor", {})
        for req_k in ("x", "y", "tail", "maxW", "top", "left", "tailLeft"):
            if req_k not in ba:
                errors.append(f"P{pnum:02d}: bubble_anchor missing '{req_k}'")

        # Titles & speech bubbles
        for lang in ALL_TEXT_LANGS:
            t_txt = page["title"][lang]
            tw = len(WORD_RE.findall(t_txt))
            ts = len(t_txt.split())
            if not (3 <= tw <= 7 and 3 <= ts <= 7 and len(t_txt) <= 48):
                errors.append(f"P{pnum:02d} title.{lang} out of budget ({tw}w/{ts}sp/{len(t_txt)}c): {t_txt!r}")

            sb_obj = page["speech_bubble"][lang]
            if lang == "en":
                if "audio_mp3" in sb_obj or "audio_ogg" in sb_obj or not sb_obj.get("is_browser_tts"):
                    errors.append(f"P{pnum:02d} speech_bubble.en must have is_browser_tts=True and NO audio files")
                check_en_gb(sb_obj["text"], f"P{pnum:02d}.speech_bubble.en", errors)
            else:
                if not sb_obj.get("audio_mp3", "").endswith(f"{lang}_bubble_p{pnum:02d}.mp3"):
                    errors.append(f"P{pnum:02d} speech_bubble.{lang} invalid audio_mp3")
                if not sb_obj.get("audio_ogg", "").endswith(f"{lang}_bubble_p{pnum:02d}.ogg"):
                    errors.append(f"P{pnum:02d} speech_bubble.{lang} invalid audio_ogg")

            sb_txt = sb_obj["text"]
            sw = len(WORD_RE.findall(sb_txt))
            if not (5 <= sw <= 14 and len(sb_txt) <= 80):
                errors.append(f"P{pnum:02d} speech_bubble.{lang} out of budget ({sw}w/{len(sb_txt)}c): {sb_txt!r}")

        check_en_gb(page["title"]["en"], f"P{pnum:02d}.title.en", errors)

        # Tiers x Languages
        for tier in TIERS:
            if tier == "seby":
                wmin, wmax, cmin, cmax = (14, 22, 65, 130) if odd else (14, 20, 65, 120)
            elif tier == "ale":
                wmin, wmax, cmin, cmax = (26, 40, 155, 240) if odd else (26, 38, 150, 225)
            else:
                wmin, wmax, cmin, cmax = (40, 58, 250, 390) if odd else (40, 54, 250, 365)

            # Check en translation
            en_tr = page["translations"]["en"][tier]
            if "audio_mp3" in en_tr or "audio_ogg" in en_tr:
                errors.append(f"P{pnum:02d} translations.en.{tier} must NOT contain audio fields")
            en_txt = en_tr["text"]
            check_en_gb(en_txt, f"P{pnum:02d}.translations.en.{tier}", errors)
            rw = len(WORD_RE.findall(en_txt))
            sp = len(en_txt.split())
            ch = len(en_txt)
            if not (wmin <= rw <= wmax and wmin <= sp <= wmax and cmin <= ch <= cmax):
                errors.append(f"P{pnum:02d} {tier}.en out of budget: rw={rw}, sp={sp}, ch={ch} vs ({wmin}-{wmax}w, {cmin}-{cmax}c)")

            # Check FR/IT/DE learning texts & tokens
            for lang in SUPPORTED_LANGS:
                lvl = page["levels"][tier][lang]
                if not lvl.get("audio_mp3", "").endswith(f"{lang}_{tier}_p{pnum:02d}.mp3"):
                    errors.append(f"P{pnum:02d} levels.{tier}.{lang} invalid audio_mp3")
                if not lvl.get("audio_ogg", "").endswith(f"{lang}_{tier}_p{pnum:02d}.ogg"):
                    errors.append(f"P{pnum:02d} levels.{tier}.{lang} invalid audio_ogg")

                txt = lvl["text"]
                rw = len(WORD_RE.findall(txt))
                sp = len(txt.split())
                ch = len(txt)
                if not (wmin <= rw <= wmax and wmin <= sp <= wmax and cmin <= ch <= cmax):
                    errors.append(f"P{pnum:02d} {tier}.{lang} out of budget: rw={rw}, sp={sp}, ch={ch} vs ({wmin}-{wmax}w, {cmin}-{cmax}c)")

                toks = lvl["tokens"]
                if len(toks) != sp:
                    errors.append(f"P{pnum:02d} {tier}.{lang} tokens len {len(toks)} != split len {sp}")

                sep_groups: dict[str, list[tuple[int, dict]]] = {}
                for t_idx, tok in enumerate(toks):
                    if tok["clean"] == "word":
                        errors.append(f"P{pnum:02d} {tier}.{lang} dummy punctuation token {tok['w']!r}")
                    if lang == "de":
                        if "g" in tok:
                            errors.append(f"P{pnum:02d} {tier}.de token {tok['w']!r} must NEVER emit gender 'g'")
                        if len(strip_outer(tok["w"])) > 24:
                            errors.append(f"P{pnum:02d} {tier}.de token {tok['w']!r} exceeds 24 chars")
                    else:
                        core_len = len(strip_outer(tok["w"]))
                        if tok["pos"] in ("noun", "adj") and core_len >= 3 and tok.get("g") not in ("m", "f"):
                            errors.append(f"P{pnum:02d} {tier}.{lang} token {tok['w']!r} missing valid gender 'g'")
                        if core_len < 3 and "g" in tok:
                            errors.append(f"P{pnum:02d} {tier}.{lang} short token {tok['w']!r} must NOT emit 'g'")

                    lem = extract_lemma(tok["w"])
                    if lem in en_gloss:
                        gloss_langs_seen.setdefault(lem, set()).add(lang)
                        used_gloss_keys.add(lem)
                    if tok["clean"] in en_gloss:
                        gloss_langs_seen.setdefault(tok["clean"], set()).add(lang)
                        used_gloss_keys.add(tok["clean"])
                    if "gloss" in tok:
                        check_en_gb(tok["gloss"].get("tr", ""), f"P{pnum:02d}.{tier}.{lang}.tok[{t_idx}].gloss.tr", errors)
                        check_en_gb(tok["gloss"].get("def", ""), f"P{pnum:02d}.{tier}.{lang}.tok[{t_idx}].gloss.def", errors)

                    if "sep_group" in tok:
                        sep_groups.setdefault(tok["sep_group"], []).append((t_idx, tok))

                for gid, items in sep_groups.items():
                    if len(items) != 2:
                        errors.append(f"P{pnum:02d} {tier}.de sep_group {gid} has {len(items)} tokens, expected 2")
                        continue
                    (i1, t1), (i2, t2) = items
                    if t1.get("sep_role") != "stem" or t2.get("sep_role") != "prefix" or i2 <= i1:
                        errors.append(f"P{pnum:02d} {tier}.de sep_group {gid} invalid role/order")
                    sinf = t1.get("sep_inf")
                    if sinf not in en_gloss:
                        errors.append(f"P{pnum:02d} {tier}.de sep_inf {sinf!r} missing from en_gloss")
                    else:
                        used_gloss_keys.add(sinf)
                    sep_verb_count += 1

        # Quizzes
        qs = page.get("questions")
        if odd:
            if qs is not None:
                errors.append(f"P{pnum:02d} (odd) must have questions=None")
        else:
            if not isinstance(qs, dict) or set(qs.keys()) != {"fr", "it", "de"}:
                errors.append(f"P{pnum:02d} (even) must have questions for fr/it/de only")
            else:
                for lang in SUPPORTED_LANGS:
                    q_list = qs[lang]
                    if len(q_list) != 3:
                        errors.append(f"P{pnum:02d} questions.{lang} must have 3 items")
                        continue
                    diffs = [q["difficulty"] for q in q_list]
                    if diffs != ["easy", "easy", "hard"]:
                        errors.append(f"P{pnum:02d} questions.{lang} difficulties must be ['easy','easy','hard'], got {diffs}")
                    for qi, q in enumerate(q_list, start=1):
                        exp_id = f"pp_p{pnum:02d}_q{qi}"
                        if q["id"] != exp_id:
                            errors.append(f"P{pnum:02d} questions.{lang}[{qi-1}] id {q['id']!r} != {exp_id!r}")
                        if (lang, q["id"]) in seen_q_ids:
                            errors.append(f"Duplicate question id {(lang, q['id'])}")
                        seen_q_ids.add((lang, q["id"]))
                        opts = q["options"]
                        if len(opts) != 3 or len(set(opts)) != 3:
                            errors.append(f"P{pnum:02d} {q['id']} ({lang}) must have 3 distinct options")
                        if q["correct"] not in (0, 1, 2):
                            errors.append(f"P{pnum:02d} {q['id']} ({lang}) invalid correct index {q['correct']}")
                        else:
                            cidx = q["correct"]
                            correct_counts[cidx] += 1
                            total_quizzes += 1
                            if q["difficulty"] == "easy":
                                easy_correct_counts[cidx] += 1
                            else:
                                hard_correct_counts[cidx] += 1
                                total_hard += 1
                            sl_dict = slot_lang_counts.setdefault((qi, lang), {0: 0, 1: 0, 2: 0})
                            sl_dict[cidx] += 1

                            opt_lens = [len(o) for o in opts]
                            c_len = opt_lens[cidx]
                            max_other = max(opt_lens[k] for k in range(3) if k != cidx)
                            if c_len > max_other:
                                longest_correct_all += 1
                                if q["difficulty"] == "hard":
                                    longest_correct_hard += 1

    if sep_verb_count < 20:
        errors.append(f"Expected >= 20 German separable verb pairs across book, found {sep_verb_count}")

    for lem, langs in gloss_langs_seen.items():
        if len(langs) > 1:
            errors.append(f"Cross-language homograph collision in en_gloss key {lem!r} used in {sorted(langs)}")

    unused_gloss = sorted(k for k in en_gloss if k not in used_gloss_keys)
    if unused_gloss:
        errors.append(f"Unused en_gloss keys: {unused_gloss}")

    if easy_correct_counts != {0: 26, 1: 26, 2: 26}:
        errors.append(f"Easy quiz 'correct' index distribution must be 26/26/26, got {easy_correct_counts}")
    if hard_correct_counts != {0: 13, 1: 13, 2: 13}:
        errors.append(f"Hard quiz 'correct' index distribution must be 13/13/13, got {hard_correct_counts}")
    for (qi, lang), counts in sorted(slot_lang_counts.items()):
        if sum(counts.values()) != 13 or set(counts.values()) != {4, 5}:
            errors.append(f"Quiz slot q{qi}.{lang} 'correct' distribution must be balanced {{4,5}} across 13 spreads, got {counts}")

    if total_quizzes > 0:
        pct_all = longest_correct_all / total_quizzes
        if pct_all > 0.40:
            errors.append(f"Quiz strictly-longest correct rate {pct_all:.1%} ({longest_correct_all}/{total_quizzes}) exceeds 40% limit")
    if total_hard > 0:
        pct_hard = longest_correct_hard / total_hard
        if pct_hard > 0.45:
            errors.append(f"Hard quiz strictly-longest correct rate {pct_hard:.1%} ({longest_correct_hard}/{total_hard}) exceeds 45% limit")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile and validate Le Petit Prince content_spec.json")
    parser.add_argument("--check-only", action="store_true", help="Validate without writing content_spec.json")
    args = parser.parse_args()

    spec = compile_content_spec()
    errors = validate_content_spec(spec)
    if errors:
        print(f"❌ Validation FAILED with {len(errors)} error(s):", file=sys.stderr)
        for err in errors[:40]:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if not args.check_only:
        BOOK_DIR.mkdir(parents=True, exist_ok=True)
        CONTENT_SPEC_PATH.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Print deterministic summary metrics
    total_tokens = {l: 0 for l in SUPPORTED_LANGS}
    total_sep = 0
    total_quizzes = 0
    correct_dist = {0: 0, 1: 0, 2: 0}
    for p in spec["pages"]:
        for tier in TIERS:
            for l in SUPPORTED_LANGS:
                toks = p["levels"][tier][l]["tokens"]
                total_tokens[l] += len(toks)
                if l == "de":
                    total_sep += sum(1 for t in toks if t.get("sep_role") == "stem")
        if p["questions"]:
            for l in SUPPORTED_LANGS:
                for q in p["questions"][l]:
                    total_quizzes += 1
                    correct_dist[q["correct"]] += 1

    print(f"✅ Compiled and validated {CONTENT_SPEC_PATH.relative_to(ROOT)} cleanly!")
    print(f"   Pages: {spec['total_pages']} | Supported langs: {spec['supported_langs']} | Default: {spec['default_lang']}")
    print(f"   Tokens compiled: FR={total_tokens['fr']}, IT={total_tokens['it']}, DE={total_tokens['de']}")
    print(f"   DE separable verb pairs: {total_sep} | en_gloss entries: {len(spec['en_gloss'])}")
    print(f"   Antolin questions: {total_quizzes} (correct index distribution: {correct_dist})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
