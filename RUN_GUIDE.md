# Run the DDC research app

The current demo reads photos locally and suggests DDC class, division and section.
It uses the saved multilingual `native_silver_v2` model and a local bibliographic
index. A matched title **and** author can supply a catalog code; the interface
shows its source separately from model scores. Confirm the edition and code.
Uncertain model paths ask for more evidence. No Gemini/API key or training is
needed to run this app.

Latest source displays provisional model codes/scores even below review thresholds.
See [score interpretation](docs/PROVISIONAL_SCORES.md); a high conditional L3 score
does not establish full-path accuracy. Reload an older open page after updating.
For previously saved books, **Update prediction** uses the latest classifier and
catalog against saved text, retaining earlier results without another OCR pass.
See the [known-book correction](docs/BOOK_IDENTITY_FIX.md).

## Download a package or clone

Use the repository's **Releases** page while signed in to an account with access:
[DDC releases](https://github.com/abhinavnath02/DDC-Classification/releases).
Download `DDC-Windows.zip` or `DDC-macOS.zip`, extract the whole archive, and read
`START_HERE.md` inside. Both packages contain the same app, local model assets,
catalog and test images. They do not include an installed Python environment.
Initial dependency installation needs internet; ordinary laptop inference does not.

Alternatively, install Git and clone the **same** project:

```sh
git clone https://github.com/abhinavnath02/DDC-Classification.git
cd DDC-Classification
```

Private-repository access is required. The small trained classifier is committed;
the setup downloads the pinned public encoder and OCR weights when absent. Cloning
does not download the release ZIPs. Keep all files in the extracted/cloned folder.

## Windows 10/11, Intel or AMD x64

1. Install **64-bit Python 3.11**, including the Python launcher, from
   [python.org](https://www.python.org/downloads/windows/).
2. Install Tesseract using the Windows builds linked from the
   [Tesseract installation guide](https://tesseract-ocr.github.io/tessdoc/Installation.html).
   The usual `C:\Program Files\Tesseract-OCR` location is detected automatically.
3. Install the [Microsoft Visual C++ x64 runtime](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
   if not already present. This is needed by ONNX Runtime.
4. Double-click `scripts\windows-setup.cmd` once. Keep internet connected until it
   finishes; it installs CPU dependencies, prepares local weights and runs checks.
5. Double-click `scripts\windows-start.cmd` and open **http://127.0.0.1:8013**.
   Keep its window open. Stop the server with Ctrl+C.

Command Prompt equivalents, from the project folder:

```bat
py -3.11 scripts\setup_demo.py
.venv\Scripts\python.exe scripts\check_windows_demo.py
set FIELDNOTE_OCR=portable
set FIELDNOTE_DB=output/fieldnote/windows-demo.sqlite3
.venv\Scripts\python.exe -m prototype.run --port 8013 --model native_silver_v2
```

No GPU is required. Allow roughly 5 GB free space and preferably 16 GB RAM;
these are planning estimates, not minimum hardware benchmarks. Windows ARM is
not validated. See [Windows demo details](docs/WINDOWS_DEMO.md).

## macOS, Apple Silicon (M1 or newer)

Install native ARM Python 3.11 and Tesseract. With Homebrew installed:

```sh
brew install python@3.11 tesseract
python3.11 scripts/setup_demo.py
```

Then double-click `scripts/macos-start.command`, or run from Terminal:

```sh
FIELDNOTE_OCR=portable FIELDNOTE_DB=output/fieldnote/macos-demo.sqlite3 \
  .venv/bin/python -m prototype.run --port 8013 --model native_silver_v2
```

Open **http://127.0.0.1:8013**. Keep Terminal open. `macos-check.command` runs the
photo checks; `macos-share.command` starts phone sharing. If Finder cannot execute
a launcher, run `bash scripts/macos-start.command` from Terminal.

Both platforms use portable English OCR for comparable behavior. On Mac,
`FIELDNOTE_OCR=auto` optionally uses Apple's reader. This release's Torch 2.8
installation targets Apple Silicon; Intel Macs are not supported by this pinned
setup because upstream macOS Intel wheels stopped after Torch 2.2.
Do not copy `.venv` between machines. If setup finds an older/incompatible `.venv`,
rename it, then rerun setup; your saved captures live separately in `output/`.

## Test and use a phone

Run `windows-check.cmd` or `macos-check.command` before the demo. The offline smoke
checks English, Hindi, Marathi and Tamil images. The English regression checks
that *The Kite Runner* maps to **800 → 810 → 813 via a catalog match**. It does not
establish general DDC/OCR accuracy. Reports record the actual operating system.

Take a well-lit cover photo with title and author visible. Inspect extracted text,
then add a back cover or contents page if requested. For a known catalog match,
check the linked source and edition. Save manual review/corrections in the app.
Your captures and originals persist in the local SQLite file under `output/fieldnote/`.

### Phone camera testing with ngrok

This is already supported. Install/connect the ngrok CLI once on your laptop
following [the complete phone walkthrough](docs/LAPTOP_SHARING.md#start-test-the-app-on-a-phone-using-ngrok).
Keep the app running, then use a second terminal from the project folder:

Mac:

```sh
.venv/bin/python -m prototype.share --backend-port 8013
```

Windows Command Prompt:

```bat
.venv\Scripts\python.exe -m prototype.share --backend-port 8013
```

Or open `scripts/windows-share.cmd` / `scripts/macos-share.command`. These shortcuts
target app port 8013. If the app is running on the fresh test port 8017, use the
explicit command with **`--backend-port 8017`** instead.

Open the printed **HTTPS Phone link** in the phone browser. On the laptop, open
`output/fieldnote/phone-access.txt` and enter its contents in the phone login form.
Choose New book, select language/page type, then use the camera. Keep both terminal
windows open and the laptop awake and online. The phone may use Wi-Fi or mobile
data. Stop an older sharing launcher before starting a replacement. Closing the
app or tunnel stops classification from the phone; this is laptop-backed testing,
not a permanently hosted service.

## Where phone photos and results are saved

Choose **Results table** beside Saved books for a combined Book/L1/L2/L3 view and
CSV/JSON downloads. Successful phone uploads are saved on the laptop. The latest
source also writes a `<database-stem>-exports` folder beside the SQLite database,
with `classifications.html`, CSV/JSON, detailed records and full-resolution PNG
photo copies. See [capture outputs](docs/CAPTURE_OUTPUTS.md) for paths and recovery.
This addition is newer than the demo-2026-10-04 ZIPs; use the latest `main` source
for automatic readable exports.

## Troubleshooting

- **Python not found:** install Python 3.11; verify `py -3.11 --version` on Windows
  or `python3.11 --version` on Mac.
- **Tesseract not found:** install it, or set `TESSERACT_CMD` to its complete
  executable path (including `.exe` on Windows) before running setup/start.
- **Missing DLL:** install the Visual C++ x64 runtime above and rerun setup.
- **Page does not load:** start the server and open its HTTP address. Opening
  `prototype/static/index.html` directly does not start the API.
- **Address already in use:** stop the older server, or launch `prototype.run`
  with another `--port`; use that port with phone sharing too.
- **Pending photo:** keep it, reload the same phone link and press Retry uploads.
- **Old result:** reload the website. Existing saved books retain their original
  result; choose **Read photo again** or make a new capture to apply the update.

## Source checks and rebuilding packages

```sh
python -m pytest tests/test_catalog.py tests/test_scene_ocr.py tests/test_windows_demo.py prototype/test_persistence.py prototype/test_gateway.py -q
python scripts/build_catalog_index.py
python scripts/build_demo_packages.py --platform both
```

Use the virtual environment's Python. Generated ZIPs and model caches stay out of
Git; attach the ZIPs to a private GitHub release. The GitHub `Demo checks` workflow
runs the shared setup, offline photo checks and targeted tests on Windows and Mac.
The `Build demo packages` workflow prepares both ZIPs as downloadable workflow
artifacts from the same source revision. Download and attach them to a release.

The old cloud-assisted app at `src.api` is retained for historical experiments.
It uses root `requirements.txt`, separate older model setup and an optional Gemini
key. It is not the demo described here and should not be started accidentally.
