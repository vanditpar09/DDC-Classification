For both release downloads and a normal Git clone, start with [RUN_GUIDE.md](../RUN_GUIDE.md).

# Windows demo

Prepared 4 October 2026. The demo uses CPU inference and local model files. Apple
Vision is not required. Windows 10/11 on an x64 Intel/AMD laptop and Python 3.11
are the intended target; Windows ARM and older Windows versions are unverified.
Aim for at least 8 GB RAM, preferably 16 GB, and about 5 GB free space. This is a
planning estimate, not a measured Windows hardware requirement. No NVIDIA GPU is
required. Initial installation needs internet; laptop inference is offline.

## Move the project to the demo laptop

The locally prepared private package is `output/releases/DDC-Windows.zip`.
Copy it to the Windows laptop and extract it with **Extract All**. It contains
project code, the saved DDC classifier, its frozen multilingual encoder, OCR
models and four test images. It excludes the Mac `.venv`, user databases, tunnel
credentials and unrelated book files. The photo fixture is for this team's
private testing; its public redistribution status is not established.

If copying the repository instead, omit `.venv`. A Mac Python environment cannot
be reused on Windows. The setup restores public pretrained weights if missing;
it does not retrain the saved classifier. The `native_silver_v2/classifier.joblib`
artifact must be included with the project.

1. Install **64-bit Python 3.11** with the Python launcher. Official downloads:
   <https://www.python.org/downloads/windows/>.
2. Install Tesseract. Its official installation guide links the Windows builds:
   <https://tesseract-ocr.github.io/tessdoc/Installation.html>. The project detects
   `tesseract.exe` on PATH or under `Program Files\Tesseract-OCR`. For another
   location set `TESSERACT_CMD` to the complete executable path.
3. Install the [Microsoft Visual C++ x64 redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
   ONNX Runtime's Windows build requires this runtime; it may already be present.
4. Open `scripts\windows-setup.cmd`. Keep an internet connection for the initial
   package installation. This installs CPU Torch, prepares OCR packs/models,
   restores the pinned encoder and runs the offline test. Existing local weights
   are reused. The first setup can take several minutes.
5. Open `scripts\windows-start.cmd`. After the server starts, visit
   **http://127.0.0.1:8013** in Edge or Chrome. Keep that window open.

Windows command-line equivalents, from the project folder:

```bat
py -3.11 scripts\setup_windows_demo.py
.venv\Scripts\python.exe scripts\check_windows_demo.py
set FIELDNOTE_OCR=portable
set FIELDNOTE_DB=output/fieldnote/windows-demo.sqlite3
.venv\Scripts\python.exe -m prototype.run --port 8013 --model native_silver_v2
```

The launcher performs asset checks and fails clearly if the portable English
reader is not prepared; it cannot silently switch to Apple's reader. It saves
demo captures in `output/fieldnote/windows-demo.sqlite3`.
`requirements-windows.txt` records the dependency resolution for Windows x64 /
Python 3.11; CPU Torch/Torchvision are installed first from the official CPU
index. Dependency resolution passed locally, but is not proof of a Windows
installation or of Windows inference quality.

## Before the presentation

Run `scripts\windows-check.cmd`. It reads the real saved English cover and the
Hindi, Marathi and Tamil test pages, then checks that OCR and all three prediction
levels finish with network connections disabled. This test uses disposable
in-memory books and does not edit saved captures. Its report is
`output/windows-demo/offline-smoke.json`; it records the actual host OS, raw OCR,
reader, elapsed work and model fingerprint. It checks that the English title and
author are recovered and keyboard background text is absent. Native pages have
functional/readability checks, not independently transcribed accuracy scores.

Then test real camera photos of the intended demo books on that laptop. Front
covers alone often have little subject evidence: include a back cover or contents
page. Inspect title/author/text before judging the DDC suggestion. Avoid presenting
an unreviewed code as verified cataloging.

## Phone access

Install/connect ngrok on Windows using its official instructions at
<https://ngrok.com/docs/getting-started/>. With `windows-start.cmd` still running,
open `scripts\windows-share.cmd`. It prints the HTTPS phone link and the path to
`output/fieldnote/phone-access.txt`; enter that access code on the phone. Keep both
windows open and the laptop awake. Internet is needed for this tunnel, even
though OCR and classification stay local. Do not copy an old Mac tunnel token or
access code into the package. The gateway now avoids Unix-only `os.fchmod`.

## Readers and measurements

English portable mode uses RapidOCR 3.4.0, CPU ONNX Runtime 1.19.2, a PP-OCRv5
server detector/recognizer and a PP-OCRv4 line-orientation model. All model paths
are explicit; hashes are checked against pinned upstream values. An OFL Noto Sans
font is prepared locally because RapidOCR constructs visualization metadata even
when only reading text. Inference model/font downloads are explicitly blocked.

The reader retains original pixels. Detected page boundaries exclude background
lines; perspective resampling was worse on this decorative title. A 45-second
child-process timeout, image/detector size limits and the existing two-pass capture
reservation/six-pass book budget remain. OCR itself uses no title dictionary, book lookup or transcription correction.
A separate classification stage can match title and author against the local
catalog and supplies explicitly attributed source codes.

Hindi, Marathi and Tamil retain Tesseract with the existing EasyOCR repair
fallback. PP-OCR's English path is not sent Indian-script selections. This update
does not claim the failing physical Hindi cover has been fixed.

On this Mac, forced **portable** mode recovered “The Kite Runner”, “Khaled
Hosseini” and “A Thousand Splendid Suns”, and excluded the keyboard. A local
reader run took about 9 seconds, including process/model startup; this is not a
Windows latency measurement. The lighter PP-OCR English model still missed the
full title. Preserving source pixels was better than a rectified image. Raw
comparison records and offline/API/browser checks are saved in
`data/research/portable-ocr-v1/`.

These are development examples. No population-level OCR accuracy is established.
The original Mac Vision result remains available in `auto` mode; use
`FIELDNOTE_OCR=portable` to reproduce the Windows reader on Mac/Linux as well.

**DDC follow-up:** The Kite Runner now displays 800 → 810 → 813 using its
matched catalog record (source code 813.6). The raw learned prediction remains
recorded separately. Uncertain parents no longer generate unsupported precise
children. This is a classification pipeline correction, not retraining or a
population accuracy claim. See `data/research/ddc-capture-fix-v1/`.

## Native Windows verification

This implementation was exercised on macOS with Apple Vision disabled, including
an offline four-image run and real browser uploads. An actual Windows run has not
yet been performed. The setup/launcher is prepared, and the Windows smoke report
is the next required check before relying on the laptop for the presentation.
The optional manual GitHub workflow `Demo checks` performs setup and these
checks on a Windows runner after the files are committed/pushed; it was dispatched, but GitHub returned `startup_failure` before starting any
jobs and supplied no runner logs. This does not verify Windows execution. Run
`windows-check.cmd` on the intended demo laptop.

Primary sources: [RapidOCR's pinned model checksums](https://github.com/RapidAI/RapidOCR/blob/v3.4.0/python/rapidocr/default_models.yaml),
[RapidOCR](https://github.com/RapidAI/RapidOCR),
[ONNX Runtime CPU installation](https://onnxruntime.ai/docs/install/),
[Noto Sans OFL license](https://github.com/google/fonts/blob/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notosans/OFL.txt).
