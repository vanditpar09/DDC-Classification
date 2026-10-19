# Minimum viable native-book dataset

Updated 4 October 2026. These are planning targets, not experimentally established minimum sample sizes.

## Scope and targets

The first native-language MVP covers Hindi and Marathi literature (candidate DDC 891), Tamil literature (894), and Tamil language/grammar (494), with other subjects as comparison examples. It does not establish coverage of all DDC sections or all Indian languages. The existing English data and model remain separate baseline resources.

| Collection stratum | First pilot target | Focused MVP target |
| --- | ---: | ---: |
| Hindi literature | 12–16 independent works | 40 |
| Marathi literature | 12–16 independent works | 40 |
| Tamil literature | 12–16 independent works | 40 |
| Tamil language/grammar | 12–16 independent works | 40 |
| Comparison subjects across the same languages | 12–16 independent works | 40 |
| Total | 60–80 | 200 |

Count distinct original works after identity and label review, rather than downloaded files, chapters, editions, or translations. At least five authors per literature stratum is a useful collection goal; include multiple publishers and periods where available. Grammar often has many editions and commentaries of the same few works: establish related-work groups before counting them independently.

Comparison books must appear in **each** target language. For example, collect Hindi nonfiction as well as Hindi novels, and Tamil history as well as Tamil fiction and grammar. Otherwise script or language can become a shortcut for the subject label. Aim for at least ten comparison works per language within the 40-book comparison target, spanning more than one subject. Thin comparison sections must retain broader predictions when fine-level support is inadequate.

## What makes a collected book usable

1. Match title, author, language, and edition using its own title page or publisher content plus a catalog. A filename or keyword is insufficient. Establish the acquisition and training-use status separately.
2. Corroborate the proposed DDC number using catalog evidence and the book's actual subject. Publisher genre categories support a proposal but do not verify a numeric DDC assignment. Do not confuse another library classification scheme with DDC.
3. Extract native text, retain the original source, and inspect sampled body passages against the source. Scanned and legacy-font PDFs need OCR or a matching Unicode edition. Preserve original notices and provenance.
4. Resolve edition, translation, anthology, commentary, and rewrite overlaps with the old catalog and development books. Keep related texts in the same work group or quarantine them while identity is unresolved.
5. Record the actual reviewer and evidence. Assistant checks must not become claims of human transcription review or librarian approval. A librarian is helpful but not a prerequisite for carrying out evidence-based collection and identifying uncertainties.

All acquisition records currently retain provisional labels and `training_eligible=false`. Downloading a book does not silently promote it into a verified training or test set.

## Sampling and evaluation

Take three to five non-overlapping body-text examples per work, including passages away from the title and front matter. This gives roughly 600–1,000 examples at 200 works, but the statistical sample size is still 200 works. Select passages without their DDC label, source URL, or catalog description embedded in the input.

Assign work groups before splitting. The project's nominal train/development/calibration/test proportions are 60/20/10/10: approximately 120/40/20/20 works at 200. Actual deterministic group assignments will differ; inspect and balance the strata before freezing the experiment. Never move individual pages across splits to fill a quota. At this scale the held-out samples per language and section are small, so uncertainty must accompany results.

Start with the frozen multilingual encoder and retrain supported hierarchical classification heads. Compare against the current model and a simple word/character baseline. Keep unsupported fine classes at broader levels. Run learning curves with increasing **training work counts**, using development data to decide whether more books help; preserve the final test set until the model choice is frozen. Measure level 1, 2, and 3 accuracy separately, macro-F1, hierarchical path consistency, and abstention/coverage by language and subject.

The 60–80-work pilot checks whether this pipeline learns anything useful. The 200-work target supports a focused demonstration; measured performance and uncertainty decide whether it is sufficient. Broad DDC coverage needs additional well-supported sections and substantially more independent works.

## Collection sources that worked locally

- [Hindi Samay novel index](https://hindisamay.com/upanyas/Index%20Novel.htm): native Hindi publisher/university web text. Follow every indexed part; exclude navigation-only pages and introductions when collecting a novel.
- [e-Sahitya](https://www.esahity.com/): Marathi PDFs, including literature and [travel writing](https://www.esahity.com/23462381235223572366236023572352238123392344.html). Inspect the book because filename titles and PDF text extraction can be misleading.
- [Project Madurai](https://www.projectmadurai.org/pmworks.html): Tamil catalog with paired PDFs and Unicode pages. Some links are broken and some works span multiple source parts.
- [Tamil Virtual Academy library](https://www.tamilvu.org/en/library): an additional source for Tamil books and language references; not yet counted as a new download in this collection.

See the saved `acquisition-v1` and `acquisition-v2` folders under `data/research/multilingual-pilot-v1` for actual local files, receipts, exclusion logs, and quality checks. Source availability does not by itself establish training or redistribution permission.

## Next experiment after text and label review

First evaluate native text classification. Then collect a separate phone-photo experiment across all three scripts, varied lighting, blur, angles, and page layouts. Keep phone captures grouped by book. Compare fixed-page capture with the adaptive capture controller using recognition quality, classification accuracy, images requested, and latency. Ebook classification results alone do not establish camera performance or patent novelty.
