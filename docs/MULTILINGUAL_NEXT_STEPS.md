# Multilingual DDC improvement plan

For the current team priorities and latest phone findings, see
[Project status and handoff](PROJECT_HANDOFF.md).

Current status: 4 October 2026. A separate native silver-label model is now trained and tested locally. It supports sections 891, 894, 494 and 510, with manual review enforced. The pilot contains 77 edition samples in 66 provisional original-work groups. Results and remaining limits are in [the experiment report](../data/research/multilingual-pilot-v1/experiment-v2/README.md). The older preparation notes below are historical; the original hierarchy model remains unchanged.

## Eight-book preparation completed

Selected development inputs are now saved at
`data/research/multilingual-pilot-v1/intake-v1/prepared-v1/`: 12 rendered PDF pages,
24 native-only / English-plus-native OCR outputs, and raw/clean text for all 28
EPUB spine documents. All 24 OCR outputs were nonempty; all 88 raw/clean
classifier calls returned valid finite results. This unreviewed preparation is
distinct from the reviewed dataset produced by `src.research.collection prepare`.
It contains no training-eligible books or checked reference transcriptions.

Catalog research is saved in `intake-v1/LABEL_REVIEW.md` and its evidence JSON.
Five books have one candidate section, two have conflicting section proposals
(Darwin and Gandhi), and Shyamchi Aai lacks numeric DDC evidence. The Tolkappiyam
hint is from commentary/partial-translation records, so the original edition
still needs checking. None is promoted to a verified label. Direct catalog fetch
limitations are recorded; the evidence comes from indexed institutional records.

The saved-model coverage audit found no active fine-class output for 891, 894 or
494. Catalog training supports 891 with three work groups and has no support for
894 or 494. Model support for 575/576 and 954 is also below the five-group rule.
OCR cleanup alone cannot fill these missing classifier classes. See
`intake-v1/head-coverage-v1.json` for the actual artifact hash and support audit.

`TRAINING_DATA_PRIORITIES.md` and `priority-review-shortlist-v1.jsonl` select 48
targeted metadata candidates from the existing cached pool. Their language,
edition, section and text must be reviewed before collection; they are not newly
downloaded books. All eight examined works remain development-only. The next
fitting step requires reviewed labels and more distinct works in the missing
sections, including contrast classes under each parent. Model weights have not
changed during this preparation.

## What the data audit found

The current catalog contains 5,034 books, with no explicit language field and no
Devanagari or Tamil titles. The collection pipeline originally selected English
catalog records; multilingual subject metadata does not establish book language.
4,986 records are marked not_reviewed. The remaining 48 have broad-label review
statuses, which do not certify their divisions/sections. The model's multilingual
representation comes from its frozen pretrained encoder; verified Indian-language
supervision and real-scan evaluation have not yet been established.

The commit-ready candidate set is at `data/research/multilingual-pilot-v1/`; its
source snapshots, candidate shortlist, empty human-review forms, provenance and
checksums are all saved with the project. The ignored `output/multilingual-pilot-v1/`
copy contains this machine's functional smoke test and editable development template.
Empty candidate forms do not count as training or evaluation books.

The team has since supplied eight books: two English EPUBs and six Hindi/Marathi/
Tamil PDFs. Local inventory, extraction and smoke results are saved under
`data/research/multilingual-pilot-v1/intake-v1/`. The EPUBs have clean Unicode text.
All six PDFs render in the requested scripts but have defective embedded-text
mapping; selected-page OCR recovered nonempty native-script text. Eight functional
classifier calls succeeded, while their fine-class suggestions expose the current
English-literature bias. This is an unlabelled intake check, not new training or
measured native-language accuracy. See that directory's README for sample choices
and limitations.

On 3 October 2026, ten low-volume Open Library searches found and shortlisted
80 edition candidates, 20 per language, covering the ten broad classes as weak
catalog hints. The selected title-script check found native-script titles in 20/20
English, 5/20 Hindi, 1/20 Marathi and 10/20 Tamil candidates. Marathi and Tamil
shortlists therefore need more real-edition review before they are a useful native
script pilot. Edition-language metadata and romanized titles do not prove the text
inside the book is in that language; reviewers must check the physical edition.
The work-level DDC hints are not the verified three-digit edition labels needed
for training.

## Work sequence and decisions

