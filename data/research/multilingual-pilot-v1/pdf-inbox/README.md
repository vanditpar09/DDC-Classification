# PDF intake for the multilingual DDC pilot

Drop one PDF per exact book edition in this folder after its reuse rights have
been checked. Use the candidate ID from
`outputs/01a0ced2-2136-77d2-8ebe-04feab872ebf/multilingual-book-collection-review.xlsx`
as the filename, for example `hin:OL31865678M.pdf` (replace `:` with `_` on
filesystems that do not allow colons).

For each PDF, fill in the edition-language check, the verified three-digit DDC
section, the source used to verify that label, and the reuse basis/licence in
the review sheet. The catalog DDC and its level 1/2/3 values are weak hints;
they are not approved training labels. Confirm the language from the actual
pages, since catalog language fields and romanized titles can be wrong.

## Pages to use

For the first OCR feasibility check, use just 2–3 pages per book: cover, title
page, and contents page if present. These pages should not show a call number or
other label that gives away the expected answer. Keep the complete PDF in this
inbox only when its licence or written permission allows that storage. Convert
the selected pages to PNG images for the current collection pipeline; it accepts
page images, not PDFs directly.

On macOS with Poppler installed, for a PDF called `hin_OL31865678M.pdf`, convert
pages 1–3 at 200 dpi like this:

```sh
pdftoppm -f 1 -l 3 -r 200 -png \
  data/research/multilingual-pilot-v1/pdf-inbox/hin_OL31865678M.pdf \
  data/research/multilingual-pilot-v1/images/hin_OL31865678M
```

Check the actual PDF page numbers first; cover/title/contents pages may not be
pages 1–3. Rename generated images consistently and record their paths and page
types in the reviewed JSONL record. Keep a checked transcription for OCR
evaluation, in the original script, separate from OCR output.

## Rights and repository handling

Prefer public-domain works, open licences that explicitly allow the intended
machine-learning use, or written permission from the rights holder/library.
Record the licence or permission source. A PDF being viewable online, borrowable,
available through a university login, or listed in a catalog does not itself
grant permission to copy, train on, or redistribute it. Do not commit a full
book PDF to GitHub unless its licence or written permission explicitly allows
redistribution. Keep restricted scans local and private, and commit the metadata,
code, and only those page images/transcriptions that the recorded rights allow.

NDLI's terms say content remains the relevant rights holder's property and
restrict copying/reuse without permission; NDLI's open-access FAQ also says the
content-provider terms govern. Use NDLI for discovery, then check the original
provider's terms for each item. Do not bulk-download or scrape it for this pilot.
