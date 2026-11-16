#!/usr/bin/env python3
"""
Builds the complete static Illustrated Kids Book & Antolin Comprehension bundle for:
  - Story 7: storia-sardegna-cala-gonone-arbatax-famiglia (16 pages)
  - Languages: Italian (it), French (fr), German (de)
  - Levels: Seby (6-7 yo, 1-2 short sentences) & Ale (8-9 yo, 2-3 richer sentences)
  - Watercolor illustrations with negative-space white patches: wc_p01.jpg .. wc_p16.jpg
  - Montessori POS + Gender Ending metadata (o/a/i/e)
  - Expressive multi-word sentences & speech bubbles via Gemini 3.8 Flash TTS (Aoede)
"""

import asyncio
import base64
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
STORY_DIR = ROOT / "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia"
KIDS_AUDIO_DIR = STORY_DIR / "kids_audio"
WORDS_AUDIO_IT = ROOT / "assets/words_audio/it"
WORDS_AUDIO_FR = ROOT / "assets/words_audio/fr"
WORDS_AUDIO_DE = ROOT / "assets/words_audio/de"

for d in (KIDS_AUDIO_DIR, WORDS_AUDIO_IT, WORDS_AUDIO_FR, WORDS_AUDIO_DE):
    d.mkdir(parents=True, exist_ok=True)

VOICE_IT = "it-IT-IsabellaNeural"
VOICE_FR = "fr-FR-eloiseNeural"
VOICE_DE = "de-DE-KatjaNeural"

# Load GEMINI_API_KEY2 or GEMINI_API_KEY_FREE_TTS_STT from ~/git/gic/.env.gprism
GEMINI_KEYS = []
gprism_path = Path("/home/riccardo/git/gic/.env.gprism")
if gprism_path.exists():
    env_txt = gprism_path.read_text(encoding="utf-8")
    for kname, kval in re.findall(r"^([A-Z0-9_]*GEMINI[A-Z0-9_]*)=[\"']?(AIza[A-Za-z0-9_-]+)", env_txt, re.M):
        if kname in ("GEMINI_API_KEY2", "GEMINI_API_KEY_FREE_TTS_STT") and kval not in GEMINI_KEYS:
            GEMINI_KEYS.append(kval)

STYLE_IT = (
    "Dolce, calda, sinuosa, affettuosa e giocosa maestra delle elementari italiana "
    "che legge una fiaba illustrata ai bambini con tantissimo pathos, meraviglia, "
    "musicalità, incanto e un sorriso affettuoso nella voce"
)
STYLE_FR = (
    "Douce, chaleureuse, mélodieuse, affectueuse et enjouée maîtresse d'école primaire française "
    "qui lit un conte illustré aux enfants avec beaucoup d'expression, d'émerveillement et un sourire dans la voix"
)
STYLE_DE = (
    "Liebevolle, warme, melodische, ausdrucksstarke und verspielte Grundschullehrerin, "
    "die Kindern ein Bilderbuch mit viel Gefühl, Staunen und einem Lächeln in der Stimme vorliest"
)

GLOSSARY_IT = {
    "aeroporto": {"pos": "noun", "tr": "l'aéroport / der Flughafen", "def": "Il luogo dove atterrano e decollano gli aeroplani."},
    "olbia": {"pos": "noun", "tr": "Olbia (città del nord Sardegna)", "def": "La città della Sardegna dove si trova l'aeroporto in cui atterra la famiglia!"},
    "sardegna": {"pos": "noun", "tr": "la Sardaigne / Sardinien", "def": "Una grande isola bellissima nel mezzo del Mar Mediterraneo."},
    "mirto": {"pos": "noun", "tr": "le myrte / die Myrte", "def": "Pianta profumatissima con bacche scure tipica della Sardegna."},
    "cugino": {"pos": "noun", "tr": "le cousin / der Cousin", "def": "Il figlio degli zii: il cugino Massimo è uno dei pochi Carlesso rimasti!"},
    "massimo": {"pos": "noun", "tr": "Cugino Massimo Carlesso", "def": "L'amatissimo cugino di Papino Riccardo che la famiglia va a trovare in Sardegna!"},
    "cala": {"pos": "noun", "tr": "la crique / die Bucht", "def": "Una piccola baia nascosta tra le rocce dove il mare è calmo."},
    "turchese": {"pos": "adj", "tr": "turquoise / türkis", "def": "Un colore azzurro-verde brillante come una pietra preziosa."},
    "trasparente": {"pos": "adj", "tr": "transparente / glasklar", "def": "Così limpida che si vede il fondo del mare come attraverso un vetro."},
    "sabbia": {"pos": "noun", "tr": "le sable / der Sand", "def": "Tanti granellini dorati e morbidi sulla riva del mare."},
    "scogli": {"pos": "noun", "tr": "les rochers / die Felsen", "def": "Grandi rocce bagnate dalle onde del mare."},
    "ponti": {"pos": "noun", "tr": "les ponts / die Brücken", "def": "Passerelle sospese tra gli alberi per camminare in alto."},
    "sospesi": {"pos": "adj", "tr": "suspendus / schwebend", "def": "Appesi in aria tra i rami senza toccare terra."},
    "corde": {"pos": "noun", "tr": "les cordes / die Seile", "def": "Funi robuste intrecciate per tenersi in equilibrio."},
    "casco": {"pos": "noun", "tr": "le casque / der Helm", "def": "Cappello duro che protegge la testa durante le avventure."},
    "terrazza": {"pos": "noun", "tr": "la terrasse / die Terrasse", "def": "Un balcone grande all'aperto da cui si guarda il mare."},
    "tramonto": {"pos": "noun", "tr": "le coucher du soleil / der Sonnenuntergang", "def": "Il momento della sera in cui il sole scende nel mare e colora il cielo d'oro."},
    "luna": {"pos": "noun", "tr": "la lune / der Mond", "def": "Brilla nel cielo di notte e illumina il mare d'argento."},
    "gommone": {"pos": "noun", "tr": "le bateau pneumatique / das Schlauchboot", "def": "Una barca veloce con i bordi gonfiabili che salta sulle onde."},
    "golfo": {"pos": "noun", "tr": "le golfe / der Golf", "def": "Una grande insenatura del mare abbracciata dalle montagne."},
    "falesie": {"pos": "noun", "tr": "les falaises / die Klippen", "def": "Altissime pareti di roccia bianca che scendono dritte nel mare blu."},
    "guglia": {"pos": "noun", "tr": "l'aiguille rocheuse / die Felsnadel", "def": "Una punta di roccia altissima che svetta verso il cielo a Cala Goloritzè."},
    "salvagenti": {"pos": "noun", "tr": "les gilets / die Schwimmwesten", "def": "Giubbotti arancioni che tengono a galla sull'acqua."},
    "tuffano": {"pos": "verb", "tr": "ils plongent / sie springen ins Wasser", "def": "Saltano con entusiasmo dentro l'acqua facendo un grande splash!"},
    "grotte": {"pos": "noun", "tr": "les grottes / die Meeresgrotten", "def": "Caverne naturali scavate dalle onde dentro la montagna."},
    "sentieri": {"pos": "noun", "tr": "les sentiers / die Wanderwege", "def": "Piccole strade di pietra e terra in mezzo alla natura."},
    "sentiero": {"pos": "noun", "tr": "le sentier / der Pfad", "def": "Piccolo cammino tra le rocce e gli alberi della montagna."},
    "supramonte": {"pos": "noun", "tr": "le Supramonte", "def": "Le montagne selvagge e bianche nel cuore della Sardegna."},
    "ginepro": {"pos": "noun", "tr": "le genévrier / der Wacholder", "def": "Albero profumato della Sardegna con il legno forte e contorto."},
    "ginepri": {"pos": "noun", "tr": "les genévriers / die Wacholderbäume", "def": "Alberi profumati che crescono tra le rocce della Sardegna."},
    "panorama": {"pos": "noun", "tr": "le panorama / das Panorama", "def": "La vista grandissima che si ammira dalla cima di una montagna."},
    "valli": {"pos": "noun", "tr": "les vallées / die Täler", "def": "Conche verdi tra le montagne."},
    "arco": {"pos": "noun", "tr": "l'arc / der Bogen", "def": "Strumento con una corda tesa per lanciare le frecce verso il bersaglio."},
    "frecce": {"pos": "noun", "tr": "les flèches / die Pfeile", "def": "Bastoncini appuntiti con le piume che volano veloci."},
    "bersaglio": {"pos": "noun", "tr": "la cible / die Zielscheibe", "def": "Il cerchio colorato da colpire al centro con la freccia."},
    "asinello": {"pos": "noun", "tr": "le petit âne / der kleine Esel", "def": "Un piccolo asino dolce e morbido con le orecchie lunghe."},
    "accarezza": {"pos": "verb", "tr": "il caresse / er streichelt", "def": "Tocca piano piano con la mano per fare le coccole."},
    "muso": {"pos": "noun", "tr": "le museau / die Schnauze", "def": "La punta morbida del naso e della bocca dell'asinello."},
    "granito": {"pos": "noun", "tr": "le granit / der Granit", "def": "Roccia durissima e brillante, che ad Arbatax è tutta color rosa!"},
    "maschera": {"pos": "noun", "tr": "le masque / die Taucherbrille", "def": "Occhiali grandi per vedere chiaramente sott'acqua."},
    "boccaglio": {"pos": "noun", "tr": "le tuba / der Schnorchel", "def": "Il tubo per respirare mentre si guarda sott'acqua."},
    "pesciolini": {"pos": "noun", "tr": "les petits poissons / die kleinen Fische", "def": "Piccoli pesci curiosi che nuotano in branco vicino agli scogli."},
    "argentati": {"pos": "adj", "tr": "argentés / silbern glänzend", "def": "Che brillano come l'argento sotto i raggi del sole."},
    "cristallina": {"pos": "adj", "tr": "cristalline / kristallklar", "def": "Pura e trasparente proprio come un cristallo prezioso."},
    "egitto": {"pos": "noun", "tr": "l'Égypte / Ägypten", "def": "Il paese del Mar Rosso e delle piramidi dove Papino porterà Ale e Seby!"},
    "barriera": {"pos": "noun", "tr": "la barrière de corail / das Korallenriff", "def": "Una scogliera sottomarina piena di coralli colorati e pesci tropicali."},
    "corallina": {"pos": "adj", "tr": "de corail / aus Korallen", "def": "Fatta di coralli coloratissimi in fondo al mare caldo."},
    "promessa": {"pos": "noun", "tr": "la promesse / das Versprechen", "def": "Quando si dà la parola d'onore che si farà qualcosa di bellissimo!"},
}

GLOSSARY_FR = {
    "aéroport": {"pos": "noun", "tr": "l'aeroporto", "def": "L'endroit où les avions atterrissent et décollent."},
    "olbia": {"pos": "noun", "tr": "Olbia", "def": "La ville du nord de la Sardaigne où se trouve l'aéroport."},
    "sardaigne": {"pos": "noun", "tr": "la Sardegna", "def": "Une grande île magnifique au milieu de la mer Méditerranée."},
    "myrte": {"pos": "noun", "tr": "il mirto", "def": "Plante parfumée typique de la Sardaigne."},
    "cousin": {"pos": "noun", "tr": "il cugino", "def": "Le cousin Massimo est le cousin de Papino Riccardo !"},
    "massimo": {"pos": "noun", "tr": "Cugino Massimo Carlesso", "def": "Le cousin de Papino Riccardo, l'un des rares Carlesso !"},
    "crique": {"pos": "noun", "tr": "la caletta / baia", "def": "Petite baie cachée entre les rochers au bord de l'eau."},
    "turquoise": {"pos": "adj", "tr": "turchese", "def": "Couleur bleu-vert brillante comme une pierre précieuse."},
    "transparente": {"pos": "adj", "tr": "trasparente", "def": "Si claire qu'on voit tout le fond de la mer."},
    "sable": {"pos": "noun", "tr": "la sabbia", "def": "Petits grains doux et dorés sur la plage."},
    "rochers": {"pos": "noun", "tr": "gli scogli", "def": "Grandes pierres au bord de la mer."},
    "ponts": {"pos": "noun", "tr": "i ponti", "def": "Passerelles suspendues entre les arbres."},
    "suspendus": {"pos": "adj", "tr": "sospesi", "def": "Accrochés en haut dans les arbres."},
    "cordes": {"pos": "noun", "tr": "le corde", "def": "Gros fils tressés pour tenir en équilibre."},
    "casque": {"pos": "noun", "tr": "il casco", "def": "Chapeau dur qui protège la tête."},
    "terrasse": {"pos": "noun", "tr": "la terrazza", "def": "Grand balcon ouvert avec vue sur la mer."},
    "coucher": {"pos": "noun", "tr": "il tramonto", "def": "Moment où le soleil descend dans la mer le soir."},
    "lune": {"pos": "noun", "tr": "la luna", "def": "Elle brille dans le ciel pendant la nuit."},
    "bateau": {"pos": "noun", "tr": "la barca / il gommone", "def": "Embarcation qui flotte et file sur les vagues."},
    "golfe": {"pos": "noun", "tr": "il golfo", "def": "Grande baie où la mer entre dans la côte."},
    "falaises": {"pos": "noun", "tr": "le falesie", "def": "Murs de roche très hauts au-dessus de la mer."},
    "gilets": {"pos": "noun", "tr": "i giubbotti salvagente", "def": "Vestes orange qui permettent de flotter sur l'eau."},
    "plongent": {"pos": "verb", "tr": "si tuffano", "def": "Sautent dans l'eau en faisant un grand plouf !"},
    "grottes": {"pos": "noun", "tr": "le grotte", "def": "Cavernes creusées par la mer dans la roche."},
    "sentier": {"pos": "noun", "tr": "il sentiero", "def": "Petit chemin à travers la montagne et la forêt."},
    "genévrier": {"pos": "noun", "tr": "il ginepro", "def": "Arbre parfumé au bois tordu par le vent."},
    "arc": {"pos": "noun", "tr": "l'arco", "def": "Instrument avec une corde tendue pour tirer des flèches."},
    "flèches": {"pos": "noun", "tr": "le frecce", "def": "Bâtons pointus qui volent vers la cible."},
    "cible": {"pos": "noun", "tr": "il bersaglio", "def": "Le cercle coloré qu'il faut viser au centre."},
    "âne": {"pos": "noun", "tr": "l'asinello", "def": "Petit animal doux avec de longues oreilles."},
    "caresse": {"pos": "verb", "tr": "accarezza", "def": "Touche doucement avec la main."},
    "museau": {"pos": "noun", "tr": "il muso", "def": "Le bout du nez tout doux des animaux."},
    "granit": {"pos": "noun", "tr": "il granito", "def": "Roche très dure de couleur rose à Arbatax."},
    "masque": {"pos": "noun", "tr": "la maschera", "def": "Lunettes larges pour voir les poissons sous l'eau."},
    "tuba": {"pos": "noun", "tr": "il boccaglio", "def": "Tube pour respirer la tête dans l'eau."},
    "poissons": {"pos": "noun", "tr": "i pesciolini", "def": "Animaux qui nagent sous l'eau."},
    "argentés": {"pos": "adj", "tr": "argentati", "def": "Qui brillent comme de l'argent sous le soleil."},
    "cristalline": {"pos": "adj", "tr": "cristallina", "def": "Pure et claire comme du cristal."},
    "égypte": {"pos": "noun", "tr": "l'Egitto", "def": "Le pays des pyramides et de la mer Rouge."},
    "corail": {"pos": "noun", "tr": "il corallo", "def": "Jardin sous-marin multicolore où habitent les poissons."},
    "promesse": {"pos": "noun", "tr": "la promessa", "def": "Parole spéciale qu'on tient toujours !"},
}