| Stage | Work | Completion evidence |
|---|---|---|
| 1 — Infrastructure | Audit existing data; build reviewed-book collection, raw OCR runner, work-group partitions and paired evaluator | Implemented; regression and real-model functional checks |
| 2 — Pilot | Collect 20 distinct works each in English, Hindi, Marathi and Tamil, spanning broad classes where available | 80 reviewed editions/works with permitted scans, faithful references and source-backed section labels |
| 3 — Compare evidence | Cover only; cover/back; cover/back/contents. Compare concatenation with page-balanced windows, separately for reference and OCR text | Per-language L1/L2/L3 accuracy, macro-F1, abstention and missing-OCR counts, plus CER/WER and latency |
| 4 — Targeted training | Prioritize the library's frequent fine sections; expand underrepresented language/section combinations; refit DDC heads and recalibrate on separate native-language data | A new versioned artifact and development results; existing artifact retained |
| 5 — Alternative models | Compare conditional heads with joint leaf ranking and a verified-catalog retrieval baseline. Consider encoder fine-tuning when data supports it | Development-only comparison with the same work groups and evidence |
| 6 — Final validation | Freeze methods/thresholds, then evaluate new held-out works and actual phone captures | Independent real-scan results and controller comparison at matched classification quality |

The 80-candidate shortlist must first pass physical-edition/language review and receive verified labels, photos and transcriptions. Some Hindi/Marathi/Tamil candidates are romanized, and the current metadata returned few Marathi-script titles. Find additional target-language catalog sources if the shortlists do not meet the pilot. After collection, the 80-book pilot identifies failure modes; it cannot establish reliable section
accuracy across hundreds of DDC labels. As a starting collection target, gather
20–30 distinct training works per priority section per language, with additional
separate development/calibration/test works. Five groups is the current model's
minimum support rule, not a reliability guarantee. Expand data based on observed
coverage and uncertainty rather than assuming one fixed total is sufficient.

Book sources can include the saved digital editions. Label review uses the book's
actual subject and catalog evidence, recording the actual reviewer and remaining
uncertainty. A librarian is helpful but is not a prerequisite. The assistant can
collect evidence and inspect sources; machine OCR and assistant proposals must
not be described as human-checked references. The code can run OCR, validate data,
freeze partitions and compare predictions. Model predictions never become ground
truth automatically.

## Implemented collection workflow

Start with the local kit:

```sh
# Already created on this machine; on another checkout use a NEW directory:
.venv/bin/python -m src.research.collection init --output-dir output/multilingual-pilot-v2
```

Each JSONL row represents one edition, with `book_id`, a shared `work_id` for
translations/editions of one work, edition language, title, verified three-digit
section, reviewer and source. Capture page images plus checked native-script
`reference_text`. The blank template's `desired_class` is only a sampling target.
It never supplies the actual label. Copy the blank shortlist to `reviewed.jsonl`, then complete actual rows only; delete rejected candidates rather than inventing replacements. Candidates come from public catalogs and stay pending until evidence-based review supports their labels. Keep assistant-reviewed proposals separate from the verified benchmark.

Photographs must be local to the collection directory, with relative paths. Keep
cover/back/contents as separate pages. For the classification benchmark, avoid or
mask catalog labels/call-number stickers that directly reveal the target; apply
the same capture protocol to every method. Preserve raw text and all combining
marks. Reviewers should label without seeing the model suggestion.

Read images using the existing local Tesseract language packs, keeping references
intact and saving failed/empty OCR explicitly:

```sh
.venv/bin/python -m src.research.collect_ocr \
  output/multilingual-pilot-v1/reviewed.jsonl \
  --output output/multilingual-pilot-v1/raw-ocr.jsonl
```

The raw runner uses one pass without repairs or OSD, so it is a controlled OCR
baseline rather than the adaptive prototype controller. The separate controller
experiment can then measure whether repairs and new-page requests help.

Prepare an immutable dataset with deterministic work-level assignments:

```sh
.venv/bin/python -m src.research.collection prepare \
  output/multilingual-pilot-v1/raw-ocr.jsonl \
  --output-dir output/multilingual-prepared-v1
```

The assignment is 60/20/10/10 train/development/calibration/test by seeded work-ID
hash, not stratified. Inspect language/section counts before training. All views,
translations and editions of one work remain together. Existing catalog overlap
is moved to development only, including aliases of Open Library IDs and ISBNs;
it cannot enter new training/calibration or a supposedly independent new test.
Human review must still link related works with different identifiers.

Validation rejects incomplete labels/reviews, machine translations or synthetic
pages, duplicate editions, conflicting catalog aliases, repeated images across
work groups, invalid page types, and image paths outside the collection. Exact
long-reference duplicates also require work resolution. These checks cannot prove
that all human-provided labels, permissions or work IDs are correct.

`training-input.jsonl` contains only newly assigned train/calibration rows with
reviewed section targets and reference text, plus a readiness report counting
DISTINCT works per language/section. The future reviewed-data trainer must honor
`assigned_partition`; the original catalog trainer's splitter must not repartition
this file. No new native-language classifier has been fitted yet.

## Page-window experiment

The saved baseline reads only the first 512 encoder tokens of concatenated text.
A long description can therefore prevent contents evidence from reaching it.
The new experimental strategy gives each page equal total weight and splits long
pages into token-bounded chunks. Each chunk shares its page's weight in proportion
to text length; a long contents page cannot dominate simply by producing more
chunks. Child joint probability mass is pooled before conditioning on its parent,
so suggestions remain consistent across L1/L2/L3.

