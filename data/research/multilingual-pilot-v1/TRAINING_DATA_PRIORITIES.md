# Training data priorities after the eight-book intake

3 October 2026. The saved classifier cannot output several required sections. Data preparation is complete for selected development inputs; no native-language model has been fitted.

| Priority | Language / section | Why |
|---|---|---|
| 1 | Hindi / 891 | Godan currently follows the English 823 branch. Only three catalog work groups support 891; no 890 fine head exists. |
| 1 | Marathi / 891 | Collect verified Marathi literature across distinct authors/works; do not assume the Shyamchi Aai autobiography label. |
| 1 | Tamil / 894 | Ponniyin Selvan has catalog support for 894; that section is absent from training support. |
| 1 | Tamil / 494 | Tamil grammar requires a missing fine class. Original texts and commentaries need separate edition/work review. |
| 2 | Marathi / 294 | Religion is present in the old catalog model, but native-language evidence still needs supervision and measurement. |
| Review first | Hindi autobiography | Gandhi records conflict between 320 and 954; do not train on a preferred guess. 954 is currently below minimum support. |

## Targeted candidates already saved

`priority-review-shortlist-v1.jsonl` triages 48 candidates from the existing 939-record cached pool, up to eight distinct catalog work IDs per target. It avoids recognized aliases of the eight diagnostic titles. It is a metadata review list, not new training data. Native-script title counts are {'hin': 0, 'mar': 0, 'tam': 10}. The poor Hindi/Marathi title-script coverage requires physical-edition checks; romanized titles can still represent native books.

