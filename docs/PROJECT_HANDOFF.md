# Project status and team handoff

Updated 8 October 2026, after adding the same-image catalog correction and prediction update. Start here when picking
up the project. This document describes the current app; earlier ETL and training
reports describe their own historical snapshots.

The main remaining work is **independent DDC model improvement and evaluation,
Indian-language OCR, and validation on the Windows demo laptop**. The app and
phone workflow are implemented. A known-book catalog match is not evidence that
the learned classifier can correctly classify an unfamiliar book.

## What is ready, and what is experimental

| Area | Current state | Evidence / starting point |
| --- | --- | --- |
| Web app and phone access | Laptop app, ngrok HTTPS tunnel and access-code gateway, camera/upload, queued-upload recovery and PWA shell implemented. Phone still needs the running laptop and tunnel. | [Run guide](../RUN_GUIDE.md), [phone sharing](LAPTOP_SHARING.md), `prototype/` |
| Saved research records | SQLite stores active full-resolution images, OCR, history, decisions and reviews. Latest main also updates a combined results table, CSV/JSON, detailed records and photo copies on the laptop. | [Capture outputs](CAPTURE_OUTPUTS.md), `prototype/storage.py`, `prototype/collection_export.py` |
| Multilingual DDC model | `native_silver_v2` trained; frozen multilingual E5 encoder with broad and conditional L2/L3 heads. Silver labels and scores remain experimental. | [Experiment v2](../data/research/multilingual-pilot-v1/experiment-v2/README.md), `models/native_silver_v2/` |
| Hierarchical output | Three levels supported. Trained provisional codes/scores now remain visible below review thresholds. Qualified paths, catalog codes and provisional suggestions stay separate; assignments need review. | [Provisional scores](PROVISIONAL_SCORES.md), `src/ocr_pipeline/catalog.py`, `prototype/controller.py`, `prototype/engine.py` |
| Known-book identification | Local catalog matcher requires title and author, with cover geometry to distinguish advertised titles. Source codes and raw learned suggestions are separate. Omitted OCR spaces are tolerated for full identities; saved books have an explicit Update prediction action preserving prior results. | `data/catalog/`, [DDC correction](../data/research/ddc-capture-fix-v1/README.md) |
| Portable English OCR | Local RapidOCR/ONNX path works on the saved cover and the fresh English phone example. | `prototype/portable_ocr.py`, `prototype/scene_ocr.py`, [OCR details](LOCAL_SCENE_OCR.md) |
| Indian-script OCR | Hindi/Marathi/Tamil pipeline and rendered-page smoke checks exist. The user's decorative Hindi cover still fails readability checks. | `prototype/scene_ocr.py`, `prototype/easy_ocr_worker.py`, [phone findings](PHONE_OCR_FINDINGS.md) |
| Distribution | Same project packaged for Windows x64 and Apple Silicon Mac, with models, launchers and instructions. | [GitHub release](https://github.com/abhinavnath02/DDC-Classification/releases/tag/demo-2026-10-04), [Windows](WINDOWS_DEMO.md), [Mac](MACOS_DEMO.md) |
| Platform verification | Fresh Mac Python 3.11 setup, extracted-package offline checks and browser checks passed. Native Windows remains unverified: GitHub returned `startup_failure` before any runner jobs started. | Release validation assets; `.github/workflows/windows-demo.yml` |
| Regression and data integrity | Latest validation: 251 tests passed; provisional scores verified through browser uploads of the three supplied images and CSV/JSON exports. Saved predictions remain unchanged by the display update. Original 5,034-record ETL snapshot verified separately. These are functionality/integrity checks, not general accuracy. | [Known-book correction](../data/research/book-identity-fix-v1/verification.json), [provisional-score verification](../data/research/provisional-scores-v1/verification.json), [collection verification](../data/research/collection-exports-v1/verification.json), [earlier integrity checks](../data/research/ddc-capture-fix-v1/verification.json) |
| Hosting | Deferred by project decision. The current phone link is a tunnel to the laptop, not a continuously hosted backend. | [Hosting plan](HOSTING_AND_PWA_PLAN.md) |

## Latest physical-phone observations

These are two development examples from user-supplied screenshots, not a measured
benchmark. Original full-resolution captures should be obtained from the laptop's
saved test records before running OCR comparisons; screenshot thumbnails are not
valid substitutes for those photos.

- **English, The Kite Runner:** title and author were recovered. The app selected
  The Kite Runner rather than the advertised A Thousand Splendid Suns. It showed
  800 → 810 → 813 from an attributed catalog record with source code 813/.6.
  Recognition indicator: 90.7/100, 26 words, 0% low-confidence words, no repair.
  This does not establish independent model correctness. The earlier raw model
  suggestion was 900 → 910 → 914; learned weights were not retrained for this fix.
  [English screenshot](images/phone-english-2026-10-04.jpg).
- **Hindi decorative cover:** some text was recovered, but readability still failed
  after one repair: indicator 64.1/100, 21 words, 38% low-confidence words. No text
  entered classifier evidence and no DDC assignment was made. This rejection is
  appropriate; reliable Hindi cover recognition remains unfinished.
  [Hindi screenshot](images/phone-hindi-2026-10-04.jpg).

Recognition indicators are internal confidence signals, not transcription accuracy.
The screenshots and latest code demonstrate the workflow, not population accuracy.

## Remaining work, in priority order

Ownership below names suggested responsibilities; no individual is assigned yet.
Record an actual owner and issue/branch when someone takes a task.

| Priority / responsibility | Task | Completion evidence |
| --- | --- | --- |
| P0 — evaluation/data | Establish an independent, reviewed book-level evaluation collection in English, Hindi, Marathi and Tamil. Separate classifier-only cases from catalog-assisted results. | Versioned work/edition identities, language, source-backed DDC, checked reference text, provenance and frozen partitions; overlap audit against training/catalog/development sources. |
| P0 — OCR | Diagnose the failing Hindi photo; compare original capture, printed title page and descriptive pages. Extend comparisons to Marathi/Tamil. | Saved paired OCR outputs against checked text, character/word error rates (CER/WER), missing-text counts, title/author recovery, latency and rejection decisions. New unseen photos must confirm improvement. |
| P0 — demo/platform | Run setup, offline checks and real phone captures on the actual Windows laptop. Investigate the GitHub runner startup limitation separately. | Actual Windows report, hardware/software versions, successful upload/reread/restart persistence and English/Indic results. A Windows-named ZIP checked on Mac is not native Windows verification. |
| P1 — model | Improve classification on unfamiliar books, especially L2/L3. Compare richer subject evidence and page-balanced inference with the current input. | Reproducible development comparison against native_silver_v2, per-language/per-level metrics, supported-class coverage, error examples, saved artifact and provenance. |
| P1 — data | Review doubtful existing labels and add targeted independent works for weak language/subject combinations. Include nonfiction contrasts within each language. | Reviewed dataset version, reconciled counts and work groups; no ambiguous labels silently promoted to ground truth. Retraining follows demonstrated gaps, not random downloads. |
| P1 — confidence/controller | Calibrate on separate works and validate abstention and repair/new-page decisions. | Frozen thresholds, error-versus-coverage results, excessive-confidence failure cases and a capture-policy comparison at matched classification quality. |
| P2 — research/report | Finish the report and evidence supporting the proposed technical contribution. | Reproducible results, adaptive versus fixed-page comparisons, latency/work savings, limitations and a documented prior-art assessment. Catalog lookup or a successful demo alone does not establish novelty. |
| P2 — deployment | Select hosting and implement the deferred deployment after the local demo is reliable. | Tested HTTPS phone workflow, resource/latency estimates, persistence, access control and documented operating cost. |

## Recommended next experiment

1. Start with a diagnostic development collection of unfamiliar books covering
   fiction and nonfiction in each target language. Check related editions,
   translations and textbook chapters before declaring a work independent.
   Do not count the already examined Kite Runner or Hindi cover as unseen tests.
2. Photograph cover, printed title page and descriptive back/contents pages.
   Retain originals and faithful transcriptions. Record blur, lighting and layout.
   Compare classifier results from checked text against results from actual OCR
   to separate recognition failures from classification failures.
3. Evaluate current weights before modifying them. Report L1/L2/L3 accuracy,
   macro-F1, valid hierarchy paths, abstention/coverage, errors by language and
   subject, and latency. Report catalog identification and catalog-code results
   separately; overlapping runtime catalog records cannot become an independent
   learned-model accuracy result.
4. Use development errors to choose OCR changes, additional labels and model
   changes. Define acceptance criteria before comparing candidates. Treat
   promotional cover text as an evidence-selection problem rather than adding
   guessed descriptions to the input.
5. Refit in new versioned directories, retaining native_silver_v2 as a baseline.
   Preserve work-group partitions. The existing pilot has four locked native test
   groups: do not open them to choose models, thresholds or OCR preprocessing.
   Freeze the method before final evaluation on untouched, reviewed works.

A focused ~200-work collection is an existing planning target, not a guaranteed
minimum for general DDC accuracy. See [dataset targets](MVP_DATASET_TARGETS.md).
The current native pilot has 77 edition samples in 66 provisional work groups;
its small silver-label development result does not replace independent validation.

## Where to make changes

| Work | Files / records |
| --- | --- |
| Reader routing, quality, framing and bounded repair | `prototype/scene_ocr.py`, `prototype/engine.py`, `prototype/controller.py`; `tests/test_scene_ocr.py`, `tests/test_prototype_ocr_quality.py` |
| Portable reader and Indian-script fallback | `prototype/portable_ocr.py`, `prototype/rapid_ocr_worker.py`, `prototype/easy_ocr_worker.py`, `prototype/easyocr_compat.py` |
| Learned model and training | `src/ocr_pipeline/multilingual.py`, `src/ocr_pipeline/hierarchy.py`, `src/research/train_silver.py` |
| Multi-page comparison and evaluation | `src/research/page_windows.py`, `src/research/evaluate.py`, `src/research/collection.py` |
| Catalog matching and source separation | `src/ocr_pipeline/catalog.py`, `scripts/build_catalog_index.py`, `data/catalog/`, `tests/test_catalog.py` |
| Prepared pilot and preserved experiments | `data/research/multilingual-pilot-v1/silver-pilot-v2/`, `experiment-v2/`, acquisition/review manifests |
| Platform setup and packages | `scripts/setup_demo.py`, `scripts/check_windows_demo.py`, `scripts/build_demo_packages.py`, platform launchers, `.github/workflows/` |
| Camera, queue and review UI | `prototype/static/app.js`, `camera.js`, `local-store.js`, `prototype/app.py`, `prototype/storage.py` |

Keep the six-pass per-book OCR budget, one-repair-per-photo limit, original-image
retention, safe upload replay and explicit model selection intact. Saved books
retain previous results until reread/recaptured; do not silently rewrite evidence.
Do not train on a model's own guesses as if they were reviewed DDC labels.

## Start locally and hand over a change

Follow [RUN_GUIDE.md](../RUN_GUIDE.md) for first setup from a clone or release.
On the current Mac, the fresh test server uses:

```sh
FIELDNOTE_OCR=portable FIELDNOTE_DB=output/fieldnote/fresh-test.sqlite3 \
  .venv/bin/python -m prototype.run --port 8017 --model native_silver_v2
```

### Phone camera testing via ngrok is already supported

Install/connect the ngrok CLI once on each teammate’s laptop using the
[phone walkthrough](LAPTOP_SHARING.md#start-test-the-app-on-a-phone-using-ngrok).
Keep the server running and use a second terminal for phone sharing. For the
fresh server on **8017**, from the project folder:

Mac:

```sh
.venv/bin/python -m prototype.share --backend-port 8017
```

Windows Command Prompt:

```bat
.venv\Scripts\python.exe -m prototype.share --backend-port 8017
```

Open the printed HTTPS Phone link in Safari/Chrome on the phone and enter the code
from `output/fieldnote/phone-access.txt`. Then use Open camera or the photo picker.
The phone can use Wi-Fi or mobile data; the laptop and both terminal windows must
stay running and connected. Packaged start/share shortcuts use **8013** instead;
match `--backend-port` to whichever app server is actually running.
Stop an older sharing launcher before starting a replacement.
Addresses, links and port numbers are local settings; another team member does
not inherit this laptop's running server, tunnel or saved capture collection.
For Windows, use the supplied setup/check/start launchers and Windows guide.

For a code change, run relevant tests and preserve experiment outputs. With the
demo dependencies installed, this targeted check works on either platform; replace
`python` with the environment's Python executable:

```sh
python -m pytest tests/test_catalog.py tests/test_scene_ocr.py tests/test_windows_demo.py \
  prototype/test_persistence.py prototype/test_gateway.py -q
python scripts/check_windows_demo.py
```

The check script's historical filename is shared across platforms; its JSON
records the actual host. Full legacy tests additionally need root
`requirements.txt`. Avoid overwriting historical reports or trained artifacts.
In a PR, identify the changed behavior, data/artifact revision, actual platform,
verification results and remaining limits. Update this handoff when a task closes.

## What is in GitHub versus local-only

The automatic readable exports were added after the demo-2026-10-04 package
revision. Use latest main for this feature; later package builds include it.

Source code, docs, the small native_silver_v2 classifier, catalog receipts, curated
training excerpts, split assignments, research reports and required smoke fixtures
are pushed to the private repository. Large pretrained encoder/OCR weights are
included in the release ZIPs or downloaded explicitly during clone setup.

Full acquired PDFs/EPUBs, intermediate full-book text/page images, installed
`.venv` folders, SQLite captures and tunnel credentials stay on the development
laptop. Git ignore rules preserve them locally; no originals were deleted.
Team members needing raw-source reproduction must arrange transfer of the files
identified in the acquisition manifests. Transfer demo captures separately from
credentials. GitHub source ZIPs are not the prepared model-bundled release ZIPs.
