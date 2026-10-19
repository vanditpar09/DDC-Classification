"""Install/download no images: prepare official local OCR weights and Mac adapter."""
import argparse
import gc
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def prepare_portable():
    from prototype.portable_ocr import MODEL_DIR, MODELS, UPSTREAM, verify_models
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for row in MODELS.values():
        path = MODEL_DIR / row['name']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']:
            print('Ready: '+row['name'], flush=True)
            continue
        temporary = path.with_suffix('.download')
        print('Preparing portable OCR: '+row['name'], flush=True)
        try:
            with urllib.request.urlopen(row['source'], timeout=60) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != row['sha256']:
                raise RuntimeError('Downloaded OCR model checksum does not match upstream: '+row['name'])
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    (MODEL_DIR / 'manifest.json').write_text(json.dumps({'rapidocr_version':'3.4.0',
        'upstream_checksum_source': UPSTREAM, 'models': MODELS,
        'files': {row['name']:row['sha256'] for row in MODELS.values()}}, indent=2)+'\n', encoding='utf-8')
    verify_models()


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-vision', action='store_true')
    parser.add_argument('--reader', choices=('all', 'portable', 'easy'), default='all')
    args = parser.parse_args()
    if args.reader in {'all', 'portable'}:
        prepare_portable()
    if args.reader == 'portable':
        return
    model_dir = ROOT / 'models/ocr_easy'
    model_dir.mkdir(parents=True, exist_ok=True)
    if platform.system() == 'Darwin' and not args.skip_vision:
        compiler = shutil.which('swiftc')
        if not compiler:
            raise RuntimeError('swiftc is required for the optional Mac Vision adapter')
        source = ROOT / 'prototype/vision_ocr.swift'
        binary = ROOT / 'output/vision-ocr'
        binary.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([compiler, '-module-cache-path', str(ROOT / 'output/swift-module-cache'),
                        str(source), '-o', str(binary)], check=True)
        (ROOT / 'output/vision-ocr-source.sha256').write_text(hashlib.sha256(source.read_bytes()).hexdigest()+'\n')
    import torch
    import easyocr
    from prototype.easyocr_compat import configure_tamil
    configure_tamil()
    torch.set_num_threads(4)
    for languages in (['en'], ['en', 'hi', 'mr'], ['en', 'ta']):
        print('Preparing local OCR: ' + ', '.join(languages), flush=True)
        reader = easyocr.Reader(languages, gpu=False, model_storage_directory=str(model_dir),
                                user_network_directory=str(model_dir / 'user_network'),
                                download_enabled=True, verbose=False)
        del reader
        gc.collect()
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in model_dir.glob('*.pth')}
    (model_dir / 'manifest.json').write_text(json.dumps({'easyocr_version': easyocr.__version__,
        'official_source': 'https://github.com/JaidedAI/EasyOCR',
        'tamil_alphabet_fix':'https://github.com/JaidedAI/EasyOCR/pull/1333',
        'files': hashes}, indent=2)+'\n', encoding='utf-8')
    print('Local OCR models prepared; no book images were uploaded.', flush=True)


if __name__ == '__main__':
    run()
