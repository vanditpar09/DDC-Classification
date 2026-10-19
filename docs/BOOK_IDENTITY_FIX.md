# Hemingway single-image diagnosis and correction

8 October 2026. The exact saved single-image example now displays **800 / 810 /
813**, from a cached source-reported catalog code, after an explicit prediction
update. OCR and model weights were not changed.

## What failed

The learned model selected L2 820 with score 0.3373 over 810 at 0.2991, a margin
of only 0.0382. Its greedy hierarchy then evaluated L3 within 820, selecting 823
at 0.9025. That high conditional score did not establish the correct parent.
Showing provisional predictions made this existing classification error visible;
it did not cause the error. Broad L1 was 800 at 0.4957.

The book is American fiction in English, whereas 820/823 are the English
literature/fiction branch. [OCLC's schedule](https://www.oclc.org/content/dam/oclc/webdewey/help/800.pdf)
distinguishes these traditions. Selecting English OCR does not resolve them.
The runtime model still needs broader independent English-literature evaluation
and improved training support; its 820 head has 198 training groups versus 88
for 810. Unequal support is a possible contributor, not proof of the sole cause.

The local index contained no Hemingway record. OCR also joined adjacent words
as THEOLD and TheOldMan, preventing exact word-token identity/geometry matching.
A development ablation inserting spaces before capitalized words and after
punctuation still predicted 800/820/823. Text spacing alone was not a classifier fix.

## What changed

- Generic title/author matching tolerates omitted spaces while requiring the
  same complete letters and word boundaries. It does not repair misspelled names,
  accept a surname alone or infer an unknown code.
- Title prominence aligns contiguous OCR boxes even when a box merges words.
  Front and back covers are eligible; contents pages are not identity evidence.
  Study-guide exclusions, advertised-title geometry, author checks and conflicting
  section abstention remain in effect.
- Cached the photographed ISBN 9789355563187's title/author metadata and two
  English edition records reporting 813/.52:
  [OL22596607M](https://openlibrary.org/books/OL22596607M/The_Old_Man_and_the_Sea),
  [OL864609M](https://openlibrary.org/books/OL864609M/The_Old_Man_and_The_Sea).
  The photographed edition's own record has no DDC; the match remains work-level
  and explicitly requires edition review. Saved API responses retain timestamps.
- **Update prediction** reclassifies existing readable text without replacing
  photos, rereading OCR or changing manual reviews. Previous predictions and
  evidence revisions are retained in `prediction_history`; attempts and outcomes
  are logged. The phone queue uses the existing revision/idempotency protections.

The primary result is explicitly **Catalog match**, with no invented probability.
Raw model alternatives still show the original 800/820/823 error. Main export
columns show 800/810/813; separate provisional model columns retain raw candidates.
This corrects the known-book response, not the learned weights or general accuracy.

## Use and verification

Reload the updated app, select the saved book, then choose **Update prediction**.
**Reload book** only loads its saved result. The failing single-image record was
already updated during this fix; new uploads use the revised matcher directly.
No server-wide automatic rewriting of historical predictions occurs.

Regression checks cover joined OCR, complete identities, missing/wrong authors,
advertised titles, study guides, image/review preservation, failure retention,
revision conflicts and safe replay. The [verification record](../data/research/book-identity-fix-v1/verification.json)
includes the same-image correction and unchanged classifier hash. Full suite:
**251 passed**. Browser verification was on Mac; native Windows testing is pending.

Use latest main. The October 4 release ZIPs predate this change. Source responses
and reports are committed; full supplied photos, SQLite and screenshots stay local.
