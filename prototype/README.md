Current Windows/Mac setup and package instructions: [RUN_GUIDE.md](../RUN_GUIDE.md).

# Book Classification: local capture prototype

This prototype uses **local OCR and the trained multilingual E5 DDC classifier**.
On this Mac, English photos can use Apple Vision with page framing; native-script
pages retain Tesseract with an optional offline scene-text fallback. See
[Local scene OCR](../docs/LOCAL_SCENE_OCR.md) for setup, comparisons and limitations.
For the Windows presentation, use the [Windows demo setup](../docs/WINDOWS_DEMO.md)
and `scripts/windows-start.cmd`; it uses the stronger portable English reader.
A transparent rule-based controller decides whether to repair
OCR, ask for a clearer photograph, request another page, or stop for human review.
It is a research demonstrator, not a trained capture policy or a patentability
finding. The code is included with the model extension; generated patent forms
and trained model binaries remain local.

## Run on this machine

From the repository root:

```sh
.venv/bin/python -m prototype.run --port 8012
```

Open http://127.0.0.1:8012 after starting the server. Port 8012 lets this version run
alongside an older prototype on 8011. Opening
`prototype/static/index.html` directly as a file cannot connect to the API.
No cloud API key is needed. The model is loaded on first
inference. Stop with Ctrl-C. Books, current images, page replacement history,
reviewer labels and operation receipts are stored in
`output/fieldnote/experiments.sqlite3` (ignored by Git). Set `FIELDNOTE_DB` to use a
different database. Run **one serving process/worker** against this database.
New book preserves previous books; use the saved-book selector to return to one.
There is no automatic expiry. A 100-book limit prompts explicit export/deletion.
Export retains text, decisions, scores, model hash and reviewer labels; it does
not include image bytes. Back up the database while the server is stopped to
retain images too. Delete book removes that book and its images/receipts.

### Local camera and offline workflow

- Open camera requests the rear camera where available. Capture, inspect, retake
  or use the photograph; camera tracks stop on capture, close and backgrounding.
- The separate photo picker can invoke the phone camera even when embedded live
  preview is unavailable. HEIC support depends on the browser/OS; export JPEG if
  an image cannot be decoded. Uploads retain their dimensions; camera frames are
  encoded as JPEG at quality 0.95 without additional resizing. Image resizing
  needs a separate OCR-quality experiment.
- The manifest, icons and service worker allow installation and offline loading
  of the application shell after an online visit. On iPhone/iPad, use Safari's
  Share → Add to Home Screen; on Android, use the browser's installation menu.
- Pending photos, transcriptions, repairs and reviews are stored explicitly in
  IndexedDB, capped at 12 operations / 48 MB of images on this device. Reopen the
  app, reconnect, or select Retry uploads to resume. Inference requires the server.
  Browser site-data deletion/eviction can remove pending items, so retain source
  photos for important experiments. The service worker never caches API data.
- Each upload carries an operation ID and expected book revision. A lost response
  can be replayed without repeating work. A stale edit or interrupted server
  operation stops the queue for inspection; it is not automatically overwritten.
  Reload the book, inspect its trace, save a pending photo if needed, remove the
  blocked item and submit corrected evidence deliberately.
- OCR attempts reserve up to two passes before execution. Successful attempts
  replace this with actual work. Failed/interrupted attempts keep the conservative
  reservation; their processed-pixel total is unknown. If classification fails,
  the OCR text, image and completed work remain saved.
- Librarian review records a three-digit section, reviewer, book/edition ID,
  source note, evidence revision and the prediction seen at review time. Broader
  labels are derived from that section. Reviews do not alter model weights or
  automatically make the current suggestion accepted.

### Phone access through an HTTPS link

The access-code gateway serves the same website and API through ngrok while OCR,
the model and records remain on this laptop. Both the local server and the sharing
process must stay running. The tunnel provider carries book uploads and results.
See [Laptop sharing](../docs/LAPTOP_SHARING.md) for the architecture, access-code
handling, start/stop instructions, limits and phone test steps. The public tunnel
has not yet been activated; local HTTPS proxy tests do not establish public access.

