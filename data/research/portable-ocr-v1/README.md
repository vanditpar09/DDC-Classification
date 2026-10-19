# Portable OCR development checks

4 October 2026. Prepared for a Windows x64 demo. These results were produced on
macOS with `FIELDNOTE_OCR=portable`, using CPU ONNX models and no Apple Vision.
An actual Windows installation/run is still pending. See `docs/WINDOWS_DEMO.md`.

The saved real phone image is reused from `ocr-upgrade-v1/fixtures/`. The light
PP-OCR English comparison missed the full title. The server models recovered
“The Kite Runner”, “Khaled Hosseini” and “A Thousand Splendid Suns” on original
pixels. Rectifying the same page worsened its decorative lettering. The chosen
reader filters background observations using the detected book boundary; there
are no known-title hints, catalog searches or guessed spelling corrections.

The reader took about nine seconds locally including process/model initialization.
Recognition confidence is not transcription accuracy. `previous-readers.json`
retains the earlier Tesseract, Mac Vision and EasyOCR comparison. The three probe
records include rejected alternatives, rather than only the successful result.

`offline-smoke.json` records four images with network connections disabled: this
cover and existing Hindi, Marathi and Tamil page samples. Indian scripts retain
Tesseract and the EasyOCR repair fallback. These native-page checks establish
functionality/basic readability, not physical-phone accuracy. The failing Hindi
phone cover remains unverified. `browser-check.json` and `phone-result.png` record
the real upload flow, all three displayed DDC levels and one bounded saved-photo
reread in a phone-sized local browser. No new handset test is claimed.

**The novel's DDC suggestion remains wrong (`900 -> 910 -> 914`).** Neither these
functional checks nor better OCR validate classification. All scores still require
review. The DDC model hash is unchanged. Runtime matrix warnings were observed in
the macOS offline classifier run; final scores passed the existing finite checks.
The model's correctness and calibration remain separate work.

`verification.json` records 215 passing regression tests and successful Windows
Python 3.11 dependency resolution. It distinguishes a Windows package resolution
from actual Windows execution. `model-manifest.json` pins public model sources and
upstream checksums, plus an OFL Noto Sans font that avoids an incidental font
network request. Serving explicitly denies model/font downloads.

The private transfer package is under `output/windows-demo/`; its build script
includes code, required weights and only the four test fixtures. It excludes
virtual environments, saved user captures, database contents and tunnel secrets.
The English photo has no established public redistribution clearance.

Run `scripts/finalize_portable_ocr.py` after reproducing checks to refresh the
artifact/code fingerprints. `manifest.json` verifies this report's files; older
reports remain intact. These development results are not a population-level
accuracy benchmark or evidence of patent novelty.
