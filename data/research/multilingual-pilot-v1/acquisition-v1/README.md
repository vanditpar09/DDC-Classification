# Native book collection — 4 October 2026

Collected **21 titles/source editions**: 4 Hindi, 6 Marathi and 11 Tamil. Original files, source URLs, retrieval times and SHA-256 receipts are saved locally. Nineteen titles have native text available; two Marathi PDFs need OCR. Four Hindi EPUBs were created from the publisher’s complete indexed page sequences. They are research derivatives, not downloaded publisher EPUBs.

**No model was retrained. No record has been promoted to a verified training label or a human-checked transcription.** Working section proposals target the missing 891, 894 and 494 outputs. Downloading a book does not validate its DDC label, extraction fidelity or training permission. Original source notices remain intact.

## Books saved

| Language | Title | Working section | Source format | Text status |
|---|---|---|---|---|
| Tamil | நேமிநாதம் | 494 | PDF + Unicode HTML | Available; unverified |
| Tamil | வடமலை நிகண்டு | 494 | PDF + Unicode HTML | Available; unverified |
| Tamil | சூடாமணி நிகண்டு | 494 | PDF + Unicode HTML | Available; unverified |
| Tamil | நன்னூல் | 494 | PDF + Unicode HTML | Available; unverified |
| Tamil | சோலைமலை இளவரசி | 894 | PDF + Unicode HTML | Available; unverified |
| Tamil | இலக்கணச் சுருக்கம் | 494 | PDF + Unicode HTML | Available; unverified |
| Tamil | ஐந்திலக்கணம் தொன்னூல் விளக்கம் | 494 | PDF + Unicode HTML | Available; unverified |
| Tamil | தியாக பூமி | 894 | PDF + Unicode HTML | Available; unverified |
| Tamil | பார்வதி பி.ஏ. (புதினம்) | 894 | PDF + Unicode HTML | Available; unverified |
| Tamil | இருளும் ஒளியும் (நாவல்) | 894 | PDF + Unicode HTML | Available; unverified |
| Marathi | लोकशाहीर अण्णा भाऊ साठे निवडक वाङ्मय | 891 | PDF | Needs OCR; anthology quarantined |
| Marathi | डिटेक्टिव्ह अल्फा आणि रत्नजडित खंजिराचे रहस्य | 891 | PDF | Available; unverified |
| Marathi | मुन्नी | 891 | PDF | Available; unverified |
| Marathi | आनंद | 891 | PDF | Available; unverified |
| Marathi | फुल्लारी | 891 | PDF | Available; unverified |
| Marathi | सईची वही | 891 | PDF | Needs OCR |
| Hindi | गबन | 891 | HTML + derived EPUB | Available; unverified |
| Hindi | प्रतिज्ञा | 891 | HTML + derived EPUB | Available; unverified |
| Hindi | निर्मला | 891 | HTML + derived EPUB | Available; unverified |
| Hindi | प्रेमा | 891 | HTML + derived EPUB | Available; unverified |
| Tamil | காதலினால் அல்ல | 894 | PDF + Unicode HTML | Available; unverified |

## What the checks caught

- Anna’s Archive was searched in Chrome through Computer Use. It returned native Hindi EPUB/PDF records, but the two selected free download endpoints returned HTTP 504. No Anna file is falsely counted as downloaded. The record/search and outcomes are in `anna-search-log.json`.
- The original providers used were [Hindi Samay](https://hindisamay.com/premchand%20samagra/Indexpremchand.htm), [e-Sahitya](https://www.esahity.com/2325236623422306234823522368.html) and [Project Madurai](https://www.projectmadurai.org/pmworks.html). Exact file URLs and source notices are preserved alongside every saved original.
- Ten Hindi chapter URLs returned empty book-content elements with HTTP success. Their responses are preserved; alternate indexed page requests recovered the missing text. All 46 indexed parts are now present across the four Hindi novels. Parts are not counted as independent books.
- `phakiraa.pdf` is a selected-writings anthology, as shown by its cover, printed title and contents pages. It is not accepted as a standalone Fakira novel. Its internal-work membership remains unresolved, so it is quarantined from training/test.
- Prema and Pratigya share a conservative grouping pending review of their rewrite relationship. Twenty-one downloaded titles therefore give at most 20 provisional groups, or 19 after excluding the unresolved anthology. These are not certified independent works.
- One Tamil source begins at a heading numbered chapter 17; its original-work completeness is unverified. Another has the wrong HTML head title; the body/title-page identity takes precedence.
- Several Tamil PDFs use legacy fonts or broken glyph mappings. Their paired Unicode HTML is retained as an alternative text source. Neither representation is presented as a checked OCR reference.
- Two catalog-listed Tamil novels (Project Madurai 923 and 924) returned 404 for both listed formats. Failures remain in `download-results.json`; they are excluded from the downloaded count.

## Saved material

- `books/`: unchanged downloaded PDFs and book source HTML, plus retrieval receipts.
- `derived-ebooks/`: the four readable Hindi EPUB derivatives.
- `prepared/`: source-body text, extracted PDF text and page offsets/script diagnostics. No titles, author names or predicted classes are prepended to book text by the preparer. Naturally occurring source front matter remains and needs selection before fitting.
- `preview/`: locally rendered covers/title/contents used to check identity.
- `collected-books.jsonl`: book records, provisional groups, source hashes, extraction status and working label proposals.
- `validation.json`: source-integrity and EPUB checks.
- `manifest.json`: checksums for this collection’s saved files, excluding the manifest itself.

## Validation

- Checked 92 original source/catalog receipts: no hash mismatches.
- All four EPUBs pass ZIP integrity, XML parsing and a separate EPUB metadata/spine reader; all 46 indexed source parts appear in their book spines.
- Downloaded book sources total 57,909,849 bytes.
- Every record remains `training_eligible=false`; model files and the previous eight-book development packet are unchanged.

## Next work

1. Corroborate the working 891/894/494 assignments with book-specific catalog evidence and resolve original-work/anthology identities. Keep any unresolved classification clearly provisional. This can continue through public catalog searches without requiring a librarian.
2. OCR the two Marathi PDFs, inspect body-page samples and check text fidelity. Select book-content windows and exclude publisher boilerplate; do not treat publisher OCR or our extracted text as ground truth.
3. Expand beyond the single-author Hindi batch and check overlap with every old catalog/train/dev/calibration/test work before freezing partitions. All editions, parts and rewrites stay together. This batch is a start; it is below the planned 20–30 distinct training works per priority section/language.
4. Fit and calibrate new hierarchy heads using reviewed native examples, preserve the current classifier for comparison, and report L1/L2/L3 results by language on untouched work groups. Then run the physical-phone capture experiment.

## Reproduce the preparation

The downloader uses Python’s standard library. Offline preparation requires Python 3.10+, `lxml` and `pypdf`; exact runtime versions are saved in `environment.json`.

```sh
python scripts/download_native_book_batch.py data/research/multilingual-pilot-v1/acquisition-v1
python scripts/prepare_native_book_batch.py data/research/multilingual-pilot-v1/acquisition-v1
python scripts/validate_native_book_batch.py data/research/multilingual-pilot-v1/acquisition-v1
```

Existing downloads are checked against their receipts before reuse. The explicit saved source list bounds collection; the script does not crawl a site or execute downloaded content. Preparation regenerates derivatives/diagnostics, so update the collection manifest after a rerun.