```sh
# Terminal 1
.venv/bin/python -m prototype.run --port 8012
# Terminal 2, once sharing via ngrok is approved
.venv/bin/python -m prototype.share
```

### Testing on a phone on your Wi-Fi

The default server remains loopback-only. Live camera and service-worker features
require a secure context: localhost qualifies on the Mac, but a phone's plain
`http://192.168…` connection does not. For a trusted home/lab LAN, use a locally
issued TLS certificate trusted by both the Mac and phone, then run, replacing the
example address and certificate paths:

```sh
.venv/bin/python -m prototype.run --host 0.0.0.0 --port 8012 \
  --origin https://192.168.1.20:8012 \
  --cert /path/to/local-cert.pem --key /path/to/local-key.pem
```

The certificate must cover the selected IP/name, and the issuing CA must be
trusted on the phone. Merely clicking through a certificate warning is insufficient
for reliable PWA/camera support. This command permits exactly the configured
origin; it does not add wildcard CORS. Without HTTPS, the picker/transcription
flow can still be tried by configuring an explicit HTTP origin, but live preview
and offline installation are unavailable. The direct LAN server has **no access-code gate**: other users who can reach it
can access its books. The protected tunnel above is a separate entry point.
Always-on hosting remains a later milestone.

Background on browser requirements: [camera secure contexts](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia),
[service workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers).

### Try these experiments

Start a **New book** between independent experiments.

1. **Ambiguous cover**, then **Descriptive back cover**: the readable cover asks
   for more subject information. The description changes the leading class to
   `000`, but its approximately 37% score remains too uncertain; the controller
   requests the contents page. It does not force a confident answer.
2. **Blurred page**: requests a clearer capture and excludes unreliable OCR from
   the classifier. The image marks the area to inspect.
3. **Small print**, then **Try one local repair**: a contrast/upscale pass recovers
   usable text and produces a `000` broad suggestion, approximately 67%. With
   the hierarchy model it requests another page because section 005 versus 006
   remains uncertain, even though the broad class and division pass.
4. Repeat an identical sample: OCR and classifier counts do not increase. Reload
   the browser, restart the server, or switch to another saved book and return:
   the current evidence remains available.
5. Select **Transcription** and try `कंप्यूटर प्रोग्रामिंग का परिचय`,
   `संगणक प्रोग्रामिंगची ओळख`, or `தமிழ் இலக்கியம்`. Unicode text is preserved;
   transcription bypasses OCR and has no fabricated image-quality score.
6. Upload your own front-cover, back-cover or contents photo. Select the matching
   OCR pack: English, English + Hindi, English + Marathi, or English + Tamil.

Built-in images are synthetic typography fixtures, not scans of actual books.
Indic phrase checks demonstrate text plumbing, not Indian-language OCR accuracy.

## Setup on another machine