GLOSSARY_DE = {
    "flughafen": {"pos": "noun", "tr": "l'aeroporto", "def": "Der Ort, an dem die Flugzeuge landen und starten."},
    "olbia": {"pos": "noun", "tr": "Olbia", "def": "Die Stadt im Norden Sardiniens, wo der Flughafen liegt."},
    "sardinien": {"pos": "noun", "tr": "la Sardegna", "def": "Eine wunderschöne große Insel im Mittelmeer."},
    "myrte": {"pos": "noun", "tr": "il mirto", "def": "Eine typisch sardische, herrlich duftende Pflanze."},
    "cousin": {"pos": "noun", "tr": "il cugino", "def": "Cousin Massimo ist einer der wenigen verbleibenden Carlessos!"},
    "massimo": {"pos": "noun", "tr": "Cugino Massimo Carlesso", "def": "Papinos lieber Cousin Massimo in Sardinien!"},
    "türkis": {"pos": "adj", "tr": "turchese", "def": "Blaugrün leuchtend wie ein Edelstein."},
    "sand": {"pos": "noun", "tr": "la sabbia", "def": "Weiche, goldene Körnchen am Meeresstrand."},
    "felsen": {"pos": "noun", "tr": "gli scogli", "def": "Große Steine und Klippen am Meer."},
    "hängebrücken": {"pos": "noun", "tr": "i ponti sospesi", "def": "Brücken aus Seilen hoch oben zwischen den Bäumen."},
    "helm": {"pos": "noun", "tr": "il casco", "def": "Schützt den Kopf beim Klettern im Abenteuerpark."},
    "vollmond": {"pos": "noun", "tr": "la luna piena", "def": "Der runde, hell leuchtende Mond am Nachthimmel."},
    "schlauchboot": {"pos": "noun", "tr": "il gommone", "def": "Ein schnelles Boot mit Luftkammern für Ausflüge auf dem Meer."},
    "klippen": {"pos": "noun", "tr": "le falesie", "def": "Hohe weiße Felswände direkt über dem blauen Meer."},
    "schwimmwesten": {"pos": "noun", "tr": "i salvagenti", "def": "Orangefarbene Westen, mit denen man sicher im Wasser schwimmt."},
    "meeresgrotten": {"pos": "noun", "tr": "le grotte marine", "def": "Geheimnisvolle Höhlen, die das Meer in den Fels gegraben hat."},
    "wacholder": {"pos": "noun", "tr": "il ginepro", "def": "Duftender Baum in den Bergen des Supramonte."},
    "bogen": {"pos": "noun", "tr": "l'arco", "def": "Sportgerät zum Pfeilschießen auf die Zielscheibe."},
    "zielscheibe": {"pos": "noun", "tr": "il bersaglio", "def": "Der bunte Kreis, den Mama Kate genau in der Mitte trifft."},
    "esel": {"pos": "noun", "tr": "l'asinello", "def": "Ein sanftes sardisches Tier mit langen, weichen Ohren."},
    "taucherbrille": {"pos": "noun", "tr": "la maschera", "def": "Brille, mit der man unter Wasser die Fische klar sieht."},
    "schnorchel": {"pos": "noun", "tr": "il boccaglio", "def": "Rohr zum Atmen, während man mit dem Kopf unter Wasser schwimmt."},
    "fische": {"pos": "noun", "tr": "i pesciolini", "def": "Tausend kleine silberne Fische in den Buchten von Arbatax."},
    "ägypten": {"pos": "noun", "tr": "l'Egitto", "def": "Das Land am Roten Meer mit dem großen Korallenriff."},
    "korallenriff": {"pos": "noun", "tr": "la barriera corallina", "def": "Ein bunter Unterwassergarten voller Korallen und Fische."},
}

IT_NOUNS = {
    "papino", "mamma", "kate", "nonna", "lucilla", "ale", "seby", "alessandro", "sebastian",
    "porto", "nave", "mare", "sole", "vento", "isola", "vacanza", "vacanze", "famiglia", "fratelli",
    "spiaggia", "acqua", "onde", "pesci", "alberi", "rami", "bosco", "cena", "tavolo", "tavola",
    "sera", "notte", "stelle", "cielo", "barca", "capitano", "costa", "roccia", "rocce",
    "punta", "montagna", "montagne", "scarponcini", "zaino", "cima", "natura", "aria",
    "parco", "animali", "orecchie", "maglia", "numero", "baia", "baie", "albergo",
    "fondale", "occhi", "meraviglia", "volta", "viaggio", "estate", "avventura", "sorriso",
    "bagno", "testa", "pini", "luci", "racconti", "mattina", "capelli", "curva", "pietra",
    "profumo", "timo", "spalla", "silenzio", "cespugli", "mira", "centro", "amicizia",
    "ulivi", "tiri", "momento", "sasso", "cuore", "sogno", "argento", "giorno", "diamanti",
    "salvagente", "asinelli", "gonone", "orosei", "goloritzè", "aereo", "valigie", "carlesso", "parenti"
}
IT_VERBS = {
    "arriva", "arrivano", "atterra", "scende", "scendono", "sorride", "sorridono", "guarda", "guardano",
    "corrono", "corre", "nuota", "nuotano", "gioca", "giocano", "ride", "ridono", "salgono",
    "cammina", "camminano", "attraversa", "attraversano", "mangiano", "cenano", "brilla", "brillano",
    "splende", "guida", "naviga", "navigano", "vola", "volare", "salta", "saltano", "indossa",
    "indossano", "arrampicano", "esplorano", "tira", "mira", "colpisce", "mette", "mettono",
    "vedono", "vede", "dice", "promette", "porterà", "porterò", "sognano", "abbraccia", "abbracciano",
    "esclama", "apre", "aprono", "respirano", "nuotare", "vedere", "scoprire", "scoprono",
    "ascolta", "specchia", "ammirano", "ammira", "svetta", "sembra", "passa", "rivela",
    "sale", "fermano", "soffia", "prende", "lancia", "fanno", "applaudono", "coccolano",
    "preparano", "tramonta", "portano", "sono", "è", "ha", "hanno", "fa", "saluta", "salutano", "trovano", "incontrano"
}
IT_ADJS = {
    "grande", "grandi", "piccolo", "piccoli", "piccola", "piccole", "bello", "bella", "belli",
    "bellissima", "bellissimo", "azzurro", "azzurra", "blu", "verde", "verdi", "bianco", "bianca",
    "bianche", "rosa", "rosso", "rossa", "arancione", "arancioni", "caldo", "calda", "calde",
    "fresco", "fresca", "limpida", "limpido", "felice", "felici", "contenti", "coraggiosi", "coraggioso",
    "veloce", "veloci", "alti", "alte", "alta", "alto", "altissima", "altissime", "dolce", "dolci",
    "morbido", "morbida", "magico", "magica", "fighissimo", "mille", "tanti", "tante", "bravi",
    "bravissimi", "vera", "vero", "segrete", "segreta", "selvaggia", "selvaggio", "luminosa",
    "luminoso", "piena", "estivo", "calmo", "dorata", "dorati", "primo", "bassa", "chiari",
    "scura", "seguente", "nuova", "forte", "silenzioso", "tiepido", "sardo", "lunghe",
    "immerso", "liberi", "curiosi", "prossima", "prossimo", "orgoglioso", "circondati", "scavate", "illuminata",
    "pochi", "rimasti", "simpatico", "affettuoso"
}
IT_ADVS = {
    "insieme", "molto", "tanto", "presto", "subito", "piano", "velocemente", "lassù",
    "intorno", "sott'acqua", "davvero", "sempre", "oggi", "domani", "già", "ancora", "più",
    "appena", "vicino", "poi", "davanti", "mentre", "invece", "poco", "così", "bene", "talmente"
}

FR_NOUNS = {
    "papa", "papino", "maman", "kate", "mamie", "lucilla", "ale", "seby", "port", "mer",
    "soleil", "vent", "île", "vacances", "famille", "frères", "plage", "eau", "vagues",
    "arbres", "branches", "forêt", "dîner", "table", "soir", "nuit", "étoiles", "ciel",
    "capitaine", "côte", "roche", "montagne", "montagnes", "chaussures", "sommet", "nature",
    "parc", "animaux", "oreilles", "maillot", "numéro", "baie", "baies", "hôtel", "fond",
    "yeux", "merveille", "fois", "voyage", "été", "aventure", "sourire", "olbia", "arbatax",
    "supramonte", "air", "baignade", "diamants", "tête", "lumières", "histoires", "lune",
    "lendemain", "matin", "aiguille", "gilet", "cheveux", "virage", "pierre", "parfum",
    "paysage", "panorama", "silence", "cible", "amis", "oliviers", "tir", "moment",
    "enfants", "cœur", "rêve", "gonone", "orosei", "goloritzè", "bonheur", "avion", "carlesso"
}
FR_VERBS = {
    "arrive", "arrivent", "atterrit", "descend", "descendent", "sourit", "sourient", "regarde", "regardent",
    "courent", "court", "nage", "nagent", "joue", "jouent", "rit", "rient", "montent", "monte",
    "marche", "marchent", "traverse", "traversent", "mangent", "dînent", "dîne", "brille", "brillent",
    "conduit", "navigue", "naviguent", "vole", "voler", "saute", "sautent", "porte", "portent",
    "grimpent", "explorent", "tire", "vise", "touche", "met", "mettent", "voient", "voit",
    "dit", "promet", "emmènera", "emmènerai", "rêvent", "embrasse", "embrassent", "est", "sont",
    "a", "ont", "fait", "font", "sent", "découvrent", "écoute", "reflète", "admirent", "admire",
    "dresse", "semble", "passe", "révèle", "arrêtent", "souffle", "lance", "deviennent",
    "applaudissent", "câlinent", "préparent", "exclame", "couche", "retrouve", "retrouvent", "salue"
}
FR_ADJS = {
    "grand", "grande", "grands", "grandes", "petit", "petite", "petits", "petites",
    "beau", "belle", "beaux", "belles", "magnifique", "bleu", "bleue", "vert", "verte",
    "blanc", "blanche", "blancs", "blanches", "rose", "roses", "rouge", "orange", "chaud",
    "chaude", "chaudes", "frais", "fraîche", "claire", "clair", "clairs", "heureux", "heureuse",
    "contents", "courageux", "rapide", "rapides", "haut", "haute", "hauts", "hautes",
    "doux", "douce", "magique", "super", "mille", "braves", "vraie", "vrai", "secrètes",
    "secrète", "sauvage", "sauvages", "pleine", "lumineux", "calme", "doré", "dorés",
    "première", "profonde", "limpide", "éclairée", "pneumatique", "rocheuse", "marines",
    "fort", "forts", "silencieux", "tiède", "sarde", "longues", "naturel", "prochaine",
    "prochain", "fier", "entourés", "creusées", "rares", "cher"
}
FR_ADVS = {
    "ensemble", "très", "beaucoup", "bientôt", "vite", "doucement", "là-haut", "autour",
    "vraiment", "toujours", "aujourd'hui", "demain", "déjà", "encore", "plus", "bien",
    "courageusement", "seulement", "librement", "loin", "droit", "si", "tout"
}

DE_NOUNS = {
    "papino", "mama", "kate", "oma", "lucilla", "ale", "seby", "flugzeug", "flughafen", "olbia",
    "sardinien", "sardiniens", "norden", "familie", "insel", "myrte", "meer", "strand", "cousin", "massimo", "carlesso", "carlessos",
    "wasser", "wellen", "sonne", "felsen", "bucht", "buchten", "brüder", "diamanten", "bäumen", "helm", "sicherheitshelm",
    "kopf", "seilen", "holz", "terrasse", "abend", "vollmond", "himmel", "nachthimmel", "geschichten", "tisch",
    "schlauchboot", "boot", "golf", "orosei", "klippen", "felsklippen", "felsnadel", "felsbogen", "felsbögen", "steinbögen", "goloritzè", "schwimmwesten",
    "meeresgrotten", "wind", "haaren", "bergen", "berge", "supramonte", "wacholder", "thymian",
    "gipfel", "berggipfel", "aussichtspunkt", "panorama", "täler", "stille", "bogen", "holzbogen", "pfeile", "zielscheibe", "esel",
    "schnauze", "trikot", "italien-trikot", "nummer", "park", "kletterpark", "naturpark", "olivenhain", "arbatax", "olivenbäumen", "blumenwiesen", "ohren", "granit", "granitfelsen",
    "taucherbrille", "taucherbrillen", "schnorchel", "fische", "kieselstein", "ägypten", "korallenriff",
    "versprechen", "sonnenuntergang", "herzen", "traum", "luft", "rucksack", "rucksäcken", "steinpfad", "pfaden", "schulter", "kreis", "mitte", "zehn", "hotels", "reise", "moment", "sonne", "tieren", "tiere", "grund", "küste", "kalkstein", "jahrtausende", "nähe", "wasser", "tag", "morgen", "umarmung", "wiedersehen"
}
DE_VERBS = {
    "landet", "kommen", "kommt", "steigen", "steigt", "riecht", "duftet", "umarmt", "umarmen",
    "begrüßen", "besuchen", "ist", "sind", "laufen", "läuft", "spielen", "spielt", "schwimmen",
    "schwimmt", "lachen", "lacht", "glitzern", "glitzert", "funkeln", "lässt", "tragen", "trägt", "klettern",
    "überqueren", "essen", "leuchtet", "scheint", "lächelt", "hört", "spiegelt", "fährt",
    "fahren", "steuert", "bewundern", "bewundert", "bestaunen", "springen", "fliegen", "schauen", "blicken", "wandern", "gehen",
    "stehen", "weht", "schießt", "spannt", "trifft", "kniet", "streichelt", "streicheln", "klatschen", "setzen", "sehen",
    "sieht", "sagt", "ruft", "verspricht", "träumen", "treten", "stürmen", "ragt", "schweben", "zusieht",
    "zeigen", "gegraben", "haben", "hält", "stellen", "hilft", "beginnt", "kreisen", "nehme", "mitnimmt", "schnorcheln", "versinkt"
}
DE_ADJS = {
    "große", "großen", "großer", "kleine", "kleinen", "kleiner", "weiße", "weißen", "helle",
    "hellen", "glücklich", "glücklichen", "schöne", "schönen", "türkis", "türkisfarbene",
    "warmen", "warme", "warm", "sonnigen", "goldenen", "goldene", "klare", "klaren", "glasklar", "flachen", "mutig", "mutigen", "hohen", "hohe",
    "schnellen", "schnelle", "orangefarbenen", "orangefarbene", "wilden", "wilde", "wilder", "stille", "stillen",
    "grünen", "grüne", "grünen", "weiche", "weichen", "langen", "lange", "langohrige", "rosa", "geheimen",
    "kristallklare", "kristallklaren", "kristallklar", "silberne", "silbernen", "tausend", "stolz", "echtes", "echten", "bunte",
    "ganze", "wenigen", "lieben", "herzlichen", "beiden", "schwankenden", "beleuchteten", "nächsten", "herrlichen",
    "riesigen", "nächster", "steinigen", "felsigen", "blauen", "weiten", "ferne", "gelbe", "sardischen", "alten", "allerschönste", "tollen", "neugierig", "sicher", "geschickt"
}
DE_ADVS = {
    "zusammen", "gemeinsam", "sofort", "oben", "abends", "morgens", "dort", "hier", "unter",
    "sehr", "bald", "wieder", "schon", "direkt", "mitten", "frei", "genau", "daneben"
}

