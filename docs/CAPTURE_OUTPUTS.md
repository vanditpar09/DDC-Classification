# Phone synchronization and laptop output files

Updated 4 October 2026. This feature is in the latest source on `main`; the
`demo-2026-10-04` release ZIPs were built before this addition. To use it on a new
machine, use the latest clone/setup instructions in [RUN_GUIDE.md](../RUN_GUIDE.md).
The package builder includes this feature in subsequent builds. Existing model
weights can be reused; no retraining or new Python dependency is required.
See the [verification record](../data/research/collection-exports-v1/verification.json)
for regression, browser and saved-photo integrity checks; these do not establish
classification accuracy or native Windows validation.

## What synchronizes

A successful phone upload goes through the ngrok gateway into the same laptop app
and SQLite database used by the laptop browser. Saved photos, raw OCR, quality
checks, supported DDC suggestions, source information, decisions and manual
reviews are available on that laptop. Unreadable OCR pages can still be saved;
they have no classification until usable evidence exists.

**Pending on this device** means that capture is still queued on the phone and
has not completed synchronization. Keep the queued photo and retry while the
server/tunnel is running. An upload/reader exception is not a completed saved
photo; inspect its saved attempt trace and the phone queue. Terminal access logs
alone are not the complete research output.

## View a Book / L1 / L2 / L3 table

Choose **Results table** beside Saved books, or visit `/api/collection` on the
running server. For the current fresh test:

- [Laptop results table](http://127.0.0.1:8017/api/collection)
- [CSV download](http://127.0.0.1:8017/api/collection/export?format=csv)
- [JSON download](http://127.0.0.1:8017/api/collection/export?format=json)

The same Results table link works on the phone through its authenticated ngrok
URL. The table refreshes every ten seconds. Its columns include Book, L1, L2, L3,
source, status, recorded manual review and photo/record links. The laptop capture
page's Saved books list can be refreshed by reloading it; a second browser is not
an independent database.

Codes are taken from saved results, not from sample table values. Unsupported or
unavailable codes appear as a dash. A rejected Hindi image remains present with
its rejection status and no invented classification. Catalog results are marked
as catalog matches; raw model alternatives remain in the detailed record. Manual
review values stay separate, with the reviewed evidence revision recorded.

The latest app/table also shows [provisional model scores](PROVISIONAL_SCORES.md)
below review thresholds. They have separate Suggested L1/L2/L3 and score fields
in CSV/JSON; they do not replace the main threshold-qualified or catalog columns.

## Files created automatically on the server computer

The export directory sits beside the configured SQLite database and is named
`<database-stem>-exports`. For the fresh test using
`output/fieldnote/fresh-test.sqlite3`:

```text
output/fieldnote/
  fresh-test.sqlite3                 authoritative database
  fresh-test-exports/
    classifications.html            readable table, refreshes every 10 seconds
    classifications.csv             combined table for analysis
    classifications.json            table rows plus page/photo identifiers
    records/<session-id>.json        raw OCR, quality, prediction, decisions, reviews
    photos/<session-id>/<page-id>.png  saved full-resolution photo pixels as PNG
```

Open `classifications.html` on the laptop to see the table and local photo/record
links without running a separate viewer. The CSV includes session IDs, revisions,
languages and reviewed codes. Import DDC columns as **text** in a spreadsheet to
preserve leading zeros such as `000` and `005`. JSON/HTML preserve the code strings.
Photo copies preserve the saved normalized image pixels; they are PNG encodings,
not the original JPEG container or its metadata.

Tables and the affected record/photo copies update after server saves, including
classification, reprocessing and manual review. Replacing a page removes the old
active photo from the database and export copies; its OCR metadata remains in
page history. Deleting a book removes its row, record and derived photo directory.
These are current collection outputs, not an immutable archive. Export/back up
needed evidence before deleting/replacing it.

SQLite remains authoritative. Restarting rebuilds missing derived exports without
rerunning OCR/classification or changing saved predictions. If export writing
fails, the capture still remains in SQLite; the server logs the export error and
`/api/status` reports it under `readable_exports`. A summary can briefly show
Classification pending while the model is still working; the final save updates
it. The directory files are derived per-file snapshots, not a transactional backup
of the entire database while captures are actively changing.

## Rebuild older saved collections manually

From the project folder, after updating to the latest source:

Mac:

```sh
.venv/bin/python scripts/export_capture_collection.py --db output/fieldnote/fresh-test.sqlite3
```

Windows Command Prompt:

```bat
.venv\Scripts\python.exe scripts\export_capture_collection.py --db output\fieldnote\windows-demo.sqlite3
```

Use the database configured by `FIELDNOTE_DB`; different app launches can use
separate collections. Prefer rebuilding while the app is stopped. Restart the
app on the same database to enable automatic updates in a previously running
older process. Keep the phone's existing pending queue; updating does not require
clearing saved books.

## Handoff and privacy

The SQLite database and all generated exports are under ignored `output/` and
are not automatically committed or sent to GitHub. Share a selected snapshot with
teammates when required. The export folder includes photos and detailed research
records, so include it intentionally when handing over data. An online table is
protected by the same phone access-code gateway as the capture interface; local
files are readable by anyone with filesystem access to the laptop.