Use Python compatible with `requirements-ml.txt` (this workspace uses 3.9), install
Tesseract through the OS package manager, then:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r prototype/requirements.txt
.venv/bin/python -m prototype.setup_ocr
.venv/bin/python -m src.ocr_pipeline.download_encoder
.venv/bin/python -m prototype.make_samples
```

If this `uv`-created environment lacks pip, use
`uv pip install --python .venv/bin/python -r prototype/requirements.txt`.
The setup step downloads public language packs; application inference stays local.
The downloader pins tessdata_fast revision
`87416418657359cb625c412a48b6e1d6d41c29bd`, retains existing packs, and records their
SHA-256 values in `models/ocr_tessdata/setup_manifest.json`. This machine's English
and OSD packs came from its installed Tesseract; Hindi, Marathi and Tamil came
from the pinned revision. Use `--base-tessdata /path/to/tessdata` to copy installed
English/OSD packs on another machine. OCR results can differ across pack versions.

Restore the trusted local artifact `models/hierarchy_v1/classifier.joblib` **and**
`models/encoders/multilingual-e5-small/`, or fit both stages on a fresh checkout:

```sh
HF_HUB_OFFLINE=1 .venv/bin/python -m src.ocr_pipeline.train_improved --output-dir models/improved_v1
HF_HUB_OFFLINE=1 .venv/bin/python -m src.ocr_pipeline.train_hierarchy --output-dir models/hierarchy_v1
```

Training directories must not already exist. The prototype also supports the
L1-only artifact `models/improved_v1/classifier.joblib` as a fallback. Model
binaries are not committed to GitHub. Do not load untrusted joblib files.

## What is implemented

- Separate OCR confidence/sharpness/character-size checks from DDC uncertainty.
- One contrast/upscale repair per image and six OCR passes per book, including
  attempted script-detection passes. The interface exposes OCR time, processed
  pixels, classifier calls and every decision.
- Script-mismatch suggestions when Tesseract OSD supplies sufficient evidence.
  OSD is unreliable on short text; users can select the language themselves.
- Three replaceable evidence slots: cover, back cover and contents. Corrections
  replace stale text. Exact repeated images and normalized repeated text are
  excluded from repeated work/evidence; Indian combining marks are retained.
- Class, division and section suggestions with broader fallback when fine model
  support is insufficient. Score at least 0.62 and margin at least 0.18 must pass
  at every ancestor before a fine suggestion is ready for human review. Readable
  but uncertain finer results request more subject evidence. **No automatic acceptance**.
- Bounded embedding caches (2,048 texts per feature object), configurable CPU
  threads (`FIELDNOTE_CPU_THREADS`, default 4), and reuse of the computed broad
  probabilities when building the hierarchy. These are inference changes, not
  retraining or measured accuracy gains.
- Oversized/invalid upload checks, localhost binding, and rejection of foreign
  browser origins for writes. No remote fonts, analytics or image services.

The `reprocess_region` action currently processes the **whole image** with
bounded contrast/upscaling; its rectangle guides recapture. Region-only OCR,
layout analysis and learned action selection are future experiments. Reported
pixel counts include the whole processed image and any OSD pass.

## Validation and limitations

27 September 2026 sharing/UI update: **16 gateway boundary tests plus 13
persistence tests passed**, as did **12 direct local browser scenarios** and
**14 browser scenarios through the access-protected loopback HTTPS gateway**.
The latter include sign-in, lost-response recovery, expired access with queued
upload recovery, real OCR/hierarchical inference, and simulated phone capture.
The public tunnel and physical phone remain untested pending sharing approval.


Local update on 26 September 2026: **82 targeted tests, 12 real OCR/model smoke
checks, 12 browser scenarios and the separate-process restart check passed**.
The browser checks use a synthetic camera and a 390-pixel viewport; physical
Android/iPad capture and installation remain to be tested. They exercise real
OCR and the saved classifier for sample images, offline HTML reload, queued
Unicode and image bytes, automatic/manual reconnect, dropped responses, stale
edits, saved reviews, camera permission denial and asset-cache isolation.
The restart check starts two independent HTTP servers against one temporary
database and verifies restored images, real repair/inference and safe replay.

```sh
.venv/bin/python -m pytest prototype/test_controller.py prototype/test_persistence.py \
  tests/test_hierarchy.py tests/test_inference_runtime.py tests/test_router.py \
  tests/test_training_protocol.py tests/test_threshold_regression.py tests/test_leakage.py -q