A maximum of four chunks per page bounds the default cost (at most 12 chunks).
Unprocessed tails are reported explicitly; other pages still get their own
budget. Each actual encoded fragment is checked against 512 tokens. This is a
fixed comparison method, not a learned weighting policy. Pooled scores are not
recalibrated, so multi-window predictions always require manual review. A short
single-page input reproduces the baseline exactly. The production prototype still
uses the existing baseline while this experiment is evaluated.

Try it with a private JSON array of pages, each containing `kind` and `text`:

```sh
HF_HUB_OFFLINE=1 .venv/bin/python -m src.research.page_windows \
  output/my-book-pages.json --output output/my-book-window-result.json
```

Run the paired development comparison when reviewed data is available:

```sh
HF_HUB_OFFLINE=1 .venv/bin/python -m src.research.evaluate \
  output/multilingual-prepared-v1 \
  --output-dir output/multilingual-evaluation-v1
```

The evaluator records the model/data hashes, encoder revision, exact predictions,
page subsets, window caps and language counts. It checks prepared text and image
hashes before running. Each work receives total weight one within a metric group,
so repeated editions do not inflate accuracy. Fine-label abstentions count as
incorrect; language groups with no books have no accuracy value.

Reference-transcription and raw-OCR results are separate. Both strategies use the
same eligible books within each page subset. Missing pages/failed OCR are counted
explicitly; paired text accuracy excludes such books and therefore is not the
end-to-end camera success rate. CER/WER includes empty OCR as complete error. It
uses NFC and whitespace normalization with case/punctuation preserved; WER tokens
are whitespace-separated. Latency excludes warm-up and is cache/order dependent.

Locked test evaluation requires explicit `--partition test --allow-locked-test`
after fixing methods and thresholds. Do not use those results to tune the model.

## Local checks

Regression tests cover data validation, grouping/catalog overlap, immutable
prepared data, OCR failures, Unicode windows, page weights, parent-mass pooling,
rare-class fallback, locked-test handling, complete evaluator output and group-
weighted metrics. Existing hierarchy and inference regressions are also run.

Real saved-model checks exercised authored English/Hindi/Marathi/Tamil phrases
and a long three-page example. The short phrases exactly reproduced baseline
predictions. A 3,785-token back-cover input used four bounded windows while the
cover and contents each kept one; its omitted tail was reported, and automatic
review readiness remained disabled. Those are functional checks, not multilingual
accuracy results. Details: `output/multilingual-pilot-v1/functional-smoke.json`.

The existing macOS NumPy/Accelerate matrix warnings remain; checked probabilities
were finite. No encoder fine-tuning, new language-labelled training, physical-
phone measurement or measured accuracy gain has occurred in this step.

## DDC working-label follow-up — 4 October 2026

The current eight-book recommendations are saved in [the label review](/Users/swayam200/Developer/DDC-Classification/data/research/multilingual-pilot-v1/intake-v1/label-review-v2/README.md). Darwin uses working section 576 under the documented modern-summary policy; Shyamchi Aai now has institutional numeric evidence for 891. Gandhi has a provisional project recommendation of 954 with the conflicting 320 source retained. Related-text limitations persist for Dasbodh/Tolkappiyam. All eight remain development-only and none is promoted to a verified training label. The unchanged classifier lacks active outputs for five recommended sections, affecting six books.

## Autonomous book collection — 4 October 2026

A first batch of 21 Hindi/Marathi/Tamil titles or source editions is saved in [the collection report](../data/research/multilingual-pilot-v1/acquisition-v1/README.md). Nineteen have unverified native text; two need OCR. Source files, receipts, provisional grouping, identity corrections and four derived Hindi EPUBs are preserved. No new model was fitted and no candidate was promoted to a verified training label. The next step is assistant-led catalog corroboration and text review, then work-level overlap checks and retraining.


## Native collection update — 4 October 2026

The two acquisition batches now contain 61 downloaded titles (14 Hindi, 20 Marathi, 27 Tamil), including 57 unverified native-text extractions. None has been promoted to verified training data and the model has not been retrained. See [current corpus status](../data/research/multilingual-pilot-v1/CORPUS_STATUS.md) and [MVP dataset targets](MVP_DATASET_TARGETS.md).


## Evidence review — 4 October 2026

The assistant assessed all 61 acquired titles, saved 141 source-page OCR comparisons and 183 candidate text windows, corroborated seven Hindi work-level section proposals and retained two Tamil label conflicts. Review documents are in [review-v3](../data/research/multilingual-pilot-v1/review-v3/README.md). Twenty-three titles need text investigation or alternate extraction; one Hindi sequence remains incomplete. These are review outcomes, not verified benchmark labels. The model remains unchanged and further balanced collection is required.