DE_SEPARABLE_VERBS = {
    ("steigt", "aus"): {
        "infinitive": "aus·steigen",
        "tr": "scendere (dall'aereo / da un mezzo)",
        "def": "Verbo separabile (trennbares Verb): «aus·steigen» (steigt … aus) significa scendere dall'aereo, mentre «steigen» da solo vuol dire salire!"
    },
    ("treten", "hinaus"): {
        "infinitive": "hinaus·treten",
        "tr": "uscire fuori (all'aperto)",
        "def": "Verbo separabile (trennbares Verb): «hinaus·treten» (treten … hinaus) significa fare un passo fuori all'aria aperta."
    },
    ("hört", "zu"): {
        "infinitive": "zu·hören",
        "tr": "ascoltare con attenzione",
        "def": "Verbo separabile (trennbares Verb): «zu·hören» (hört … zu) significa ascoltare con attenzione, non solo «hören» (sentire)."
    },
    ("ragt", "empor"): {
        "infinitive": "empor·ragen",
        "tr": "svettare / innalzarsi verso l'alto",
        "def": "Verbo separabile (trennbares Verb): «empor·ragen» (ragt … empor) significa svettare altissimo verso il cielo."
    },
    ("fährt", "vorbei"): {
        "infinitive": "vorbei·fahren",
        "tr": "passare davanti (in barca o auto)",
        "def": "Verbo separabile (trennbares Verb): «vorbei·fahren» (fährt … vorbei) significa passare accanto navigando o guidando."
    },
    ("stellen", "ab"): {
        "infinitive": "ab·stellen",
        "tr": "posare / appoggiare giù",
        "def": "Verbo separabile (trennbares Verb): «ab·stellen» (stellen … ab) significa posare a terra lo zaino."
    },
    ("laufen", "umher"): {
        "infinitive": "umher·laufen",
        "tr": "camminare / gironzolare liberamente",
        "def": "Verbo separabile (trennbares Verb): «umher·laufen» (laufen … umher) significa camminare qua e là in libertà."
    },
    ("setzen", "auf"): {
        "infinitive": "auf·setzen",
        "tr": "indossare / mettersi (maschera o cappello)",
        "def": "Verbo separabile (trennbares Verb): «auf·setzen» (setzen … auf) significa indossare sul viso o sulla testa."
    },
    ("nehme", "mit"): {
        "infinitive": "mit·nehmen",
        "tr": "portare con sé",
        "def": "Verbo separabile (trennbares Verb): «mit·nehmen» (nehme … mit) significa portare qualcuno con sé in viaggio."
    },
}


def classify_word(word_raw: str, lang: str):
    clean = re.sub(r"^[^\wÀ-ÿÄÖÜäöüß]+|[^\wÀ-ÿÄÖÜäöüß]+$", "", word_raw.lower())
    if "'" in clean or "’" in clean:
        parts = re.split(r"['’]", clean)
        clean = parts[-1] if parts[-1] else parts[0]

    pos = "other"
    gloss = None

    if lang == "it":
        if clean in GLOSSARY_IT:
            g = GLOSSARY_IT[clean]
            pos, gloss = g["pos"], {"tr": g["tr"], "def": g["def"]}
        elif clean in IT_NOUNS:
            pos = "noun"
        elif clean in IT_VERBS:
            pos = "verb"
        elif clean in IT_ADJS:
            pos = "adj"
        elif clean in IT_ADVS:
            pos = "adv"
    elif lang == "fr":
        if clean in GLOSSARY_FR:
            g = GLOSSARY_FR[clean]
            pos, gloss = g["pos"], {"tr": g["tr"], "def": g["def"]}
        elif clean in FR_NOUNS:
            pos = "noun"
        elif clean in FR_VERBS:
            pos = "verb"
        elif clean in FR_ADJS:
            pos = "adj"
        elif clean in FR_ADVS:
            pos = "adv"
    elif lang == "de":
        if clean in GLOSSARY_DE:
            g = GLOSSARY_DE[clean]
            pos, gloss = g["pos"], {"tr": g["tr"], "def": g["def"]}
        elif clean in DE_NOUNS:
            pos = "noun"
        elif clean in DE_VERBS:
            pos = "verb"
        elif clean in DE_ADJS:
            pos = "adj"
        elif clean in DE_ADVS:
            pos = "adv"

    # Gender ending detection for nouns & adjectives (blue masculine vs pink feminine desinenza).
    # Only applicable to Italian and French! In German (das Flugzeug, der Flughafen, glücklich),
    # final letters (-g, -n, -h) are NOT masculine/feminine gender endings.
    gender = None
    if pos in ("noun", "adj") and len(clean) >= 3:
        if lang == "it":
            if clean in ("papino", "massimo", "ale", "seby", "alessandro", "sebastian", "mare", "sole", "vento", "porto", "aereo", "gommone", "supramonte", "amore", "cuore", "pesce"):
                gender = "m"
            elif clean in ("mamma", "kate", "nonna", "lucilla", "sardegna", "olbia", "estate", "notte", "luce", "parete"):
                gender = "f"
            elif clean[-1] in ("o", "i"):
                gender = "m"
            elif clean[-1] in ("a", "e"):
                gender = "f"
        elif lang == "fr":
            if clean.endswith(("e", "es", "ion", "ions", "té")):
                gender = "f"
            else:
                gender = "m"

    return pos, gloss, clean, gender


