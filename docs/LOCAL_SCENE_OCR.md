# Local OCR upgrade

Follow-up: the Windows demo now has a stronger portable English reader and a
transfer package. See [Windows demo](WINDOWS_DEMO.md) and
`data/research/portable-ocr-v1/`. The original results below remain the historical
comparison for the first Mac OCR upgrade.

4 October 2026. The laptop prototype now uses page framing and optional local
scene-text readers. Book photos are not sent to a cloud OCR service.

## What changed

- On this Mac, English photos use Apple's Vision accurate reader. A detected
  central page polygon excludes background text. Original pixels are retained
  for recognition: perspective resampling worsened decorative text in this
  example. No book-title dictionary or `customWords` hints are supplied; Vision
  language correction is disabled.
- For Hindi, Marathi and Tamil, the existing native Tesseract packs remain the
  first reader. When recognition is poor and a second pass is available, a local
  EasyOCR reader can try the page. Explicit rereads can use that reader as well.
  The fallback is selected only when it passes basic checks; a rejected fallback
  cannot displace the original rejected text. Both outputs are retained in the
  trace when they complete. This is not a calibrated accuracy guarantee.
- Scene readers detect text lines rather than forcing a cover into one uniform
  paragraph. EasyOCR inputs use detected page framing and bounded perspective
  correction. A failed/weak primary reader may use one fallback; the existing
  six-pass book budget and one-repair-per-photo limit still apply. A scene pass
  means one detection/recognition pipeline, not equal computation to Tesseract.
  Actual elapsed time and processed pixels are also recorded. Failed readers
  consume their reservation; a second-reader failure cannot trigger a third.
- **Read photo again** lets a user apply the upgraded reader to a saved image.
  The original image and previous OCR remain preserved. Reloading the app itself
  does not silently reprocess earlier captures. The operation queue still retains
  its IDs and revision checks.

## Observed results

The saved physical-phone image of *The Kite Runner* is a development example:

| Check | Previous Tesseract | New Mac path |
| --- | --- | --- |
| Actual title recovered | No | Yes: The Kite Runner |
| Author recovered | Yes | Yes: Khaled Hosseini |
| Laptop-keyboard text included | Yes | No |
| Reader elapsed time in local diagnostic | About 0.5 s | About 0.8 s |

Some subtitle/punctuation errors remain (for example “Thovsand”). The reader's
100-point line confidence is **not 100% transcription accuracy**. Neural scores
describe lines and are not directly comparable to Tesseract word scores.

The portable EasyOCR English comparison did not recover this decorative title;
do not assume a Linux deployment will have the same quality as this Mac. All
three existing native-script sample pages remain usable through the automatic
path. EasyOCR was weaker on the clean Hindi/Marathi body pages, which is why it
has not replaced their first reader. Only Tamil's comparison passed the current
basic quality checks. These are PDF-rendered pages, not new phone benchmarks.
The original failing Hindi phone image is unavailable; no repaired Hindi-phone
result is claimed.

The real API and browser checks confirm successful upload, title/author recovery,
background exclusion, three displayed DDC levels and saved-photo rereading.
They **do not validate the DDC code**: this cover's API suggestion was
`900 -> 910 -> 914`, which is inappropriate for this novel. Better OCR therefore
does not establish classifier accuracy. Descriptive subject evidence and further
classifier validation remain necessary; all candidate predictions require review.

The complete regression suite passes **203 tests**. Actual diagnostic outputs,
API results and the phone-size browser screenshot are preserved in
`output/ocr-upgrade-v1/`; a repository report is under `data/research/ocr-upgrade-v1/`.
The user-provided photo is preserved as a private research fixture; its public
redistribution status is not established. No patentability or
population-level accuracy claim follows from these tests.

## Restore the optional readers

The existing Python 3.9 / Torch 2.8 training environment is used:

```sh
uv pip install --python .venv/bin/python -r requirements-ocr.txt
.venv/bin/python scripts/setup_scene_ocr.py
```

On macOS the setup compiles `prototype/vision_ocr.swift` using the installed
`swiftc`; the executable and matching source hash are local under `output/`.
On other platforms Vision is unavailable. EasyOCR weights are downloaded once
from its official release locations into `models/ocr_easy/`, verified by the
package's expected checksums, and recorded with SHA-256 hashes. They total about
505 MiB and are ignored by Git. Serving uses `download_enabled=False`; it never
downloads weights in response to a book upload. Restore them with the setup
script on a new machine.

EasyOCR 1.7.2's published Tamil alphabet is truncated and cannot load its own
143-output pretrained model. `prototype/easyocr_compat.py` applies the narrow
alphabet correction documented in [upstream PR #1333](https://github.com/JaidedAI/EasyOCR/pull/1333/files).
It preserves ordering, checks the expected size, and does not edit the installed
package or retrain weights.

For an explicit original-reader comparison, launch with
`FIELDNOTE_OCR=tesseract`; otherwise the mode is `auto`. `/api/status` reports
available readers. The DDC artifact has not been retrained or replaced.

The macOS implementation uses Apple's documented
[text-recognition API](https://developer.apple.com/documentation/vision/vnrecognizetextrequest).
The portable reader uses [EasyOCR](https://github.com/JaidedAI/EasyOCR) 1.7.2 and
its official pretrained models. GPU/graphics access is needed for Mac Vision;
the local server runs with normal application permissions.
