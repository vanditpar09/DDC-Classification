"""Fetch explicitly pinned public Tesseract language packs during setup only."""
import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = "87416418657359cb625c412a48b6e1d6d41c29bd"
PACKS = ("eng", "osd", "hin", "mar", "tam")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-tessdata", type=Path, help="Optionally copy installed eng/osd packs from this directory")
    args = parser.parse_args()
    directory = ROOT / "models/ocr_tessdata"
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {"repo": "tesseract-ocr/tessdata_fast", "revision": REVISION, "packs": {}}
    for pack in PACKS:
        path = directory / (pack + ".traineddata")
        if path.exists():
            source = "existing local pack (retained)"
        elif args.base_tessdata and pack in {"eng", "osd"}:
            source = str(args.base_tessdata / path.name)
            shutil.copyfile(source, path)
        else:
            source = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/{REVISION}/{path.name}"
            temporary = path.with_suffix(".download")
            try:
                with urllib.request.urlopen(source, timeout=60) as response, temporary.open("wb") as output:
                    shutil.copyfileobj(response, output)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        manifest["packs"][pack] = {"source": source, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        print(f"Ready: {pack}")
    (directory / "setup_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