PAGES_SPEC = [
    {
        "page": 1,
        "patch_pos": "bottom",
        "title": {
            "it": "1. Atterraggio all'Aeroporto di Olbia!",
            "fr": "1. Atterrissage à l'Aéroport d'Olbia !",
            "de": "1. Landung am Flughafen von Olbia!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p01.jpg",
        "speech_bubble": {
            "speaker": "Ale & Seby",
            "it": "Evviva! L'aereo è atterrato a Olbia! Sentite che profumo di mirto!",
            "fr": "Hourra ! L'avion a atterri à Olbia ! Sentez ce bon parfum de myrte !",
            "de": "Hurra! Das Flugzeug ist in Olbia gelandet! Riecht ihr den herrlichen Duft von Myrte?"
        },
        "seby": {
            "it": "L'aereo atterra all'aeroporto di Olbia nel nord della Sardegna. Tutta la famiglia scende felice tra i fiori di mirto.",
            "fr": "L'avion atterrit à l'aéroport d'Olbia au nord de la Sardaigne. Toute la famille descend heureuse parmi les fleurs de myrte.",
            "de": "Das Flugzeug landet am Flughafen von Olbia im Norden von Sardinien. Die ganze Familie steigt glücklich aus."
        },
        "ale": {
            "it": "L'aereo atterra nel luminoso aeroporto di Olbia, nel nord della Sardegna. Papino, Mamma Kate, Nonna Lucilla, Ale e Seby escono con le valigie dove l'aria profuma già di mirto selvatico.",
            "fr": "L'avion atterrit dans le lumineux aéroport d'Olbia, au nord de la Sardaigne. Papino, Maman Kate, Mamie Lucilla, Ale et Seby sortent avec leurs valises où l'air sent bon le myrte.",
            "de": "Das Flugzeug landet am sonnigen Flughafen von Olbia im Norden Sardiniens. Papino, Mama Kate, Oma Lucilla, Ale und Seby treten hinaus, wo die warme Luft nach wilder Myrte duftet."
        },
        "questions": {
            "it": [
                {"id": "sard_p01_q1", "difficulty": "easy", "q": "In quale città della Sardegna si trova l'aeroporto dove atterra la famiglia?", "options": ["A Olbia", "A Cala Gonone", "Ad Arbatax"], "correct": 0},
                {"id": "sard_p01_q2", "difficulty": "easy", "q": "Chi parte per questa vacanza in Sardegna insieme a Papino, Mamma Kate, Ale e Seby?", "options": ["Nonna Lucilla", "Solo Papino e Ale", "I compagni di scuola di Zurigo"], "correct": 0},
                {"id": "sard_p01_q3", "difficulty": "hard", "q": "Quale pianta profumata tipica della Sardegna si sente subito nell'aria appena usciti dall'aeroporto?", "options": ["Il mirto", "La lavanda delle Alpi", "La menta glaciale"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p01_q1", "difficulty": "easy", "q": "Dans quelle ville de Sardaigne se trouve l'aéroport où atterrit la famille ?", "options": ["À Olbia", "À Cala Gonone", "À Arbatax"], "correct": 0},
                {"id": "sard_p01_q2", "difficulty": "easy", "q": "Qui voyage en Sardaigne avec Papino, Maman Kate, Ale et Seby ?", "options": ["Mamie Lucilla", "Seulement Papino et Ale", "Les camarades d'école de Zurich"], "correct": 0},
                {"id": "sard_p01_q3", "difficulty": "hard", "q": "Quelle plante parfumée typique de Sardaigne sent-on dès la sortie de l'aéroport ?", "options": ["Le myrte", "La lavande des Alpes", "Le sapin du Nord"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p01_q1", "difficulty": "easy", "q": "In welcher Stadt auf Sardinien befindet sich der Flughafen, auf dem die Familie landet?", "options": ["In Olbia", "In Cala Gonone", "In Arbatax"], "correct": 0},
                {"id": "sard_p01_q2", "difficulty": "easy", "q": "Wer reist zusammen mit Papino, Mama Kate, Ale und Seby nach Sardinien?", "options": ["Oma Lucilla", "Nur Papino und Ale", "Die Schulfreunde aus Zürich"], "correct": 0},
                {"id": "sard_p01_q3", "difficulty": "hard", "q": "Nach welcher typisch sardischen Pflanze duftet die Luft schon am Flughafen?", "options": ["Nach Myrte", "Nach Edelweiß", "Nach Tannenbäumen"], "correct": 0}
            ]
        }
    },
    {
        "page": 2,
        "patch_pos": "top",
        "title": {
            "it": "2. A Cala Gonone dal Cugino Massimo Carlesso!",
            "fr": "2. À Cala Gonone chez le Cousin Massimo Carlesso !",
            "de": "2. In Cala Gonone bei Cousin Massimo Carlesso!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p02.jpg",
        "speech_bubble": {
            "speaker": "Papino & Cugino Massimo",
            "it": "Ciao Cugino Massimo! Che bello riabbracciare uno dei pochi Carlesso rimasti qui sul mare di Cala Gonone!",
            "fr": "Salut Cousin Massimo ! Quel bonheur d'embrasser l'un des rares Carlesso au bord de la mer de Cala Gonone !",
            "de": "Hallo Cousin Massimo! Wie schön, einen der wenigen Carlessos hier am Meer von Cala Gonone zu umarmen!"
        },
        "seby": {
            "it": "A Cala Gonone Papino abbraccia felice il cugino Massimo, uno dei pochi Carlesso rimasti! Ale e Seby corrono nel mare turchese.",
            "fr": "À Cala Gonone, Papino embrasse son cousin Massimo, l'un des rares Carlesso ! Ale et Seby courent dans la mer turquoise.",
            "de": "In Cala Gonone umarmt Papino glücklich seinen Cousin Massimo, einen der wenigen Carlessos! Ale und Seby laufen ins türkisfarbene Meer."
        },
        "ale": {
            "it": "Sulla spiaggia dorata di Cala Gonone andiamo a trovare il mitico cugino Massimo, cugino di Papino e uno dei pochi Carlesso rimasti! Dopo un grande abbraccio, Ale e Seby corrono nel mare turchese.",
            "fr": "Sur la plage dorée de Cala Gonone, nous rendons visite au cousin Massimo, cousin de Papino et l'un des rares Carlesso ! Après une grande accolade, Ale et Seby courent dans la mer turquoise.",
            "de": "Am goldenen Strand von Cala Gonone besuchen wir Papinos lieben Cousin Massimo, einen der wenigen Carlessos! Nach einer herzlichen Umarmung stürmen Ale und Seby ins türkisfarbene Wasser."
        },
        "questions": {
            "it": [
                {"id": "sard_p02_q1", "difficulty": "easy", "q": "Chi vanno a trovare e abbracciare sulla spiaggia di Cala Gonone?", "options": ["Il cugino Massimo", "Il cugino Marco di Milano", "Il maestro di nuoto"], "correct": 0},
                {"id": "sard_p02_q2", "difficulty": "easy", "q": "In quale paese sul mare si trovano quando incontrano il cugino Massimo?", "options": ["A Cala Gonone", "A Olbia in aeroporto", "In montagna sul Supramonte"], "correct": 0},
                {"id": "sard_p02_q3", "difficulty": "hard", "q": "Perché l'incontro con il cugino Massimo è così speciale per la famiglia di Papino?", "options": ["Perché è il cugino di Papino e uno dei pochi Carlesso rimasti", "Perché guida lui l'aeroplano", "Perché abita dentro una grotta marina"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p02_q1", "difficulty": "easy", "q": "Qui la famille retrouve-t-elle avec joie sur la plage de Cala Gonone ?", "options": ["Le cousin Massimo", "Le capitaine du port", "Le moniteur de voile"], "correct": 0},
                {"id": "sard_p02_q2", "difficulty": "easy", "q": "Dans quel village au bord de la mer rencontrent-ils le cousin Massimo ?", "options": ["À Cala Gonone", "À l'aéroport d'Olbia", "Au sommet du Supramonte"], "correct": 0},
                {"id": "sard_p02_q3", "difficulty": "hard", "q": "Pourquoi le cousin Massimo est-il une personne si spéciale pour Papino ?", "options": ["C'est le cousin de Papino et l'un des rares Carlesso restants", "C'est le pilote de l'avion", "Il habite en Égypte"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p02_q1", "difficulty": "easy", "q": "Wen besucht und umarmt Papino am Strand von Cala Gonone?", "options": ["Seinen Cousin Massimo", "Den Flugkapitän", "Einen Fischer aus Olbia"], "correct": 0},
                {"id": "sard_p02_q2", "difficulty": "easy", "q": "In welchem Küstenort treffen sie Cousin Massimo?", "options": ["In Cala Gonone", "Am Flughafen Olbia", "In den Bergen des Supramonte"], "correct": 0},
                {"id": "sard_p02_q3", "difficulty": "hard", "q": "Warum ist Cousin Massimo für Papinos Familie so besonders?", "options": ["Er ist Papinos Cousin und einer der wenigen verbleibenden Carlessos", "Er hat tausend kleine Fische gefangen", "Er wohnt auf einem Segelschiff"], "correct": 0}
            ]
        }
    },
    {
        "page": 3,
        "patch_pos": "bottom",
        "title": {
            "it": "3. Giochi tra gli Scogli di Cala Gonone",
            "fr": "3. Jeux entre les Rochers de Cala Gonone",
            "de": "3. Wasserspiele zwischen den Felsen"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p03.jpg",
        "speech_bubble": {
            "speaker": "Ale",
            "it": "Vieni Seby! L'acqua vicino a questi scogli chiari brilla come i diamanti!",
            "fr": "Viens Seby ! L'eau près de ces rochers clairs brille comme des diamants !",
            "de": "Komm Seby! Das Wasser bei diesen hellen Felsen glitzert wie tausend Diamanten!"
        },
        "seby": {
            "it": "I due fratelli giocano insieme nell'acqua bassa. Le piccole onde brillano sotto il caldo sole.",
            "fr": "Les deux frères jouent ensemble dans l'eau peu profonde. Les petites vagues brillent sous le soleil.",
            "de": "Die beiden Brüder spielen zusammen im flachen Wasser. Die kleinen Wellen glitzern unter der warmen Sonne."
        },
        "ale": {
            "it": "Vicino agli scogli chiari di Cala Gonone, Ale e Seby nuotano e ridono insieme nell'acqua limpida. Il sole caldo fa brillare ogni onda come tanti piccoli diamanti.",
            "fr": "Près des rochers clairs de Cala Gonone, Ale et Seby nagent et rient ensemble dans l'eau limpide. Le soleil chaud fait briller chaque vague comme de petits diamants.",
            "de": "Nahe den hellen Felsen von Cala Gonone schwimmen und lachen Ale und Seby im klaren Wasser. Die warme Sonne lässt jede Welle wie kleine Diamanten funkeln."
        },
        "questions": {
            "it": [
                {"id": "sard_p03_q1", "difficulty": "easy", "q": "Dove giocano e si schizzano l'acqua Ale e Seby?", "options": ["Nell'acqua bassa vicino agli scogli chiari", "In mezzo al mare profondo col gommone", "Nella piscina dell'aeroporto"], "correct": 0},
                {"id": "sard_p03_q2", "difficulty": "easy", "q": "Com'è l'acqua vicino agli scogli di Cala Gonone?", "options": ["Bassa, limpida e luminosa", "Alta e piena di onde giganti", "Calda come il tè"], "correct": 0},
                {"id": "sard_p03_q3", "difficulty": "hard", "q": "A quali pietre preziose assomigliano le onde quando riflettono il sole?", "options": ["A tanti piccoli diamanti", "Ai graniti rosa di Arbatax", "Ai coralli rossi dell'Egitto"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p03_q1", "difficulty": "easy", "q": "Où Ale et Seby jouent-ils dans l'eau ?", "options": ["Dans l'eau peu profonde près des rochers clairs", "Au large loin de la plage", "Dans une piscine couverte"], "correct": 0},
                {"id": "sard_p03_q2", "difficulty": "easy", "q": "Comment est l'eau près des rochers de Cala Gonone ?", "options": ["Peu profonde et limpide", "Très agitée avec d'immenses vagues", "Sombre et profonde"], "correct": 0},
                {"id": "sard_p03_q3", "difficulty": "hard", "q": "À quelles pierres précieuses ressemblent les vagues sous le soleil ?", "options": ["À de petits diamants", "Au granit rose d'Arbatax", "Aux coraux de la mer Rouge"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p03_q1", "difficulty": "easy", "q": "Wo spielen und planschen Ale und Seby zusammen?", "options": ["Im flachen Wasser nahe den hellen Felsen", "Tief unten am Meeresgrund", "Im Hafen von Olbia"], "correct": 0},
                {"id": "sard_p03_q2", "difficulty": "easy", "q": "Wie ist das Wasser bei den Felsen von Cala Gonone?", "options": ["Flach, klar und glitzernd", "Stürmisch mit hohen Wellen", "Trüb und kalt"], "correct": 0},
                {"id": "sard_p03_q3", "difficulty": "hard", "q": "Wie welche Edelsteine funkeln die Wellen im Sonnenlicht?", "options": ["Wie kleine Diamanten", "Wie der rosa Granit von Arbatax", "Wie rote Korallen"], "correct": 0}
            ]
        }
    },
    {
        "page": 4,
        "patch_pos": "top",
        "title": {
            "it": "4. I Ponti Sospesi tra i Pini!",
            "fr": "4. Les Ponts Suspendus dans les Pins !",
            "de": "4. Die Hängebrücken zwischen den Pinien!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p04.jpg",
        "speech_bubble": {
            "speaker": "Seby & Ale",
            "it": "Guarda giù Ale! Camminiamo sui ponti di corda tra i pini con vista sul mare!",
            "fr": "Regarde en bas Ale ! On marche sur les ponts de corde entre les pins avec vue sur la mer !",
            "de": "Schau nach unten, Ale! Wir laufen über Seilbrücken zwischen den Pinien mit Blick aufs Meer!"
        },
        "seby": {
            "it": "Con il casco in testa, Ale e Seby camminano sui ponti sospesi tra gli alberi.",
            "fr": "Avec un casque sur la tête, Ale et Seby marchent sur les ponts suspendus dans les arbres.",
            "de": "Mit einem Helm auf dem Kopf laufen Ale und Seby über die Hängebrücken zwischen den Bäumen."
        },
        "ale": {
            "it": "Nel parco avventura Ale e Seby indossano il casco e l'imbragatura per attraversare i ponti sospesi di corda e legno tra i pini, guardando dall'alto il mare blu della Sardegna.",
            "fr": "Dans le parc d'aventure, Ale et Seby portent un casque et un baudrier pour traverser les ponts suspendus de corde entre les pins, en admirant d'en haut la mer bleue.",
            "de": "Im Kletterpark tragen Ale und Seby ihren Sicherheitshelm und überqueren mutig die schwankenden Hängebrücken aus Holz und Seilen hoch über dem blauen Meer."
        },
        "questions": {
            "it": [
                {"id": "sard_p04_q1", "difficulty": "easy", "q": "Di che colore sono i caschi che indossano Ale e Seby sui ponti sospesi?", "options": ["Arancione per Ale e giallo per Seby", "Neri come quelli dei pompieri", "Verdi con le piume"], "correct": 0},
                {"id": "sard_p04_q2", "difficulty": "easy", "q": "Su cosa camminano i due fratelli in alto tra i pini?", "options": ["Su ponti sospesi di legno e corde", "Su un ponte di pietra antica", "Sul tetto del gommone"], "correct": 0},
                {"id": "sard_p04_q3", "difficulty": "hard", "q": "Quale paesaggio si vede là sotto mentre attraversano il ponte tra gli alberi?", "options": ["La costa verde e il mare azzurro con le barchette", "L'aeroporto di Olbia con gli aerei", "Il parco degli asinelli di Arbatax"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p04_q1", "difficulty": "easy", "q": "De quelles couleurs sont les casques d'Ale et Seby sur le pont ?", "options": ["Orange pour Ale et jaune pour Seby", "Tout noirs", "Bleus à rayures"], "correct": 0},
                {"id": "sard_p04_q2", "difficulty": "easy", "q": "Sur quoi marchent les deux frères en haut dans les pins ?", "options": ["Sur des ponts suspendus de bois et de cordes", "Sur une route goudronnée", "Sur un mur de granit"], "correct": 0},
                {"id": "sard_p04_q3", "difficulty": "hard", "q": "Quel paysage aperçoit-on en contrebas depuis les ponts dans les arbres ?", "options": ["La côte verte et la mer bleue avec des bateaux", "La piste de l'aéroport d'Olbia", "Les pyramides d'Égypte"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p04_q1", "difficulty": "easy", "q": "Welche Farben haben die Helme von Ale und Seby im Kletterpark?", "options": ["Orange für Ale und Gelb für Seby", "Schwarz und Grau", "Lila mit Sternen"], "correct": 0},
                {"id": "sard_p04_q2", "difficulty": "easy", "q": "Worüber balancieren die Brüder hoch oben zwischen den Pinien?", "options": ["Über Hängebrücken aus Holzbrettern und Seilen", "Über eine Steinbrücke", "Über das Dach des Hotels"], "correct": 0},
                {"id": "sard_p04_q3", "difficulty": "hard", "q": "Was sieht man im Hintergrund tief unter den Baumkronen?", "options": ["Die grüne Küste und das blaue Meer mit kleinen Booten", "Den Flughafen von Olbia", "Die Eselwiese von Arbatax"], "correct": 0}
            ]
        }
    },
    {
        "page": 5,
        "patch_pos": "bottom",
        "title": {
            "it": "5. Sotto la Luna Piena con Nonna Lucilla",
            "fr": "5. Sous la Pleine Lune avec Mamie Lucilla",
            "de": "5. Unter dem Vollmond mit Oma Lucilla"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p05.jpg",
        "speech_bubble": {
            "speaker": "Nonna Lucilla",
            "it": "Che serata meravigliosa con i miei nipotini davanti al mare illuminato dalla luna!",
            "fr": "Quelle soirée merveilleuse avec mes petits-enfants devant la mer éclairée par la lune !",
            "de": "Was für ein wundervoller Abend mit meinen Enkelkindern vor dem mondbeschienenen Meer!"
        },
        "seby": {
            "it": "Di sera la luna piena brilla sul mare. Nonna Lucilla sorride a tavola con Ale e Seby.",
            "fr": "Le soir, la pleine lune brille sur la mer. Mamie Lucilla sourit à table avec Ale et Seby.",
            "de": "Am Abend scheint der Vollmond über dem Meer. Oma Lucilla lächelt am Tisch mit Ale und Seby."
        },
        "ale": {
            "it": "Sulla terrazza illuminata dalle luci calde, Nonna Lucilla ascolta felice i racconti di Ale e Seby. In cielo splende una grande luna piena che si specchia sull'acqua del mare.",
            "fr": "Sur la terrasse éclairée de lumières chaudes, Mamie Lucilla écoute avec bonheur les histoires d'Ale et Seby. Dans le ciel brille une grande pleine lune qui se reflète sur la mer.",
            "de": "Auf der warm beleuchteten Terrasse hört Oma Lucilla glücklich den Geschichten von Ale und Seby zu. Am Nachthimmel leuchtet ein großer Vollmond, der sich im Meer spiegelt."
        },
        "questions": {
            "it": [
                {"id": "sard_p05_q1", "difficulty": "easy", "q": "Chi è seduto a tavola con Ale e Seby sulla terrazza vista mare?", "options": ["Nonna Lucilla", "Il cugino Massimo", "L'istruttore del parco avventura"], "correct": 0},
                {"id": "sard_p05_q2", "difficulty": "easy", "q": "Cosa illumina il mare e il cielo stellato durante la cena?", "options": ["Una grande luna piena", "Il sole di mezzogiorno", "Il faro dell'aeroporto"], "correct": 0},
                {"id": "sard_p05_q3", "difficulty": "hard", "q": "Cosa c'è acceso sul tavolo di legno accanto a Nonna Lucilla?", "options": ["Una calda lampada da tavolo insieme a biscotti e panini", "Un computer portatile", "Una bussola da marinaio"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p05_q1", "difficulty": "easy", "q": "Qui est assis à table avec Ale et Seby sur la terrasse ?", "options": ["Mamie Lucilla", "Le cousin Massimo", "Le moniteur d'escalade"], "correct": 0},
                {"id": "sard_p05_q2", "difficulty": "easy", "q": "Qu'est-ce qui éclaire la mer et le ciel étoilé pendant le dîner ?", "options": ["Une grande pleine lune", "Le soleil de midi", "Un feu d'artifice"], "correct": 0},
                {"id": "sard_p05_q3", "difficulty": "hard", "q": "Qu'est-ce qui est posé sur la table en bois à côté de Mamie Lucilla ?", "options": ["Une lampe chaude avec des biscuits et du pain", "Un masque de plongée", "Un arc et des flèches"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p05_q1", "difficulty": "easy", "q": "Wer sitzt am Abend mit Ale und Seby am Tisch auf der Terrasse?", "options": ["Oma Lucilla", "Cousin Massimo", "Der Bootskapitän"], "correct": 0},
                {"id": "sard_p05_q2", "difficulty": "easy", "q": "Was leuchtet am Nachthimmel und spiegelt sich im Meer?", "options": ["Der große runde Vollmond", "Die Mittagssonne", "Ein Regenbogen"], "correct": 0},
                {"id": "sard_p05_q3", "difficulty": "hard", "q": "Was steht neben Oma Lucilla auf dem Holztisch?", "options": ["Eine warme Tischlampe, Becher, Kekse und Brötchen", "Ein Schnorchel und Flossen", "Ein Rucksack"], "correct": 0}
            ]
        }
    },
    {
        "page": 6,
        "patch_pos": "top",
        "title": {
            "it": "6. Tutti sul Gommone nel Golfo di Orosei!",
            "fr": "6. Tous sur le Bateau dans le Golfe d'Orosei !",
            "de": "6. Mit dem Schlauchboot durch den Golf von Orosei!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p06.jpg",
        "speech_bubble": {
            "speaker": "Papino",
            "it": "Tenetevi forte ragazzi! Oggi esploriamo le calette segrete del Golfo di Orosei col nostro gommone!",
            "fr": "Tenez-vous bien les garçons ! Aujourd'hui on explore les criques secrètes du Golfe d'Orosei en bateau !",
            "de": "Haltet euch fest, Jungs! Heute erkunden wir mit unserem Schlauchboot die geheimen Buchten im Golf von Orosei!"
        },
        "seby": {
            "it": "Il giorno dopo salgono tutti su un gommone arancione. Navigano lungo le alte falesie bianche.",
            "fr": "Le lendemain, tout le monde monte sur un bateau orange. Ils naviguent le long des hautes falaises blanches.",
            "de": "Am nächsten Tag steigen alle in ein schnelles Schlauchboot. Sie fahren entlang der hohen weißen Klippen."
        },
        "ale": {
            "it": "La mattina seguente Papino guida al timone il gommone nel bellissimo Golfo di Orosei. Ale e Seby con i giubbotti salvagenti arancioni indicano entusiasti le altissime falesie di roccia bianca.",
            "fr": "Le lendemain matin, Papino conduit le bateau pneumatique dans le magnifique Golfe d'Orosei. Ale et Seby avec leurs gilets orange montrent les très hautes falaises blanches.",
            "de": "Am nächsten Morgen steuert Papino das Schlauchboot durch den herrlichen Golf von Orosei. Ale und Seby tragen orangefarbene Schwimmwesten und bestaunen die hohen weißen Felsklippen."
        },
        "questions": {
            "it": [
                {"id": "sard_p06_q1", "difficulty": "easy", "q": "Chi guida al timone il gommone arancione nel Golfo di Orosei?", "options": ["Papino Riccardo", "Nonna Lucilla", "Seby"], "correct": 0},
                {"id": "sard_p06_q2", "difficulty": "easy", "q": "Cosa indossano Ale e Seby a prua del gommone per sicurezza?", "options": ["I giubbotti salvagenti arancioni", "Il casco da arrampicata", "La maglia numero 10"], "correct": 0},
                {"id": "sard_p06_q3", "difficulty": "hard", "q": "Come si chiamano il grande golfo e le altissime pareti di roccia bianca lungo cui navigano?", "options": ["Il Golfo di Orosei e le sue falesie bianche", "Le baie di granito rosa di Arbatax", "Il porto di Olbia"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p06_q1", "difficulty": "easy", "q": "Qui tient le volant du bateau pneumatique dans le Golfe d'Orosei ?", "options": ["Papino Riccardo", "Mamie Lucilla", "Seby"], "correct": 0},
                {"id": "sard_p06_q2", "difficulty": "easy", "q": "Que portent Ale et Seby à l'avant du bateau pour leur sécurité ?", "options": ["Des gilets de sauvetage orange", "Un casque d'escalade", "Un manteau"], "correct": 0},
                {"id": "sard_p06_q3", "difficulty": "hard", "q": "Comment s'appellent le golfe et les hautes parois de roche blanche ?", "options": ["Le Golfe d'Orosei et ses falaises blanches", "Les baies de granit rose d'Arbatax", "Le port d'Olbia"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p06_q1", "difficulty": "easy", "q": "Wer steuert das Schlauchboot am Lenkrad durch den Golf von Orosei?", "options": ["Papino Riccardo", "Oma Lucilla", "Seby"], "correct": 0},
                {"id": "sard_p06_q2", "difficulty": "easy", "q": "Was tragen Ale und Seby vorne im Boot zu ihrer Sicherheit?", "options": ["Orangefarbene Schwimmwesten", "Einen Kletterhelm", "Wanderschuhe"], "correct": 0},
                {"id": "sard_p06_q3", "difficulty": "hard", "q": "Wie heißen die Bucht und die steilen weißen Felswände an der Küste?", "options": ["Der Golf von Orosei und seine weißen Klippen", "Die rosa Granitbuchten von Arbatax", "Der Flughafen von Olbia"], "correct": 0}
            ]
        }
    },
    {
        "page": 7,
        "patch_pos": "bottom",
        "title": {
            "it": "7. Tuffi a Cala Goloritzè!",
            "fr": "7. Plongeons à Cala Goloritzè !",
            "de": "7. Kopfsprung in Cala Goloritzè!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p07.jpg",
        "speech_bubble": {
            "speaker": "Ale & Seby",
            "it": "Uno, due, tre... TUFFO! L'acqua qui a Cala Goloritzè è così trasparente che si vede l'ombra sul fondo!",
            "fr": "Un, deux, trois... PLOUF ! L'eau ici à Cala Goloritzè est si transparente qu'on voit l'ombre au fond !",
            "de": "Eins, zwei, drei... PLATSCH! Das Wasser in Cala Goloritzè ist so klar, dass das Boot zu schweben scheint!"
        },
        "seby": {
            "it": "Davanti alla grande guglia di roccia, Ale e Seby si tuffano dal gommone nell'acqua turchese.",
            "fr": "Devant la grande aiguille rocheuse, Ale et Seby plongent du bateau dans l'eau turquoise.",
            "de": "Vor der hohen Felsnadel springen Ale und Seby vom Schlauchboot ins türkisfarbene Wasser."
        },
        "ale": {
            "it": "A Cala Goloritzè svetta una guglia di roccia altissima e un arco naturale sulla riva. L'acqua è così trasparente che il gommone proietta l'ombra sul fondale mentre Nonna Lucilla guarda Ale e Seby tuffarsi!",
            "fr": "À Cala Goloritzè se dresse une haute aiguille rocheuse et une arche naturelle. L'eau est si transparente que le bateau semble voler pendant que Mamie Lucilla regarde Ale et Seby plonger !",
            "de": "In Cala Goloritzè ragt eine hohe Felsnadel über dem Felsbogen empor. Das Wasser ist so glasklar, dass das Boot über dem Grund zu schweben scheint, während Oma Lucilla Ale und Seby beim Springen zusieht!"
        },
        "questions": {
            "it": [
                {"id": "sard_p07_q1", "difficulty": "easy", "q": "Chi resta sul gommone col giubbotto salvagente arancione a guardare divertita i tuffi di Ale e Seby?", "options": ["Nonna Lucilla", "Cugino Massimo", "Mamma Kate con l'arco"], "correct": 0},
                {"id": "sard_p07_q2", "difficulty": "easy", "q": "Come si chiama questa famosa cala con la grande punta di roccia e l'arco naturale?", "options": ["Cala Goloritzè", "Olbia", "Arbatax"], "correct": 0},
                {"id": "sard_p07_q3", "difficulty": "hard", "q": "Perché il gommone sembra quasi volare sospeso sopra il fondale?", "options": ["Perché l'acqua è così limpida che si vede l'ombra nitida del gommone sul fondo", "Perché c'è la bassa marea e tocca la sabbia", "Perché ha le ali subacquee"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p07_q1", "difficulty": "easy", "q": "Qui reste sur le bateau avec son gilet orange en regardant plonger Ale et Seby ?", "options": ["Mamie Lucilla", "Le cousin Massimo", "L'ânon sarde"], "correct": 0},
                {"id": "sard_p07_q2", "difficulty": "easy", "q": "Comment s'appelle cette célèbre crique avec sa haute aiguille rocheuse ?", "options": ["Cala Goloritzè", "Olbia", "Arbatax"], "correct": 0},
                {"id": "sard_p07_q3", "difficulty": "hard", "q": "Pourquoi a-t-on l'impression que le bateau flotte dans l'air ?", "options": ["Parce que l'eau est si transparente qu'on voit l'ombre du bateau sur le fond", "Parce qu'il est posé sur le sable", "Parce qu'il vole vraiment"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p07_q1", "difficulty": "easy", "q": "Wer sitzt mit orangefarbener Schwimmweste im Boot und schaut Ale und Seby beim Springen zu?", "options": ["Oma Lucilla", "Cousin Massimo", "Der Pilot"], "correct": 0},
                {"id": "sard_p07_q2", "difficulty": "easy", "q": "Wie heißt diese berühmte Bucht mit der hohen Felsnadel und dem Felsbogen?", "options": ["Cala Goloritzè", "Olbia", "Arbatax"], "correct": 0},
                {"id": "sard_p07_q3", "difficulty": "hard", "q": "Warum sieht es so aus, als würde das Schlauchboot in der Luft schweben?", "options": ["Weil das Wasser so glasklar ist, dass man den Schatten des Bootes am Meeresgrund sieht", "Weil das Boot Flügel hat", "Weil kein Wasser mehr da ist"], "correct": 0}
            ]
        }
    },
    {
        "page": 8,
        "patch_pos": "top",
        "title": {
            "it": "8. Le Grandi Grotte Marine nella Roccia",
            "fr": "8. Les Grandes Grottes Marines dans la Roche",
            "de": "8. Die großen Meeresgrotten in den Klippen"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p08.jpg",
        "speech_bubble": {
            "speaker": "Mamma Kate & Papino",
            "it": "Guardate là dentro! Le onde del mare hanno scavato delle grotte giganti nella falesia!",
            "fr": "Regardez là-dedans ! Les vagues de la mer ont creusé des grottes géantes dans la falaise !",
            "de": "Schaut mal dort hinein! Die Wellen haben riesige Höhlen in die weißen Felsklippen gegraben!"
        },
        "seby": {
            "it": "Il gommone passa davanti alle grandi grotte marine. Tutti indicano meravigliati gli archi di roccia.",
            "fr": "Le bateau passe devant les grandes grottes marines. Tout le monde montre avec émerveillement les arches de roche.",
            "de": "Das Boot fährt an den großen Meeresgrotten vorbei. Alle zeigen staunend auf die Felsbögen."
        },
        "ale": {
            "it": "Navigando lungo la costa selvaggia, la famiglia ammira da vicino le enormi grotte marine e gli archi naturali scavati dalle onde nella roccia bianca del Golfo di Orosei.",
            "fr": "En naviguant le long de la côte sauvage, la famille admire de près les immenses grottes marines et les arches naturelles creusées par les vagues dans la roche blanche.",
            "de": "Entlang der wilden Küste bewundert die Familie aus nächster Nähe die riesigen Meeresgrotten und Steinbögen, die die Wellen über Jahrtausende in den weißen Kalkstein gegraben haben."
        },
        "questions": {
            "it": [
                {"id": "sard_p08_q1", "difficulty": "easy", "q": "Cosa indicano con la mano Papino e Mamma Kate dal gommone?", "options": ["Le grandi grotte marine e gli archi nella roccia", "L'aeroporto di Olbia", "Un branco di delfini volanti"], "correct": 0},
                {"id": "sard_p08_q2", "difficulty": "easy", "q": "Cosa portano in testa i bambini e Papino per proteggersi dal sole in barca?", "options": ["I cappellini da sole", "Il casco con la corda", "La maschera da sci"], "correct": 0},
                {"id": "sard_p08_q3", "difficulty": "hard", "q": "Come si sono formate queste grandi caverne e gli archi nella roccia bianca?", "options": ["Sono state scavate lentamente dalla forza delle onde del mare", "Sono state costruite con i mattoni", "Sono state scavate dagli asinelli"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p08_q1", "difficulty": "easy", "q": "Que montrent du doigt Papino et Maman Kate depuis le bateau ?", "options": ["Les grandes grottes marines et les arches de roche", "L'aéroport d'Olbia", "Le parc d'Arbatax"], "correct": 0},
                {"id": "sard_p08_q2", "difficulty": "easy", "q": "Que portent les enfants et Papino sur la tête contre le soleil ?", "options": ["Des casquettes et chapeaux de soleil", "Un casque d'escalade", "Une couronne"], "correct": 0},
                {"id": "sard_p08_q3", "difficulty": "hard", "q": "Comment ces grandes cavernes et arches dans la falaise se sont-elles formées ?", "options": ["Elles ont été creusées lentement par la force des vagues", "Elles ont été bâties en briques", "Elles ont été creusées par des machines"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p08_q1", "difficulty": "easy", "q": "Worauf zeigen Papino und Mama Kate vom Schlauchboot aus?", "options": ["Auf die riesigen Meeresgrotten und Felsbögen", "Auf den Flughafen Olbia", "Auf eine Zielscheibe"], "correct": 0},
                {"id": "sard_p08_q2", "difficulty": "easy", "q": "Was tragen die Kinder und Papino auf dem Kopf gegen die Sonne?", "options": ["Sonnenhüte und Kappen", "Kletterhelme", "Wintermützen"], "correct": 0},
                {"id": "sard_p08_q3", "difficulty": "hard", "q": "Wie sind diese großen Höhlen und Steinbögen in den Klippen entstanden?", "options": ["Durch die Kraft der Meereswellen über lange Zeit", "Sie wurden aus Ziegelsteinen gebaut", "Durch Bagger"], "correct": 0}
            ]
        }
    },
    {
        "page": 9,
        "patch_pos": "bottom",
        "title": {
            "it": "9. Mano nella Mano sui Sentieri del Supramonte",
            "fr": "9. Main dans la Main sur les Sentiers du Supramonte",
            "de": "9. Hand in Hand auf den Pfaden des Supramonte"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p09.jpg",
        "speech_bubble": {
            "speaker": "Ale",
            "it": "Vieni Seby, dammi la mano! Saliamo su questo sentiero tra i fiori e i ginepri del Supramonte!",
            "fr": "Viens Seby, donne-moi la main ! On monte sur ce sentier parmi les fleurs et les genévriers du Supramonte !",
            "de": "Komm Seby, gib mir die Hand! Wir steigen diesen Steinpfad zwischen den Wacholderbäumen im Supramonte hinauf!"
        },
        "seby": {
            "it": "Ale e Seby camminano mano nella mano sui sentieri del Supramonte tra le rocce bianche e i ginepri.",
            "fr": "Ale et Seby marchent main dans la main sur les sentiers du Supramonte entre les roches et les genévriers.",
            "de": "Ale und Seby wandern Hand in Hand auf den Pfaden des Supramonte zwischen weißen Felsen und Wacholder."
        },
        "ale": {
            "it": "Lasciato il mare, i due fratelli salgono con lo zainetto in spalla tra le montagne selvagge del Supramonte. Ale tiene per mano Seby lungo il sentiero di pietra bianca profumato di ginepro e timo.",
            "fr": "Après la mer, les deux frères montent avec leur sac à dos dans les montagnes sauvages du Supramonte. Ale tient Seby par la main sur le sentier de pierre blanche parfumé de genévrier.",
            "de": "Nach dem Meer wandern die beiden Brüder mit ihren Rucksäcken in die wilden Berge des Supramonte. Ale hält Seby an der Hand auf dem weißen Steinpfad, der nach Wacholder und Thymian duftet."
        },
        "questions": {
            "it": [
                {"id": "sard_p09_q1", "difficulty": "easy", "q": "Come camminano Ale e Seby lungo il sentiero di montagna del Supramonte?", "options": ["Mano nella mano con lo zainetto in spalla", "In bicicletta", "In braccio a Papino"], "correct": 0},
                {"id": "sard_p09_q2", "difficulty": "easy", "q": "Come si chiama questo massiccio di montagne bianche e selvagge della Sardegna?", "options": ["Il Supramonte", "Il Golfo di Orosei", "Arbatax"], "correct": 0},
                {"id": "sard_p09_q3", "difficulty": "hard", "q": "Quali piante profumate crescono ai lati del sentiero sassoso del Supramonte?", "options": ["Ginepri dal tronco contorto, timo e fiorellini selvatici", "Alberi di mele e abeti", "Palme da dattero"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p09_q1", "difficulty": "easy", "q": "Comment marchent Ale et Seby sur le sentier de montagne ?", "options": ["Main dans la main avec leur sac à dos", "À vélo", "Sur le dos d'un petit âne"], "correct": 0},
                {"id": "sard_p09_q2", "difficulty": "easy", "q": "Comment s'appellent ces montagnes blanches et sauvages de Sardaigne ?", "options": ["Le Supramonte", "Cala Goloritzè", "Olbia"], "correct": 0},
                {"id": "sard_p09_q3", "difficulty": "hard", "q": "Quelles plantes parfumées bordent le sentier pierreux du Supramonte ?", "options": ["Des genévriers au tronc tordu, du thym et des fleurs sauvages", "Des pommiers", "Des cactus géants"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p09_q1", "difficulty": "easy", "q": "Wie wandern Ale und Seby den Bergpfad hinauf?", "options": ["Hand in Hand mit ihren Rucksäcken", "Mit dem Fahrrad", "Auf einem Esel"], "correct": 0},
                {"id": "sard_p09_q2", "difficulty": "easy", "q": "Wie heißt dieses wilde Gebirge mit weißen Kalksteinfelsen auf Sardinien?", "options": ["Der Supramonte", "Cala Gonone", "Arbatax"], "correct": 0},
                {"id": "sard_p09_q3", "difficulty": "hard", "q": "Welche duftenden Pflanzen wachsen am steinigen Wegesrand im Supramonte?", "options": ["Knorrige Wacholderbäume, Thymian und Wildblumen", "Tannen und Apfelbäume", "Kokospalmen"], "correct": 0}
            ]
        }
    },
    {
        "page": 10,
        "patch_pos": "top",
        "title": {
            "it": "10. Fratelli Esploratori in Cima al Supramonte!",
            "fr": "10. Frères Explorateurs au Sommet du Supramonte !",
            "de": "10. Brüder am Gipfel des Supramonte!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p10.jpg",
        "speech_bubble": {
            "speaker": "Seby & Ale",
            "it": "Ce l'abbiamo fatta! Da quassù si vedono tutte le valli verdi e perfino il mare azzurro!",
            "fr": "On a réussi ! D'ici là-haut on voit toutes les vallées vertes et même la mer bleue au loin !",
            "de": "Wir haben es geschafft! Von hier oben sieht man alle grünen Täler und sogar das blaue Meer!"
        },
        "seby": {
            "it": "Dalla cima della montagna i due fratelli guardano abbracciati le valli verdi e il mare lontano.",
            "fr": "Depuis le sommet de la montagne, les deux frères regardent ensemble les vallées vertes et la mer au loin.",
            "de": "Vom Berggipfel aus schauen die beiden Brüder auf die grünen Täler und das ferne Meer."
        },
        "ale": {
            "it": "Arrivati in cima al belvedere di roccia del Supramonte, Ale e Seby posano gli zainetti blu e verde per ammirare spalla a spalla le grandi valli silenziose che scendono fino al mare.",
            "fr": "Arrivés en haut du belvédère rocheux du Supramonte, Ale et Seby posent leurs sacs à dos bleu et vert pour admirer côte à côte les grandes vallées qui descendent jusqu'à la mer.",
            "de": "Oben am felsigen Aussichtspunkt des Supramonte stellen Ale und Seby ihren blauen und grünen Rucksack ab und blicken Schulter an Schulter über die weiten grünen Täler bis zum Meer."
        },
        "questions": {
            "it": [
                {"id": "sard_p10_q1", "difficulty": "easy", "q": "Dove appoggiano i loro zainetti blu e verde Ale e Seby?", "options": ["Sulla roccia in cima al belvedere della montagna", "Sulla sabbia della spiaggia", "Dentro il gommone"], "correct": 0},
                {"id": "sard_p10_q2", "difficulty": "easy", "q": "Cosa si vede in lontananza oltre le grandi valli verdi del Supramonte?", "options": ["Il mare azzurro della Sardegna", "La torre dell'aeroporto di Olbia", "Le piramidi d'Egitto"], "correct": 0},
                {"id": "sard_p10_q3", "difficulty": "hard", "q": "Di che colore sono i due zainetti da escursione di Ale e Seby?", "options": ["Uno azzurro/blu per Ale e uno verde per Seby", "Tutti e due rossi", "Gialli a pallini neri"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p10_q1", "difficulty": "easy", "q": "Où Ale et Seby posent-ils leurs sacs à dos au sommet ?", "options": ["Sur la roche tout en haut du belvédère", "Sur le sable de la plage", "Dans le bateau"], "correct": 0},
                {"id": "sard_p10_q2", "difficulty": "easy", "q": "Que voit-on au loin par-delà les grandes vallées vertes ?", "options": ["La mer bleue de Sardaigne", "L'aéroport d'Olbia", "Un glacier"], "correct": 0},
                {"id": "sard_p10_q3", "difficulty": "hard", "q": "De quelles couleurs sont les deux sacs à dos de randonnée d'Ale et Seby ?", "options": ["Un bleu pour Ale et un vert pour Seby", "Tous les deux rouges", "Jaunes et noirs"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p10_q1", "difficulty": "easy", "q": "Wo stellen Ale und Seby oben auf dem Berg ihre Rucksäcke ab?", "options": ["Auf dem hellen Felsen am Aussichtspunkt", "Im Sand am Strand", "Im Schlauchboot"], "correct": 0},
                {"id": "sard_p10_q2", "difficulty": "easy", "q": "Was sieht man in der Ferne hinter den grünen Tälern des Supramonte?", "options": ["Das blaue Meer", "Den Flughafen von Olbia", "Die Pyramiden"], "correct": 0},
                {"id": "sard_p10_q3", "difficulty": "hard", "q": "Welche Farben haben die beiden Wanderrucksäcke von Ale und Seby?", "options": ["Blau bei Ale und Grün bei Seby", "Beide sind knallrot", "Weiß und Rosa"], "correct": 0}
            ]
        }
    },
    {
        "page": 11,
        "patch_pos": "bottom",
        "title": {
            "it": "11. L'Arco di Mamma Kate e l'Asinello di Seby!",
            "fr": "11. L'Arc de Maman Kate et le Petit Âne de Seby !",
            "de": "11. Mama Kates Bogen und Sebys kleiner Esel!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p11.jpg",
        "speech_bubble": {
            "speaker": "Mamma Kate & Seby",
            "it": "ZAC! Freccia dritta nel centro giallo da 10 punti! E che morbido il muso di questo asinello sardo!",
            "fr": "ZAC ! Flèche en plein centre jaune à 10 points ! Et comme le museau de ce petit âne est doux !",
            "de": "ZACK! Pfeil mitten ins gelbe Zentrum! Und wie weich die Schnauze von diesem kleinen Esel ist!"
        },
        "seby": {
            "it": "Ad Arbatax Mamma Kate tira con l'arco nel centro. Seby con la maglia numero dieci accarezza un dolce asinello.",
            "fr": "À Arbatax, Maman Kate tire à l'arc en plein centre. Seby avec le maillot numéro dix caresse un petit âne.",
            "de": "In Arbatax trifft Mama Kate mit dem Bogen ins Schwarze. Seby im Trikot Nummer zehn streichelt einen kleinen Esel."
        },
        "ale": {
            "it": "Arrivati ad Arbatax, Mamma Kate tende l'arco di legno e centra il disco giallo da dieci punti del bersaglio! Accanto a lei, Seby con la maglia azzurra dell'Italia numero 10 accarezza il muso di un asinello sardo.",
            "fr": "Arrivés à Arbatax, Maman Kate tend son arc en bois et touche le centre jaune à dix points de la cible ! À côté d'elle, Seby avec son maillot bleu d'Italie numéro 10 caresse le museau d'un petit âne sarde.",
            "de": "In Arbatax spannt Mama Kate ihren Holzbogen und trifft genau die gelbe Zehn in der Mitte der Zielscheibe! Daneben kniet Seby im blauen Italien-Trikot mit der Nummer 10 und streichelt einen sardischen Esel."
        },
        "questions": {
            "it": [
                {"id": "sard_p11_q1", "difficulty": "easy", "q": "Quale punteggio colpisce Mamma Kate al centro giallo del bersaglio con la sua freccia?", "options": ["Il 10 al centro del bersaglio", "L'anello esterno da 1 punto", "Finisce fuori dal bersaglio"], "correct": 0},
                {"id": "sard_p11_q2", "difficulty": "easy", "q": "Quale animale accarezza Seby vicino al muretto di pietra?", "options": ["Un dolce asinello sardo grigio", "Un cavallo bianco", "Una capretta di montagna"], "correct": 0},
                {"id": "sard_p11_q3", "difficulty": "hard", "q": "Che maglia indossa Seby mentre fa le coccole all'asinello?", "options": ["La maglia azzurra dell'Italia con il numero 10", "Il giubbotto salvagente arancione", "Una camicia a fiori"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p11_q1", "difficulty": "easy", "q": "Quel score Maman Kate atteint-elle au centre jaune de la cible ?", "options": ["Le 10 en plein centre", "Le bord extérieur", "Elle rate la cible"], "correct": 0},
                {"id": "sard_p11_q2", "difficulty": "easy", "q": "Quel animal Seby caresse-t-il près du muret en pierre ?", "options": ["Un doux petit âne sarde gris", "Un cheval blanc", "Un mouton"], "correct": 0},
                {"id": "sard_p11_q3", "difficulty": "hard", "q": "Quel maillot porte Seby pendant qu'il caresse le petit âne ?", "options": ["Le maillot bleu de l'Italie avec le numéro 10", "Son gilet de sauvetage orange", "Un pull vert"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p11_q1", "difficulty": "easy", "q": "Welche Zahl trifft Mama Kate genau in der gelben Mitte der Zielscheibe?", "options": ["Die 10 genau in der Mitte", "Den äußeren Ring", "Den Baum daneben"], "correct": 0},
                {"id": "sard_p11_q2", "difficulty": "easy", "q": "Welches Tier streichelt Seby an der Steinmauer?", "options": ["Einen grauen sardischen Esel", "Ein weißes Pony", "Einen Hund"], "correct": 0},
                {"id": "sard_p11_q3", "difficulty": "hard", "q": "Welches Trikot trägt Seby auf diesem Bild?", "options": ["Das blaue Italien-Trikot mit der Nummer 10", "Ein gelbes Hemd", "Seine Schwimmweste"], "correct": 0}
            ]
        }
    },
    {
        "page": 12,
        "patch_pos": "top",
        "title": {
            "it": "12. Tra gli Ulivi e gli Asinelli del Parco di Arbatax",
            "fr": "12. Parmi les Oliviers et les Ânons du Parc d'Arbatax",
            "de": "12. Unter Olivenbäumen bei den Eseln von Arbatax"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p12.jpg",
        "speech_bubble": {
            "speaker": "Ale & Mamma Kate",
            "it": "Guarda Mamma! Ci sono due asinelli qui sotto gli ulivi e vogliono farsi accarezzare da tutti e due!",
            "fr": "Regarde Maman ! Il y a deux petits ânes sous les oliviers et ils veulent des câlins !",
            "de": "Schau mal, Mama! Hier unter den Olivenbäumen stehen zwei liebe Esel und möchten gestreichelt werden!"
        },
        "seby": {
            "it": "Nel parco pieno di ulivi di Arbatax, Ale e Seby coccolano due asinelli mentre Mamma Kate sorride con l'arco.",
            "fr": "Dans le parc plein d'oliviers d'Arbatax, Ale et Seby câlinent deux petits ânes pendant que Maman Kate sourit.",
            "de": "Im Olivenhain von Arbatax streicheln Ale und Seby zwei Esel, während Mama Kate mit ihrem Bogen lächelt."
        },
        "ale": {
            "it": "Dentro il grande parco naturale dell'albergo di Arbatax, gli animali camminano liberi tra i prati fioriti e gli ulivi. Ale e Seby abbracciano due asinelli dalle orecchie lunghe insieme a Mamma Kate.",
            "fr": "Dans le grand parc naturel de l'hôtel d'Arbatax, les animaux marchent librement entre les prés fleuris et les oliviers. Ale et Seby câlinent deux petits ânes aux longues oreilles avec Maman Kate.",
            "de": "Im großen Naturpark des Hotels von Arbatax laufen die Tiere frei zwischen Blumenwiesen und alten Olivenbäumen umher. Ale und Seby streicheln gemeinsam zwei langohrige Esel."
        },
        "questions": {
            "it": [
                {"id": "sard_p12_q1", "difficulty": "easy", "q": "Quanti asinelli stanno accarezzando insieme Ale e Seby sotto gli alberi?", "options": ["Due asinelli marroni", "Dieci asinelli", "Uno solo"], "correct": 0},
                {"id": "sard_p12_q2", "difficulty": "easy", "q": "Cosa porta sulla spalla Mamma Kate mentre passeggia col vestito a fiori nel parco?", "options": ["La faretra con le frecce e l'arco in mano", "Lo zaino da montagna", "Le pinne da sub"], "correct": 0},
                {"id": "sard_p12_q3", "difficulty": "hard", "q": "Quali alberi tipici mediterranei circondano il sentiero del parco di Arbatax?", "options": ["Grandi alberi di ulivo", "Abeti innevati", "Querce giganti"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p12_q1", "difficulty": "easy", "q": "Combien de petits ânes Ale et Seby caressent-ils ensemble ?", "options": ["Deux petits ânes bruns", "Dix ânes", "Un seul"], "correct": 0},
                {"id": "sard_p12_q2", "difficulty": "easy", "q": "Que porte Maman Kate en robe à fleurs pendant la promenade au parc ?", "options": ["Son carquois de flèches à l'épaule et son arc à la main", "Un gilet de sauvetage", "Une valise"], "correct": 0},
                {"id": "sard_p12_q3", "difficulty": "hard", "q": "Quels arbres méditerranéens entourent le sentier du parc d'Arbatax ?", "options": ["De grands oliviers", "Des sapins enneigés", "Des palmiers dattiers"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p12_q1", "difficulty": "easy", "q": "Wie viele Esel streicheln Ale und Seby hier gemeinsam?", "options": ["Zwei braune Esel", "Zehn Esel", "Nur einen"], "correct": 0},
                {"id": "sard_p12_q2", "difficulty": "easy", "q": "Was trägt Mama Kate im geblümten Kleid bei den Eseln?", "options": ["Ihren Bogen in der Hand und den Köcher mit Pfeilen über der Schulter", "Eine Schwimmweste", "Einen Koffer"], "correct": 0},
                {"id": "sard_p12_q3", "difficulty": "hard", "q": "Welche mediterranen Bäume wachsen überall im Park von Arbatax?", "options": ["Alte Olivenbäume", "Verschneite Tannen", "Birken"], "correct": 0}
            ]
        }
    },
    {
        "page": 13,
        "patch_pos": "bottom",
        "title": {
            "it": "13. Le Baie di Granito Rosa dell'Albergo di Arbatax",
            "fr": "13. Les Baies de Granit Rose de l'Hôtel d'Arbatax",
            "de": "13. Die Buchten aus rosa Granit in Arbatax"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p13.jpg",
        "speech_bubble": {
            "speaker": "Papino",
            "it": "Mettete bene maschera e boccaglio ragazzi! Sotto questi scogli di granito rosa di Arbatax c'è un acquario naturale!",
            "fr": "Mettez bien masque et tuba les garçons ! Sous ces rochers de granit rose d'Arbatax il y a un aquarium naturel !",
            "de": "Setzt Taucherbrille und Schnorchel gut auf, Jungs! Unter diesen rosa Granitfelsen von Arbatax wartet ein Natur-Aquarium!"
        },
        "seby": {
            "it": "Sugli scogli di granito rosa di Arbatax, Papino aiuta Ale e Seby a mettere la maschera e il boccaglio.",
            "fr": "Sur les rochers de granit rose d'Arbatax, Papino aide Ale et Seby à mettre le masque et le tuba.",
            "de": "Auf den rosa Granitfelsen von Arbatax hilft Papino Ale und Seby mit Taucherbrille und Schnorchel."
        },
        "ale": {
            "it": "Il momento più bello di tutto il viaggio arriva nelle baie segrete dell'albergo fighissimo di Arbatax. Sugli scogli caldi di granito rosa, Papino prepara Ale e Seby con maschera e boccaglio.",
            "fr": "Le plus beau moment de tout le voyage arrive dans les baies secrètes du super hôtel d'Arbatax. Sur les rochers chauds de granit rose, Papino prépare Ale et Seby avec masque et tuba.",
            "de": "Der allerschönste Moment der Reise beginnt in den geheimen Buchten des tollen Hotels von Arbatax. Auf den warmen rosa Granitfelsen setzen Papino, Ale und Seby ihre Taucherbrillen und Schnorchel auf."
        },
        "questions": {
            "it": [
                {"id": "sard_p13_q1", "difficulty": "easy", "q": "Cosa stanno indossando sul viso Ale e Seby con l'aiuto di Papino?", "options": ["La maschera da sub e il boccaglio per fare snorkeling", "Gli occhiali da sole", "Il casco per i ponti sospesi"], "correct": 0},
                {"id": "sard_p13_q2", "difficulty": "easy", "q": "Di che colore speciale sono gli scogli delle baie di Arbatax?", "options": ["Di granito rosa", "Bianchi come sul Supramonte", "Neri come il carbone"], "correct": 0},
                {"id": "sard_p13_q3", "difficulty": "hard", "q": "Di che colore sono le maschere con boccaglio di Ale e di Seby?", "options": ["Blu per Ale e arancione per Seby", "Tutte e due verdi", "Rosse e nere"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p13_q1", "difficulty": "easy", "q": "Que mettent Ale et Seby sur le visage avec l'aide de Papino ?", "options": ["Un masque et un tuba de snorkeling", "Des lunettes de soleil", "Un casque de vélo"], "correct": 0},
                {"id": "sard_p13_q2", "difficulty": "easy", "q": "De quelle couleur spéciale sont les rochers des baies d'Arbatax ?", "options": ["De granit rose", "Tout blancs comme au Supramonte", "Noirs"], "correct": 0},
                {"id": "sard_p13_q3", "difficulty": "hard", "q": "De quelles couleurs sont les masques et tubas d'Ale et de Seby ?", "options": ["Bleu pour Ale et orange pour Seby", "Tous les deux verts", "Violets"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p13_q1", "difficulty": "easy", "q": "Was setzen Ale und Seby mit Papinos Hilfe auf?", "options": ["Taucherbrille und Schnorchel", "Sonnenbrillen", "Kletterhelme"], "correct": 0},
                {"id": "sard_p13_q2", "difficulty": "easy", "q": "Welche besondere Gesteinsfarbe haben die Felsen in den Buchten von Arbatax?", "options": ["Rosa Granit", "Schneeweißer Kalkstein", "Schwarzer Basalt"], "correct": 0},
                {"id": "sard_p13_q3", "difficulty": "hard", "q": "Welche Farben haben die Taucherbrillen von Ale und Seby?", "options": ["Blau bei Ale und Orange bei Seby", "Beide sind grün", "Gelb und Lila"], "correct": 0}
            ]
        }
    },
    {
        "page": 14,
        "patch_pos": "top",
        "title": {
            "it": "14. Mille Pesciolini nell'Acqua Cristallina!",
            "fr": "14. Mille Petits Poissons dans l'Eau Cristalline !",
            "de": "14. Tausend kleine Fische im kristallklaren Wasser!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p14.jpg",
        "speech_bubble": {
            "speaker": "Ale & Seby",
            "it": "Guarda quanti pesciolini! Sono mille e nuotano in cerchio intorno a noi nell'acqua super trasparente!",
            "fr": "Regarde tous ces petits poissons ! Il y en a mille qui nagent en cercle autour de nous dans l'eau transparente !",
            "de": "Schau mal, wie viele kleine Fische! Es sind tausend und sie schwimmen im Kreis um uns herum!"
        },
        "seby": {
            "it": "Nelle baie di Arbatax l'acqua è cristallina. Mille piccoli pesciolini argentati nuotano in cerchio intorno ad Ale e Seby!",
            "fr": "Dans les baies d'Arbatax, l'eau est cristalline. Mille petits poissons argentés nagent en cercle autour d'Ale et Seby !",
            "de": "In den Buchten von Arbatax ist das Wasser kristallklar. Tausend kleine silberne Fische schwimmen im Kreis um Ale und Seby!"
        },
        "ale": {
            "it": "Appena entrano nelle baie dell'albergo di Arbatax, l'acqua è così cristallina e super trasparente che si vede ogni sasso sul fondale. Mille piccoli pesciolini argentati e dorati nuotano in vortice intorno ad Ale e Seby!",
            "fr": "Dès qu'ils entrent dans les baies de l'hôtel d'Arbatax, l'eau est si cristalline et super transparente qu'on voit chaque caillou. Mille petits poissons argentés et dorés tournent autour d'Ale et Seby !",
            "de": "Sobald sie in den Buchten des Hotels von Arbatax ins Wasser gehen, ist das Meer so kristallklar, dass man jeden Kieselstein sieht. Tausend kleine silberne und goldene Fische kreisen neugierig um Ale und Seby!"
        },
        "questions": {
            "it": [
                {"id": "sard_p14_q1", "difficulty": "easy", "q": "Come nuotano i mille piccoli pesciolini intorno ad Ale e Seby?", "options": ["Tutti in cerchio intorno a loro nell'acqua bassa e trasparente", "Scappano via spaventati nel mare profondo", "Saltano fuori dall'acqua sugli scogli"], "correct": 0},
                {"id": "sard_p14_q2", "difficulty": "easy", "q": "Perché si riescono a vedere così bene tutti i sassi e i pesciolini sul fondo?", "options": ["Perché l'acqua delle baie di Arbatax è cristallina e super trasparente", "Perché usano una lampada subacquea", "Perché sono dentro una piscina"], "correct": 0},
                {"id": "sard_p14_q3", "difficulty": "hard", "q": "In quale località della Sardegna si trovano queste baie dell'albergo piene di pesciolini?", "options": ["Ad Arbatax, tra gli scogli di granito rosa", "Al porto di Olbia", "A Cala Goloritzè"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p14_q1", "difficulty": "easy", "q": "Comment nagent les mille petits poissons autour d'Ale et Seby ?", "options": ["En cercle tout autour d'eux dans l'eau transparente", "Ils s'enfuient très loin", "Ils dorment sous le sable"], "correct": 0},
                {"id": "sard_p14_q2", "difficulty": "easy", "q": "Pourquoi voit-on si bien chaque caillou et chaque poisson au fond ?", "options": ["Parce que l'eau des baies d'Arbatax est cristalline et super transparente", "Parce qu'ils ont une lampe torche", "Parce qu'il n'y a pas d'eau"], "correct": 0},
                {"id": "sard_p14_q3", "difficulty": "hard", "q": "Dans quel endroit précis de Sardaigne se trouvent ces baies de l'hôtel ?", "options": ["À Arbatax, entourées de granit rose", "À l'aéroport d'Olbia", "Au sommet du Supramonte"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p14_q1", "difficulty": "easy", "q": "Wie schwimmen die tausend kleinen Fische um Ale und Seby herum?", "options": ["Im Kreis direkt um sie herum im klaren Wasser", "Sie schwimmen erschrocken davon", "Sie verstecken sich im Sand"], "correct": 0},
                {"id": "sard_p14_q2", "difficulty": "easy", "q": "Warum kann man jeden Kieselstein am Grund so deutlich erkennen?", "options": ["Weil das Wasser in den Buchten von Arbatax kristallklar ist", "Weil sie eine Taschenlampe haben", "Weil es ein Schwimmbad ist"], "correct": 0},
                {"id": "sard_p14_q3", "difficulty": "hard", "q": "Wo genau auf Sardinien liegen diese Hotelbuchten voller kleiner Fische?", "options": ["In Arbatax zwischen den rosa Granitfelsen", "Am Flughafen von Olbia", "In den Bergen des Supramonte"], "correct": 0}
            ]
        }
    },
    {
        "page": 15,
        "patch_pos": "bottom",
        "title": {
            "it": "15. La Grande Promessa di Papino: L'Egitto!",
            "fr": "15. La Grande Promesse de Papino : L'Égypte !",
            "de": "15. Papinos großes Versprechen: Ägypten!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p15.jpg",
        "speech_bubble": {
            "speaker": "Papino",
            "it": "Siete talmente bravi che la prossima volta Papino vi porterà in Egitto a vedere dei pesci ancora più belli e una barriera corallina come si deve!",
            "fr": "Vous êtes si doués que la prochaine fois Papino vous emmènera en Égypte voir de plus beaux poissons et une vraie barrière de corail !",
            "de": "Ihr macht das so toll, dass Papino euch das nächste Mal nach Ägypten mitnimmt, um ein echtes Korallenriff und noch buntere Fische zu sehen!"
        },
        "seby": {
            "it": "Papino abbraccia Ale e Seby in acqua e promette: «La prossima volta vi porterò in Egitto a vedere la barriera corallina!»",
            "fr": "Papino embrasse Ale et Seby dans l'eau et promet : « La prochaine fois je vous emmènerai en Égypte voir la barrière de corail ! »",
            "de": "Papino umarmt Ale und Seby im Wasser und verspricht: «Nächstes Mal nehme ich euch mit nach Ägypten zum Korallenriff!»"
        },
        "ale": {
            "it": "Vedendo Ale e Seby nuotare così bene con maschera e boccaglio tra i pesciolini di Arbatax, Papino li abbraccia orgoglioso: «Siete talmente bravi che la prossima volta vi porterò in Egitto a vedere una barriera corallina come si deve!»",
            "fr": "En voyant Ale et Seby nager si bien avec masque et tuba parmi les petits poissons d'Arbatax, Papino les serre fier d'eux : « Vous êtes si braves que la prochaine fois je vous emmènerai en Égypte voir une vraie barrière de corail ! »",
            "de": "Als Papino sieht, wie sicher Ale und Seby in Arbatax schnorcheln, umarmt er sie stolz: «Ihr seid so geschickt, dass Papino euch das nächste Mal nach Ägypten zu einem echten Korallenriff mitnimmt!»"
        },
        "questions": {
            "it": [
                {"id": "sard_p15_q1", "difficulty": "easy", "q": "In quale paese promette di portarli Papino la prossima volta?", "options": ["In Egitto", "In Norvegia", "In America"], "correct": 0},
                {"id": "sard_p15_q2", "difficulty": "easy", "q": "Cosa si vede disegnato nella nuvoletta dei sogni sopra Papino, Ale e Seby?", "options": ["Le piramidi con la Sfinge e la barriera corallina piena di pesci pagliaccio", "Un aeroplano all'aeroporto di Olbia", "Gli asinelli di Arbatax"], "correct": 0},
                {"id": "sard_p15_q3", "difficulty": "hard", "q": "Perché Papino decide di fare ad Ale e Seby la promessa del viaggio in Egitto?", "options": ["Perché sono stati bravissimi a nuotare con maschera e boccaglio tra i pesciolini di Arbatax", "Perché hanno camminato sul Supramonte", "Perché hanno tirato con l'arco"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p15_q1", "difficulty": "easy", "q": "Dans quel pays Papino promet-il de les emmener la prochaine fois ?", "options": ["En Égypte", "En Norvège", "En Amérique"], "correct": 0},
                {"id": "sard_p15_q2", "difficulty": "easy", "q": "Que voit-on dessiné dans la bulle de rêve au-dessus de Papino, Ale et Seby ?", "options": ["Les pyramides, le Sphinx et la barrière de corail avec des poissons-clowns", "L'aéroport d'Olbia", "Les ponts dans les arbres"], "correct": 0},
                {"id": "sard_p15_q3", "difficulty": "hard", "q": "Pourquoi Papino leur promet-il ce voyage en Égypte ?", "options": ["Parce qu'ils nagent super bien avec masque et tuba parmi les poissons d'Arbatax", "Parce qu'ils ont caressé les petits ânes", "Parce qu'ils ont pris l'avion"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p15_q1", "difficulty": "easy", "q": "In welches Land verspricht Papino mit Ale und Seby beim nächsten Mal zu reisen?", "options": ["Nach Ägypten", "Nach Norwegen", "Nach Amerika"], "correct": 0},
                {"id": "sard_p15_q2", "difficulty": "easy", "q": "Was sieht man in der Traumwolke über Papino, Ale und Seby?", "options": ["Die Pyramiden mit der Sphinx und ein buntes Korallenriff mit Clownfischen", "Den Flughafen von Olbia", "Die Hängebrücken"], "correct": 0},
                {"id": "sard_p15_q3", "difficulty": "hard", "q": "Warum macht Papino seinen Söhnen dieses tolle Versprechen?", "options": ["Weil sie beim Schnorcheln in den Buchten von Arbatax so geschickt und mutig waren", "Weil sie auf den Berg gestiegen sind", "Weil sie die Esel gefüttert haben"], "correct": 0}
            ]
        }
    },
    {
        "page": 16,
        "patch_pos": "top",
        "title": {
            "it": "16. Tramonto d'Oro ad Arbatax: Grazie Sardegna!",
            "fr": "16. Coucher de Soleil d'Or à Arbatax : Merci la Sardaigne !",
            "de": "16. Goldener Sonnenuntergang in Arbatax: Danke, Sardinien!"
        },
        "image": "stories/alessandro/storia-sardegna-cala-gonone-arbatax-famiglia/wc_p16.jpg",
        "speech_bubble": {
            "speaker": "Tutta la Famiglia",
            "it": "Grazie Sardegna! Da Olbia al Cugino Massimo, da Nonna Lucilla ai mille pesciolini di Arbatax: che vacanza indimenticabile!",
            "fr": "Merci la Sardaigne ! D'Olbia au Cousin Massimo, de Mamie Lucilla aux mille petits poissons d'Arbatax : quelles vacances inoubliables !",
            "de": "Danke, Sardinien! Von Olbia und Cousin Massimo über Oma Lucilla bis zu den tausend Fischen von Arbatax: Was für eine magische Reise!"
        },
        "seby": {
            "it": "Al tramonto tutta la famiglia si abbraccia felice sugli scogli rosa di Arbatax. Arrivederci Sardegna!",
            "fr": "Au coucher du soleil, toute la famille s'embrasse heureuse sur les rochers roses d'Arbatax. Au revoir la Sardaigne !",
            "de": "Bei Sonnenuntergang umarmt sich die ganze Familie glücklich auf den rosa Felsen von Arbatax. Auf Wiedersehen, Sardinien!"
        },
        "ale": {
            "it": "Mentre il sole tramonta dietro gli scogli di granito rosa di Arbatax, Papino, Mamma Kate, Nonna Lucilla, Ale e Seby si abbracciano felici. Nel cuore portano il cugino Massimo, i pesciolini d'argento e il sogno dell'Egitto!",
            "fr": "Tandis que le soleil se couche derrière les rochers de granit rose d'Arbatax, Papino, Maman Kate, Mamie Lucilla, Ale et Seby s'embrassent heureux. Dans leur cœur brillent le cousin Massimo, les petits poissons et le rêve de l'Égypte !",
            "de": "Während die Sonne hinter den rosa Granitfelsen von Arbatax versinkt, umarmen sich Papino, Mama Kate, Oma Lucilla, Ale und Seby glücklich. Im Herzen tragen sie Cousin Massimo, die silbernen Fische und den Traum von Ägypten!"
        },
        "questions": {
            "it": [
                {"id": "sard_p16_q1", "difficulty": "easy", "q": "Quante persone della famiglia si abbracciano sugli scogli rosa al tramonto?", "options": ["Cinque: Papino, Mamma Kate, Nonna Lucilla, Ale e Seby", "Solo Ale e Seby", "Tre persone"], "correct": 0},
                {"id": "sard_p16_q2", "difficulty": "easy", "q": "Cosa brilla nell'acqua turchese proprio sotto gli scogli mentre il sole tramonta?", "options": ["I pesciolini argentati di Arbatax", "Le stelle marine giganti", "I sassi bianchi del Supramonte"], "correct": 0},
                {"id": "sard_p16_q3", "difficulty": "hard", "q": "Metti in ordine le tappe del viaggio della famiglia in Sardegna:", "options": ["1. Aeroporto di Olbia → 2. Cala Gonone (Cugino Massimo e Golfo di Orosei) → 3. Supramonte → 4. Arbatax", "1. Arbatax → 2. Egitto → 3. Olbia", "1. Supramonte → 2. Aeroporto di Olbia → 3. Zurigo"], "correct": 0}
            ],
            "fr": [
                {"id": "sard_p16_q1", "difficulty": "easy", "q": "Combien de membres de la famille s'embrassent sur les rochers roses au coucher du soleil ?", "options": ["Cinq : Papino, Maman Kate, Mamie Lucilla, Ale et Seby", "Seulement Ale et Seby", "Trois personnes"], "correct": 0},
                {"id": "sard_p16_q2", "difficulty": "easy", "q": "Qu'est-ce qui brille dans l'eau turquoise au pied des rochers ?", "options": ["Les petits poissons argentés d'Arbatax", "Un bateau pirate", "La pleine lune"], "correct": 0},
                {"id": "sard_p16_q3", "difficulty": "hard", "q": "Quel est l'ordre exact des étapes de ce voyage en Sardaigne ?", "options": ["1. Aéroport d'Olbia → 2. Cala Gonone (Cousin Massimo et Golfe d'Orosei) → 3. Supramonte → 4. Arbatax", "1. Arbatax → 2. Égypte → 3. Olbia", "1. Supramonte → 2. Olbia → 3. Zurich"], "correct": 0}
            ],
            "de": [
                {"id": "sard_p16_q1", "difficulty": "easy", "q": "Wie viele Familienmitglieder umarmen sich bei Sonnenuntergang auf den rosa Felsen?", "options": ["Fünf: Papino, Mama Kate, Oma Lucilla, Ale und Seby", "Nur Ale und Seby", "Drei Personen"], "correct": 0},
                {"id": "sard_p16_q2", "difficulty": "easy", "q": "Was glitzert unten im türkisfarbenen Wasser neben den Felsen?", "options": ["Die silbernen Fische von Arbatax", "Das Schlauchboot", "Eine Schatzkiste"], "correct": 0},
                {"id": "sard_p16_q3", "difficulty": "hard", "q": "In welcher Reihenfolge hat die Familie Sardinien bereist?", "options": ["1. Flughafen Olbia → 2. Cala Gonone (Cousin Massimo & Golf von Orosei) → 3. Supramonte → 4. Arbatax", "1. Arbatax → 2. Ägypten → 3. Olbia", "1. Supramonte → 2. Olbia → 3. Zürich"], "correct": 0}
            ]
        }
    }
]


def slugify_word(w: str) -> str:
    clean = re.sub(r"^[^\wÀ-ÿÄÖÜäöüß]+|[^\wÀ-ÿÄÖÜäöüß]+$", "", w.lower())
    clean = re.sub(r"[^\wÀ-ÿÄÖÜäöüß]+", "_", clean)
    return clean or "word"


def mp3_to_ogg(mp3_path: Path, ogg_path: Path):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3_path), "-c:a", "libopus", "-b:a", "32k", str(ogg_path)],
        check=True
    )


def get_audio_duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            text=True
        ).strip()
        return float(out)
    except Exception:
        return 0.0


def try_gemini_tts_sync(text: str, lang: str, mp3_path: Path, ogg_path: Path) -> bool:
    if not GEMINI_KEYS:
        return False
    style_map = {"it": STYLE_IT, "fr": STYLE_FR, "de": STYLE_DE}
    style_prompt = style_map.get(lang, STYLE_IT)
    for key in GEMINI_KEYS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent?key={key}"
        payload = {
            "contents": [{
                "parts": [{
                    "text": text,
                    "speech_metadata": {
                        "style": style_prompt
                    }
                }]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": "Aoede"
                        }
                    }
                }
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=28) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                wav_bytes = base64.b64decode(b64)
                tmp_wav = mp3_path.with_suffix(".tmp.wav")
                tmp_wav.write_bytes(wav_bytes)
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_wav),
                        "-af", "silenceremove=stop_periods=-1:stop_duration=0.35:stop_threshold=-45dB,volume=1.35",
                        "-c:a", "libmp3lame", "-q:a", "3", str(mp3_path)
                    ],
                    check=True
                )
                tmp_wav.unlink(missing_ok=True)
                mp3_to_ogg(mp3_path, ogg_path)
                return True
        except Exception as e:
            continue
    return False


async def synth_sentence(sem: asyncio.Semaphore, text: str, lang: str, voice: str, mp3_path: Path, ogg_path: Path, force_gemini: bool = False):
    async with sem:
        tmp_edge = mp3_path.with_suffix(".edge.mp3")
        timings = []
        edge_ok = False
        if not mp3_path.exists() or mp3_path.stat().st_size < 1000:
            for attempt in range(3):
                try:
                    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
                    timings = []
                    with open(tmp_edge, "wb") as f:
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                            elif chunk["type"] == "WordBoundary":
                                start_s = round(chunk["offset"] / 10_000_000, 3)
                                dur_s = round(chunk["duration"] / 10_000_000, 3)
                                timings.append({
                                    "w": chunk["text"],
                                    "s": start_s,
                                    "e": round(start_s + max(dur_s, 0.12), 3)
                                })
                    edge_ok = True
                    break
                except Exception:
                    await asyncio.sleep(0.4 * (attempt + 1))

        used_gemini = False
        if force_gemini or not mp3_path.exists() or mp3_path.stat().st_size < 1000:
            used_gemini = await asyncio.to_thread(try_gemini_tts_sync, text, lang, mp3_path, ogg_path)

        if not used_gemini and edge_ok and (not mp3_path.exists() or mp3_path.stat().st_size < 1000):
            tmp_edge.replace(mp3_path)
            await asyncio.to_thread(mp3_to_ogg, mp3_path, ogg_path)
        else:
            tmp_edge.unlink(missing_ok=True)

        actual_dur = await asyncio.to_thread(get_audio_duration, mp3_path)
        if actual_dur <= 0.2:
            actual_dur = max(2.2, len(text.split()) * 0.42)

        if timings:
            edge_end = max(timings[-1]["e"], 0.2)
            scale = (actual_dur * 0.96) / edge_end
            for t in timings:
                t["s"] = round(t["s"] * scale, 3)
                t["e"] = round(t["e"] * scale, 3)
        else:
            # Character-length weighted timings across actual_dur
            words = text.split()
            weights = [max(2, len(w)) for w in words]
            total_w = sum(weights) or 1
            cur_t = 0.08
            usable_dur = max(1.0, actual_dur - 0.18)
            for w, wg in zip(words, weights):
                d = usable_dur * (wg / total_w)
                timings.append({
                    "w": w,
                    "s": round(cur_t, 3),
                    "e": round(cur_t + d, 3)
                })
                cur_t += d

        return timings


async def synth_single_word(sem: asyncio.Semaphore, word_clean: str, voice: str, mp3_path: Path, ogg_path: Path):
    if mp3_path.exists() and ogg_path.exists() and mp3_path.stat().st_size > 200:
        return
    async with sem:
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(word_clean, voice)
                with open(mp3_path, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                await asyncio.to_thread(mp3_to_ogg, mp3_path, ogg_path)
                return
            except Exception:
                await asyncio.sleep(0.5 * (attempt + 1))


def align_tokens_with_timings(sentence: str, timings: list, lang: str):
    raw_tokens = sentence.split()
    tokens_out = []
    t_idx = 0
    for tok in raw_tokens:
        pos, gloss, clean_lemma, gender = classify_word(tok, lang)
        slug = slugify_word(tok)
        start_s, end_s = 0.0, 0.5
        if t_idx < len(timings):
            start_s = timings[t_idx]["s"]
            end_s = timings[t_idx]["e"]
            t_idx += 1
        token_entry = {
            "w": tok,
            "clean": slug,
            "pos": pos,
            "s": start_s,
            "e": end_s,
            "audio_mp3": f"assets/words_audio/{lang}/{slug}.mp3",
            "audio_ogg": f"assets/words_audio/{lang}/{slug}.ogg",
        }
        if gender:
            token_entry["g"] = gender
        if gloss:
            token_entry["gloss"] = gloss
        tokens_out.append(token_entry)

    if lang == "de":
        for i, tok_i in enumerate(tokens_out):
            if tok_i.get("sep_group"):
                continue
            for j in range(i + 1, len(tokens_out)):
                tok_j = tokens_out[j]
                pair_key = (tok_i["clean"], tok_j["clean"])
                if pair_key in DE_SEPARABLE_VERBS and not tok_j.get("sep_group"):
                    sep_info = DE_SEPARABLE_VERBS[pair_key]
                    group_id = f"sep_{i}_{j}"
                    pair_display = f"{tok_i['clean']} … {tok_j['clean']}"
                    gloss_obj = {
                        "tr": sep_info["tr"],
                        "def": sep_info["def"],
                        "sep_inf": sep_info["infinitive"],
                        "sep_pair": pair_display,
                    }
                    tok_i["pos"] = "verb"
                    tok_i["sep_group"] = group_id
                    tok_i["sep_role"] = "stem"
                    tok_i["sep_inf"] = sep_info["infinitive"]
                    tok_i["sep_pair"] = pair_display
                    tok_i["gloss"] = gloss_obj

                    tok_j["pos"] = "verb"
                    tok_j["sep_group"] = group_id
                    tok_j["sep_role"] = "prefix"
                    tok_j["sep_inf"] = sep_info["infinitive"]
                    tok_j["sep_pair"] = pair_display
                    tok_j["gloss"] = gloss_obj
                    break
                if tok_j["w"].endswith((".", "!", "?")):
                    break

    return tokens_out


async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemini-sentences", action="store_true", help="Regenerate sentence & bubble audio with gemini-3.8-flash-tts Aoede")
    args = ap.parse_args()

    sem = asyncio.Semaphore(6)
    unique_words = {"it": {}, "fr": {}, "de": {}}

    print("🎙️ [1/3] Synthesizing 16 pages x 2 levels (seby/ale) x 3 langs (it/fr/de) + speech bubbles...")
    sentence_tasks = []

    voice_map = {"it": VOICE_IT, "fr": VOICE_FR, "de": VOICE_DE}
    for p in PAGES_SPEC:
        pnum = f"{p['page']:02d}"
        for lang, voice in voice_map.items():
            sb_text = p["speech_bubble"][lang]
            sb_mp3 = KIDS_AUDIO_DIR / f"{lang}_bubble_p{pnum}.mp3"
            sb_ogg = KIDS_AUDIO_DIR / f"{lang}_bubble_p{pnum}.ogg"
            sentence_tasks.append(("bubble", p["page"], lang, sb_text, voice, sb_mp3, sb_ogg))

            for level in ("seby", "ale"):
                txt = p[level][lang]
                mp3_p = KIDS_AUDIO_DIR / f"{lang}_{level}_p{pnum}.mp3"
                ogg_p = KIDS_AUDIO_DIR / f"{lang}_{level}_p{pnum}.ogg"
                sentence_tasks.append((level, p["page"], lang, txt, voice, mp3_p, ogg_p))

                for raw_tok in txt.split():
                    slug = slugify_word(raw_tok)
                    spoken = re.sub(r"^[^\wÀ-ÿÄÖÜäöüß]+|[^\wÀ-ÿÄÖÜäöüß]+$", "", raw_tok)
                    if slug and spoken:
                        unique_words[lang][slug] = spoken

    results_map = {}
    coros = [
        synth_sentence(sem, item[3], item[2], item[4], item[5], item[6], force_gemini=args.gemini_sentences)
        for item in sentence_tasks
    ]
    all_timings = await asyncio.gather(*coros)
    for item, timings in zip(sentence_tasks, all_timings):
        kind, page_no, lang, txt, _, mp3_p, ogg_p = item
        results_map[(kind, page_no, lang)] = {
            "timings": timings,
            "mp3": str(mp3_p.relative_to(ROOT)),
            "ogg": str(ogg_p.relative_to(ROOT)),
        }

    print(f"🎙️ [2/3] Synthesizing single words (IT={len(unique_words['it'])}, FR={len(unique_words['fr'])}, DE={len(unique_words['de'])})...")
    word_coros = []
    dir_map = {"it": WORDS_AUDIO_IT, "fr": WORDS_AUDIO_FR, "de": WORDS_AUDIO_DE}
    for lang, voice in voice_map.items():
        out_dir = dir_map[lang]
        for slug, spoken in unique_words[lang].items():
            mp3_w = out_dir / f"{slug}.mp3"
            ogg_w = out_dir / f"{slug}.ogg"
            word_coros.append(synth_single_word(sem, spoken, voice, mp3_w, ogg_w))
    await asyncio.gather(*word_coros)

    print("📦 [3/3] Building static kids_book_data.json and kids_books_catalog.js...")
    pages_compiled = []
    for p in PAGES_SPEC:
        pnum = p["page"]
        bubble_obj = {"speaker": p["speech_bubble"]["speaker"]}
        for lang in ("it", "fr", "de"):
            bubble_obj[lang] = {
                "text": p["speech_bubble"][lang],
                "audio_mp3": results_map[("bubble", pnum, lang)]["mp3"],
                "audio_ogg": results_map[("bubble", pnum, lang)]["ogg"],
            }

        levels_obj = {}
        for level in ("seby", "ale"):
            levels_obj[level] = {}
            for lang in ("it", "fr", "de"):
                res = results_map[(level, pnum, lang)]
                tokens = align_tokens_with_timings(p[level][lang], res["timings"], lang)
                levels_obj[level][lang] = {
                    "text": p[level][lang],
                    "audio_mp3": res["mp3"],
                    "audio_ogg": res["ogg"],
                    "tokens": tokens
                }

        pages_compiled.append({
            "page": pnum,
            "patch_pos": p.get("patch_pos", "bottom" if pnum % 2 == 1 else "top"),
            "title": p["title"],
            "image": p["image"],
            "speech_bubble": bubble_obj,
            "levels": levels_obj,
            "questions": p["questions"]
        })

    book_bundle = {
        "story_id": "storia-sardegna-cala-gonone-arbatax-famiglia",
        "title": {
            "it": "Sardegna Magica: Dal Cugino Massimo ai Mille Pesciolini di Arbatax",
            "fr": "Sardaigne Magique : Du Cousin Massimo aux Mille Petits Poissons d'Arbatax",
            "de": "Magisches Sardinien: Von Cousin Massimo zu den Tausend Fischen von Arbatax"
        },
        "buttons": {
            "seby": {
                "image": "assets/buttons/seby_leggi_qui.jpg",
                "label": {
                    "it": "🧒 Seby leggi qui! (6-7 anni)",
                    "fr": "🧒 Seby lis ici ! (6-7 ans)",
                    "de": "🧒 Seby lies hier! (6-7 J.)"
                }
            },
            "ale": {
                "image": "assets/buttons/ale_leggi_qui.jpg",
                "label": {
                    "it": "👦 Ale leggi qui! (8-9 anni)",
                    "fr": "👦 Ale lis ici ! (8-9 ans)",
                    "de": "👦 Ale lies hier! (8-9 J.)"
                }
            }
        },
        "supported_langs": ["it", "fr", "de"],
        "total_pages": len(pages_compiled),
        "pages": pages_compiled
    }

    json_path = STORY_DIR / "kids_book_data.json"
    json_path.write_text(json.dumps(book_bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    catalog_js_path = ROOT / "kids_books_catalog.js"
    catalog_obj = {
        "storia-sardegna-cala-gonone-arbatax-famiglia": book_bundle
    }
    catalog_js_path.write_text(
        "window.KIDS_BOOKS_CATALOG = " + json.dumps(catalog_obj, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8"
    )
    print(f"✅ Done! Wrote {json_path} and {catalog_js_path}")


if __name__ == "__main__":
    asyncio.run(main())
