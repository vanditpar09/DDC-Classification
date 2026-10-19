# Offline OCR improvement experiment

4 October 2026. This is a continued-development diagnostic on one user-provided
phone photo and three existing native-script page samples. It is not an
independent multilingual OCR accuracy benchmark.

The Mac automatic reader recovers **The Kite Runner** and **Khaled Hosseini** and
excludes laptop-keyboard text. The old Tesseract reader misses the title. The
portable EasyOCR comparison still misses that decorative title. Native-script
pages remain readable through Tesseract; EasyOCR has therefore been added as a
bounded fallback/repair rather than replacing the working first reader.

The server's DDC path for this cover is **900 / 910 / 914**, which is wrong for
this novel. The API/browser tests verify the software flow, not classification
correctness. OCR improvement does not certify the separate DDC classifier.

- `fixtures/phone-english-cover.png`: original user-provided development input;
  retained for private research. Public redistribution rights are not established.
- `source-receipt.json`: image hash and the limited visually checked reference.
  There is no complete gold transcription or verified catalog label here.
- `results.json`: raw reader outputs, coordinates, scores, elapsed times and work.
  Native comparison images are referenced by the earlier multilingual pilot's
  saved local-server source records; they are not new physical-phone captures.
- `server-check.json`: actual local image upload, OCR and hierarchical API result.
- `browser-check.json`, `phone-result.png`: phone-size browser check, including
  rereading the saved photo while respecting the one-repair limit. This uses a
  real phone-source image; the verification browser is not a physical handset.
- `model-manifest.json`: hashes/source of separately restored official weights.
- `code-hashes.json`, `manifest.json`: implementation and artifact checksums.

See [local OCR setup and limitations](../../../docs/LOCAL_SCENE_OCR.md).

Reproduce after preparing the optional readers and launching the app on port 8013:

```sh
.venv/bin/python scripts/evaluate_scene_ocr.py
.venv/bin/python scripts/check_server_ocr_gate.py
node scripts/check_scene_ocr_browser.cjs
```

The browser check requires Playwright. The setup is documented in
`docs/LOCAL_SCENE_OCR.md`. Serving never downloads weights or sends photos to an
online OCR service. The complete regression suite passed **203 tests**.
