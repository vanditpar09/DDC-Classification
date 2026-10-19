"""Run local OCR/inference on representative intake samples; not an accuracy test.

The page/section choices are documented in the report. Extracted text is kept as
raw OCR and must not be treated as a human-verified transcription or DDC label.
Run from the repository with its ML virtual environment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from prototype.controller import Policy
from prototype.engine import image_from_bytes, predict, recognize


def run(intake, output, with_predictions):
    inventory = json.loads((intake / 'inventory.json').read_text())
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for book in inventory['books']:
        source = Path(inventory['source_directory']) / book['file']
        if hashlib.sha256(source.read_bytes()).hexdigest() != book['source_sha256']:
            raise ValueError('Source book changed since intake: ' + book['file'])
        row = {'file': book['file'], 'source_sha256': book['source_sha256'],
               'expected_language': book['expected_language'],
               'ground_truth_ddc': None, 'accuracy': None}
        stem = source.stem
        text = ''
        if book['format'] == 'pdf':
            page = 15 if stem == 'ponniyin-selvan' else 10
            prefix = output / f'{stem}-page-{page}'
            subprocess.run(['pdftoppm', '-f', str(page), '-l', str(page), '-r', '200',
                            '-singlefile', '-png', str(source), str(prefix)],
                           check=True, capture_output=True, timeout=60)
            image_path = prefix.with_suffix('.png')
            language = 'eng+' + book['expected_language']
            row.update({'sample_source': 'rendered_pdf_page', 'pdf_page': page,
                        'dpi': 200, 'image_path': image_path.name,
                        'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
                        'ocr_language': language})
            try:
                result = recognize(image_from_bytes(image_path.read_bytes()), language, Policy(), allow_osd=False)
                text = result['text']
                row.update({'ocr_quality': result['quality'], 'ocr_work': result['work'],
                            'ocr_error': None, 'nonempty_ocr': bool(text.strip())})
            except ValueError as exc:
                row.update({'ocr_error': str(exc), 'nonempty_ocr': False})
        else:
            # Darwin's first chapter is spine item 4. Austen item 3 starts at
            # chapter XI, avoiding publisher introductions and licence text.
            ordinal = 4 if stem == 'pg1228-images-3' else 3
            sections = (intake / book['extracted_text']).read_text().split('\n\f\n')
            text = sections[ordinal - 1][:2500]
            row.update({'sample_source': 'epub_spine_text', 'spine_ordinal': ordinal,
                        'sample_limit_chars': 2500, 'nonempty_text': bool(text.strip())})
        sample_path = output / f'{stem}.raw-sample.txt'
        sample_path.write_text(text, encoding='utf-8')
        row.update({'raw_sample_path': sample_path.name, 'raw_sample_chars': len(text),
                    'sample_sha256': hashlib.sha256(sample_path.read_bytes()).hexdigest()})
        if with_predictions and text.strip():
            # A fixed bounded excerpt, with no subject metadata or DDC evidence.
            input_text = book['expected_title'] + '\n' + text[:2500]
            (output / f'{stem}.classifier-input.txt').write_text(input_text, encoding='utf-8')
            try:
                row['prediction'] = predict(input_text)
                row['prediction_error'] = None
            except Exception as exc:
                row['prediction_error'] = f'{type(exc).__name__}: {exc}'
        rows.append(row)
        (output / 'functional-smoke.json').write_text(json.dumps({
            'inventory_sha256': hashlib.sha256((intake / 'inventory.json').read_bytes()).hexdigest(),
            'samples': rows, 'complete': len(rows) == len(inventory['books']),
            'note': 'Functional test on book excerpts/rasterized PDFs only. No human-verified transcriptions or DDC labels, no training, no accuracy measurement, and no physical camera capture.'
        }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'file': book['file'], 'chars': len(text),
                          'prediction': row.get('prediction', {}).get('label'),
                          'error': row.get('prediction_error') or row.get('ocr_error')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intake', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--predict', action='store_true')
    args = parser.parse_args()
    run(args.intake, args.output, args.predict)
