# Label review for the eight supplied books

Status: research proposals only, 3 October 2026. All books remain development-only; no labels are verified and no model was fitted. Catalog evidence is from indexed institutional records, with direct retrieval limitations recorded in the JSON.

| Supplied book | Language | Candidate section(s) | Remaining check |
|---|---|---|---|
| दासबोध, खंड २ | mar | 294 | Identity inspected by assistant; resolve exact-edition DDC correspondence |
| सत्य के प्रयोग अथवा आत्मकथा | hin | 320, 954 | Resolve schedule/catalog-policy conflict |
| गोदान | hin | 891 | Identity inspected by assistant; resolve exact-edition DDC correspondence |
| On the Origin of Species | eng | 575, 576 | Resolve schedule/catalog-policy conflict |
| Pride and Prejudice | eng | 823 | Identity inspected by assistant; resolve exact-edition DDC correspondence |
| பொன்னியின் செல்வன் | tam | 894 | Identity inspected by assistant; resolve exact-edition DDC correspondence |
| श्यामची आई | mar | unresolved | Locate numeric DDC in an original-edition catalog |
| தொல்காப்பியம் | tam | 494 | Hints are from a commentary/partial translation; find original-edition label |

## Completed identity inspection

On 4 October 2026, Codex inspected the supplied title/publishing material and filled [SELF_REVIEW.md](SELF_REVIEW.md). See [identity-v1/README.md](identity-v1/README.md) for publisher, translator, edition dates and page evidence. Austen’s base illustrated print edition is George Allen, 1894; Darwin’s EPUB identifies the 1859 John Murray first edition. Digital release dates are recorded separately. These checks do not promote any DDC label to verified status.

## Source evidence

- [CUTN-GODAN-7395](https://library.cutn.ac.in/cgi-bin/koha/opac-detail.pl?biblionumber=7395): गोदान / Godaan; 891.433. Uploaded HindiKosh PDF has 526 pages, no matching ISBN established.
- [GSU-AUSTEN-1112](https://opac.gsu.ac.zw/bib/1112): Pride and prejudice; 823/.7 (DDC 22). Penguin edition differs from illustrated Gutenberg EPUB; slash removed only in numeric interpretation, not original evidence.
- [LBSNAA-PONNI-59184](https://gsl.lbsnaa.gov.in/cgi-bin/koha/opac-detail.pl?biblionumber=59184): Ponniyin Selvan pt.1; TN 894.81136 KRI. Uploaded file appears to collect multiple parts. Volume/edition/ISBN not matched.
- [CUTN-TOLKAPPIYAM-31183](https://library.cutn.ac.in/bib/31183): தொல்காப்பியம் - சொல்லதிகாரம் உரைக்கொத்து; 494.8115 GOP. Commentary on part of Tolkappiyam, not the uploaded original Project Madurai 2001 text. Subject-class hint only.
- [KERALA-TOLKAPPIYAM-752104](https://campuslib.keralauniversity.ac.in/cgi-bin/koha/opac-detail.pl?biblionumber=752104): Tolkappiyam - Porulatikaram: An English Translation with Critical Notes; 494.8115 GLO/T. Only a part of the original grammar; does not verify the full uploaded Tamil edition.
- [BNF-DARWIN-37353344](https://catalogue.bnf.fr/ark%3A/12148/cb373533442): On the origin of species; 576.82 (DDC 23). Modern DDC differs at section level from older catalog classifications. Do not silently choose a preferred edition of the schedule.
- [FINNA-DARWIN-99542518306247](https://www.finna.fi/Record/kamk.99542518306247): On the origin of species; Dewey-luokitus 575. Conflicts with BnF section 576. Publisher/year not confirmed from returned excerpt.
- [LBSNAA-GANDHI-205011](https://gsl.lbsnaa.gov.in/cgi-bin/koha/opac-detail.pl?biblionumber=205011&query_desc=pl%3A%22New+Delhi%3B%22): Satya ke prayog athava atmkatha / translated by Kashinath Trivedi; GL H 320.55. Publisher and translator agree with uploaded front page, but edition/date/page count do not establish exact match.
- [CINII-GANDHI-BA55263465](https://ci.nii.ac.jp/ncid/BA55263465?l=en): An autobiography or The story of my experiments with truth; DC19 954.03/5/0924. English translation gives a different section from the Hindi LBSNAA record. Needs a documented choice of local cataloging convention.
- [LBSNAA-DASBODH-204794](https://gsl.lbsnaa.gov.in/cgi-bin/koha/opac-MARCdetail.pl?biblionumber=204794): Hindi dasbodh / translated by Ramchandra Verma; 082: GL H 294.561. Hindi translation of the Marathi work, not the uploaded Marathi second volume. Requires original-edition review.
- [UNIPUNE-SHYAM-IDENTITY](https://brlibrary.unipune.ac.in/book/shyamchi-aai-4/): Shyamchi Aai; no DDC recorded. Book-review portal corroborates work/language; no DDC is present. Its publication date is inconsistent within the page, so it is not edition verification.

## Human review

The reviewer may be a team member; a librarian is not mandatory for a local
pilot. Use [SELF_REVIEW.md](SELF_REVIEW.md) to record your own catalog-backed
checks, provisional matches and unresolved cases. Self-review does not establish
independent professional validation.

Review the images and raw/clean OCR pairs in `prepared-v1/`. Correct OCR into a separate `reference_text` only after checking the image. Keep labels in this packet separate from classifier text. Do not use raw embedded PDF text as an Indic reference.

Fill the checked three-digit section, reviewer, exact label source, edition identity and applicable permission fields in the existing reviewed-book collection workflow. A proposal here must not be copied as a verified label without that review. Related editions/translations keep the same `work_id`. The current excerpts have already informed development and must not become an independent final test.

The first PDF page of Ponniyin Selvan is a table of contents, not a cover. Body pages are kept as body diagnostics, not substituted into the cover/back/contents camera benchmark.

The eight works cover a narrow mix of literature, grammar, evolution, autobiography and religious writing. They cannot support fitting reliable fine classes on their own. Additional distinct works are required for training, calibration and a new held-out test.
