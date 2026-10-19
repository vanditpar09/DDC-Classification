# Catalog-assisted DDC correction, 4 October 2026

The native_silver_v2 learned model misclassified the real photographed cover of
The Kite Runner as 900 → 910 → 914 even after readable OCR. Title-only and
clean title/author probes also failed. See `raw-model-probe.json` and earlier
portable-ocr-v1 records. These examples are development regressions, not a test
set for tuning reported model accuracy. No learned weights were changed here.

A separate offline bibliographic matcher now requires a complete title and
complete author on a cover. Several matching books abstain unless OCR geometry
clearly distinguishes a prominent main title from advertised titles. An unknown
code, conflicting section, study guide or unverified identity does not supply a
catalog assignment. This strict matching may miss valid books; it intentionally
does not guess or use a language model to invent text.

The saved Open Library edition OL24237802M reports 813/.6. Its title and author
match this cover, with The Kite Runner substantially larger than the advertised
A Thousand Splendid Suns. The interface displays 800 → 810 → 813, the source
code and source link. Raw model scores/path remain in `model_suggestion`; catalog
assignments have no model probability. All catalog matches require edition review.
The Pride and Prejudice edition OL28581875M reports 823.7 and supplies another
identity regression. These source-derived labels are not librarian certification.
Some editions for A Thousand Splendid Suns lack DDC; search-aggregated conflicting
codes are preserved as receipts but not silently used as authoritative labels.

`data/catalog/index.json` is reproducibly built by scripts/build_catalog_index.py
from the original weak catalog plus cached edition responses. No network lookup
occurs during capture/classification. Do not describe catalog lookup coverage as
held-out learned-model accuracy: much of this metadata overlaps training sources.

Without a catalog match, each displayed hierarchy step now requires supported
training, score >= 0.62 and margin >= 0.18. An uncertain parent prevents any finer
code from appearing as established. These inherited heuristic thresholds are
not calibrated probabilities; richer subject pages and manual review remain
necessary. The full unfiltered learned suggestion is preserved for research.

Offline photo checks and the mobile-sized browser upload/reread passed on macOS,
with portable OCR and network-disabled inference. Hindi/Marathi/Tamil images
retain functional OCR checks only. No general DDC/OCR accuracy claim follows.
Native platform setup/check reports are published separately with the packages.
Original saved user books were not rewritten; reread or recapture to apply this
policy. The shared source is packaged for Windows x64 and Apple Silicon macOS.
