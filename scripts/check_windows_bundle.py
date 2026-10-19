"""Extract the generated private bundle and check it independently of this checkout."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def run():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform',choices=('windows','macos'),default='windows')
    args=parser.parse_args()
    label='Windows' if args.platform=='windows' else 'macOS'
    archive_path=ROOT/f'output/releases/DDC-{label}.zip'
    with tempfile.TemporaryDirectory(prefix='ddc-demo-bundle-') as temporary:
        temporary=Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            names=archive.namelist()
            assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in names)
            archive.extractall(temporary)
        project=temporary/f'DDC-{label}'
        manifest=json.loads((project/'demo-bundle-manifest.json').read_text(encoding='utf-8'))
        for name,row in manifest.items():
            path=project/name
            assert path.stat().st_size==row['bytes']
            digest=hashlib.sha256()
            with path.open('rb') as handle:
                for chunk in iter(lambda:handle.read(1024*1024),b''):digest.update(chunk)
            assert digest.hexdigest()==row['sha256'],name
        result=subprocess.run([sys.executable,str(project/'scripts/check_windows_demo.py')],cwd=project,
            env={**os.environ,'PYTHONPYCACHEPREFIX':str(temporary/'python-cache'),'PYTHONIOENCODING':'utf-8'},
            capture_output=True,text=True,encoding='utf-8',timeout=180)
        destination=ROOT/'output/releases'
        prefix=label.lower()+'-'
        (destination/(prefix+'bundle-smoke.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:
            raise RuntimeError('Extracted demo did not pass; inspect output/windows-demo/bundle-smoke.log')
        report=json.loads((project/'output/windows-demo/offline-smoke.json').read_text(encoding='utf-8'))
        report['bundle_manifest_files_verified']=len(manifest)
        report['extracted_bundle_test']=True
        report['original_checkout_assets_used']=False
        (destination/(prefix+'bundle-smoke.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('PASS: extracted demo bundle, all file hashes, and offline four-image inference using bundled assets.')


if __name__=='__main__':run()
