# Eight-book intake check

Checked locally on 3 October 2026. All eight files open: six PDFs and two EPUBs.
The two English EPUBs have readable Unicode text and matching title/author/language
metadata. PDF previews show the requested Hindi, Marathi and Tamil scripts.

Follow-up work is now in [`prepared-v1/README.md`](prepared-v1/README.md): clean
EPUB spine text, 24 raw/clean OCR outputs from 12 selected PDF pages and 88 saved
classifier calls. See [`LABEL_REVIEW.md`](LABEL_REVIEW.md) for catalog evidence
and unresolved labels, and `head-coverage-v1.json` for missing classifier sections.
These follow-up artifacts still have no training-eligible books or verified
reference transcriptions. The original intake and smoke results below are retained.

| Language | Book | Format | Extent | Text route |
| --- | --- | --- | --- | --- |
| English | Pride and Prejudice | EPUB | 9 spine documents | Direct EPUB extraction |
| English | On the Origin of Species | EPUB | 19 spine documents | Direct EPUB extraction |
| Hindi | Godaan | PDF | 526 pages | Rasterize selected pages and OCR |
| Hindi | Gandhi autobiography | PDF | 539 pages | Rasterize selected pages and OCR |
| Marathi | Shyamchi Aai | PDF | 231 pages | Rasterize selected pages and OCR |
| Marathi | Dasbodh, volume 2 | PDF | 411 pages | Rasterize selected pages and OCR |
| Tamil | Ponniyin Selvan | PDF | 1,940 pages | Rasterize selected pages and OCR |
| Tamil | Tolkappiyam | PDF | 126 pages | Rasterize/OCR; optional separately validated TSCII conversion |

## Findings

Direct PDF extraction produces broken text in all six Indic books even though
the rendered pages are readable. Hindi/Marathi mappings substitute or omit letters.
Ponniyin Selvan contains Tamil mixed with incorrect Latin/control characters.
Tolkappiyam explicitly uses the legacy InaimathiTSC/TSCII font and extracts as
Latin/symbol characters instead of Unicode Tamil. Do not use these raw embedded
PDF extracts as reference transcriptions or classifier training text.

`text/` preserves complete raw extraction and page/spine boundaries for diagnosis.
`inventory.json` records file hashes, sizes, metadata, extraction errors, and script
counts. Script counts identify a possible extraction route, not text correctness.
`review-findings.json` records the observed visual/text issues separately.

`previews/` contains PDF pages 1 and 10 at 95 dpi. `smoke-v1/` contains a 200 dpi
sample and raw local OCR for every PDF, plus two EPUB chapter excerpts. All six
OCR samples were nonempty; all eight classifier calls produced finite scores.
The OCR samples are uncorrected outputs, not human references. No CER/WER or DDC
accuracy is reported. No physical phone capture or whole-book OCR was performed.

The classifier smoke input is the book title plus at most 2,500 characters from
the selected excerpt. It excludes catalog subject/DDC metadata. Samples use PDF
page 10, except Ponniyin Selvan page 15 (start of the first chapter). Shyamchi
Aai's page 10 is introductory material, so its result is not a representative
whole-book classification. EPUB samples use Darwin spine document 4 and Austen
document 3 to avoid the front licence/introductory material.

The model suggested 800 for Godaan and Ponniyin Selvan, but then followed its
English-literature branch to 823. Gandhi's childhood excerpt received 400 and
Tolkappiyam received 200. These are failure cases to investigate using appropriate
book evidence and verified edition labels. They are not measured benchmark errors
or librarian labels. Some samples exceed the baseline encoder's 512-token input
limit, which the report records. Existing macOS NumPy/Accelerate warnings occurred;
the predictor's finite-probability checks passed for every sample.

## Readiness

This is a useful four-language intake and functional test, not a prepared training
dataset. Source download links/rights records, verified three-digit edition DDC
labels, appropriate page types, faithful corrected references, work-group
deduplication and evaluation partitions remain to be established. Model weights
have not changed. Keep all editions/pages/excerpts of the same work in one group;
individual chapters do not count as independent books. Eight works cannot establish
general accuracy across the DDC hierarchy.

## Reproduce

Use a Python environment with `pypdf` for the intake audit. The smoke script uses
the existing project ML environment, Poppler's `pdftoppm`, and the project's local
Tesseract language packs. Choose NEW output directories; the scripts refuse to
overwrite prior outputs.

```sh
python scripts/audit_multilingual_intake.py \
  data/research/multilingual-pilot-v1/pdf-inbox --output /path/to/new-intake
.venv/bin/python scripts/smoke_book_intake.py /path/to/new-intake \
  --output /path/to/new-intake/new-smoke --predict
```

Original EPUBs and PDFs remain unchanged in `../pdf-inbox/`. This directory's
derived text/images inherit each source's rights; being inside the repository
does not establish permission to redistribute them.
