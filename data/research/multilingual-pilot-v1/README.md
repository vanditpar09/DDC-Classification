GitHub snapshot note: saved reviews, source receipts, split assignments, curated
training excerpts, reports and the small fitted classifier are retained in Git.
Full acquired PDFs/EPUBs and intermediate full-book text/page images stay intact
on the development laptop and are excluded from Git. The four required offline
demo images are included. Reproduction of raw-book preparation needs the original
files identified in acquisition manifests; no original file has been deleted.

# DDC multilingual research pilot

Latest result (4 October 2026): [native silver-label training and local tests](experiment-v2/README.md). The new pilot contains 77 edition samples, 66 provisional work groups and 228 passages. A separate classifier was fitted; the earlier acquisition and review snapshots remain preserved. This is an experimental dataset, not a human-verified benchmark.

This directory contains a small, source-traceable *candidate set* for the next
multilingual DDC study. The candidates have not yet been checked against physical
editions. The Open Library DDC values are weak catalog hints, not verified labels.
The team has now supplied eight books (six PDFs and two EPUBs) in `pdf-inbox/`.
`intake-v1/` preserves local extraction, page previews and functional OCR/model
checks. These supplied books have not received verified DDC labels or been used
to fit a new model. The candidate metadata and eight-book intake are not yet a
prepared multilingual training dataset.

The follow-up preparation is saved in `intake-v1/prepared-v1/`: all EPUB spine
text, selected PDF pages, paired native-only/bilingual OCR and raw/clean model
diagnostics. `intake-v1/LABEL_REVIEW.md` records catalog proposals and conflicts;
all labels remain pending. `TRAINING_DATA_PRIORITIES.md` and the separate
48-candidate `priority-review-shortlist-v1.jsonl` focus further collection on
missing classifier sections. These are unreviewed development artifacts, not
the validated training dataset or a newly fitted multilingual model.

## What is here

- `sources/`: ten cached Open Library Search API responses, each with its original
  query URL, retrieval time and response hash. Four initial language searches;
  second relevance pages for Marathi/Tamil; one randomized page per language.
- `candidate-pool.jsonl`: unique works with a matching catalog edition and some
  DDC metadata. `candidates.jsonl`: a review shortlist of 20 works per language.
  `candidate-manifest.json` records counts, script evidence and hashes.
- `candidate-review-forms.jsonl`: 80 blank human-review records, prefilled only
  with bibliographic identifiers, edition-language search result and title.
  The DDC section, librarian source, capture permission and page records are
  intentionally empty. Search language is a clue; verify the language and edition.
- `collection-template.jsonl`: a blank 80-row, four-language sampling template.
  Desired class is a sampling target and never a ground-truth label.
- `images/`: local team scans after obtaining the required permission. Images are
  not fetched from Open Library, Internet Archive or a cover service.
- `pdf-inbox/README.md`: rights checks and instructions for adding permitted PDFs
  and converting only selected pages for the existing image-based OCR workflow.
- `intake-v1/README.md`: findings for the eight supplied books. The English EPUBs
  extract cleanly; all six Indic PDFs need OCR or validated font conversion because
  their embedded text is corrupted. Sample OCR and inference succeeded locally.
- Candidate review workbook: `../../../outputs/01a0ced2-2136-77d2-8ebe-04feab872ebf/multilingual-book-collection-review.xlsx`.
  It contains the 80 catalog candidates plus blank fields for verifying edition,
  language, DDC label provenance and reuse rights. Its catalog DDC values are
  weak hints only.

## Review the candidate shortlist

Open `candidates.jsonl` or `candidate-review-forms.jsonl` with a text editor; one
line represents one edition candidate. Copy the review forms to the separate
working file before making edits (preserving source records):

```sh
cp data/research/multilingual-pilot-v1/candidate-review-forms.jsonl \
  data/research/multilingual-pilot-v1/reviewed.jsonl
```

The shortlist currently has 20 candidates per language. Native-script title
checks found English 20, Hindi 5, Marathi 1 and Tamil 10. For an edition with a
Latin-script title, inspect the physical copy carefully to verify its language;
if its text is not in the requested language, replace it with a verified edition.
We do not yet have enough Marathi-script candidates to treat this shortlist as a
native-language benchmark. DDC hints span broad classes but do not validate a
section. These counts are in `candidate-manifest.json`.

## Start collecting

1. Open each candidate's `candidate_source_url`, locate the physical edition, and
   check its actual language, book/work identity, available DDC evidence and image
   rights. Reject a bad edition; never guess the label from its predicted class.
