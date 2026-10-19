"""Prepare reproducible development inputs from EPUBs and selected PDF pages.

No labels are read by this script. No fitting, verified references, or accuracy
measurement takes place. Native-only and English+native OCR are retained together
for human comparison; Tesseract confidence does not select a winner.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.research.intake_cleaning import VERSION, prepare_text, script_profile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def ocr(image, language):
    import pytesseract
    from PIL import Image
    start = time.perf_counter()
    config = f'--tessdata-dir "{ROOT / "models/ocr_tessdata"}" --oem 1 --psm 6'
    with Image.open(image) as img:
        data = pytesseract.image_to_data(img, lang=language, config=config,
                                        output_type=pytesseract.Output.DICT, timeout=30)
    lines = {}
    confidences = []
    for i, word in enumerate(data['text']):
        if not word.strip() or float(data['conf'][i]) < 0:
            continue
        confidences.append(float(data['conf'][i]))
        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        lines.setdefault(key, []).append(word.strip())
    return '\n'.join(' '.join(words) for words in lines.values()), {
        'language': language, 'psm': 6, 'oem': 1, 'osd': False,
        'seconds': time.perf_counter() - start, 'word_count': len(confidences),
        'mean_word_confidence': sum(confidences) / len(confidences) if confidences else None}


def save_sample(output, name, raw, language, excluded, pdf, gutenberg, metadata, predict):
    clean, audit = prepare_text(raw, excluded, pdf=pdf, gutenberg=gutenberg)
    raw_path = output / 'text' / (name + '.raw.txt')
    clean_path = output / 'text' / (name + '.clean.txt')
    raw_path.write_text(raw, encoding='utf-8')
    clean_path.write_text(clean, encoding='utf-8')
    audit_path = output / 'text' / (name + '.cleaning.json')
    write_json(audit_path, audit)
    sample = {**metadata, 'raw_text': str(raw_path.relative_to(output)), 'raw_sha256': sha(raw_path),
              'clean_text': str(clean_path.relative_to(output)), 'clean_sha256': sha(clean_path),
              'cleaning_audit': str(audit_path.relative_to(output)),
              'cleaning_audit_sha256': sha(audit_path),
              'script_diagnostic': script_profile(clean, language),
              'reference_text': None, 'nonempty': bool(clean), 'human_checked': False}
    if predict and clean:
        from prototype.engine import predict as classify
        # Body excerpts are NOT represented as covers or inserted in camera metrics.
        for variant, text in (('raw', raw), ('clean', clean)):
            input_text = text[:2500]
            input_path = output / 'text' / (name + '.' + variant + '.classifier-input.txt')
            input_path.write_text(input_text, encoding='utf-8')
            try:
                # Persist runtime warnings rather than flooding the console or
                # concealing them. Finite-probability validation stays enabled.
                with warnings.catch_warnings(record=True) as notices:
                    warnings.simplefilter('always', RuntimeWarning)
                    result = classify(input_text)
                sample[variant + '_runtime_warnings'] = sorted({str(w.message) for w in notices})
                sample[variant + '_prediction'] = result
            except Exception as exc:
                sample[variant + '_prediction_error'] = f'{type(exc).__name__}: {exc}'
            sample[variant + '_classifier_input'] = str(input_path.relative_to(output))
            sample[variant + '_classifier_input_sha256'] = sha(input_path)
    return sample


def run(intake, plan_path, output, with_predictions, source_directory=None):
    inventory_path = intake / 'inventory.json'
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    source_directory = Path(source_directory or inventory['source_directory'])
    by_file = {b['file']: b for b in inventory['books']}
    # Validate every source before creating output; refuse a changed intake.
    for entry in plan['books']:
        book = by_file[entry['file']]
        source = source_directory / book['file']
        if Path(book['file']).name != book['file'] or sha(source) != book['source_sha256']:
            raise ValueError('Source identity changed: ' + book['file'])
        if sha(intake / book['extracted_text']) != book['extracted_text_sha256']:
            raise ValueError('Extracted text changed: ' + book['file'])
        if entry['language'] != book['expected_language']:
            raise ValueError('Plan language differs from intake')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'text').mkdir()
    (output / 'images').mkdir()
    report = {'schema_version': 1, 'created_at': datetime.now(timezone.utc).isoformat(),
              'cleaning_version': VERSION, 'inventory_sha256': sha(inventory_path),
              'plan_sha256': sha(plan_path), 'complete': False, 'books': [],
              'note': 'Development-only text/OCR comparison. No labels, fitting, human reference transcriptions, OCR error rates, classification accuracy, or physical camera captures.'}
    write_json(output / 'page-plan.json', plan)
    for entry in plan['books']:
        book = by_file[entry['file']]
        source = source_directory / book['file']
        stem = source.stem
        row = {'file': book['file'], 'source_sha256': book['source_sha256'],
               'edition_id': 'local-' + book['source_sha256'][:16],
               'work_id': entry['work_id'], 'language': entry['language'],
               'partition': 'development', 'verified_section': None,
               'training_eligible': False, 'samples': []}
        excluded = entry.get('excluded_lines', [])
        if book['format'] == 'epub':
            from scripts.audit_multilingual_intake import epub
            _, sections = epub(source)
            for ordinal, (identifier, raw, error) in enumerate(sections, 1):
                name = f'{stem}-spine-{ordinal:02}'
                # All selected readable spine documents retain raw and clean text.
                # Covers/license/index remain out of classifier comparisons.
                eligible = ordinal in entry['diagnostic_spine_ordinals']
                sample = save_sample(output, name, raw, entry['language'], excluded, False, True,
                    {'origin': 'epub_text', 'source_id': identifier, 'spine_ordinal': ordinal,
                     'role': 'body' if eligible else 'other_spine', 'extraction_error': error},
                    with_predictions and eligible)
                sample['use_as_development_text'] = eligible and sample['nonempty']
                row['samples'].append(sample)
        else:
            for page in entry['pages']:
                ordinal = page['pdf_page']
                if not 1 <= ordinal <= book['pdf_pages']:
                    raise ValueError('PDF page outside source')
                prefix = output / 'images' / f'{stem}-page-{ordinal}'
                subprocess.run(['pdftoppm', '-f', str(ordinal), '-l', str(ordinal),
                                '-r', str(plan['dpi']), '-singlefile', '-png', str(source), str(prefix)],
                               check=True, capture_output=True, timeout=60)
                image_path = prefix.with_suffix('.png')
                for language in (entry['language'], 'eng+' + entry['language']):
                    name = f'{stem}-page-{ordinal}-{language.replace("+", "_")}'
                    metadata = {'origin': 'ocr_from_rendered_pdf', 'pdf_page': ordinal,
                                'role': page['role'], 'selection_note': page['selection_note'],
                                'image_path': str(image_path.relative_to(output)),
                                'image_sha256': sha(image_path), 'dpi': plan['dpi']}
                    try:
                        raw, work = ocr(image_path, language)
                        metadata.update(ocr=work, ocr_error=None)
                    except Exception as exc:
                        raw = ''
                        metadata.update(ocr={'language': language}, ocr_error=f'{type(exc).__name__}: {exc}')
                    sample = save_sample(output, name, raw, entry['language'], excluded, True, False,
                                         metadata, with_predictions)
                    row['samples'].append(sample)
        report['books'].append(row)
        write_json(output / 'preparation.json', report)
        print(json.dumps({'file': entry['file'], 'samples': len(row['samples']),
                          'failed_ocr': sum(bool(s.get('ocr_error')) for s in row['samples'])}), flush=True)
    report['complete'] = len(report['books']) == len(plan['books'])
    report['summary'] = {'books': len(report['books']),
        'ocr_samples': sum(s['origin'] == 'ocr_from_rendered_pdf' for b in report['books'] for s in b['samples']),
        'failed_ocr': sum(bool(s.get('ocr_error')) for b in report['books'] for s in b['samples']),
        'nonempty_ocr': sum(s['origin'] == 'ocr_from_rendered_pdf' and s['nonempty'] for b in report['books'] for s in b['samples']),
        'classifier_calls': sum(k.endswith('_prediction') for b in report['books'] for s in b['samples'] for k in s),
        'classifier_errors': sum(k.endswith('_prediction_error') for b in report['books'] for s in b['samples'] for k in s),
        'training_eligible_books': 0}
    write_json(output / 'preparation.json', report)
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('intake', type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--predict', action='store_true')
    parser.add_argument('--source', type=Path, help='Override original source directory on another machine; hashes must still match')
    args = parser.parse_args()
    run(args.intake, args.plan, args.output, args.predict, args.source)
