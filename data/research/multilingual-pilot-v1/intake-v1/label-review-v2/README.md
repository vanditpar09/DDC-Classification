# DDC working-label review

Completed by Codex assistant, 4 October 2026. These are documented working recommendations for local development. They are not exact-edition, human-reviewed gold labels or permission to train on the supplied text. No model was fitted. Original proposals and identity evidence remain preserved.

| Book | Working L1 → L2 → L3 | Evidence decision | Active L3 in saved model? |
|---|---|---|---|
| दासबोध, खंड २ / Dasbodh, volume 2 | 200 → 290 → 294 | related translation hint only | Yes |
| सत्य के प्रयोग अथवा आत्मकथा / Satya ke Prayog athava Atmakatha | 900 → 950 → 954 | provisional catalog policy choice | No |
| गोदान / Godan | 800 → 890 → 891 | same work other edition provisional | No |
| On the Origin of Species By Means of Natural Selection; Or, the Preservation of Favoured Races in the Struggle for Life | 500 → 570 → 576 | schedule supported working selection | No |
| Pride and Prejudice | 800 → 820 → 823 | same work other edition provisional | Yes |
| பொன்னியின் செல்வன் / Ponniyin Selvan | 800 → 890 → 894 | same work other volume edition provisional | No |
| श्यामची आई / Shyamachi Aai | 800 → 890 → 891 | same work library class supported provisional | No |
| தொல்காப்பியம் / Tolkappiyam | 400 → 490 → 494 | related partial work hint only | No |

## What changed

Darwin: choose **576** for this pilot’s modern section vocabulary. [OCLC’s DDC 23 summary](https://www.oclc.org/content/dam/oclc/dewey/ddc23-summaries.pdf) puts evolution in 576; the [BnF facsimile record](https://catalogue.bnf.fr/ark%3A/12148/cb373533442) explicitly records 576.82 under DDC 23. The earlier 575 record is preserved; its schedule edition was not established, so this review does not assert its historical origin.

Shyamchi Aai: numeric work-level evidence is now available. [Vivekanand College’s library list](https://www.vivekanandcollege.ac.in/uploads/library/Marathi%202_merged.pdf), PDF page 93 / printed page 92, row 4170, accession U11989, shows Sane Guruji, श्यामची आई and 891.463. The complete row was visually checked. A [second college list](https://www.moderneducation.org/pdf/Library_Books_List.pdf), PDF page 30, accessions 899–903, corroborates 891.463. Its [institutional self-study report](https://www.moderneducation.org/naac/Revised%20version%20of%20SSR.pdf) names DDC. These are other editions, not the E Sahitya ebook. Repeated copies count as one work.

Gandhi: use **954** as a provisional project recommendation, while preserving the 320 conflict. [IIT Gandhinagar’s Hindi list](https://library.iitgn.ac.in/documents/library_files/Hindi-Books.pdf), PDF page 28, records the autobiography in 2011 and 2025 editions under 954.035092. The [library collection page](https://library.iitgn.ac.in/printresources) confirms DDC use. [Tezpur’s library bulletin](https://www.tezu.ernet.in/Library/InfoGranth/InfoGranth23/IGJuly23.pdf) provides another institutional Hindi-work record with 954.035092, available through its search index. However, the closer translator/publisher match at LBSNAA uses 320.55. This is not uniquely resolved by the schedule heading or by language. Gandhi is excluded from a single-label correctness tally.

Tolkappiyam: further explicit DDC evidence exists, including [CUTN MARC 2226](https://library.cutn.ac.in/cgi-bin/koha/opac-MARCdetail.pl?biblionumber=2226) and a [Tamil original-author part with commentary at CiNii](https://ci.nii.ac.jp/ncid/BA71774228). They support a 494 subject hint; neither verifies the full uploaded digital edition. Dasbodh’s 294 evidence remains a Hindi-translation hint.

Godan, Austen and Ponniyin Selvan retain the earlier work-level proposals 891, 823 and 894. Their different digital/print editions and volume limitations remain recorded.

## What this permits

Five books have enough work-level evidence for an explicitly provisional diagnostic comparison: Godan, Austen, Ponniyin Selvan, Darwin and Shyamchi Aai. Gandhi, Dasbodh and Tolkappiyam remain outside a single-label correctness tally. None of the eight is eligible for formal accuracy claims, an independent test or this pipeline’s reviewed-data training input. The assistant review is recorded honestly; human_checked remains false. A team member may later review the record without needing a librarian.

## Training readiness

The current artifact lacks active L3 outputs for 891, 894, 494, 576 and 954. Those gaps affect six of the eight working recommendations. Fine-class support needs additional distinct works, contrast classes under the same parent, and consistent schedule/policy labels. OCR cleanup cannot create a missing classifier output.

| Section | Existing weak catalog groups | Additional groups to reach current minimum of 5 |
|---|---|---|
| 891 | 3 | 2 |
| 894 | 0 | 5 |
| 494 | 0 | 5 |
| 576 | 1 | 4 |
| 954 | 4 | 1 |

These counts are an implementation threshold, not a reliable training target. The examined books remain development material. Additional training, calibration and test works should preserve one work group across editions and translations; more pages from the same book do not supply more independent works. Native-language reference/OCR quality and reuse fields also remain incomplete.

## Saved files

- decisions.jsonl: all eight recommendations, alternate candidates, rationale, eligibility and stable work/source identities.
- evidence.json: prior primary records plus 9 new evidence entries, exact field roles and retrieval limitations.
- policy.json: explicit modern-section vocabulary and catalog-conflict handling.
- readiness.json: actual unchanged model hash and per-book classifier support.
- sources/: three downloaded reference PDFs with URLs, timestamps and hashes.
- pages/: the three relevant PDF pages rendered and visually inspected, with raw extracted text kept separately. Raw Indic extraction is not a checked transcription.
- manifest.json: all packet hashes plus references to the unchanged earlier snapshots.