.venv/bin/python -m prototype.smoke_test
.venv/bin/python -m prototype.check_restart
# With a local server on 8012 and Playwright available to Node:
node prototype/browser_checks.cjs
```

Browser screenshots/results are written to `output/browser-tests/`; the HTTP
restart result/log is in `output/fieldnote/`. Set `FIELDNOTE_TEST_URL` to test a
different local port. The restart test uses port 8013 and a disposable database.

Local validation on 24 September 2026: **73 targeted tests passed; 12/12 real-OCR/model smoke checks passed**. Browser checks
verified the cover-to-description flow, blur guidance, small-print repair, session
reset and Hindi transcription. These are functional checks, not accuracy estimates.

```sh
PYTHONPYCACHEPREFIX=/tmp/ddc-pycache .venv/bin/python -m pytest prototype/test_controller.py -q
HF_HUB_OFFLINE=1 .venv/bin/python -m prototype.smoke_test
```

`smoke_results.json` records actual real-OCR/model outputs. Initial smoke testing
incorrectly expected the descriptive back cover to finish classification. It
produced score 0.373 and margin 0.076: correctly below the unchanged thresholds.
The regression now checks continued evidence gathering and improved ranking;
it is a development check, not an independent accuracy evaluation.
The full legacy application suite cannot collect in the lean prototype environment
because its `src.api` imports `python-dotenv`, which is not installed. Its cloud
application dependencies are separate from this prototype.

The classifier has been trained; the capture policy has **not**. Thresholds are
experimental and have not been tuned on representative scans. English synthetic
image cases and Hindi/Marathi/Tamil transcription cases do not establish
multilingual scan accuracy. Calibration on catalog text need not transfer to OCR.
Inputs over 512 encoder tokens require human review if they would otherwise be
marked ready. The model now covers 70 divisions and 149 sections; see
`docs/HIERARCHICAL_MODEL.md` for measured accuracy and training limitations.
No translation, chunking, OCR correction model, decimal DDC subdivisions,
semantic duplicate detection, deskewing, or automatic camera quality guidance is
implemented. The new camera preview provides manual framing/focus guidance.

The current macOS NumPy/Accelerate stack may print numerical matmul warnings.
Inference validates finite normalized scores; the separate model experiment
checked scores against an explicit float64 calculation. Warnings are not hidden.

## Next experiment before making research claims

Collect consented/private book scans with librarian labels, language, page type,
OCR transcription, capture defect and book ID. Include legible-but-ambiguous
covers, blur/glare, mixed scripts, and books where another page resolves ambiguity.
Split by book/edition and hold out libraries or publishers; never mix pages from
the same book across train/test partitions.

Compare this controller with (a) one cover only, (b) all three pages, and (c) OCR
retry before every extra-page request. Measure DDC accuracy/macro-F1, OCR CER/WER,
unnecessary recaptures, classifier calls, processed pixels, latency and human
review rate by language. Set routing thresholds using a separate development set.
Evaluate quality-only and uncertainty-only ablations to test whether combining
the signals helps. Make efficiency claims only at matched classification quality.
Use a locked, independently collected real-scan test set for the final comparison.

The CLI and prototype prefer the local `models/hierarchy_v1/classifier.joblib`
artifact when present. The small-print smoke case now requests a back cover after
repair: L1 and L2 pass, but section 005 versus 006 remains uncertain. This is the
intended hierarchy-aware change from the earlier broad-class-only behavior.

For the current multilingual data collection and page-window comparison workflow,
see [Multilingual next steps](../docs/MULTILINGUAL_NEXT_STEPS.md). The experimental
window predictor is available separately; the prototype still uses its saved
baseline pending real-book evaluation.

## Native-language experiment - 4 October 2026

A separately trained experimental artifact is available at `models/native_silver_v2/classifier.joblib`. It supports Indian-language literature and Tamil language sections using assistant-reviewed silver labels. Scores are uncalibrated and every suggestion requires review. The original default model remains available.

```sh
FIELDNOTE_DB=output/fieldnote/native-silver-v2.sqlite3 .venv/bin/python -m prototype.run --port 8013 --model native_silver_v2
```

Use [the local experiment](http://127.0.0.1:8013/) while that process is running. The separate database preserves experiment captures. [Training results](../data/research/multilingual-pilot-v1/experiment-v2/README.md) distinguish small body-text development checks from actual camera validation.