2. Get permission for each scan. Store each chosen edition's actual verified
   three-digit DDC section, reviewer, and the catalog record or other source used
   to verify it. Keep the source DDC as a clue with its provenance, not as a
   librarian-verified label.
3. Capture cover, back cover and contents pages where permitted. The collection
   accepts one to three page types. Record a faithful human-checked reference
   transcription in the book's original script, and preserve OCR output separately.
   Do not include call-number labels that reveal the answer in classifier input.
4. Use one stable `work_id` for every edition/translation of the same work. Link
   ISBN and Open Library work/edition IDs in `catalog_ids`. Never put scans,
   editions, translations or transcription variants of one work in different
   partitions. Related work identity needs human review.
5. Do not fill the pilot's missing Marathi/Tamil script coverage with English,
   romanized titles, machine-translated text, generated text or copied predictions.
   Collect a verified native-language physical edition or record the gap.

## Local commands

The prototype's ignored `output/` folder contains the actual-machine audit and
functional smoke check; it is local development output, not training data.

```sh
.venv/bin/python -m src.research.collection audit --output output/catalog-audit.json
.venv/bin/python -m src.research.collect_ocr data/research/multilingual-pilot-v1/reviewed.jsonl --output data/research/multilingual-pilot-v1/raw-ocr.jsonl
.venv/bin/python -m src.research.collection prepare data/research/multilingual-pilot-v1/raw-ocr.jsonl --output-dir output/multilingual-prepared-v1
```

Only completed `reviewed.jsonl` entries go to the OCR command. Blank review forms
are templates and will fail validation until the label, reviewer, source,
permission, image paths and checked reference text have been supplied. Keep the
source JSONL and scans with their hashes. Prepared split files are created in a
new output directory; inspect counts before considering any model fitting.

## Provenance and reuse

Candidate metadata was retrieved from the [Open Library Search API](https://openlibrary.org/dev/docs/api/search).
See its [API guidance](https://openlibrary.org/developers/api) and
[licensing note](https://openlibrary.org/developers/licensing). Open Library says
it claims no new proprietary rights in its database, while warning of possible
existing rights issues in contributions and jurisdictions. Candidate facts do
not establish a right to copy, publish or train on book images or full text.
The candidate files preserve public metadata provenance. Supplied books and their
derived text/images have separate rights requirements; verify contributor and
institutional requirements before redistributing any added material.

The Search API serves catalog work/edition records, but Open Library describes it
as low-volume and recommends monthly dumps for bulk ingestion. This pilot uses
only ten small search requests. Do not scale this candidate search into a bulk
import without moving to the recommended dump workflow and checking its use
conditions. [Open Library developer guidance](https://openlibrary.org/developers)

See [the data collection and model-comparison protocol](../../../docs/MULTILINGUAL_NEXT_STEPS.md).

## DDC working-label follow-up — 4 October 2026

The current eight-book recommendations are saved in [the label review](/Users/swayam200/Developer/DDC-Classification/data/research/multilingual-pilot-v1/intake-v1/label-review-v2/README.md). Darwin uses working section 576 under the documented modern-summary policy; Shyamchi Aai now has institutional numeric evidence for 891. Gandhi has a provisional project recommendation of 954 with the conflicting 320 source retained. Related-text limitations persist for Dasbodh/Tolkappiyam. All eight remain development-only and none is promoted to a verified training label. The unchanged classifier lacks active outputs for five recommended sections, affecting six books.

## Autonomous book collection — 4 October 2026

A first batch of 21 Hindi/Marathi/Tamil titles or source editions is saved in [the collection report](acquisition-v1/README.md). Nineteen have unverified native text; two need OCR. Source files, receipts, provisional grouping, identity corrections and four derived Hindi EPUBs are preserved. No new model was fitted and no candidate was promoted to a verified training label. The next step is assistant-led catalog corroboration and text review, then work-level overlap checks and retraining.


## Native collection update — 4 October 2026

See [current corpus status](CORPUS_STATUS.md) for both saved batches and [the second batch](acquisition-v2/README.md) for the 40 new titles, extraction checks, and remaining source problems. The recommended next milestones are 60–80 reviewed independent works for an initial pilot and 200 for a focused MVP. Collection counts are not verified training counts.


## Assistant evidence review — 4 October 2026

See [review-v3](review-v3/README.md) for the completed first evidence/quality review of all 61 collected titles. The corpus still needs more balanced books and text/label repair before its first training experiment.
