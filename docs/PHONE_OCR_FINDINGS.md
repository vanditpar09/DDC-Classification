# First physical-phone OCR findings

For the current team priorities and latest phone findings, see
[Project status and handoff](PROJECT_HANDOFF.md).

4 October 2026. The phone upload works, but decorative-cover recognition is not
adequate. This is a diagnostic on user captures, not a representative benchmark.

This records the initial Tesseract findings. A subsequent local-reader upgrade
now recovers the English title and author; see [Local scene OCR](LOCAL_SCENE_OCR.md)
for the implementation, measured improvement and remaining limits.

The English capture of *The Kite Runner* includes a laptop keyboard, perspective,
shadow and glossy cover lettering. Its initial OCR includes keyboard labels,
misses the title, and reads some ordinary printed words correctly. A mean token
confidence of 61.5 is not a 61.5% transcription-accuracy estimate. Of the 64
recognized tokens, 40.6% score below the current 55-point confidence threshold.
The former mean-only check nevertheless admitted this text for classification.

The Hindi screenshot has a mean score of 38.8 and was correctly flagged as needing
attention. Its original capture is not present in the current server databases;
only the supplied screenshot was assessed. No claimed Hindi repair was tested.

## Checks and changes

- Preserved the English original and previous session in
  `output/ocr-phone-review/`. These diagnostic copies remain local and ignored.
- Compared PSM 6 (uniform text block), PSM 3 (automatic layout), and PSM 11
  (sparse text) on the complete photo and a manually specified cover crop.
  Six recognition runs are recorded in `layout-comparison.json`. The crop is a
  diagnostic, not an implemented automatic page detector. None recovered the
  actual title. Cropped PSM 3 scored 83.3 while still missing it, demonstrating
  why selecting the highest-confidence result alone is unsafe.
- Added a provisional quality rule: reject a page when more than 30% of its
  recognized tokens score below 55. The mean, sharpness, script and small-print
  checks still apply. This rejects the observed English failure. The 30% limit
  is an experimental heuristic, not a calibrated correctness guarantee.
- Kept raw OCR available for inspection. Rejected pages do not enter combined
  classifier evidence. Old saved sessions are not silently rewritten.
- Replaced the misleading “Readable OCR” badge with “Text extracted · check
  photo”; the displayed recognition score explicitly says it is not accuracy.
- Verified noisy text with a high mean is excluded, clear text remains usable,
  and the existing suite passes: **193 tests**.

The OCR engine was not retrained or replaced. These changes improve rejection and
reporting; they do not solve the stylized-title recognition failure. The DDC model
is a separate classifier and cannot correct text that the OCR reader misses.

## Next practical test and engineering work

Capture the plain printed title page and a descriptive back cover, filling the
frame with the page and avoiding reflected light. Compare the extracted title,
author and subject text directly with the photo. Cover-only scores are insufficient
to establish quality.

The next OCR improvement cycle should add page framing/cropping and compare a
local scene-text recognition system against the current reader on these same
saved images plus independent Hindi, Marathi and Tamil captures. Preserve raw
outputs, manually check the reference text, and report both recognition errors
and latency. Do not invent missing titles from known-book lookups or count these
development examples as an independent test of a tuned system.

Tesseract's [official image-quality and layout guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
explains segmentation assumptions, borders, skew and contrast. It does not imply
that preprocessing alone will recover decorative cover lettering.
