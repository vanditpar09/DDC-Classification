# Local book preparation results

3 October 2026. Eight development books; 24 nonempty OCR outputs from 12 selected PDF pages; 28 raw/clean EPUB spine pairs. All 88 classifier calls returned finite, valid probability results. No classifier weights were changed. These are functional diagnostics, not accuracy or camera results.

| Book | Evidence used below | Native OCR / extracted clean text suggestion (L1 / L2 / L3) | Catalog proposal |
|---|---|---|---|
| दासबोध, खंड २ | [PDF page 10](text/dasbodh_khand_2-page-10-mar.clean.txt) | 200 / 220 / abstain | 294; unverified |
| सत्य के प्रयोग अथवा आत्मकथा | [PDF page 10](text/gandhi-autobiography-hindi-page-10-hin.clean.txt) | 400 / 420 / 428 | 320, 954; unverified |
| गोदान | [PDF page 10](text/godan_by_premchand-page-10-hin.clean.txt) | 800 / 820 / 823 | 891; unverified |
| On the Origin of Species | [EPUB spine 3](text/pg1228-images-3-spine-03.clean.txt) | 500 / 590 / 599 | 575, 576; unverified |
| Pride and Prejudice | [EPUB spine 3](text/pg1342-images-3-spine-03.clean.txt) | 800 / 820 / 823 | 823; unverified |
| பொன்னியின் செல்வன் | [PDF page 15](text/ponniyin-selvan-page-15-tam.clean.txt) | 800 / 820 / 823 | 894; unverified |
| श्यामची आई | [PDF page 17](text/shyamachi_aai-page-17-mar.clean.txt) | 200 / 290 / 294 | unresolved; unverified |
| தொல்காப்பியம் | [PDF page 10](text/tolkappiyar-page-10-tam.clean.txt) | 600 / 610 / 616 | 494; unverified |

The input for each comparison is the first 2,500 characters of its own raw or clean text; no externally supplied title, subject keywords or DDC label is injected. The encoder further truncates inputs longer than 512 tokens. This differs from the earlier smoke run, which prefixed the expected title. Comparisons across those two reports are therefore not controlled method comparisons. All spine documents belong to their original work; 88 calls do not represent 88 independent books.

## Findings

Godan and Ponniyin Selvan still receive section 823 on the selected prose samples. Their primary catalog proposals are 891 and 894 respectively. The existing model cannot return either target: section 891 has only three catalog work groups, 894 has none, and no fine head for parent 890 was fitted. Section 494 is also absent from the active child classes. Cleaner OCR cannot replace that missing supervised coverage.

Native-only OCR produced more expected-script letters on several bilingual covers, but script proportion and Tesseract confidence do not measure transcription accuracy. No variant is declared the winner. The selected Shyamchi Aai story page is new; the earlier sample was author biography. Religious themes in a single story excerpt can still produce a religion suggestion.

## Saved artifacts

- `preparation.json`: every sample, exact inputs, predictions, source/work IDs and cleaning records.
- `text/`: raw text, cleaned text and a separate removal audit for each sample.
- `images/`: source PDF pages rendered at 200 DPI for checking OCR.
- `runtime-observations.json`: package versions, model/language-pack hashes and observed warnings.
- `../LABEL_REVIEW.md`: primary catalog evidence, conflicts and remaining label checks.
- `../head-coverage-v1.json`: exact active-class coverage of the saved model.

No human reference transcriptions, CER/WER, training, calibrated multilingual accuracy, real phone captures or patent novelty conclusions are produced by this run.

## Reproduce

Use the project ML environment with local encoder/model artifacts, Tesseract
language packs and Poppler available. Select a NEW output directory. `--source`
allows source relocation while requiring the original file hashes.

```sh
.venv/bin/python scripts/prepare_book_intake.py \
  data/research/multilingual-pilot-v1/intake-v1 \
  --plan data/research/multilingual-pilot-v1/intake-v1/page-plan-v1.json \
  --source data/research/multilingual-pilot-v1/pdf-inbox \
  --output output/book-preparation-next --predict
```
