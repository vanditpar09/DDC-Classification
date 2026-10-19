# Provisional DDC scores

Updated 8 October 2026. The latest app displays trained model candidates at
L1/L2/L3 even when they fall below the review thresholds. Each is marked
**Provisional**. This is a display change, not retraining or a measured accuracy
improvement. Reload an older open app page to load the updated interface.
The later [Hemingway identity fix](BOOK_IDENTITY_FIX.md) diagnoses the single-image
820/823 error and explains the source-backed 810/813 correction.

The saved threshold-qualified path and capture decisions remain separate. A
book may show provisional codes while still requesting another page or manual
review. The model score threshold remains 0.62 and margin threshold 0.18. No
code is invented for a missing or rare trained branch. Failed/unreadable OCR
still needs a clearer capture or checked transcription before classification.

L1 shows a broad class score. L2 and L3 scores are **conditional on the predicted
parent**, not independent correctness probabilities. A high L3 score cannot
resolve an uncertain L1/L2 choice. The combined path score multiplies the three
model scores; it is uncalibrated too. None of these scores measures OCR accuracy
or overall classifier accuracy.

Catalog matches continue to show source-reported codes without a fabricated
probability. Expand **Raw model alternatives** to inspect their learned L1/L2/L3
path and scores separately.

## Exports and team handoff

The [results table and local exports](CAPTURE_OUTPUTS.md) now include a
**Provisional model / scores** column. CSV/JSON additionally include `Suggested
L1`, `Suggested L2`, `Suggested L3`, `L1 model score (%)`, `L2 conditional score
(%)`, and `L3 conditional score (%)`. Main L1/L2/L3 columns remain reserved for
threshold-qualified or catalog results. Recorded manual review remains separate.
Existing SQLite collections rebuild these fields at restart; their saved OCR,
predictions and reviews are not rewritten or rerun.

## Development example

Three user-supplied images of The Old Man and the Sea were uploaded through the
browser as cover, back cover and contents. All passed the existing OCR checks.
The cover alone led to a provisional History branch; adding descriptive evidence
changed the candidate. With all three images, the candidate was **800 / 810 / 813**
with scores **31.1% / 35.4% / 96.5%**, and a combined path score **10.6%**. No level
passed the full review chain. These are functional development observations, not
an independent accuracy benchmark or a newly verified DDC label.

The user's original contents-only capture and all existing books remain saved.
The new three-page example is saved separately. Generated captures/screenshots
remain local under ignored `output/`. No example images are added to training or
used to change the learned model. See the [verification record](../data/research/provisional-scores-v1/verification.json).

Use latest `main`; the earlier demo-2026-10-04 ZIPs predate this addition. Future
packages use the same updated `prototype/` source on Windows and Mac. Actual
native Windows validation remains pending.
