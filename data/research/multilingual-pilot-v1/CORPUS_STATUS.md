# Native-book collection status

Updated 4 October 2026.

Two saved acquisition batches contain **61 downloaded titles**, with **57 unverified native text extractions**. There are **60 provisional work groups**, or **59 after excluding the quarantined anthology**. These counts do not certify independent originals or complete books.

**Verified training books: 0. The model has not been retrained on these batches.** Labels, text fidelity, source-use status, and overlap with the original catalog/development books still require review.

| Language / collection stratum | Downloaded titles | Target distinct reviewed works |
| --- | ---: | ---: |
| Hindi literature | 14 | 40 |
| Marathi literature | 16 | 40 |
| Tamil literature | 12 | 40 |
| Tamil language/grammar | 13 | 40 |
| Comparison subjects | 6 | 40 |

The counts in this table are collection proposals, not verified DDC assignments. Hindi and Marathi literature share candidate DDC section 891. The Marathi literature total includes an unresolved selected-writings anthology. Several Tamil grammar/prosody texts have competing possible classifications.

The focused MVP recommendation is 200 reviewed original-work groups. A 60–80-work reviewed pilot is sufficient to begin a small training experiment, not to claim broad accuracy. See [the dataset targets](../../../docs/MVP_DATASET_TARGETS.md) for sampling, splits, within-language subject balance, and evaluation.

The immediate collection gap is comparison subjects in Hindi and more nonfiction across all three languages. Also resolve OCR needs, exact numeric labels and related-work identities before assigning an untouched test split.

Saved files include original PDFs/HTML, acquisition receipts and checksums, Unicode text derivatives, indexed Hindi EPUB derivatives, page previews, quality notes, and exclusions. Existing development books are separate and are not included in these new collection counts.

- [First batch report](acquisition-v1/README.md)
- [Second batch report](acquisition-v2/README.md)
- [Combined inventory](corpus-inventory-v2.jsonl)
- [Combined summary](corpus-summary-v2.json)


## Latest evidence review — 4 October 2026

All 61 titles have an assistant review pass saved in [the review report](review-v3/README.md). Across 141 sampled PDF pages, 24 titles passed the conservative text/OCR agreement screen, 19 need fidelity investigation and four had unusable original extraction. Thirteen Hindi HTML texts remain candidate transcriptions without an independent page-image comparison; one Hindi sequence is incomplete. These categories sum to 61, and screen agreement is not a checked transcription. Seven Hindi works have supporting numeric catalog evidence; two Tamil works have section conflicts. Data collection is not complete, and no model has been retrained.

## Native training update - 4 October 2026

NCERT comparison samples are retained in acquisition-v3/v4 (selected chapters, not complete books). Silver-pilot-v2 contains 77 edition samples in 66 provisional work groups: Hindi 30, Marathi 23 and Tamil 24. Four work groups remain locked for later test evaluation. Experimental training and local OCR/API checks are complete; see [experiment-v2](experiment-v2/README.md). Acquisition-v1/v2 and review-v3 remain historical snapshots, and their original eligibility flags were not promoted.
