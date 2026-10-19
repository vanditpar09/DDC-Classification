# macOS demo

Use the shared instructions in [RUN_GUIDE.md](../RUN_GUIDE.md). The Mac release
uses the same code, classifier and portable OCR weights as the Windows release.
Its launchers are `scripts/macos-{setup,check,start,share}.command`.

The pinned setup targets Apple Silicon and Python 3.11. A Mac environment cannot
be copied to Windows. Setup needs internet for Python dependencies; included
model assets are reused. Inference works offline on the laptop, while the optional
phone tunnel needs internet. The saved capture database is
`output/fieldnote/macos-demo.sqlite3`.
