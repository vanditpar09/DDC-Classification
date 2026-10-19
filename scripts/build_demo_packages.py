"""Build Windows and Mac archives from one source tree and shared local weights."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from build_windows_demo import ROOT, selected_files


def build(platform):
    label = 'Windows' if platform=='windows' else 'macOS'
    directory = ROOT/'output/releases'; directory.mkdir(parents=True,exist_ok=True)
    destination = directory/f'DDC-{label}.zip'
    files=set(selected_files())
    for name in ('README.md','RUN_GUIDE.md','requirements-macos.txt','data/books.jsonl','docs/MACOS_DEMO.md','docs/LAPTOP_SHARING.md','docs/CAPTURE_OUTPUTS.md','docs/PROVISIONAL_SCORES.md','docs/BOOK_IDENTITY_FIX.md',
                 'scripts/setup_demo.py','scripts/build_demo_packages.py','scripts/build_windows_demo.py',
                 'scripts/check_windows_bundle.py','scripts/build_catalog_index.py','scripts/export_capture_collection.py'):
        files.add(ROOT/name)
    files.update((ROOT/'data/catalog').glob('*.json'))
    files.update((ROOT/'data/research/ddc-capture-fix-v1').glob('*.md'))
    files.update((ROOT/'data/research/ddc-capture-fix-v1').glob('*.json'))
    for name in ('test_catalog.py','test_scene_ocr.py','test_windows_demo.py','test_collection_export.py','test_reclassify.py'):
        files.add(ROOT/'tests'/name)
    files.update((ROOT/'scripts').glob('macos-*.command'))
    # Include source licenses / model receipts where supplied by upstream/setup.
    for folder in ('models/ocr_rapid','models/ocr_easy','models/encoders/multilingual-e5-small'):
        for pattern in ('*LICENSE*','*OFL*','README.md'):
            files.update((ROOT/folder).glob(pattern))
    prefix=f'DDC-{label}'
    setup='scripts\\windows-setup.cmd' if platform=='windows' else 'scripts/macos-setup.command'
    start='scripts\\windows-start.cmd' if platform=='windows' else 'scripts/macos-start.command'
    arch='Windows 10/11 x64 (Intel/AMD)' if platform=='windows' else 'Apple Silicon Mac (M1 or newer)'
    instructions=f'''# Start the DDC demo — {label}

Same project as the other platform package; this download targets {arch}.

1. Extract this entire ZIP into a normal folder.
2. Install Python 3.11 and Tesseract following **RUN_GUIDE.md** in this folder.
   Windows also needs the Microsoft Visual C++ x64 runtime.
3. Run `{setup}` once with internet connected. Python dependencies are installed
   into a new local `.venv`; bundled model files are reused.
4. Run `{start}`, then open **http://127.0.0.1:8013**. Keep its window open.
5. For phone access, follow the sharing section in **RUN_GUIDE.md**.

These are project packages with model assets, not standalone executables. They
exclude saved captures, credentials and environments. See RUN_GUIDE.md for command
line equivalents, clone instructions, checks and troubleshooting.

Catalog results are explicitly sourced and still require edition review. Raw
model scores are separate. This package does not claim general DDC/OCR accuracy.
'''
    manifest={}
    temporary=destination.with_suffix('.building')
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
            for path in sorted(files):
                if not path.is_file():raise FileNotFoundError(path)
                name=path.relative_to(ROOT).as_posix()
                archive.write(path,f'{prefix}/{name}')
                digest=hashlib.sha256()
                with path.open('rb') as handle:
                    for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
                manifest[name]={'sha256':digest.hexdigest(),'bytes':path.stat().st_size}
            revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
            source={'git_revision':revision.stdout.strip() if revision.returncode==0 else None,
                    'platform':platform,'python':'3.11','classifier':'native_silver_v2',
                    'classification_policy':'catalog-assisted-v1','standalone_executable':False}
            archive.writestr(f'{prefix}/package-source.json',json.dumps(source,indent=2)+'\n')
            archive.writestr(f'{prefix}/START_HERE.md',instructions)
            archive.writestr(f'{prefix}/demo-bundle-manifest.json',json.dumps(manifest,indent=2)+'\n')
        temporary.replace(destination)
    finally:temporary.unlink(missing_ok=True)
    (directory/f'{label}-bundle-files.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Saved {destination} ({destination.stat().st_size/1024**2:.0f} MiB)',flush=True)
    return destination


def digest_file(path):
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform',choices=('windows','macos','both'),default='both')
    args=parser.parse_args()
    paths=[build(p) for p in (('windows','macos') if args.platform=='both' else (args.platform,))]
    (ROOT/'output/releases/SHA256SUMS.txt').write_text('\n'.join(
        digest_file(path)+'  '+path.name for path in paths)+'\n',encoding='utf-8')


if __name__=='__main__':run()
