# DDC class division and section model

The local prototype now produces three-level suggestions with parent consistency
and broader fallback. This is a fitted model, not extra digits appended to a
broad prediction. It remains experimental: finer catalog accuracy is substantially
lower than broad-class accuracy.

## Implementation and coverage

The frozen multilingual E5-small encoder and existing calibrated ten-class head
are reused. Ten conditional division heads and 58 conditional section heads were
fitted locally. Their outputs cover **70 divisions and 149 sections**, not all
DDC codes. No decimal subdivisions beyond the first three digits are assigned.

A section is considered only under the predicted division, which is considered
only under the predicted broad class. For example, `000 → 000 → 005` is a valid
three-level path; the first two codes legitimately share the same padded digits.
A parent error propagates to its children. Fine scores are conditional on the
shown parent and must not be read as end-to-end confidence or accuracy.

Each supported fine label must occur in at least five distinct training book
groups. Rarer labels are pooled into an OTHER outcome. A winning OTHER outcome,
an absent head, or a one-class branch keeps a broader suggestion. This reduces
false precision but does not reliably detect every unseen class. Labels absent
from training and catalog noise remain limitations.

## Label audit and training

The dataset has broad labels and raw catalog codes, not verified L2/L3 labels.
A fine target is derived only when every catalog code agrees at that prefix and
matches the corrected L1 label. Leading zeros are retained. The L1-only corrected
record cannot inherit its incompatible original fine codes. Two different
sections can agree on a division, so label eligibility is evaluated per level.

Of 3,061 fitting books, 3,041 have unambiguous division labels and 3,028 have
unambiguous section labels. They contain 94 divisions and 436 sections before
minimum support and branch checks. Catalog-number subject entries are removed
from fine-model inputs to avoid reading the target from metadata; ordinary prose
and Indic combining marks are preserved. This is not a complete audit of every
possible catalog label cue.

The exact prior split assignments are retained: 3,061 fitting, 542 calibration,
1,007 test and 424 historical-reserved books. Historical holdouts do not enter
fitting or calibration. Catalog and title/subtitle views receive total weight 1
per book. C=10 and minimum support=5 groups were fixed before this evaluation;
there was no fine-level hyperparameter search.

A single temperature per fine level was fitted on held-out calibration text,
using the true parent. Division calibration used 541 books; section calibration
used 512 representable books. Unsupported calibration outcomes are excluded when
the relevant head has no OTHER output. This does not validate routing thresholds
or calibration on scans. The encoder was not fine-tuned.

## Development benchmark

| Level | Eligible test books | Catalog accuracy | Cover proxy accuracy | Catalog macro-F1 | Cover macro-F1 |
|---|---:|---:|---:|---:|---:|
| Class | 1,007 | 65.34% | 55.21% | 0.653 | 0.552 |
| Division | 1,001 | 47.35% | 37.66% | 0.277 | 0.206 |
| Section | 998 | 28.06% | 23.45% | 0.084 | 0.077 |

These are end-to-end results, including parent errors. Six division and nine
section test labels are ambiguous and excluded. Unsupported labels remain in
the accuracy denominator and missing predictions count as incorrect. Macro-F1
uses all eligible truth labels, including those the model cannot output.
Cover proxy means clean title/subtitle, not OCR or a photograph.

The unchanged experimental checks (score ≥0.62 and top-two margin ≥0.18 at every
ancestor) pass 85 catalog section suggestions, of which 63 are correct (74.12%).
They pass 62 cover-proxy section suggestions, of which 43 are correct (69.35%).
This small selected subset is **not** evidence of safe automatic cataloging.
The test set was inspected previously; these are development results, not fresh
validation. Indian-language book/scan accuracy has not been measured.

Full metrics and per-label counts are in `docs/benchmarks/hierarchy_v1.json`;
label availability is in `docs/benchmarks/hierarchy_label_audit.json`.

## Local use

```sh
HF_HUB_OFFLINE=1 .venv/bin/python -m src.ocr_pipeline.train_hierarchy --output-dir models/hierarchy_v2
HF_HUB_OFFLINE=1 .venv/bin/python -m src.ocr_pipeline.predict_text 'कंप्यूटर प्रोग्रामिंग का परिचय'
HF_HUB_OFFLINE=1 .venv/bin/python -m uvicorn prototype.app:app --host 127.0.0.1 --port 8011
```

Training needs the previous `models/improved_v1/classifier.joblib` and local E5
encoder. Output directories must be new. The CLI and prototype prefer
`models/hierarchy_v1/classifier.joblib` when present, otherwise use the L1 model.
Use CLI `--model models/hierarchy_v2/classifier.joblib` to inspect another run.
Restart the prototype after replacing an artifact; its loader is cached.
The separate legacy cloud API remains unchanged and does not return this hierarchy.

## Capture controller and patent context

The prototype distinguishes three conditions: unreliable OCR needs recognition
repair; readable but uncertain fine classification needs more subject evidence;
an unsupported finer branch below a passing parent needs librarian review and
better training data. It retains a broader suggestion rather than forcing a
section. OCR budget, evidence replacement, duplicate exclusion and human review
continue to apply. The interface shows each level, conditional alternatives,
training support and review status.

For a synthetic small-print programming image, one repair makes the text usable.
L1 and L2 then pass, while section 005 scores 0.479 versus 006 at 0.402, so the
controller requests a back cover. An authored Hindi programming phrase returns
000 → 000 → 005. These are functional examples, not language accuracy evidence.

This extends the implemented evidence controller described in the private patent
draft. Hierarchical classification alone is not presented as an established novel
invention. The testable research question remains whether coordinated image
quality, per-level uncertainty, model coverage and evidence replacement reduce
processing work at matched classification quality. That benefit is not measured.

## Validation and next work

73 targeted tests and 12 real-OCR/model smoke checks passed. All 68 fine heads
converged with finite coefficients. Decision scores matched an independent
float64 einsum calculation (tolerance 1e-10); all 2,014 evaluated paths obeyed
parent constraints, and split files exactly matched the earlier experiment.
The macOS NumPy/Accelerate stack still emits matmul warnings; checks did not find
non-finite scores. The legacy cloud application suite was not part of this run.

The immediate bottleneck is reliable fine-label coverage. Collect librarian-verified
section labels and actual cover/back/contents scans in the target languages,
starting with the library's most frequent sections. Audit conflicting catalog
codes and reserve unseen books/editions/libraries for evaluation. Keep all photos
and translations of one work in one partition. Expand training examples for rare
sections before claiming broad coverage.

Then compare this conditional model against a joint leaf-ranking model and a
retrieval-assisted candidate list using a permitted, verified catalog. Add
page-aware chunking so late contents evidence survives the 512-token limit.
Evaluate these alternatives on development data and use a new locked scan set
for the final comparison. Do not tune on the reported test results or claim a
technical efficiency gain before the controller ablation experiment.

## Multilingual experiment tooling (3 October 2026)

The reviewed-book collection, local raw-OCR runner, immutable work partitions,
paired language evaluator and experimental page-window predictor are now
implemented. The saved model/prototype still use the existing inference baseline.
See [the next-steps plan](MULTILINGUAL_NEXT_STEPS.md) for collection fields,
commands and comparison protocol. Native-language training and accuracy
measurement require reviewed real books; authored smoke examples are excluded.
