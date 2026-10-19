# Multilingual DDC model: experiment and handoff

For the newer three-level extension, see [HIERARCHICAL_MODEL.md](HIERARCHICAL_MODEL.md).

Run date: 23 September 2026. Scope: the existing ten broad classes, `000` through
`900`. These are subject classes, not the book's language. A Hindi science book
should be classified as science; writing in Hindi does not imply class `400`.

## Completed work

The selected model is a frozen **multilingual E5-small encoder + logistic
regression (C=10) + sigmoid calibration**. The pretrained encoder was downloaded;
the DDC classifier and calibrators were fitted locally. The encoder itself was
not fine-tuned. Inference requires no cloud API after the download.

Training compares 16 fixed candidates: word/character TF-IDF with logistic
regression or linear SVM, and multilingual E5 embeddings with logistic regression.
Each family is compared with/without title-and-subtitle augmentation. Every book
has total weight 1, even when it contributes two text views. Unicode is preserved.

The selected model uses augmentation. Original catalog text and cover proxies
are grouped together throughout model selection. No new descriptions, subjects,
translations or labels were invented.

## Measured results

All rows below use the same 1,007 test books. Cover proxy means clean title plus
available subtitle, not an image or real OCR.

| Model | Catalog accuracy | Catalog macro-F1 | Cover accuracy | Cover macro-F1 |
|---|---:|---:|---:|---:|
| Previous saved baseline | 61.27% | 0.612 | 43.69% | 0.436 |
| TF-IDF reference, matched new splits/calibration | 60.48% | 0.604 | 44.59% | 0.450 |
| Selected multilingual E5 | **65.34%** | **0.653** | **55.21%** | **0.552** |

The gain over the previous model is 4.07 percentage points for catalog text and
11.52 points for cover proxies. A paired bootstrap over book groups (2,000
resamples, seed 42) gives descriptive 95% intervals of +1.10 to +7.18 points and
+8.26 to +15.09 points, respectively. These intervals do not capture dataset
selection bias, label errors or the difference between catalog text and scans.

Tradeoff: on the 414 books with subject headings, catalog accuracy fell from
82.13% to 77.78%; on the 593 without subjects it rose from 46.71% to 56.66%.
Overall top-3 accuracy is 86.89% for catalog text and 80.83% for cover proxies.

## Evaluation protocol

- Preserve the original seed-42 test assignment; do not train on it.
- Exclude all historical holdout groups from fitting and calibration. Split:
  3,061 training, 542 calibration, 1,007 test, 424 historical-reserved books.
- Select model/settings by three-fold StratifiedGroupKFold on training only.
  Objective: equal-weight average of catalog and cover-proxy macro-F1.
- Fit sigmoid calibration on 542 separate books, with one seeded catalog or cover
  view per book. Do not report in-sample calibration performance as validation.
- Evaluate the selected model and two predefined reference models. Save exact
  assignments, candidate scores, per-class results, confusion matrices, predictions,
  dataset checksum, encoder revision and environment.

The original test set was already inspected in earlier analysis. This is a
development benchmark, not a newly blinded deployment test. Obtain an independent
real-scan benchmark before making application claims. The previous model used
more fitting data and different calibration; the matched reference controls these
differences. A frozen pretrained encoder may have seen books during pretraining;
its original data cannot be audited from this repository.

## Run locally

From the repository root, with Python 3.9+ compatible with the pinned dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-ml.txt
.venv/bin/python -m src.ocr_pipeline.download_encoder
.venv/bin/python -m src.ocr_pipeline.train_improved --output-dir models/improved_v2
.venv/bin/python -m src.ocr_pipeline.predict_text "कंप्यूटर प्रोग्रामिंग का परिचय"
```

This workspace's environment was created with `uv`; if pip is unavailable, use
`uv pip install --python .venv/bin/python -r requirements-ml.txt` instead.
Output directories must be new so an experiment cannot silently overwrite another.
The CLI now prefers `models/hierarchy_v1/classifier.joblib` when available,
otherwise `models/improved_v1/classifier.joblib`; use
`--model models/improved_v2/classifier.joblib` for another run. Windows users can
replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

`--lexical-only` runs a smaller benchmark without the encoder download.
Download revision: `614241f622f53c4eeff9890bdc4f31cfecc418b3` of
`intfloat/multilingual-e5-small`. Copy both the classifier and
`models/encoders/multilingual-e5-small/` when moving the model to another machine.
The joblib file alone does not contain the encoder weights. The encoder is about
449 MiB, plus tokenizer files. Inputs beyond 512 tokens are truncated; page-aware
chunking remains future work.

## Integration status and limits

- The new model is ready for local text inference. The existing web API still
  loads `models/baseline_classifier.joblib` through `pipeline_config.yaml`.
- To trial the new model through that API, set `paths.model_artifact` to
  `models/improved_v1/classifier.joblib` and install the ML requirements alongside
  the application's dependencies. The API still requires Gemini; this does not
  make the entire web application offline.
- The API's `tfidf_*` response keys and UI label are legacy names; rename them to
  `local_model_*` before presenting an encoder-based ensemble as a finished app.
- The unchanged 0.85 auto-accept threshold accepted **zero** selected-model test
  cases. Set routing thresholds using separate representative development data
  and a precision/coverage goal, not test-set tuning. Gemini's confidence is not
  directly interchangeable with the local classifier's calibrated scores.
- The Tesseract implementation currently rejects non-Latin scripts. Multilingual
  text classification does not fix that OCR limitation. Install and select language
  packs, preserve original scripts, and validate each script end to end.
- Hindi, Marathi and Tamil phrase smoke checks passed plausible labels. They are
  illustrative, hand-written examples, not a labeled multilingual benchmark.
  No language-specific DDC accuracy is established by this experiment.
- NumPy 2.0.2 on this Mac emitted known Accelerate matrix-multiplication warnings.
  Features, coefficients and checked outputs were finite. Scores agreed with an
  independent float64 einsum calculation to less than 9e-15 on smoke inputs.
  See https://github.com/numpy/numpy/issues/28687. No warning suppression was added.

## Next data to collect

Start with English plus two priority Indian languages, provisionally Hindi and
Marathi. A pilot of 20 books per class per language gives 600 books across three
languages. Capture cover, back cover and contents where permitted; keep all
editions, translations and photos of a work in one split. Record original script,
language, verified broad class, reviewer, source evidence, page type and OCR text.
Use this pilot to identify failure modes; expand the independent test portion
before making precise language-level or 95%-precision claims.

Compare native-script embeddings, a translation-assisted baseline and reviewed
fine-tuning on the same book groups. Never use machine-translated copies as the
only evidence of native-language performance. Reserve real photos for evaluation.

## Validation

37 targeted tests passed for training partitions, feature leakage, augmentation,
Unicode preservation, encoder cache serialization, calibration reporting, routing
and threshold regression. Local model reload and multilingual phrase inference
were checked with Hugging Face offline mode. Dataset verification remains passing.
The full OCR/cloud application suite was not run as part of this model change.