| Language | Candidate title | Catalog section hint | Source |
|---|---|---|---|
| hin | Rubāʻīyāt-i ʻUmar K̲h̲ayyām | 891 | [Edition record](https://openlibrary.org/books/OL16500844M) |
| hin | Punarjīvana | 891 | [Edition record](https://openlibrary.org/books/OL165023M) |
| hin | Post-independence Sanskrit literature | 891 | [Edition record](https://openlibrary.org/books/OL1681374M) |
| hin | Kumārasambhavaḥ | 891 | [Edition record](https://openlibrary.org/books/OL18353880M) |
| hin | Gitanjali. | 891 | [Edition record](https://openlibrary.org/books/OL19413338M) |
| hin | Mālavikāgnimitra | 891 | [Edition record](https://openlibrary.org/books/OL19431745M) |
| hin | Yūropa kī śreshṭha kahāniyām̐ | 891 | [Edition record](https://openlibrary.org/books/OL23042249M) |
| hin | Akelā melā | 891 | [Edition record](https://openlibrary.org/books/OL23219141M) |
| mar | The rough and the smooth | 891 | [Edition record](https://openlibrary.org/books/OL11647M) |
| mar | Narasiṃha Cintāmaṇa | 891 | [Edition record](https://openlibrary.org/books/OL19431815M) |
| mar | Pratishṭhā | 891 | [Edition record](https://openlibrary.org/books/OL21133114M) |
| mar | Sāgarā, prāṇa taḷamaḷalā | 891 | [Edition record](https://openlibrary.org/books/OL21608154M) |
| mar | Vhāyā-- vastraharaṇa | 891 | [Edition record](https://openlibrary.org/books/OL23217081M) |
| mar | Jhumbara | 891 | [Edition record](https://openlibrary.org/books/OL23946017M) |
| mar | Jhuṇḍa | 891 | [Edition record](https://openlibrary.org/books/OL23973947M) |
| mar | Prakāśa śalākā | 891 | [Edition record](https://openlibrary.org/books/OL24409830M) |
| tam | முதல் ஐந்து தமிழ் நாவல்கள் | 894 | [Edition record](https://openlibrary.org/books/OL58503876M) |
| tam | க்ருபாமந்திர் | 894 | [Edition record](https://openlibrary.org/books/OL59280111M) |
| tam | திருக்குறள் | 894 | [Edition record](https://openlibrary.org/books/OL59422650M) |
| tam | அவளுக்கென்று ஒரு இடம் | 894 | [Edition record](https://openlibrary.org/books/OL59539257M) |
| tam | சத்யாக்ரகி | 894 | [Edition record](https://openlibrary.org/books/OL59591625M) |
| tam | மேலகரம் திரிகூட ராசப்பக் கவிராயர் பாடியருளிய திருக்குற்றாலக் குறவஞ்சி | 894 | [Edition record](https://openlibrary.org/books/OL60172098M) |
| tam | பாரிவேள் | 894 | [Edition record](https://openlibrary.org/books/OL60638959M) |
| tam | புறநானூறு | 894 | [Edition record](https://openlibrary.org/books/OL60679844M) |
| tam | தொல்காப்பியத்தில் மெய்ப்பாட்டியல், உவமையியல், செய்யுளியல், மரபியல் | 494 | [Edition record](https://openlibrary.org/books/OL53826333M) |
| tam | வள்ளுவர் தமிழ் இலக்கணம் | 494 | [Edition record](https://openlibrary.org/books/OL62220018M) |
| tam | Percival's Tamil-English dictionary = | 494 | [Edition record](https://openlibrary.org/books/OL1059094M) |
| tam | Tolkāppiyam | 494 | [Edition record](https://openlibrary.org/books/OL175013M) |
| tam | Tamil newspaper reader = | 494 | [Edition record](https://openlibrary.org/books/OL2231342M) |
| tam | Centamil̲c cor̲pir̲appiyal pērakaramutali | 494 | [Edition record](https://openlibrary.org/books/OL2693732M) |
| tam | Tolkāppiyam - Poruḷatikāram | 494 | [Edition record](https://openlibrary.org/books/OL30810392M) |
| tam | A handbook of the Tamil language | 494 | [Edition record](https://openlibrary.org/books/OL3152462M) |
| mar | The Vr̥ishā kapi sūkta | 294 | [Edition record](https://openlibrary.org/books/OL1253501M) |
| mar | Yugānta | 294 | [Edition record](https://openlibrary.org/books/OL15679M) |
| mar | Dainandina Dāsabodha | 294 | [Edition record](https://openlibrary.org/books/OL171066M) |
| mar | Asā āhe Śrīviththala | 294 | [Edition record](https://openlibrary.org/books/OL19794787M) |
| mar | Brahm vidya | 294 | [Edition record](https://openlibrary.org/books/OL2360773M) |
| mar | Talks on the Gita | 294 | [Edition record](https://openlibrary.org/books/OL26404073M) |
| mar | Spandakārikā | 294 | [Edition record](https://openlibrary.org/books/OL2692636M) |
| mar | Devācyā nāvānã... | 294 | [Edition record](https://openlibrary.org/books/OL30428020M) |
| hin | Discovering Vidisha | 954 | [Edition record](https://openlibrary.org/books/OL24470413M) |
| hin | Gaṛhā-maṇḍala ke goṇḍa rājavaṃśa kā sāṃskr̥tika itihāsa | 954 | [Edition record](https://openlibrary.org/books/OL25142247M) |
| hin | Bhārata jagāo! | 954 | [Edition record](https://openlibrary.org/books/OL31213865M) |
| hin | Bhārata aura Yūropa | 954 | [Edition record](https://openlibrary.org/books/OL44010962M) |
| hin | Rāma-janmabhūmi mandira Ayodhyā kī prācīnatā | 954 | [Edition record](https://openlibrary.org/books/OL44053850M) |
| hin | Bhāratīya rājanītika cintana meṃ rāshṭavāda | 954 | [Edition record](https://openlibrary.org/books/OL44448003M) |
| hin | Śibū Sorena, Jhārakhaṇḍa āndolana kā eka sipāhī | 954 | [Edition record](https://openlibrary.org/books/OL44478629M) |
| hin | Hindustāna kī kahānī | 954 | [Edition record](https://openlibrary.org/books/OL512756M) |

## What constitutes enough data

First complete the eight development-book labels and checked transcriptions to diagnose failures. For a substantive training comparison, start with 20–30 **distinct training works** per priority section/language combination, plus separate development/calibration/test works. This is an initial collection target, not a proven sample-size guarantee. A 60% work-hash train partition generally needs a larger total collection than 20–30 works; inspect the actual counts rather than choosing IDs to obtain a desired split. The eight examined works stay in development.

Five distinct work groups is the current fine-head support threshold. It does not establish multilingual reliability, and a head requires at least two outcomes. Add reviewed neighboring/contrast classes under the same parent; do not create a one-class head that reports certain confidence. Existing weak catalog support does not substitute for verified native-language examples.

Freeze the encoder for the first training comparison. Fit classifier heads on train works, tune methods only on development, calibrate on calibration works, then evaluate untouched new test works. Keep every edition, translation, page and chapter of a work together. Retain the existing artifact for comparison and save model/data hashes, support counts, calibration parameters and per-language L1/L2/L3 results.

Actual phone capture and adaptive-controller experiments follow on separate permitted captures and matched quality targets. Selected PDF-page diagnostics do not demonstrate phone performance or patent novelty.
